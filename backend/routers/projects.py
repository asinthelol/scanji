import json

from fastapi import APIRouter, HTTPException

from ..schemas import Project, ProjectCreate
from ..storage import create_project, delete_project, list_projects, load_project, save_project

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("")
def list_all():
    return list_projects()


@router.post("", status_code=201)
def create(req: ProjectCreate):
    title = req.title.strip()
    if not title:
        raise HTTPException(400, "Project name is required")
    return {"id": create_project(title), "title": title}


@router.get("/{pid}")
def get_project(pid: str):
    return load_project(pid)


@router.put("/{pid}")
def put_project(pid: str, p: Project):
    data = json.loads(p.model_dump_json())
    data["title"] = load_project(pid)["title"]  # the name is fixed at creation
    save_project(pid, data)
    return {"ok": True}


@router.delete("/{pid}")
def delete(pid: str):
    delete_project(pid)
    return {"ok": True}
