from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.models.module_registry import ModuleRegistry
from app.services.module_loader_service import DomainServiceBroker


class PlatformKnowledgeService:
    def __init__(self, db: Session):
        self.db = db
        self._repo_root = Path(__file__).resolve().parents[2]

    def get_platform_overview(self) -> dict[str, Any]:
        return {
            "overview": self._load_doc_excerpt("docs/platform_operational_report.md", max_chars=2200),
            "architecture": self.get_architecture_summary(),
            "capabilities": self.get_capability_summary(),
        }

    def get_capability_summary(self) -> dict[str, Any]:
        return {
            "capability_report": self._load_doc_excerpt("docs/platform_capability_report.md", max_chars=1800),
            "domains": sorted(self._domain_service_registry().keys()),
        }

    def get_domain_capabilities(self, domain_name: str) -> dict[str, Any]:
        domain = (domain_name or "").strip().lower()
        registry = self._domain_service_registry()
        return {
            "domain": domain,
            "services": registry.get(domain, []),
            "known_domains": sorted(registry.keys()),
        }

    def get_architecture_summary(self) -> dict[str, Any]:
        return {
            "architecture_report": self._load_doc_excerpt("docs/platform_v1_architecture.md", max_chars=1800),
            "operational_report": self._load_doc_excerpt("docs/platform_operational_report.md", max_chars=1200),
        }

    def get_module_descriptions(self) -> list[dict[str, Any]]:
        modules = self.db.query(ModuleRegistry).order_by(ModuleRegistry.module_name.asc(), ModuleRegistry.version.desc()).all()
        descriptions: list[dict[str, Any]] = []
        for module in modules:
            descriptions.append(
                {
                    "module_name": module.module_name,
                    "version": module.version,
                    "status": module.status,
                    "is_active": bool(module.is_active),
                    "required_services": module.required_services or [],
                    "allowed_actions": module.allowed_actions or [],
                }
            )
        return descriptions

    def _domain_service_registry(self) -> dict[str, list[str]]:
        broker = DomainServiceBroker()
        domains: dict[str, set[str]] = {
            "system": {"ai_orchestration_service", "module_registry_service", "module_loader_service", "escalation_service"},
            "lead_intelligence": {"lead_intelligence_service"},
            "foreclosure_intelligence": {"foreclosure_intelligence_service", "property_analysis_service"},
            "skiptrace": {"skiptrace_service"},
            "essential_worker": {"essential_worker_housing_service"},
            "veteran_intelligence": {"veteran_intelligence_service"},
            "partner_routing": {"partner_routing_service"},
            "portfolio": {"property_portfolio_service"},
            "membership": {"membership_service"},
            "training": {"system_training_service"},
            "impact_analytics": {"impact_analytics_service", "platform_capability_service"},
        }

        for service in broker.allowed_services:
            if "veteran" in service:
                domains.setdefault("veteran_intelligence", set()).add(service)
            elif "foreclosure" in service or "property_analysis" in service:
                domains.setdefault("foreclosure_intelligence", set()).add(service)
            elif "portfolio" in service:
                domains.setdefault("portfolio", set()).add(service)
            elif "membership" in service:
                domains.setdefault("membership", set()).add(service)
            elif "ai_" in service:
                domains.setdefault("system", set()).add(service)

        return {key: sorted(value) for key, value in domains.items()}

    def _load_doc_excerpt(self, relative_path: str, *, max_chars: int = 1500) -> str:
        path = self._repo_root / relative_path
        if not path.exists():
            return f"{relative_path} not found"
        text = path.read_text(encoding="utf-8")
        text = " ".join(text.split())
        return text[:max_chars]
