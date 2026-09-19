"""
api.cleaning

    POST /api/runs/{run_id}/clean -> run the cleaning pipeline on this
                                      run's source data, store the
                                      result as a new run, return it

The real version of the prototype's "Execute DataScore Pipeline"
button - see services/cleaning_service.py for what it actually does
and why the scope is deliberately narrow.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.api.deps import get_current_user
from backend.db.session import get_db
from backend.models import User
from backend.schemas.analysis import AnalysisRunDetail
from backend.services.cleaning_service import NoRawData, RunNotFound, clean_run

router = APIRouter(prefix="/api", tags=["cleaning"])


@router.post("/runs/{run_id}/clean", response_model=AnalysisRunDetail)
def clean_run_route(
    run_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    try:
        return clean_run(db, current_user.organization_id, run_id)
    except RunNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except NoRawData as exc:
        raise HTTPException(status_code=400, detail=str(exc))
