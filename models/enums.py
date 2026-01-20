import enum

class CaseStatus(enum.Enum):
    intake_submitted = "intake_submitted"
    intake_incomplete = "intake_incomplete"
    under_review = "under_review"
    in_progress = "in_progress"
    program_completed_positive_outcome = "program_completed_positive_outcome"
    case_closed_other_outcome = "case_closed_other_outcome"

class DocumentType(enum.Enum):
    id_verification = "id_verification"
    income_verification = "income_verification"
    lease_or_mortgage = "lease_or_mortgage"
    foreclosure_notice = "foreclosure_notice"
    eviction_notice = "eviction_notice"
    signed_consent = "signed_consent"
    taskcheck_evidence = "taskcheck_evidence"
    training_proof = "training_proof"
    system_doc = "system_doc"
    other = "other"

class ReferralStatus(enum.Enum):
    draft = "draft"
    queued = "queued"
    sent = "sent"
    failed = "failed"
    cancelled = "cancelled"
