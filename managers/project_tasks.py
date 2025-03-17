import json
import logging
from db.database import SessionLocal
from db.models.search_history import SearchHistory
from services.serper_service import google_search
from app.celery_app import celery_app

logger = logging.getLogger(__name__)

@celery_app.task(name="managers.project_tasks.scheduled_search_task")
def scheduled_search_task(project_id: int, user_id: int, query: str, country="US", language="en", domain="google.com"):
    logger.info(f"[Celery Task] Start task: project_id={project_id}, user_id={user_id}, query='{query}'")
    results = {}
    try:
        results = google_search(query, country, language, domain)
        logger.info("Google search success")
    except Exception as e:
        logger.error(f"Error google_search: {e}")

    db = SessionLocal()
    try:
        entry = SearchHistory(
            project_id=project_id,
            user_id=user_id,
            query_text=query,
            results_json=json.dumps(results)
        )
        db.add(entry)
        db.commit()
        logger.info("[Celery Task] Result saved in SearchHistory.")
    except Exception as e:
        logger.error(f"[Celery Task] Error saving SearchHistory: {e}")
        db.rollback()
    finally:
        db.close()
