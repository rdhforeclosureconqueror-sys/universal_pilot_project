# foreclosure_policy_module.py

FORECLOSURE_POLICY = {
    "version": "v1.0.0",
    "program_key": "foreclosure_stabilization_v1",
    "states": [
        "intake_submitted",
        "intake_incomplete",
        "under_review",
        "stabilization_active",
        "rehab_in_progress",
        "exit_ready",
        "program_completed_positive_outcome",
        "case_closed_other_outcome",
    ],
    "invariants": [
        "no_outcome_without_evidence",
        "no_discretion_without_audit",
        "no_payment_escalation_from_rehabilitation",
        "no_extraction_through_complexity",
        "no_graduation_without_completion",
    ],
    "required_evidence": {
        "intake": [
            "identity_verification",
            "foreclosure_notice",
            "occupancy_confirmation",
            "signed_consent"
        ],
        "stabilization": [
            "leaseback_agreement",
            "payment_compliance_records",
            "responsibility_acknowledgment"
        ],
        "exit": [
            "refinance_offer_or_buyback_docs",
            "rehab_reconciliation_record"
        ]
    },
    "rehab": {
        "lifecycle_states": [
            "rehab_planned",
            "rehab_funded",
            "rehab_in_progress",
            "rehab_completed",
            "rehab_verified",
            "rehab_reconciled"
        ],
        "classification_types": {
            "ERL": "External Rehab Loan",
            "PFDR": "Program-Funded Deferred Recovery",
            "SER": "Shared Equity Rehabilitation"
        },
        "prohibited_structures": [
            "compounding_rehab_interest",
            "rehab_triggered_payment_increase",
            "automatic_conversion_to_rent_or_debt",
            "indefinite_equity_claims",
            "undocumented_scope_or_recovery_terms"
        ]
    },
    "exit_conditions": {
        "allowed_exit_types": [
            "refinance",
            "buyback",
            "voluntary_sale",
            "program_termination"
        ],
        "graduation_criteria": [
            "occupancy_compliance_met",
            "rehab_verified",
            "exit_docs_recorded",
            "no_unresolved_audit_flags"
        ]
    },
    "audit_reason_codes": [
        "stabilization_started",
        "rehab_classified",
        "rehab_progress_logged",
        "rehab_completed",
        "exit_ready_confirmed",
        "program_completed_positive_outcome",
        "policy_violation_detected",
        "pfdr_authorized",
        "pfdr_disbursed",
        "rehab_milestone_completed",
        "shared_equity_active",
        "cdfi_review_granted",
        "refinance_decision_logged"
    ],
    "pfdr": {
        "label": "PFDR_ACTIVE",
        "allowed_uses": [
            "code_compliance",
            "health_safety_remediation",
            "structural_repairs",
            "foreclosure_cure_costs"
        ],
        "excluded_uses": [
            "cosmetic_upgrades",
            "cash_to_occupant",
            "unrelated_operating_expenses"
        ],
        "recovery_events": [
            "refinance",
            "sale",
            "program_exit"
        ]
    },
    "shared_equity": {
        "label": "SHARED_EQUITY_ACTIVE",
        "eligibility": [
            "stabilization_active",
            "leaseback_executed",
            "equity_participation_signed",
            "pfdr_recorded"
        ],
        "caps": {
            "appreciation_share": "capped",
            "duration": "non-perpetual",
            "transferable": False
        },
        "extinguishment": [
            "refinance",
            "buyback",
            "exit_event"
        ]
    },
    "cdfi_interface": {
        "visible_when": [
            "exit_ready",
            "pfdr_complete",
            "shared_equity_active",
            "all_docs_complete",
            "min_performance_window_met"
        ],
        "outputs": [
            "readiness_packet",
            "compliance_score",
            "payment_history",
            "rehab_evidence"
        ]
    }
}
