from __future__ import annotations

from collections import defaultdict
from typing import Any

from sqlalchemy.orm import Session

from app.models.veteran_intelligence import BenefitProgress, BenefitRegistry, VeteranProfile
from app.services.veteran_intelligence_service import DEFAULT_BENEFITS


CLAIMED_STATUSES = {"SUBMITTED", "APPROVED"}
UNLOCKED_STATUSES = {"APPROVED"}
FORECLOSURE_PREVENTION_BENEFITS = {
    "VA_FORECLOSURE_ASSISTANCE",
    "VA_IRRRL_REFINANCE",
}


def get_impact_summary(db: Session) -> dict[str, Any]:
    rows = _collect_case_impact_rows(db)
    return {
        "veterans_served": len(rows),
        "benefits_discovered": sum(r["benefits_discovered"] for r in rows),
        "benefits_claimed": sum(r["benefits_claimed"] for r in rows),
        "benefit_value_unlocked": round(sum(r["benefit_value_unlocked"] for r in rows), 2),
        "foreclosures_prevented": sum(1 for r in rows if r["foreclosure_prevented"]),
    }


def get_opportunity_map(db: Session) -> list[dict[str, Any]]:
    rows = _collect_case_impact_rows(db)
    grouped: dict[str, dict[str, Any]] = defaultdict(lambda: {
        "state": "UNKNOWN",
        "veterans_served": 0,
        "benefit_value_discovered": 0.0,
        "benefits_claimed": 0,
    })

    for row in rows:
        state = row["state"] or "UNKNOWN"
        node = grouped[state]
        node["state"] = state
        node["veterans_served"] += 1
        node["benefit_value_discovered"] += row["benefit_value_discovered"]
        node["benefits_claimed"] += row["benefits_claimed"]

    return sorted(
        [
            {
                **value,
                "benefit_value_discovered": round(value["benefit_value_discovered"], 2),
            }
            for value in grouped.values()
        ],
        key=lambda item: (item["benefit_value_discovered"], item["veterans_served"]),
        reverse=True,
    )


def _collect_case_impact_rows(db: Session) -> list[dict[str, Any]]:
    profiles = db.query(VeteranProfile).all()
    progresses = db.query(BenefitProgress).all()

    benefit_value_map = {row.benefit_name: float(row.estimated_value or 0.0) for row in db.query(BenefitRegistry).all()}
    for benefit in DEFAULT_BENEFITS:
        benefit_value_map.setdefault(benefit["benefit_name"], float(benefit.get("estimated_value") or 0.0))

    progress_by_case: dict[str, list[BenefitProgress]] = defaultdict(list)
    for progress in progresses:
        progress_by_case[str(progress.case_id)].append(progress)

    rows: list[dict[str, Any]] = []
    for profile in profiles:
        case_progress = progress_by_case.get(str(profile.case_id), [])
        discovered = len(case_progress)
        claimed = sum(1 for p in case_progress if p.status in CLAIMED_STATUSES)

        discovered_value = sum(benefit_value_map.get(p.benefit_name, 0.0) for p in case_progress)
        unlocked_value = sum(benefit_value_map.get(p.benefit_name, 0.0) for p in case_progress if p.status in UNLOCKED_STATUSES)

        foreclosure_prevented = bool(
            profile.foreclosure_risk
            and any(
                p.benefit_name in FORECLOSURE_PREVENTION_BENEFITS and p.status in CLAIMED_STATUSES
                for p in case_progress
            )
        )

        rows.append(
            {
                "state": profile.state_of_residence or "UNKNOWN",
                "benefits_discovered": discovered,
                "benefits_claimed": claimed,
                "benefit_value_discovered": discovered_value,
                "benefit_value_unlocked": unlocked_value,
                "foreclosure_prevented": foreclosure_prevented,
            }
        )

    return rows



def get_housing_summary(db: Session) -> dict[str, Any]:
    rows = _collect_case_impact_rows(db)
    total_value_discovered = sum(r["benefit_value_discovered"] for r in rows)
    homes_saved = sum(1 for r in rows if r["foreclosure_prevented"])
    homes_acquired = sum(1 for r in rows if r["benefits_claimed"] > 0 and r["benefit_value_discovered"] >= 25000)
    equity_preserved = round(total_value_discovered * 0.35, 2)
    homeowners_stabilized = sum(1 for r in rows if r["benefits_claimed"] > 0)

    return {
        "homes_saved": homes_saved,
        "homes_acquired": homes_acquired,
        "equity_preserved": equity_preserved,
        "portfolio_value": round(total_value_discovered, 2),
        "homeowners_stabilized": homeowners_stabilized,
    }
