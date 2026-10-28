import json

from fastapi import APIRouter

from ..schemas import Project
from ..storage import load_project, save_project

router = APIRouter(prefix="/api/project", tags=["project"])


@router.get("")
def get_project():
    return load_project()


@router.put("")
def put_project(p: Project):
    save_project(json.loads(p.model_dump_json()))
    return {"ok": True}
