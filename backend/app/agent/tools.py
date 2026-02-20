from __future__ import annotations

import json
import asyncio
from pathlib import Path

from app.models.project import Project, ProjectState
from app.services import git as git_svc
from app.services import docker as docker_svc
from app.services import project as project_svc
from app.generator.scaffold import scaffold_project


async def _run_shell(command: str, cwd: Path) -> dict:
    proc = await asyncio.create_subprocess_shell(
        command,
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
    except asyncio.TimeoutError:
        proc.kill()
        return {"stdout": "", "stderr": "Command timed out", "returncode": 1}
    return {
        "stdout": stdout.decode(errors="replace"),
        "stderr": stderr.decode(errors="replace"),
        "returncode": proc.returncode,
    }


async def execute_tool(
    project: Project,
    tool_name: str,
    arguments: dict,
) -> str:
    """Execute a tool and return the result as a string."""
    project_dir = project.directory

    try:
        if tool_name == "read_file":
            file_path = project_dir / arguments["path"]
            if not file_path.exists():
                return f"Error: File not found: {arguments['path']}"
            return file_path.read_text()

        elif tool_name == "write_file":
            file_path = project_dir / arguments["path"]
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(arguments["content"])
            return f"Written: {arguments['path']}"

        elif tool_name == "edit_file":
            file_path = project_dir / arguments["path"]
            if not file_path.exists():
                return f"Error: File not found: {arguments['path']}"
            content = file_path.read_text()
            old_text = arguments["old_text"]
            if old_text not in content:
                return f"Error: old_text not found in {arguments['path']}"
            new_content = content.replace(old_text, arguments["new_text"], 1)
            file_path.write_text(new_content)
            return f"Edited: {arguments['path']}"

        elif tool_name == "list_directory":
            dir_path = project_dir / arguments.get("path", ".")
            if not dir_path.exists():
                return f"Error: Directory not found: {arguments.get('path', '.')}"
            entries = sorted(dir_path.iterdir())
            return "\n".join(
                f"{'[dir] ' if e.is_dir() else ''}{e.name}" for e in entries
            )

        elif tool_name == "run_command":
            result = await _run_shell(arguments["command"], project_dir)
            parts = []
            if result["stdout"]:
                parts.append(f"stdout:\n{result['stdout']}")
            if result["stderr"]:
                parts.append(f"stderr:\n{result['stderr']}")
            parts.append(f"exit code: {result['returncode']}")
            return "\n".join(parts)

        elif tool_name == "git_commit":
            commit_hash = await git_svc.git_commit(project_dir, arguments["message"])
            return f"Committed: {commit_hash}"

        elif tool_name == "git_log":
            log = await git_svc.git_log(project_dir)
            if not log:
                return "No commits yet."
            return "\n".join(f"{e['hash']} {e['message']}" for e in log)

        elif tool_name == "docker_compose_up":
            project.state = ProjectState.BUILDING
            await project_svc.update_project(project)
            ok, output = await docker_svc.compose_up(project_dir)
            if ok:
                project.state = ProjectState.RUNNING
                project.swagger_url = f"http://localhost:{project.app_port}/docs"
                project.api_url = f"http://localhost:{project.app_port}"
                await project_svc.update_project(project)
                return (
                    f"SUCCESS: Containers started and running.\n"
                    f"API URL: http://localhost:{project.app_port}\n"
                    f"Swagger UI: http://localhost:{project.app_port}/docs\n\n"
                    f"IMPORTANT: Now call build_complete with swagger_url="
                    f"\"http://localhost:{project.app_port}/docs\" and api_url="
                    f"\"http://localhost:{project.app_port}\". "
                    f"Do NOT test with curl. Call build_complete NOW."
                )
            else:
                project.state = ProjectState.ERROR
                await project_svc.update_project(project)
                return f"Docker compose up failed:\n{output[-2000:]}"

        elif tool_name == "docker_compose_down":
            ok, output = await docker_svc.compose_down(project_dir)
            project.state = ProjectState.STOPPED
            await project_svc.update_project(project)
            return "Containers stopped." if ok else f"Error: {output[-1000:]}"

        elif tool_name == "docker_status":
            status = await docker_svc.compose_status(project_dir)
            return json.dumps(status, indent=2)

        elif tool_name == "docker_logs":
            service = arguments.get("service", "")
            logs = await docker_svc.compose_logs(project_dir, service=service)
            return logs[-3000:] if logs else "No logs available."

        elif tool_name == "scaffold_project":
            scaffold_project(project)
            await git_svc.git_init(project_dir)
            await git_svc.git_commit(project_dir, "Initial scaffold from template")
            project.state = ProjectState.SCAFFOLDED
            await project_svc.update_project(project)
            return "Project scaffolded and initial commit created."

        elif tool_name == "build_complete":
            project.swagger_url = arguments["swagger_url"]
            project.api_url = arguments["api_url"]
            project.state = ProjectState.RUNNING
            await project_svc.update_project(project)
            return "Build marked as complete."

        elif tool_name == "ask_user":
            return "__ASK_USER__"

        elif tool_name == "check_spec_completeness":
            from app.agent.state import ProjectSpec

            spec_json = arguments.get("spec_json", "{}")
            try:
                spec_data = json.loads(spec_json)
                spec = ProjectSpec.from_dict(spec_data)
                missing = spec.missing_fields()
                return json.dumps({"complete": len(missing) == 0, "missing": missing})
            except Exception as e:
                return f"Error parsing spec: {e}"

        elif tool_name == "finalize_spec":
            spec_json = arguments.get("spec_json", "{}")
            return f"__FINALIZE_SPEC__{spec_json}"

        elif tool_name == "submit_plan":
            manifest_json = arguments.get("manifest_json", "[]")
            return f"__SUBMIT_PLAN__{manifest_json}"

        else:
            return f"Unknown tool: {tool_name}"

    except Exception as e:
        return f"Error executing {tool_name}: {e}"
