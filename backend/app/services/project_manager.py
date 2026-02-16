import asyncio
import shutil
from pathlib import Path

from app.config import settings
from app.services.template_engine import TemplateEngine


class ProjectManager:
    def __init__(self):
        self.base_dir = Path(settings.projects_base_dir)
        self.template_engine = TemplateEngine()

    def get_project_dir(self, project_id: str) -> Path:
        return self.base_dir / project_id

    async def scaffold_project(self, project_id: str, project_name: str) -> None:
        """Create project directory, render templates, init git."""
        project_dir = self.get_project_dir(project_id)
        project_dir.mkdir(parents=True, exist_ok=True)

        # Render scaffold templates
        safe_name = project_name.lower().replace(" ", "_").replace("-", "_")
        config = {
            "project_name": safe_name,
            "db_name": f"{safe_name}_db",
            "db_user": "postgres",
            "db_password": "postgres",
            "app_port": 8000,
            "host_port": await self._allocate_port(),
        }
        await self.template_engine.render_scaffold(project_dir, config)

        # Init git
        await self._run_in_dir(project_dir, "git", "init")
        await self._run_in_dir(project_dir, "git", "add", "-A")
        await self._run_in_dir(
            project_dir, "git", "commit", "-m", "Initial scaffold"
        )

    async def delete_project(self, project_id: str) -> None:
        """Stop containers and remove project directory."""
        project_dir = self.get_project_dir(project_id)

        # Try to stop containers first
        try:
            await self._run_in_dir(project_dir, "docker", "compose", "down", "-v")
        except Exception:
            pass

        if project_dir.exists():
            shutil.rmtree(project_dir)

    async def _allocate_port(self) -> int:
        """Simple sequential port allocation starting from 8080."""
        base_port = 8080
        existing = list(self.base_dir.iterdir()) if self.base_dir.exists() else []
        return base_port + len(existing)

    async def _run_in_dir(self, cwd: Path, *cmd: str) -> str:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(cwd),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(
                f"Command failed: {' '.join(cmd)}\n{stderr.decode()}"
            )
        return stdout.decode()
