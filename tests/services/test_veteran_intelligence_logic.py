from app.models.veteran_intelligence import BenefitRegistry, VeteranProfile
from app.services.veteran_intelligence_service import (
    CATEGORY_100_PERCENT_PERMANENT_TOTAL,
    CATEGORY_70_PERCENT_DISABLED,
    CATEGORY_COMBAT_VETERAN,
    _benefit_matches,
    categorize_profile,
)


def test_categorize_profile_disability_and_combat():
    profile = VeteranProfile(
        disability_rating=100,
        permanent_and_total_status=True,
        combat_service=True,
        discharge_status="medical retirement",
    )

    categories = categorize_profile(profile)

    assert CATEGORY_70_PERCENT_DISABLED in categories
    assert CATEGORY_100_PERCENT_PERMANENT_TOTAL in categories
    assert CATEGORY_COMBAT_VETERAN in categories


def test_benefit_matches_min_disability_rule():
    profile = VeteranProfile(disability_rating=80, discharge_status="honorable")
    benefit = BenefitRegistry(
        benefit_name="SPECIAL_ADAPTED_HOUSING_GRANT",
        eligibility_rules={"min_disability_rating": 70},
        required_documents=[],
        estimated_value=10.0,
        application_steps=[],
    )

    assert _benefit_matches(profile, benefit) is True
