"""
Keyword-based intent override rules.

Given a service key and the user's normalised text, returns an intent name if
a high-confidence keyword phrase is found, otherwise returns None.

This is a pure function extracted from IntentHandler so the 800-line rule
table can be maintained independently of the classification logic.
"""
from __future__ import annotations

from typing import Optional

from backend.chat_helpers import normalize_text


def _contains_any_phrase(text: str, phrases: list[str]) -> bool:
    return any(phrase in text for phrase in phrases)


def keyword_intent_override(service_key: str, text: str) -> Optional[str]:
    """
    Return a hard-coded intent if the user's message matches a known phrase list
    for the given service, otherwise return None.
    """
    normalized = normalize_text(text)

    if service_key == "bin_collection":
        missed_bin_phrases = [
            "missed bin",
            "missed collection",
            "bin not collected",
            "bins not collected",
            "not collected",
            "not emptied",
            "my bin was missed",
            "my bin was not collected",
            "did not collect my bin",
            "they didn't empty my bin",
        ]
        if _contains_any_phrase(normalized, missed_bin_phrases):
            return "report_bin_not_collected_info"

        assisted_phrases = [
            "assisted collection",
            "assisted bin collection",
            "help moving bin",
            "cannot move my bin",
            "can't move my bin",
            "need help with bin",
            "medical condition",
            "mobility issue",
            "disability",
        ]
        if _contains_any_phrase(normalized, assisted_phrases):
            return "assisted_collection_request"

        disruption_phrases = [
            "disruption",
            "delay",
            "delayed",
            "weather delay",
            "strike",
            "service issue",
            "operational issue",
        ]
        if _contains_any_phrase(normalized, disruption_phrases):
            return "service_disruption_bin"

        outside_area_phrases = [
            "outside bradford",
            "not in bradford",
            "outside district",
            "outside the council area",
            "i am in harrogate",
            "i live in harrogate",
            "harrogate",
            "i am in leeds",
            "i live in leeds",
            "i am in wakefield",
            "i live in calderdale",
            "not in the bradford area",
            "live outside bradford",
        ]
        if _contains_any_phrase(normalized, outside_area_phrases):
            return "bin_collection_outside_area"

        recycling_guidance_phrases = [
            "what can i put",
            "what goes in",
            "what goes into",
            "which bin",
            "what bin",
            "can i recycle",
            "recycling rules",
            "bin guidance",
            "where do i put",
            "what can go in",
            "what belongs in",
            "green bin",
            "blue bin",
            "brown bin",
            "cardboard",
            "glass",
            "foil",
            "food waste",
            "plastic trays",
        ]
        if _contains_any_phrase(normalized, recycling_guidance_phrases):
            return "bin_recycling_guidance"

        usual_day_phrases = [
            "collection day",
            "what day is my bin",
            "what day are bins collected",
            "bin day",
            "usual collection day",
            "when is the brown bin",
            "brown bin collected",
            "when is brown bin",
            "what day is my brown bin",
            "when is the blue bin",
            "blue bin collected",
            "when is the green bin",
            "green bin collected",
        ]
        if _contains_any_phrase(normalized, usual_day_phrases):
            return "check_bin_day_general"

        # Live date lookup — strong phrases that signal a specific collection date query
        live_bin_phrases = [
            "next bin",
            "next collection",
            "collection date",
            "collection dates",
            "bin collection date",
            "bin collection dates",
            "next bin collection",
            "next bin collection date",
            "when is my bin",
            "when is my next bin",
            "when is the next collection",
            "when is the next bin collection",
            "check my bin collection",
            "find my collection date",
            "find my next collection",
            "pickup date",
            "next pickup",
        ]
        live_bin_blockers = [
            "what can i put", "what goes in", "what goes into", "which bin",
            "what bin", "can i recycle", "recycling rules", "bin guidance",
            "where do i put", "what can go in", "what belongs in",
            "missed bin", "missed collection", "not collected", "not emptied",
            "my bin was missed", "my bin was not collected",
        ]
        if not _contains_any_phrase(normalized, live_bin_blockers) and _contains_any_phrase(normalized, live_bin_phrases):
            return "check_bin_collection_dates"

        return None

    if service_key == "council_tax":
        band_phrases = [
            "council tax band",
            "find my band",
            "check my band",
            "what is my council tax band",
            "what band is my house",
            "what band is my property",
            "property band",
            "band lookup",
        ]
        if _contains_any_phrase(normalized, band_phrases):
            return "find_council_tax_band"

        balance_phrases = [
            "check my council tax balance",
            "my council tax balance",
            "how much do i owe",
            "outstanding council tax",
            "amount due",
            "balance due",
            "check my bill",
        ]
        if _contains_any_phrase(normalized, balance_phrases):
            return "check_council_tax_balance"

        payment_problem_phrases = [
            "missed payment",
            "missed a council tax",
            "missed my council tax",
            "behind with council tax",
            "overdue council tax",
            "struggling to pay",
            "cant pay council tax",
            "can't pay council tax",
            "payment problem",
            "late payment",
            "behind on council tax",
        ]
        if _contains_any_phrase(normalized, payment_problem_phrases):
            return "council_tax_payment_problem"

        payment_method_phrases = [
            "how can i pay council tax",
            "payment methods",
            "ways to pay council tax",
            "pay by direct debit",
            "pay online",
            "how do i pay",
            "pay by card",
            "card payment",
            "online payment",
            "pay council tax online",
            "pay by card online",
        ]
        if _contains_any_phrase(normalized, payment_method_phrases):
            return "council_tax_payment_methods"

        payment_phrases = [
            "pay council tax",
            "make a council tax payment",
            "pay my bill",
            "pay my council tax",
            "council tax payment",
            "pay now",
        ]
        if _contains_any_phrase(normalized, payment_phrases):
            return "council_tax_payment"

        discount_phrases = [
            "single person discount",
            "apply for discount",
            "discount on council tax",
            "council tax discount",
            "25 percent discount",
            "live alone discount",
        ]
        if _contains_any_phrase(normalized, discount_phrases):
            return "apply_council_tax_discount"

        general_discount_phrases = [
            "discounts and exemptions",
            "council tax reduction",
            "council tax support",
            "reduce my council tax",
            "exemption",
            "discount available",
        ]
        if _contains_any_phrase(normalized, general_discount_phrases):
            return "council_tax_general_discounts"

        move_phrases = [
            "moving house",
            "moved house",
            "report a move",
            "change address council tax",
            "new address",
            "moved in",
            "moved out",
        ]
        if _contains_any_phrase(normalized, move_phrases):
            return "report_move_council_tax"

        change_details_phrases = [
            "change my details",
            "update council tax details",
            "change name on council tax",
            "change account details",
            "report a change",
            "partner moved in",
            "someone moved in",
            "update my council tax account",
            "update account details",
            "change my council tax",
            "amend council tax",
            "update council tax",
        ]
        if _contains_any_phrase(normalized, change_details_phrases):
            return "council_tax_change_details"

        appeal_phrases = [
            "appeal council tax",
            "challenge my band",
            "wrong band",
            "band appeal",
            "council tax appeal",
            "review my band",
        ]
        if _contains_any_phrase(normalized, appeal_phrases):
            return "council_tax_appeal"

        arrears_phrases = [
            "arrears",
            "debt",
            "council tax debt",
            "help with council tax debt",
            "struggling with council tax",
            "can't afford council tax",
            "behind on payments",
            "payment arrears",
            "owe council tax",
        ]
        if _contains_any_phrase(normalized, arrears_phrases):
            return "council_tax_arrears_help"

        general_info_phrases = [
            "what is council tax",
            "council tax help",
            "council tax info",
            "how council tax works",
            "general council tax information",
        ]
        if _contains_any_phrase(normalized, general_info_phrases):
            return "council_tax_general_info"

        # Live lookup fallback — resolve ambiguous queries by keyword
        live_ct_phrases = [
            "find my council tax band", "check my council tax band",
            "what is my council tax band", "what band is my house",
            "what band is my property", "check my council tax balance",
            "my council tax balance", "how much do i owe", "outstanding council tax",
            "amount due", "balance due", "pay my council tax", "pay council tax",
            "make a council tax payment", "pay my bill",
        ]
        live_ct_blockers = [
            "how can i pay", "payment methods", "ways to pay",
            "what is council tax", "how council tax works", "discounts",
            "exemptions", "reduction", "single person discount", "appeal",
            "challenge my band", "wrong band", "arrears help",
            "struggling to pay", "missed payment",
        ]
        if not _contains_any_phrase(normalized, live_ct_blockers) and _contains_any_phrase(normalized, live_ct_phrases):
            if "band" in normalized:
                return "find_council_tax_band"
            if "balance" in normalized or "owe" in normalized or "amount due" in normalized or "bill" in normalized:
                return "check_council_tax_balance"
            if "pay" in normalized:
                return "council_tax_payment"

        return None

    if service_key == "school_admissions":
        finder_phrases = [
            "school finder",
            "find a school",
            "find schools",
            "search for a school",
            "search schools",
            "find nearby school",
            "nearby school",
            "local school",
            "schools near",
            "schools in bradford",
            "bradford schools",
            "show me school",
            "list of school",
            "find primary school",
            "find secondary school",
            "locate school",
            "find me a school",
            "find an academy",
            "school search",
            "schools by postcode",
            "find schools by postcode",
        ]
        if _contains_any_phrase(normalized, finder_phrases):
            return "school_finder"

        primary_phrases = [
            "primary school application",
            "apply for primary",
            "apply for reception",
            "reception place",
            "starting school",
            "starting primary",
            "primary admissions",
            "register for primary",
            "year 1 application",
            "infant school",
            "p1 application",
        ]
        if _contains_any_phrase(normalized, primary_phrases):
            return "primary_admissions"

        secondary_phrases = [
            "secondary school application",
            "apply for secondary",
            "apply for year 7",
            "year 7 application",
            "secondary admissions",
            "high school application",
            "starting secondary",
            "year 7 admissions",
            "year7 admissions",
            "yr7 admissions",
            "year 7 place",
            "high school admissions",
        ]
        if _contains_any_phrase(normalized, secondary_phrases):
            return "secondary_admissions"

        dates_phrases = [
            "admissions deadline",
            "application deadline",
            "offer day",
            "offer date",
            "allocation date",
            "when do i find out",
            "when will i find out",
            "when will i hear",
            "when do i hear",
            "find out about school place",
            "hear about school place",
            "key dates",
            "when to apply",
            "march offer",
            "april offer",
            "when are places",
        ]
        if _contains_any_phrase(normalized, dates_phrases):
            return "school_admissions_dates"

        appeal_phrases = [
            "school appeal",
            "appeal school",
            "appeal admissions",
            "not offered",
            "refused a place",
            "refused school",
            "rejected from school",
            "challenge school",
            "appeal decision",
            "waiting list",
        ]
        if _contains_any_phrase(normalized, appeal_phrases):
            return "school_appeals"

        in_year_phrases = [
            "in year",
            "in-year",
            "mid year",
            "change school",
            "move school",
            "transfer school",
            "moved house",
            "new to the area",
            "new school during",
            "school place during term",
            "apply during term",
            "term time application",
        ]
        if _contains_any_phrase(normalized, in_year_phrases):
            return "in_year_admissions"

        contact_phrases = [
            "contact admissions",
            "admissions team",
            "phone admissions",
            "email admissions",
            "admissions number",
            "admissions contact",
            "speak to someone about school",
        ]
        if _contains_any_phrase(normalized, contact_phrases):
            return "contact_admissions"

        criteria_phrases = [
            "how are places allocated",
            "oversubscribed",
            "sibling priority",
            "catchment area",
            "admissions criteria",
            "distance criteria",
            "faith criteria",
            "looked after children",
            "admissions criteria bradford",
            "criteria bradford schools",
        ]
        if _contains_any_phrase(normalized, criteria_phrases):
            return "school_admissions_criteria"

        process_phrases = [
            "icaf",
            "how to apply",
            "application form",
            "where do i apply",
            "apply online",
            "how does admissions",
            "what form",
            "admissions process",
            "sen school",
            "special educational needs",
            "ehc plan",
            "catholic school",
            "faith school",
            "missed deadline",
            "late application",
            "miss the school deadline",
            "missed the school deadline",
            "what happens if i miss",
            "missed school application",
        ]
        if _contains_any_phrase(normalized, process_phrases):
            return "school_admissions_process"

        return None

    if service_key == "blue_badge":
        apply_phrases = [
            "apply for a blue badge",
            "how do i apply",
            "blue badge application",
            "how to get a blue badge",
            "blue badge form",
            "what documents do i need",
            "how long does it take to get",
            "apply online blue badge",
            "apply for disabled parking badge",
        ]
        if _contains_any_phrase(normalized, apply_phrases):
            return "blue_badge_apply"

        eligibility_phrases = [
            "who is eligible",
            "do i qualify",
            "can i get a blue badge",
            "blue badge criteria",
            "hidden disability",
            "am i eligible",
            "who qualifies",
            "blue badge dla",
            "blue badge pip",
            "blue badge autism",
            "blue badge anxiety",
            "blue badge epilepsy",
            "blue badge mental health",
            "child blue badge",
            "registered blind blue badge",
            "non visible disability",
            "invisible disability",
        ]
        if _contains_any_phrase(normalized, eligibility_phrases):
            return "blue_badge_eligibility"

        cost_phrases = [
            "how much does a blue badge cost",
            "blue badge fee",
            "blue badge cost",
            "how much is a blue badge",
            "is blue badge free",
            "blue badge charge",
            "do i have to pay for blue badge",
            "blue badge price",
        ]
        if _contains_any_phrase(normalized, cost_phrases):
            return "blue_badge_cost"

        renewal_phrases = [
            "renew my blue badge",
            "blue badge renewal",
            "blue badge expiring",
            "blue badge about to expire",
            "expired blue badge",
            "reapply for blue badge",
            "how long does blue badge last",
            "blue badge expires",
            "blue badge 3 years",
        ]
        if _contains_any_phrase(normalized, renewal_phrases):
            return "blue_badge_renewal"

        replacement_phrases = [
            "lost my blue badge",
            "lost blue badge",
            "stolen blue badge",
            "damaged blue badge",
            "replace my blue badge",
            "blue badge replacement",
            "blue badge lost",
            "badge stolen",
            "get a new blue badge",
        ]
        if _contains_any_phrase(normalized, replacement_phrases):
            return "blue_badge_replacement"

        parking_phrases = [
            "where can i park",
            "blue badge parking",
            "park on yellow lines",
            "disabled bay",
            "parking concessions",
            "parking clock",
            "blue badge car park",
            "loading restrictions",
            "blue badge abroad",
            "blue badge europe",
            "where can't i park",
            "where cannot i park",
            "badge holder must be present",
            "someone else drive",
            "lend my blue badge",
            "can i park for free",
        ]
        if _contains_any_phrase(normalized, parking_phrases):
            return "blue_badge_parking_rules"

        misuse_phrases = [
            "report misuse",
            "report blue badge misuse",
            "blue badge fraud",
            "someone using a blue badge",
            "using without holder",
            "misuse blue badge",
            "blue badge hotline",
            "is it illegal to use someone",
            "using dead person",
            "using deceased",
            "forged blue badge",
            "expired badge misuse",
            "report abuse blue badge",
        ]
        if _contains_any_phrase(normalized, misuse_phrases):
            return "blue_badge_misuse"

        org_phrases = [
            "organisation blue badge",
            "organisational blue badge",
            "charity blue badge",
            "care home blue badge",
            "day centre blue badge",
            "apply blue badge organisation",
        ]
        if _contains_any_phrase(normalized, org_phrases):
            return "blue_badge_organisations"

        contact_phrases = [
            "contact blue badge",
            "blue badge phone number",
            "blue badge email",
            "blue badge team",
            "transport concessions",
            "01274 438723",
        ]
        if _contains_any_phrase(normalized, contact_phrases):
            return "blue_badge_contact"

        return None

    if service_key == "libraries":
        finder_phrases = [
            "find a library",
            "library near me",
            "local library",
            "nearest library",
            "libraries in bradford",
            "library finder",
            "find my nearest library",
            "libraries near me",
            "library search",
            "show me libraries",
        ]
        if _contains_any_phrase(normalized, finder_phrases):
            return "library_finder"

        hours_phrases = [
            "opening hours",
            "what time does",
            "when does the library open",
            "when does the library close",
            "is the library open",
            "library hours",
            "library times",
            "library open today",
            "when is the library open",
            "library opening",
        ]
        if _contains_any_phrase(normalized, hours_phrases):
            return "library_hours"

        membership_phrases = [
            "join the library",
            "library card",
            "library membership",
            "how do i join",
            "sign up for library",
            "get a library card",
            "is it free to join",
            "register at library",
            "free to join",
            "library registration",
        ]
        if _contains_any_phrase(normalized, membership_phrases):
            return "library_membership"

        catalogue_phrases = [
            "search books",
            "reserve a book",
            "renew a book",
            "library catalogue",
            "borrow a book",
            "ebook",
            "e-book",
            "audiobook",
            "renew my books",
            "book search",
            "place a reservation",
            "borrow books",
            "search for a book",
            "online catalogue",
            "borrowbox",
        ]
        if _contains_any_phrase(normalized, catalogue_phrases):
            return "library_catalogue"

        events_phrases = [
            "library events",
            "storytime",
            "story time",
            "childrens activities",
            "children's activities",
            "book group",
            "reading group",
            "clubs at library",
            "craft group",
            "what's on at the library",
            "chess club library",
            "knit and natter",
            "rhyme time",
            "rhymetime",
            "duplo",
            "library activities",
        ]
        if _contains_any_phrase(normalized, events_phrases):
            return "library_events"

        services_phrases = [
            "library computers",
            "computer at library",
            "wifi at library",
            "wi-fi at library",
            "print at library",
            "printing at library",
            "meeting room library",
            "photocopier library",
            "library facilities",
            "use a computer at",
            "print documents library",
            "free wifi library",
            "free internet library",
        ]
        if _contains_any_phrase(normalized, services_phrases):
            return "library_services"

        home_service_phrases = [
            "home library",
            "home library service",
            "home delivery library",
            "books delivered",
            "cant visit library",
            "can't visit library",
            "housebound library",
            "library delivery",
            "books brought to me",
            "unable to visit library",
            "books to my door",
        ]
        if _contains_any_phrase(normalized, home_service_phrases):
            return "library_home_service"

        contact_phrases = [
            "contact library",
            "library phone number",
            "library email",
            "speak to library",
            "library contact details",
            "ring the library",
            "call the library",
            "email the library",
        ]
        if _contains_any_phrase(normalized, contact_phrases):
            return "library_contact"

        return None

    if service_key == "benefits_support":
        calculator_phrases = [
            "benefits calculator",
            "calculate my benefits",
            "calculate housing benefit",
            "estimate my housing benefit",
            "how much housing benefit",
            "how much council tax reduction",
            "calculate council tax reduction",
            "benefit entitlement calculator",
            "work out my benefits",
            "how much will i get",
            "how much benefit am i entitled to",
            "calculate my entitlement",
        ]
        if _contains_any_phrase(normalized, calculator_phrases):
            return "benefits_calculator"

        dhp_phrases = [
            "dhp",
            "discretionary housing payment",
            "rent shortfall",
            "help with rent shortfall",
            "bedroom tax",
            "housing benefit does not cover",
            "benefit does not cover my rent",
            "top up payment",
        ]
        if _contains_any_phrase(normalized, dhp_phrases):
            return "discretionary_housing_payment"

        myinfo_phrases = [
            "myinfo",
            "benefits account",
            "sign in to benefits",
            "log in to benefits",
            "login to benefits",
            "register account",
            "view my claim online",
            "check my housing benefit online",
            "access to my claim",
            "access my claim",
            "housing benefit online account",
            "benefit account online",
            "view my claim",
            "online access",
        ]
        if _contains_any_phrase(normalized, myinfo_phrases):
            return "benefits_myinfo_access"

        evidence_phrases = [
            "submit evidence",
            "upload evidence",
            "send documents",
            "supporting documents",
            "upload proof",
            "submit payslips",
            "provide proof",
            "upload documents",
            "upload payslips",
            "send payslips",
            "payslip",
        ]
        if _contains_any_phrase(normalized, evidence_phrases):
            return "submit_benefit_evidence"

        change_phrases = [
            "change of circumstances",
            "circumstances have changed",
            "my circumstances changed",
            "something has changed",
            "report a change",
            "i have a new job",
            "my income has changed",
            "someone moved in",
            "someone moved out",
            "i have started work",
            "my rent has changed",
            "lodger moved in",
            "lodger has moved",
            "someone has moved in",
            "person moved in",
            "new person in house",
        ]
        if _contains_any_phrase(normalized, change_phrases):
            return "report_change_of_circumstances"

        appeal_phrases = [
            "appeal",
            "reconsideration",
            "wrong decision",
            "decision review",
            "challenge my benefit",
            "disagree with",
            "claim was refused",
            "benefit has been reduced",
        ]
        if _contains_any_phrase(normalized, appeal_phrases):
            return "benefit_appeal_or_reconsideration"

        contact_phrases = [
            "contact benefits",
            "benefits team",
            "benefits helpline",
            "phone number for benefits",
            "email benefits",
            "welfare advice",
            "speak to someone about benefits",
            "talk to someone about my claim",
            "number to ring",
            "number to call",
            "phone number for housing benefit",
            "ring about my housing benefit",
            "call about housing benefit",
            "phone about housing benefit",
            "number for my housing benefit",
        ]
        if _contains_any_phrase(normalized, contact_phrases):
            return "benefits_support_contact"

        apply_phrases = [
            "apply for housing benefit",
            "apply for council tax reduction",
            "apply for ctr",
            "housing benefit form",
            "housing benefit application",
            "council tax reduction form",
            "make a claim",
            "start a claim",
            "claim housing benefit",
            "new claim for council tax reduction",
            "claim council tax reduction online",
            "apply council tax reduction online",
        ]
        if _contains_any_phrase(normalized, apply_phrases):
            return "apply_housing_benefit_ctr"

        eligibility_phrases = [
            "am i eligible",
            "eligibility",
            "can i get housing benefit",
            "do i qualify",
            "am i entitled",
            "benefit eligibility",
            "who is eligible",
            "housing benefit rules",
            "housing benefit criteria",
            "can i claim housing benefit",
            "low wages rent",
            "help with rent",
            "low income rent",
            "can i get help with rent",
            "council tax support scheme",
            "council tax support eligibility",
            "council tax support scheme eligibility",
        ]
        if _contains_any_phrase(normalized, eligibility_phrases):
            return "housing_benefit_eligibility"

        return None

    return None
