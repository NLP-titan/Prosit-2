import asyncio
import json
import logging
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)


class DockerManager:
    def __init__(self):
        self.base_dir = Path(settings.projects_base_dir)

    def _project_dir(self, project_id: str) -> Path:
        return self.base_dir / project_id

    def _docker_compose_cmd(self, project_id: str) -> list[str]:
        """Build the docker compose command prefix.
        We simply point to the compose file; Docker Compose resolves `build: .`
        relative to the compose file location, reads the context from the
        container filesystem, and sends it to the Docker daemon."""
        compose_file = str(self._project_dir(project_id) / "docker-compose.yml")
        return ["docker", "compose", "-f", compose_file]

    async def build_and_start(self, project_id: str) -> dict:
        """Run docker compose up --build -d."""
        project_dir = self._project_dir(project_id)
        cmd = self._docker_compose_cmd(project_id) + ["up", "--build", "-d"]
        logger.info(f"Starting containers: {' '.join(cmd)} (cwd={project_dir})")
        stdout, stderr, code = await self._run(project_dir, *cmd)
        logger.info(f"Docker build result: code={code}, stdout={stdout[:500]}, stderr={stderr[:500]}")

        if code != 0:
            return {"status": "error", "message": stderr}

        # Get the mapped port
        status = await self.get_status(project_id)
        logger.info(f"Container status after start: {status}")
        port = None
        for service in status.get("services", []):
            if "api" in service.get("name", ""):
                port = service.get("port")
                break

        return {
            "status": "running",
            "port": port,
            "swagger_url": f"http://localhost:{port}/docs" if port else None,
            "output": stdout + stderr,
        }

    async def stop(self, project_id: str) -> dict:
        """Run docker compose down."""
        project_dir = self._project_dir(project_id)
        cmd = self._docker_compose_cmd(project_id) + ["down"]
        stdout, stderr, code = await self._run(project_dir, *cmd)
        return {"status": "stopped", "output": stdout + stderr}

    async def get_status(self, project_id: str) -> dict:
        """Get container status."""
        project_dir = self._project_dir(project_id)
        cmd = self._docker_compose_cmd(project_id) + ["ps", "--format", "json"]
        stdout, stderr, code = await self._run(project_dir, *cmd)

        if code != 0:
            return {"status": "error", "services": []}

        services = []
        # docker compose ps --format json may output:
        # - a JSON array (newer docker compose): [{"Service":...}, ...]
        # - one JSON object per line (older versions): {"Service":...}\n{"Service":...}
        containers = []
        stripped = stdout.strip()
        if not stripped:
            return {"status": "ok", "services": []}

        try:
            parsed = json.loads(stripped)
            if isinstance(parsed, list):
                containers = parsed
            elif isinstance(parsed, dict):
                containers = [parsed]
        except json.JSONDecodeError:
            # Fallback: try line-by-line parsing
            for line in stripped.split("\n"):
                line = line.strip()
                if not line:
                    continue
                try:
                    containers.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

        for container in containers:
            port = None
            publishers = container.get("Publishers", [])
            if publishers:
                for pub in publishers:
                    published = pub.get("PublishedPort", 0)
                    if published and published > 0:
                        port = published
                        break

            services.append(
                {
                    "name": container.get("Service", ""),
                    "state": container.get("State", ""),
                    "status": container.get("Status", ""),
                    "port": port,
                }
            )

        return {"status": "ok", "services": services}

    async def get_logs(self, project_id: str, tail: int = 100) -> dict:
        """Get container logs."""
        project_dir = self._project_dir(project_id)
        cmd = self._docker_compose_cmd(project_id) + [
            "logs", "--tail", str(tail), "--no-color",
        ]
        stdout, stderr, code = await self._run(project_dir, *cmd)
        return {"logs": stdout + stderr}

    async def _run(
        self, cwd: Path, *cmd: str, timeout: int = 120
    ) -> tuple[str, str, int]:
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(cwd),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
            return stdout.decode(), stderr.decode(), proc.returncode
        except asyncio.TimeoutError:
            proc.kill()
            return "", "Command timed out", 1
        except FileNotFoundError:
            return "", f"Command not found: {cmd[0]}", 1
