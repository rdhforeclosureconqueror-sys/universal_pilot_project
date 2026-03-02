from sqlalchemy import (
    Column,
    String,
    DateTime,
    Integer,
    Boolean,
    JSON,
    Float,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from .base import Base


class BotSetting(Base):
    __tablename__ = "bot_settings"

    key = Column(String, primary_key=True)
    value = Column(String, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class BotReport(Base):
    __tablename__ = "bot_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    bot = Column(String, nullable=False)
    level = Column(String, nullable=False)
    code = Column(String, nullable=True)
    message = Column(String, nullable=False)
    details_json = Column(JSON, nullable=True)


class BotCommand(Base):
    __tablename__ = "bot_commands"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    target_bot = Column(String, nullable=False)
    command = Column(String, nullable=False)
    args_json = Column(JSON, nullable=True)
    priority = Column(Integer, nullable=False, default=10)
    status = Column(String, nullable=True)
    notes = Column(String, nullable=True)


class BotTrigger(Base):
    __tablename__ = "bot_triggers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    enabled = Column(Boolean, nullable=False, default=True)
    metric = Column(String, nullable=False)
    operator = Column(String, nullable=False, default=">=")
    threshold = Column(Float, nullable=False, default=0)
    priority = Column(Integer, nullable=False, default=10)
    target_bot = Column(String, nullable=False)
    command = Column(String, nullable=False)
    args_json = Column(JSON, nullable=True)


class BotInboundLog(Base):
    __tablename__ = "bot_inbound_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    source_bot = Column(String, nullable=False)
    payload_hash = Column(String, nullable=True)
    type = Column(String, nullable=True)
    status = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    raw_json = Column(JSON, nullable=True)


class BotPage(Base):
    __tablename__ = "bot_pages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    url = Column(String, nullable=False)
    status = Column(String, nullable=True)
    last_crawl = Column(DateTime(timezone=True), nullable=True)
    title = Column(String, nullable=True)
    notes = Column(String, nullable=True)
