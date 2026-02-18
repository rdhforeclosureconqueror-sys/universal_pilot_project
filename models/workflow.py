import enum
import uuid

from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Boolean, Enum, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from .base import Base


class WorkflowResponsibleRole(enum.Enum):
    operator = "operator"
    occupant = "occupant"
    system = "system"
    lender = "lender"


class WorkflowStepStatus(enum.Enum):
    pending = "pending"
    active = "active"
    blocked = "blocked"
    complete = "complete"


class WorkflowOverrideCategory(enum.Enum):
    data_correction = "data_correction"
    legal_exception = "legal_exception"
    executive_directive = "executive_directive"
    system_recovery = "system_recovery"


class WorkflowTemplate(Base):
    __tablename__ = "workflow_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    program_key = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    template_version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class WorkflowStep(Base):
    __tablename__ = "workflow_steps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_id = Column(UUID(as_uuid=True), ForeignKey("workflow_templates.id"), nullable=False, index=True)
    step_key = Column(String, nullable=False)
    display_name = Column(String, nullable=False)
    responsible_role = Column(Enum(WorkflowResponsibleRole), nullable=False)
    required_documents = Column(JSON, nullable=False, default=list)
    required_actions = Column(JSON, nullable=False, default=list)
    blocking_conditions = Column(JSON, nullable=False, default=list)
    kanban_column = Column(String, nullable=False)
    order_index = Column(Integer, nullable=False)
    auto_advance = Column(Boolean, nullable=False, default=False)
    sla_days = Column(Integer, nullable=False, default=30)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CaseWorkflowInstance(Base):
    __tablename__ = "case_workflow_instances"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False, unique=True, index=True)
    template_id = Column(UUID(as_uuid=True), ForeignKey("workflow_templates.id"), nullable=False, index=True)
    locked_template_version = Column(Integer, nullable=False, default=1)
    current_step_key = Column(String, nullable=False)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)


class CaseWorkflowProgress(Base):
    __tablename__ = "case_workflow_progress"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    instance_id = Column(UUID(as_uuid=True), ForeignKey("case_workflow_instances.id"), nullable=False, index=True)
    step_key = Column(String, nullable=False)
    status = Column(Enum(WorkflowStepStatus), nullable=False, default=WorkflowStepStatus.pending)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    block_reason = Column(String, nullable=True)


class WorkflowOverride(Base):
    __tablename__ = "workflow_overrides"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False, index=True)
    instance_id = Column(UUID(as_uuid=True), ForeignKey("case_workflow_instances.id"), nullable=False, index=True)
    from_step_key = Column(String, nullable=False)
    to_step_key = Column(String, nullable=False)
    reason_category = Column(Enum(WorkflowOverrideCategory), nullable=False)
    reason = Column(String, nullable=False)
    actor_id = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
