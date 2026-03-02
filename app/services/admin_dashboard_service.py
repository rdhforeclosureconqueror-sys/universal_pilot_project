from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.schemas.admin_dashboard import (
    AdminMembershipDetailResponse,
    AdminMembershipListResponse,
    AdminMembershipRow,
)


BASE_LIST_SQL = """
WITH latest_stability AS (
    SELECT DISTINCT ON (sa.user_id, sa.program_key)
        sa.user_id,
        sa.program_key,
        sa.stability_score,
        sa.created_at
    FROM stability_assessments sa
    ORDER BY sa.user_id, sa.program_key, sa.created_at DESC
), installment_counts AS (
    SELECT
        mi.membership_id,
        COUNT(*) FILTER (WHERE mi.status = 'missed') AS missed_installments_count,
        COUNT(*) FILTER (WHERE mi.status = 'due') AS due_installments_count
    FROM membership_installments mi
    GROUP BY mi.membership_id
), activity AS (
    SELECT
        m.id AS membership_id,
        GREATEST(
            COALESCE(max(mi.paid_at), to_timestamp(0)),
            COALESCE(max(cc.created_at), to_timestamp(0)),
            COALESCE(max(mc.created_at), to_timestamp(0)),
            COALESCE(max(d.uploaded_at), to_timestamp(0)),
            COALESCE(max(tqa.created_at), to_timestamp(0))
        ) AS last_activity_at
    FROM memberships m
    LEFT JOIN membership_installments mi ON mi.membership_id = m.id
    LEFT JOIN contribution_credits cc ON cc.membership_id = m.id
    LEFT JOIN member_checkins mc ON mc.membership_id = m.id
    LEFT JOIN cases c ON c.created_by = m.user_id AND c.program_key = m.program_key
    LEFT JOIN documents d ON d.case_id = c.id
    LEFT JOIN training_quiz_attempts tqa ON tqa.user_id = m.user_id
    GROUP BY m.id
)
SELECT
    m.id AS membership_id,
    m.user_id,
    u.email,
    u.full_name,
    m.program_key,
    m.status::text AS status,
    m.good_standing,
    m.term_start,
    m.term_end,
    m.created_at,
    ls.stability_score AS latest_stability_score,
    ls.created_at AS latest_stability_at,
    COALESCE(ic.missed_installments_count, 0) AS missed_installments_count,
    COALESCE(ic.due_installments_count, 0) AS due_installments_count,
    a.last_activity_at
FROM memberships m
LEFT JOIN users u ON u.id = m.user_id
LEFT JOIN latest_stability ls ON ls.user_id = m.user_id AND ls.program_key = m.program_key
LEFT JOIN installment_counts ic ON ic.membership_id = m.id
LEFT JOIN activity a ON a.membership_id = m.id
WHERE 1=1
"""


def _fetch_memberships(
    db: Session,
    where_clause: str,
    params: dict,
    limit: int,
    offset: int,
) -> AdminMembershipListResponse:
    sql = BASE_LIST_SQL + where_clause + " ORDER BY m.created_at DESC LIMIT :limit OFFSET :offset"
    rows = db.execute(text(sql), {**params, "limit": limit, "offset": offset}).mappings().all()
    items = [AdminMembershipRow(**dict(row)) for row in rows]
    return AdminMembershipListResponse(items=items, limit=limit, offset=offset)


def list_memberships(
    db: Session,
    program_key: str | None = None,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> AdminMembershipListResponse:
    where = ""
    params: dict = {}
    if program_key:
        where += " AND m.program_key = :program_key"
        params["program_key"] = program_key
    if status:
        where += " AND m.status::text = :status"
        params["status"] = status
    return _fetch_memberships(db, where, params, limit, offset)


def memberships_below_stability(
    db: Session,
    threshold: int = 65,
    program_key: str | None = None,
    status: str = "active",
    limit: int = 100,
    offset: int = 0,
) -> AdminMembershipListResponse:
    where = " AND COALESCE(ls.stability_score, 70) < :threshold"
    params: dict = {"threshold": threshold}
    if program_key:
        where += " AND m.program_key = :program_key"
        params["program_key"] = program_key
    if status:
        where += " AND m.status::text = :status"
        params["status"] = status
    return _fetch_memberships(db, where, params, limit, offset)


def memberships_with_missed_installments(
    db: Session,
    program_key: str | None = None,
    status: str = "active",
    limit: int = 100,
    offset: int = 0,
) -> AdminMembershipListResponse:
    where = " AND COALESCE(ic.missed_installments_count, 0) > 0"
    params: dict = {}
    if program_key:
        where += " AND m.program_key = :program_key"
        params["program_key"] = program_key
    if status:
        where += " AND m.status::text = :status"
        params["status"] = status
    return _fetch_memberships(db, where, params, limit, offset)


def get_membership_detail(db: Session, membership_id: UUID) -> AdminMembershipDetailResponse:
    membership_payload = _fetch_memberships(
        db,
        " AND m.id = :membership_id",
        {"membership_id": str(membership_id)},
        limit=1,
        offset=0,
    )
    if not membership_payload.items:
        raise HTTPException(status_code=404, detail="Membership not found")

    membership = membership_payload.items[0]

    installments = db.execute(
        text(
            """
            SELECT id, due_date, amount_cents, status::text AS status, paid_at, notes, created_at
            FROM membership_installments
            WHERE membership_id = :membership_id
            ORDER BY due_date ASC
            LIMIT 12
            """
        ),
        {"membership_id": str(membership_id)},
    ).mappings().all()

    stability_history = db.execute(
        text(
            """
            SELECT id, stability_score, risk_level, breakdown_json, created_at
            FROM stability_assessments
            WHERE user_id = :user_id AND program_key = :program_key
            ORDER BY created_at DESC
            LIMIT 5
            """
        ),
        {"user_id": str(membership.user_id), "program_key": membership.program_key},
    ).mappings().all()

    checkins = db.execute(
        text(
            """
            SELECT id, type::text AS type, notes, created_at
            FROM member_checkins
            WHERE membership_id = :membership_id
            ORDER BY created_at DESC
            LIMIT 10
            """
        ),
        {"membership_id": str(membership_id)},
    ).mappings().all()

    credits = db.execute(
        text(
            """
            SELECT id, credit_type::text AS credit_type, amount_cents_equivalent, installment_id, evidence_document_id, created_at
            FROM contribution_credits
            WHERE membership_id = :membership_id
            ORDER BY created_at DESC
            LIMIT 10
            """
        ),
        {"membership_id": str(membership_id)},
    ).mappings().all()

    workflow = db.execute(
        text(
            """
            SELECT cwi.id AS instance_id, cwi.current_step_key, ws.display_name AS current_step_label
            FROM case_workflow_instances cwi
            JOIN cases c ON c.id = cwi.case_id
            LEFT JOIN workflow_steps ws
                ON ws.template_id = cwi.template_id
               AND ws.step_key = cwi.current_step_key
            WHERE c.created_by = :user_id
              AND c.program_key = :program_key
            ORDER BY c.created_at DESC
            LIMIT 1
            """
        ),
        {"user_id": str(membership.user_id), "program_key": membership.program_key},
    ).mappings().first()

    return AdminMembershipDetailResponse(
        membership=membership,
        installments=[dict(r) for r in installments],
        stability_history=[dict(r) for r in stability_history],
        member_checkins=[dict(r) for r in checkins],
        contribution_credits=[dict(r) for r in credits],
        workflow=dict(workflow) if workflow else None,
    )
