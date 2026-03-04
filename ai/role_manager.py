from __future__ import annotations

from enum import Enum


class AIRole(str, Enum):
    READ = "READ"
    OPERATE = "OPERATE"
    STRUCTURE = "STRUCTURE"
    INFRA = "INFRA"


def user_ai_role(user) -> AIRole:
    role_value = getattr(getattr(user, "role", None), "value", None) or str(getattr(user, "role", "") or "")
    if role_value == "admin":
        return AIRole.INFRA
    if role_value == "ai_policy_chair":
        return AIRole.STRUCTURE
    if role_value in {"case_worker", "referral_coordinator"}:
        return AIRole.OPERATE
    return AIRole.READ


def authorize(required_role: AIRole, provided_role: AIRole) -> bool:
    rank = {
        AIRole.READ: 1,
        AIRole.OPERATE: 2,
        AIRole.STRUCTURE: 3,
        AIRole.INFRA: 4,
    }
    return rank[provided_role] >= rank[required_role]
