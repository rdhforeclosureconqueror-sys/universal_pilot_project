from datetime import datetime, timedelta
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.session import get_db
from models.botops import (
    BotSetting,
    BotReport,
    BotCommand,
    BotTrigger,
    BotInboundLog,
    BotPage,
    Lead,
)
from schemas.botops import (
    BotSettingUpsert,
    BotReportCreate,
    BotReportRead,
    BotCommandCreate,
    BotCommandRead,
    BotTriggerCreate,
    BotTriggerRead,
    BotInboundLogCreate,
    BotInboundLogRead,
    BotPageCreate,
    BotPageRead,
    LeadUpsert,
    LeadRead,
)

router = APIRouter(prefix="/botops", tags=["BotOps"])


def _lead_id_or_uuid(lead_id: str | None) -> str:
    return lead_id or f"lead-{uuid4().hex[:12]}"


@router.get("/dashboard")
def botops_dashboard(limit: int = 200, hours: int = 24, db: Session = Depends(get_db)):
    since = datetime.utcnow() - timedelta(hours=hours)
    reports = (
        db.query(BotReport)
        .filter(BotReport.created_at >= since)
        .order_by(BotReport.created_at.desc())
        .limit(limit)
        .all()
    )
    commands = (
        db.query(BotCommand)
        .order_by(BotCommand.created_at.desc())
        .limit(limit)
        .all()
    )
    triggers = db.query(BotTrigger).order_by(BotTrigger.id.desc()).limit(limit).all()
    leads = db.query(Lead).order_by(Lead.created_at.desc()).limit(limit).all()
    return {
        "reports": [
            {
                "id": str(r.id),
                "created_at": r.created_at,
                "bot": r.bot,
                "level": r.level,
                "code": r.code,
                "message": r.message,
                "details_json": r.details_json,
            }
            for r in reports
        ],
        "commands": [
            {
                "id": str(c.id),
                "created_at": c.created_at,
                "target_bot": c.target_bot,
                "command": c.command,
                "args_json": c.args_json,
                "priority": c.priority,
                "status": c.status,
                "notes": c.notes,
            }
            for c in commands
        ],
        "triggers": [
            {
                "id": str(t.id),
                "enabled": t.enabled,
                "metric": t.metric,
                "operator": t.operator,
                "threshold": t.threshold,
                "priority": t.priority,
                "target_bot": t.target_bot,
                "command": t.command,
                "args_json": t.args_json,
            }
            for t in triggers
        ],
        "leads": [
            {
                "id": str(l.id),
                "lead_id": l.lead_id,
                "source": l.source,
                "address": l.address,
                "city": l.city,
                "state": l.state,
                "zip": l.zip,
                "status": l.status,
                "score": l.score,
                "created_at": l.created_at,
                "updated_at": l.updated_at,
            }
            for l in leads
        ],
    }


@router.get("/settings")
def list_settings(db: Session = Depends(get_db)):
    settings = db.query(BotSetting).order_by(BotSetting.key.asc()).all()
    return [{"key": s.key, "value": s.value, "updated_at": s.updated_at} for s in settings]


@router.post("/settings")
def upsert_setting(payload: BotSettingUpsert, db: Session = Depends(get_db)):
    setting = db.query(BotSetting).filter(BotSetting.key == payload.key).first()
    if setting:
        setting.value = payload.value
    else:
        setting = BotSetting(key=payload.key, value=payload.value)
        db.add(setting)
    db.commit()
    return {"key": setting.key, "value": setting.value}


@router.get("/reports", response_model=list[BotReportRead])
def list_reports(limit: int = 200, db: Session = Depends(get_db)):
    return (
        db.query(BotReport)
        .order_by(BotReport.created_at.desc())
        .limit(limit)
        .all()
    )


@router.post("/reports", response_model=BotReportRead)
def create_report(payload: BotReportCreate, db: Session = Depends(get_db)):
    report = BotReport(**payload.model_dump())
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


@router.get("/commands", response_model=list[BotCommandRead])
def list_commands(limit: int = 200, db: Session = Depends(get_db)):
    return (
        db.query(BotCommand)
        .order_by(BotCommand.created_at.desc())
        .limit(limit)
        .all()
    )


@router.post("/commands", response_model=BotCommandRead)
def create_command(payload: BotCommandCreate, db: Session = Depends(get_db)):
    command = BotCommand(**payload.model_dump())
    db.add(command)
    db.commit()
    db.refresh(command)
    return command


@router.get("/triggers", response_model=list[BotTriggerRead])
def list_triggers(limit: int = 200, db: Session = Depends(get_db)):
    return db.query(BotTrigger).order_by(BotTrigger.id.desc()).limit(limit).all()


@router.post("/triggers", response_model=BotTriggerRead)
def create_trigger(payload: BotTriggerCreate, db: Session = Depends(get_db)):
    trigger = BotTrigger(**payload.model_dump())
    db.add(trigger)
    db.commit()
    db.refresh(trigger)
    return trigger


@router.get("/inbound", response_model=list[BotInboundLogRead])
def list_inbound(limit: int = 200, db: Session = Depends(get_db)):
    return (
        db.query(BotInboundLog)
        .order_by(BotInboundLog.created_at.desc())
        .limit(limit)
        .all()
    )


@router.post("/inbound", response_model=BotInboundLogRead)
def create_inbound(payload: BotInboundLogCreate, db: Session = Depends(get_db)):
    inbound = BotInboundLog(**payload.model_dump())
    db.add(inbound)
    db.commit()
    db.refresh(inbound)
    return inbound


@router.get("/pages", response_model=list[BotPageRead])
def list_pages(limit: int = 200, db: Session = Depends(get_db)):
    return db.query(BotPage).order_by(BotPage.id.desc()).limit(limit).all()


@router.post("/pages", response_model=BotPageRead)
def create_page(payload: BotPageCreate, db: Session = Depends(get_db)):
    page = BotPage(**payload.model_dump())
    db.add(page)
    db.commit()
    db.refresh(page)
    return page


@router.get("/leads", response_model=list[LeadRead])
def list_leads(limit: int = 200, db: Session = Depends(get_db)):
    return db.query(Lead).order_by(Lead.created_at.desc()).limit(limit).all()


@router.post("/leads/upsert", response_model=list[LeadRead])
def upsert_leads(payload: list[LeadUpsert], db: Session = Depends(get_db)):
    results = []
    for lead_payload in payload:
        data = lead_payload.model_dump()
        lead_id = _lead_id_or_uuid(data.pop("lead_id", None))
        lead = db.query(Lead).filter(Lead.lead_id == lead_id).first()
        if lead:
            for key, value in data.items():
                setattr(lead, key, value)
        else:
            lead = Lead(lead_id=lead_id, **data)
            db.add(lead)
        results.append(lead)
    db.commit()
    for lead in results:
        db.refresh(lead)
    return results


@router.get("/leads/{lead_id}", response_model=LeadRead)
def get_lead(lead_id: str, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.lead_id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead
