from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from db.database import get_db
from db.models.telegram_user import TelegramUser
from db.models.project_member import ProjectMember
from db.models.project import Project

router = APIRouter()

@router.get("/bot/find_user_by_chat_id")
def find_user_by_chat_id(chat_id: str, db: Session = Depends(get_db)):
    user = db.query(TelegramUser).filter_by(chat_id=chat_id).first()
    if not user:
        return {"error": "not found"}
    return {"id": user.id, "chat_id": user.chat_id}

@router.post("/bot/register_user")
def register_user(chat_id: str, db: Session = Depends(get_db)):
    user = db.query(TelegramUser).filter_by(chat_id=chat_id).first()
    if not user:
        user = TelegramUser(chat_id=chat_id)
        db.add(user)
        db.commit()
        db.refresh(user)
    return {"id": user.id, "chat_id": user.chat_id}

@router.get("/users/{user_id}/projects")
def get_user_projects(user_id: int, db: Session = Depends(get_db)):
    pm_list = db.query(ProjectMember).filter_by(user_id=user_id).all()
    project_ids = [pm.project_id for pm in pm_list]
    projects = db.query(Project).filter(Project.id.in_(project_ids)).all()
    output = []
    for p in projects:
        output.append({"id": p.id, "name": p.name})
    return output
