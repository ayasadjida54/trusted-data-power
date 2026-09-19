"""
api.reports

Authenticated (org-scoped, same as api/datasets.py):
    GET    /api/runs/{run_id}/report.pdf  -> downloadable PDF report
    GET    /api/runs/{run_id}/report.csv  -> downloadable CSV findings export
    POST   /api/runs/{run_id}/share       -> create (or return existing) share link
    DELETE /api/runs/{run_id}/share       -> revoke the share link

Public, no auth required - anyone with the token can view/download:
    GET /api/public/reports/{token}            -> the run's full detail, as JSON
    GET /api/public/reports/{token}/report.pdf -> the same PDF report

A run with no share token behaves identically to an unrecognized token
(404) - there's no way to tell "not shared" from "wrong token" from the
outside, which is the point.
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from backend.api.deps import get_current_user
from backend.db.session import get_db
from backend.models import AnalysisRun, Dataset, User
from backend.schemas.analysis import AnalysisRunDetail, ShareResponse
from backend.services.report_csv import build_csv_report
from backend.services.report_pdf import build_pdf_report
from backend.services.share_service import (
    RunNotFound,
    get_or_create_share_token,
    get_run_by_share_token,
    revoke_share,
)

router = APIRouter(prefix="/api", tags=["reports"])
public_router = APIRouter(prefix="/api/public", tags=["public-reports"])


def _get_owned_run(db: Session, run_id: int, organization_id: int) -> AnalysisRun:
    run = (
        db.query(AnalysisRun)
        .join(Dataset)
        .filter(AnalysisRun.id == run_id, Dataset.organization_id == organization_id)
        .first()
    )
    if run is None:
        raise HTTPException(status_code=404, detail="Analysis run not found.")
    return run


@router.get("/runs/{run_id}/report.pdf")
def download_pdf_report(
    run_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    run = _get_owned_run(db, run_id, current_user.organization_id)
    pdf_bytes = build_pdf_report(run)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{run.filename}-report.pdf"'},
    )


@router.get("/runs/{run_id}/report.csv")
def download_csv_report(
    run_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    run = _get_owned_run(db, run_id, current_user.organization_id)
    csv_text = build_csv_report(run)
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{run.filename}-findings.csv"'},
    )


@router.post("/runs/{run_id}/share", response_model=ShareResponse)
def create_share_link(
    run_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    try:
        token = get_or_create_share_token(db, current_user.organization_id, run_id)
    except RunNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return ShareResponse(share_token=token, share_path=f"/public/reports/{token}")


@router.delete("/runs/{run_id}/share", status_code=204)
def delete_share_link(
    run_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    try:
        revoke_share(db, current_user.organization_id, run_id)
    except RunNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@public_router.get("/reports/{token}", response_model=AnalysisRunDetail)
def get_public_report(token: str, db: Session = Depends(get_db)):
    run = get_run_by_share_token(db, token)
    if run is None:
        raise HTTPException(status_code=404, detail="This report link is invalid or has been revoked.")
    return run


@public_router.get("/reports/{token}/report.pdf")
def download_public_pdf_report(token: str, db: Session = Depends(get_db)):
    run = get_run_by_share_token(db, token)
    if run is None:
        raise HTTPException(status_code=404, detail="This report link is invalid or has been revoked.")
    pdf_bytes = build_pdf_report(run)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{run.filename}-report.pdf"'},
    )
