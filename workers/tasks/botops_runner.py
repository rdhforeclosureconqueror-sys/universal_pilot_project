import hashlib
import logging
from datetime import datetime

from sqlalchemy.orm import Session

from db.session import SessionLocal
from ingestion.dallas.public_records import fetch_public_records
from app.models.botops import BotCommand, BotReport, BotSetting, Lead
from workers.celery_worker import celery_app

logger = logging.getLogger(__name__)


def _get_setting(db: Session, key: str) -> str | None:
    setting = db.query(BotSetting).filter(BotSetting.key == key).first()
    return setting.value if setting else None


def _make_lead_id(address: str, zip_code: str, source: str) -> str:
    basis = f"{address}|{zip_code}|{source}".lower().encode("utf-8")
    digest = hashlib.sha256(basis).hexdigest()[:12]
    return f"lead-{digest}"


def _log_report(db: Session, bot: str, level: str, code: str, message: str, details: dict) -> None:
    report = BotReport(
        bot=bot,
        level=level,
        code=code,
        message=message,
        details_json=details,
    )
    db.add(report)


@celery_app.task(bind=True, max_retries=2)
def run_botops_commands(self):
    db: Session = SessionLocal()
    try:
        commands = (
            db.query(BotCommand)
            .filter(BotCommand.target_bot == "CrawlerBot", BotCommand.status.is_(None))
            .order_by(BotCommand.created_at.asc())
            .all()
        )
        if not commands:
            return

        for command in commands:
            command.status = "processing"
            db.commit()

            if command.command == "CRAWL_DALLAS_PUBLIC_RECORDS":
                url = (command.args_json or {}).get("url") or _get_setting(
                    db, "DALLAS_PUBLIC_RECORDS_URL"
                )
                if not url:
                    command.status = "failed"
                    _log_report(
                        db,
                        "CrawlerBot",
                        "error",
                        "CRAWLER-NO-URL",
                        "Missing Dallas public records URL",
                        {"command_id": str(command.id)},
                    )
                    db.commit()
                    continue

                try:
                    records = fetch_public_records(url)
                    upserted = 0
                    for record in records:
                        lead_id = _make_lead_id(record.address, record.zip, record.source)
                        lead = db.query(Lead).filter(Lead.lead_id == lead_id).first()
                        if not lead:
                            lead = Lead(
                                lead_id=lead_id,
                                source=record.source,
                                address=record.address,
                                city=record.city,
                                state=record.state,
                                zip=record.zip,
                                status=record.status,
                                notes=None,
                            )
                            db.add(lead)
                        else:
                            lead.address = record.address
                            lead.city = record.city
                            lead.state = record.state
                            lead.zip = record.zip
                            lead.status = record.status
                            lead.source = record.source
                        upserted += 1

                    command.status = "done"
                    _log_report(
                        db,
                        "CrawlerBot",
                        "info",
                        "CRAWLER-SUCCESS",
                        "Dallas public records crawled",
                        {"command_id": str(command.id), "records": upserted},
                    )
                    db.commit()
                except Exception as exc:
                    db.rollback()
                    command.status = "failed"
                    _log_report(
                        db,
                        "CrawlerBot",
                        "error",
                        "CRAWLER-FAIL",
                        "Dallas public records crawl failed",
                        {"command_id": str(command.id), "error": str(exc)},
                    )
                    db.commit()
            else:
                command.status = "skipped"
                _log_report(
                    db,
                    "CrawlerBot",
                    "warn",
                    "CRAWLER-UNKNOWN",
                    "Unsupported command",
                    {"command_id": str(command.id), "command": command.command},
                )
                db.commit()
    finally:
        db.close()
