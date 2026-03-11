from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ModuleSpec(BaseModel):
    module_name: str = Field(min_length=1, max_length=120)
    module_type: str = Field(min_length=1, max_length=64)
    version: str = Field(default="1.0.0", min_length=1, max_length=32)

    permissions: list[str] = Field(default_factory=list)
    required_services: list[str] = Field(default_factory=list)
    data_schema: dict[str, Any] = Field(default_factory=dict)
    allowed_actions: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class ModuleRegistryRead(ModuleSpec):
    id: str
    status: str
    policy_validation_status: str
    is_active: bool
    validation_errors: list[str] | None = None
    activated_at: str | None = None

    model_config = ConfigDict(from_attributes=True)
