from __future__ import annotations


TURN2US_CALCULATOR_URL = (
    "https://benefits-calculator.turn2us.org.uk/survey/1/"
    "29b25c2f-00ab-4e91-a4c1-894ba8228ad1"
    "?utm_source=dwp&utm_medium=referral&utm_campaign=ip&utm_term=bc_web"
)

BRADFORD_BENEFITS_URL = "https://www.bradford.gov.uk/benefits/"
BRADFORD_HOUSING_BENEFIT_URL = (
    "https://www.bradford.gov.uk/benefits/"
    "housing-benefit-and-council-tax-support/housing-benefit/"
)
BRADFORD_CTR_URL = (
    "https://www.bradford.gov.uk/benefits/"
    "housing-benefit-and-council-tax-support/council-tax-support/"
)
BRADFORD_CONTACT_URL = "https://www.bradford.gov.uk/benefits/contact-us/"


class BenefitsConnector:
    """
    Connector for benefits eligibility guidance and the Turn2Us benefits calculator.
    Provides eligibility text based on age group and housing situation, and returns
    the Turn2Us URL for a full personalised calculation.
    """

    TURN2US_URL = TURN2US_CALCULATOR_URL
    BRADFORD_BENEFITS_URL = BRADFORD_BENEFITS_URL
    BRADFORD_HOUSING_BENEFIT_URL = BRADFORD_HOUSING_BENEFIT_URL
    BRADFORD_CTR_URL = BRADFORD_CTR_URL
    BRADFORD_CONTACT_URL = BRADFORD_CONTACT_URL

    def get_eligibility_overview(self, age_group: str, housing_type: str) -> dict:
        """
        Returns eligibility overview based on age group (working/pension)
        and housing type (private/council/own).
        """
        is_pension = age_group == "pension"
        is_private_renter = housing_type == "private"
        is_council_renter = housing_type == "council"
        is_owner = housing_type == "own"
        is_renting = housing_type in ("private", "council")

        # Housing Benefit text
        if is_pension:
            if is_renting:
                housing_benefit_text = (
                    "As a pension-age resident who rents, you may be eligible for "
                    "<strong>Housing Benefit</strong> to help cover your rent costs. "
                    "The amount depends on your income, savings, and household circumstances."
                )
            else:
                housing_benefit_text = (
                    "As a pension-age homeowner, you are generally not eligible for Housing Benefit. "
                    "However, if you receive certain qualifying benefits, you may be entitled to "
                    "<strong>Support for Mortgage Interest (SMI)</strong> to help with mortgage costs."
                )
        else:
            if is_renting:
                housing_benefit_text = (
                    "Working-age people who rent may be eligible for <strong>Housing Benefit</strong> "
                    "if they already receive certain qualifying benefits (such as Income Support or "
                    "Pension Credit). Otherwise, you will likely need to claim the "
                    "<strong>housing cost element of Universal Credit</strong> instead."
                )
            else:
                housing_benefit_text = (
                    "As a working-age homeowner, Housing Benefit is not available to you. "
                    "If you are on Universal Credit and struggling with housing costs, "
                    "you may be able to claim the <strong>housing cost element</strong> "
                    "of Universal Credit to help with your mortgage interest."
                )

        # Council Tax Reduction text
        if is_pension:
            ctr_text = (
                "Pension-age residents may be entitled to a higher rate of "
                "<strong>Council Tax Reduction (CTR)</strong> — in many cases up to "
                "<strong>100%</strong> of your bill. "
                "Eligibility depends on your income, savings, and household composition."
            )
        else:
            ctr_text = (
                "Working-age residents in Bradford may be eligible for "
                "<strong>Council Tax Reduction (CTR)</strong>, "
                "which can reduce your Council Tax bill by up to <strong>72.5%</strong> "
                "depending on your income, savings, and household circumstances."
            )

        # Extra tip for renter type
        if is_private_renter:
            extra_tip = (
                "For private renters, Housing Benefit is limited by the "
                "<strong>Local Housing Allowance (LHA)</strong> rate for your area "
                "and bedroom entitlement — it may not cover your full rent."
            )
        elif is_council_renter:
            extra_tip = (
                "If you rent from the council or a housing association, Housing Benefit "
                "can be paid directly to your landlord and may cover up to the "
                "eligible rent amount set by Bradford Council."
            )
        else:
            extra_tip = ""

        return {
            "age_group": age_group,
            "housing_type": housing_type,
            "is_pension": is_pension,
            "is_renting": is_renting,
            "housing_benefit_text": housing_benefit_text,
            "ctr_text": ctr_text,
            "extra_tip": extra_tip,
        }
