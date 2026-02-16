from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Project, generate_uuid
from app.services.project_manager import ProjectManager

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


class CreateProjectRequest(BaseModel):
    name: str
    description: str = ""


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: str
    status: str
    docker_port: int | None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


@router.post("", response_model=ProjectResponse)
async def create_project(
    body: CreateProjectRequest, session: AsyncSession = Depends(get_session)
):
    project_id = generate_uuid()
    project = Project(
        id=project_id,
        name=body.name,
        description=body.description,
        status="idle",
    )
    session.add(project)
    await session.commit()
    await session.refresh(project)

    # Scaffold the project directory
    pm = ProjectManager()
    await pm.scaffold_project(project_id, body.name)

    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        status=project.status,
        docker_port=project.docker_port,
        created_at=project.created_at.isoformat(),
        updated_at=project.updated_at.isoformat(),
    )


@router.get("", response_model=list[ProjectResponse])
async def list_projects(session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Project).order_by(Project.created_at.desc())
    )
    projects = result.scalars().all()
    return [
        ProjectResponse(
            id=p.id,
            name=p.name,
            description=p.description,
            status=p.status,
            docker_port=p.docker_port,
            created_at=p.created_at.isoformat(),
            updated_at=p.updated_at.isoformat(),
        )
        for p in projects
    ]


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, session: AsyncSession = Depends(get_session)):
    project = await session.get(Project, project_id)
    if not project:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        status=project.status,
        docker_port=project.docker_port,
        created_at=project.created_at.isoformat(),
        updated_at=project.updated_at.isoformat(),
    )


@router.delete("/{project_id}")
async def delete_project(project_id: str, session: AsyncSession = Depends(get_session)):
    project = await session.get(Project, project_id)
    if not project:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Project not found")

    pm = ProjectManager()
    await pm.delete_project(project_id)

    await session.delete(project)
    await session.commit()
    return {"status": "deleted"}
