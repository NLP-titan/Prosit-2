from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Project
from app.services.docker_manager import DockerManager

router = APIRouter(prefix="/api/v1/docker", tags=["docker"])


@router.post("/{project_id}/start")
async def start_containers(
    project_id: str, session: AsyncSession = Depends(get_session)
):
    project = await session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    dm = DockerManager()
    result = await dm.build_and_start(project_id)

    if result.get("port"):
        project.docker_port = result["port"]
        project.status = "running"
        await session.commit()

    return result


@router.post("/{project_id}/stop")
async def stop_containers(
    project_id: str, session: AsyncSession = Depends(get_session)
):
    project = await session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    dm = DockerManager()
    result = await dm.stop(project_id)

    project.status = "idle"
    project.docker_port = None
    await session.commit()

    return result


@router.get("/{project_id}/status")
async def get_container_status(project_id: str):
    dm = DockerManager()
    return await dm.get_status(project_id)


@router.get("/{project_id}/logs")
async def get_container_logs(project_id: str, tail: int = 100):
    dm = DockerManager()
    return await dm.get_logs(project_id, tail=tail)
