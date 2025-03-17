from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, validator
from typing import Optional
import json
from typing import List
from datetime import datetime
from sqlalchemy.orm import Session
from db.database import get_db
from db.models.project import Project
from db.models.project_member import ProjectMember
from db.models.telegram_user import TelegramUser
from db.models.search_history import SearchHistory
from services.serper_service import google_search

from sqlalchemy_celery_beat.models import PeriodicTask, IntervalSchedule, ClockedSchedule, PeriodicTaskChanged

router = APIRouter()


class ProjectCreateSchema(BaseModel):
    name: str


class ProjectAddMembersSchema(BaseModel):
    usernames: List[str]


class SearchRequest(BaseModel):
    query: str
    country: str = "US"
    language: str = "en"
    domain: str = "google.com"
    user_id: int


# api/routes/project_routes.py

class ScheduleData(BaseModel):
    user_id: int
    query: str
    schedule_type: str
    date_time: Optional[str] = None
    interval_seconds: Optional[int] = None
    country: str = "US"
    language: str = "en"
    domain: str = "google.com"

    @validator("schedule_type")
    def check_schedule_type(cls, v):
        if v not in {"clocked", "interval"}:
            raise ValueError("schedule_type must be 'clocked' or 'interval'")
        return v

    @validator("date_time", always=True)
    def check_date_time(cls, v, values):
        if values.get("schedule_type") == "clocked":
            if not v:
                raise ValueError("date_time is required for clocked schedule")
            try:
                datetime.fromisoformat(v)
            except Exception:
                raise ValueError("date_time must be in ISO format or 'YYYY-MM-DD HH:MM'")
        return v

    @validator("interval_seconds", always=True)
    def check_interval(cls, v, values):
        if values.get("schedule_type") == "interval":
            if v is None or v <= 0:
                raise ValueError("interval_seconds must be a positive integer for interval schedule")
        return v


@router.post("/projects/create")
def create_project(schema: ProjectCreateSchema, user_id: int, db: Session = Depends(get_db)):
    user = db.query(TelegramUser).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    project = Project(name=schema.name, creator_id=user.id)
    db.add(project)
    db.commit()
    db.refresh(project)

    pm = ProjectMember(project_id=project.id, user_id=user.id, role="admin")
    db.add(pm)
    db.commit()
    return {"project_id": project.id, "name": project.name}


@router.post("/projects/{project_id}/add_members")
def add_members(project_id: int, schema: ProjectAddMembersSchema, db: Session = Depends(get_db)):
    project = db.query(Project).filter_by(id=project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    added = []
    for username in schema.usernames:
        name_str = username.lstrip("@")
        user = db.query(TelegramUser).filter_by(chat_id=name_str).first()
        if not user:
            continue
        pm = db.query(ProjectMember).filter_by(project_id=project_id, user_id=user.id).first()
        if pm:
            continue
        new_pm = ProjectMember(project_id=project_id, user_id=user.id, role="member")
        db.add(new_pm)
        added.append(user.chat_id)
    db.commit()
    return {"added": added}


@router.post("/projects/{project_id}/search")
def project_search(project_id: int, req: SearchRequest, db: Session = Depends(get_db)):
    pm = db.query(ProjectMember).filter_by(project_id=project_id, user_id=req.user_id).first()
    if not pm:
        raise HTTPException(status_code=403, detail="User not in project")

    results = google_search(req.query, req.country, req.language, req.domain)
    entry = SearchHistory(
        project_id=project_id,
        user_id=req.user_id,
        query_text=req.query,
        results_json=json.dumps(results)
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return {"ok": True, "entry_id": entry.id, "results": results}


@router.get("/projects/{project_id}/history")
def get_history(project_id: int, db: Session = Depends(get_db)):
    items = db.query(SearchHistory).filter_by(project_id=project_id) \
        .order_by(SearchHistory.created_at.desc()).all()
    output = []
    for h in items:
        output.append({
            "id": h.id,
            "query_text": h.query_text,
            "created_at": str(h.created_at)
        })
    return output


@router.get("/projects/{project_id}/history/{item_id}")
def get_history_item(project_id: int, item_id: int, db: Session = Depends(get_db)):
    item = db.query(SearchHistory).filter_by(project_id=project_id, id=item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    return {
        "id": item.id,
        "query_text": item.query_text,
        "created_at": str(item.created_at),
        "results": item.results_json
    }


class ScheduleData(BaseModel):
    user_id: int
    query: str
    schedule_type: str
    date_time: str = None
    interval_seconds: int = None
    country: str = "US"
    language: str = "en"
    domain: str = "google.com"


@router.post("/projects/{project_id}/schedule")
def schedule_search(project_id: int, data: ScheduleData, db: Session = Depends(get_db)):
    pm = db.query(ProjectMember).filter_by(project_id=project_id, user_id=data.user_id).first()
    if not pm:
        raise HTTPException(status_code=403, detail="User not in project")

    if data.schedule_type == "clocked":
        try:
            scheduled_dt = datetime.fromisoformat(data.date_time)
        except Exception as e:
            raise HTTPException(status_code=400, detail="Invalid date_time format")
        schedule_obj = db.query(ClockedSchedule).filter_by(clocked_time=scheduled_dt).first()
        if not schedule_obj:
            schedule_obj = ClockedSchedule(clocked_time=scheduled_dt)
            db.add(schedule_obj)
            db.commit()
            db.refresh(schedule_obj)
        one_off = True
    else:  # interval
        schedule_obj = db.query(IntervalSchedule).filter_by(every=data.interval_seconds, period="seconds").first()
        if not schedule_obj:
            schedule_obj = IntervalSchedule(every=data.interval_seconds, period="seconds")
            db.add(schedule_obj)
            db.commit()
            db.refresh(schedule_obj)
        one_off = False

    task_name = f"project_search_{project_id}_{data.user_id}_{data.query[:10]}"
    task = db.query(PeriodicTask).filter_by(name=task_name).first()
    if not task:
        task = PeriodicTask(
            name=task_name,
            task="managers.project_tasks.scheduled_search_task",
            one_off=one_off,
            enabled=True
        )
        db.add(task)

    task.kwargs = json.dumps({
        "project_id": project_id,
        "user_id": data.user_id,
        "query": data.query,
        "country": data.country,
        "language": data.language,
        "domain": data.domain
    })
    task.schedule_model = schedule_obj
    task.start_time = datetime.utcnow()
    db.commit()
    db.refresh(task)
    PeriodicTaskChanged.update_from_session(db)
    return {"scheduled": True, "message": f"The request is scheduled with the type {data.schedule_type}"}