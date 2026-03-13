from __future__ import annotations


def calculate_equity(*, estimated_property_value: float, loan_balance: float) -> float:
    return round(float(estimated_property_value or 0) - float(loan_balance or 0), 2)


def calculate_ltv(*, loan_balance: float, estimated_property_value: float) -> float:
    value = float(estimated_property_value or 0)
    if value <= 0:
        return 0.0
    return round((float(loan_balance or 0) / value) * 100, 2)


def calculate_rescue_score(*, arrears_amount: float, homeowner_income: float, foreclosure_stage: str) -> float:
    stage = (foreclosure_stage or "").lower()
    stage_boost = {"pre_foreclosure": 20, "notice_of_default": 35, "auction_scheduled": 50, "post_sale": 70}.get(stage, 15)
    income = float(homeowner_income or 0)
    arrears = float(arrears_amount or 0)
    distress = 0 if income <= 0 else min(30, (arrears / max(income, 1)) * 10)
    return round(min(100.0, stage_boost + distress), 2)


def calculate_acquisition_score(*, equity: float, ltv: float, foreclosure_stage: str) -> float:
    stage = (foreclosure_stage or "").lower()
    stage_factor = {"pre_foreclosure": 10, "notice_of_default": 15, "auction_scheduled": 25, "post_sale": 35}.get(stage, 5)
    equity_factor = min(40.0, max(0.0, float(equity or 0) / 5000))
    ltv_factor = max(0.0, (100 - float(ltv or 0)) / 2)
    return round(min(100.0, stage_factor + equity_factor + ltv_factor), 2)


def classify_intervention(*, rescue_score: float, acquisition_score: float, ltv: float) -> str:
    if rescue_score >= 70:
        return "LEGAL_DEFENSE"
    if rescue_score >= 45:
        return "LOAN_MODIFICATION"
    if acquisition_score >= 65 and ltv <= 85:
        return "ACQUISITION_CANDIDATE"
    return "NONPROFIT_REFERRAL"
