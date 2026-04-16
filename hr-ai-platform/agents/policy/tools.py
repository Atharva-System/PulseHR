"""Policy Agent tools — HR policy knowledge base from official company policy."""

from utils.logger import get_logger

logger = get_logger(__name__)

# ── Official HR Policy Knowledge Base ─────────────────────────────────────
# Source: Final HR Policy.pdf
# ---------------------------------------------------------------------------

_POLICIES: dict[str, str] = {
    "probation_period": (
        "The probation period will be for three months for everyone. "
        "During probation, leaves will be assigned to a particular account "
        "but can be used only after the probation period has been completed."
    ),
    "leave_policy_overview": (
        "During the year, 18 Paid Leaves (PL) are assigned to every employee: "
        "Casual Leaves — 12 days, Sick Leaves — 6 days. "
        "If leaves exceed 18 days, those extra days are considered unpaid leaves "
        "and the day's pay is cut from the salary. "
        "Employees who take less than 18 days of leave will be entitled to leave "
        "encashment based on their leave balance in the December month's payment "
        "(half payment of each unused leave). "
        "These leaves cannot be carried forward to the next year."
    ),
    "sick_leave": (
        "The company provides sick leave to employees when they are ailing. "
        "If employees take sick leave for more than 2 consecutive days, they must "
        "submit a medical certificate to support the grant of sick leave. "
        "If employees have serious health issues, based on medical certificates "
        "and the situation, there may be possibilities to balance sick leaves "
        "into casual leave."
    ),
    "leave_intimation": (
        "All employees, before proceeding on leave, must send their intimation "
        "through email to their immediate reporting team leader and the HR department. "
        "All Team Leaders must keep the HR department in CC while approving leave "
        "of their team members. "
        "At the time of sick leave or any emergency, employees must email or call "
        "the HR Department with early intimation and a valid reason."
    ),
    "leave_prior_notice": (
        "All employees are required to obtain prior permission or sanction before "
        "proceeding on any kind of leave. Prior notice requirements:\n"
        "• 1 day leave → 1 week prior intimation\n"
        "• 2 days leave → 2 weeks prior intimation\n"
        "• 5 days leave → 1 month prior intimation\n"
        "• 10+ days leave → 1.5 months prior intimation\n"
        "Employees who fail to report their leave based on the above criteria "
        "will be entitled to unpaid leave."
    ),
    "quarterly_leave_limit": (
        "Employees can take a maximum of 3 days casual leave and 1.5 days sick leave "
        "on a quarterly basis. After exceeding this limit, the extra day's pay is "
        "cut from that particular month's salary."
    ),
    "leave_adjacent_to_weekoff": (
        "All employees are allowed to take leave on the previous day or post day of "
        "a weekly off or holiday at least two times. If employees take this type of "
        "leave more than 2 times, they shall face deduction of two days' leave "
        "instead of one day. "
        "Example: If total leave balance is 18 and you take leave more than two times "
        "on Friday with weekly off/holidays, then 2 days (Friday + Saturday) leave "
        "will be deducted. Similarly for Monday with weekly off, Saturday and Monday "
        "leave will be deducted. Remaining balance becomes 16 days."
    ),
    "sandwich_leave": (
        "If you take 4 days leave — for example, taking leave on Friday and Monday "
        "with a weekend off/holidays in between — it will be considered as a sandwich "
        "leave and 4 days' leave will be deducted from your leave balance account."
    ),
    "notice_period_leave": (
        "Any employee serving notice period will have their leave balance voided "
        "from the starting day of the notice period."
    ),
    "minimum_working_hours": (
        "All employees are required to complete 40 working hours per week "
        "(across 5 working days). Completing 8 working hours per day is mandatory. "
        "However, in some cases, the company may allow flexibility — such as "
        "medical or genuine personal reasons — to adjust the missed hours on "
        "another working day. "
        "To be eligible to apply for a half-day leave, employees must have worked "
        "for at least 4 effective working hours on that same day. "
        "Payroll is attached to KEKA based on working hour criteria to make the "
        "process easy, transparent, and healthy."
    ),
    "work_from_home": (
        "Medical reasons for self and family members are NOT considered for WFH "
        "in any case — employees must apply for leave instead. "
        "However, in special situations, the possibility of remote work may be "
        "entertained, subject to the discretion of the authoritative body. "
        "To facilitate this, employees must formally engage with their Project Manager, "
        "ensuring that both the authoritative body and the Human Resources Department "
        "are apprised. The final decision is anchored by the authoritative body, "
        "and if approved, specific tools may be stipulated to guarantee work "
        "efficiency and dedication."
    ),
    "policy_changes": (
        "This policy is subject to regular reviews or as deemed necessary by the "
        "authoritative body. Any consequent changes will be effectively communicated "
        "to the entire team, superseding previous renditions."
    ),
    "posh_policy": (
        "The company follows a strict Prevention of Sexual Harassment (POSH) policy "
        "in compliance with the Sexual Harassment of Women at Workplace Act, 2013. "
        "Any form of unwelcome sexual behavior — including physical contact, verbal "
        "remarks, showing pornography, sexual jokes, gestures, stalking, or any "
        "conduct of sexual nature — is strictly prohibited. "
        "All employees (male, female, and other genders) are protected under this policy. "
        "Complaints of sexual harassment will be immediately referred to the Internal "
        "Complaints Committee (ICC) and a formal ticket will be raised. "
        "The company ensures full confidentiality, protection from retaliation, and "
        "a fair inquiry process. Perpetrators may face disciplinary action including "
        "termination, and the matter may be reported to authorities as required by law."
    ),
    "anti_harassment": (
        "The company maintains a zero-tolerance policy against all forms of harassment "
        "in the workplace. Harassment includes but is not limited to: unwelcome verbal "
        "or physical conduct, intimidation, bullying, humiliation, threats, insults, "
        "offensive jokes, slurs, or any behavior that creates a hostile or offensive "
        "work environment. "
        "Harassment based on gender, race, religion, caste, disability, age, sexual "
        "orientation, or any protected characteristic is strictly prohibited. "
        "Any reported instance of harassment will result in an immediate formal "
        "investigation. Confirmed violations will lead to disciplinary action up to "
        "and including termination."
    ),
    "anti_discrimination": (
        "The company is committed to providing equal opportunity and a discrimination-free "
        "workplace. Discrimination based on gender, race, caste, religion, disability, "
        "age, marital status, sexual orientation, or any other protected characteristic "
        "is strictly prohibited in hiring, promotions, compensation, and all employment "
        "decisions. "
        "Any employee who experiences or witnesses discrimination must report it "
        "immediately. All reports will be investigated promptly and action taken."
    ),
    "workplace_conduct": (
        "All employees are expected to maintain professional conduct and mutual respect "
        "in the workplace. The following behaviors are strictly prohibited: "
        "verbal abuse, public humiliation, intimidation, threatening behavior, "
        "spreading rumors, deliberate exclusion, sabotaging work, misuse of authority, "
        "and any behavior that undermines a colleague's dignity. "
        "Managers and team leaders have an added responsibility to maintain a healthy "
        "work environment. Abuse of authority — including shouting at subordinates, "
        "insulting employees in front of others, or making demeaning remarks — is a "
        "serious policy violation. "
        "Violations will be investigated and may result in formal warnings, suspension, "
        "or termination depending on severity."
    ),
    "anti_bullying": (
        "The company prohibits all forms of workplace bullying. Bullying includes "
        "repeated unreasonable behavior directed toward an employee that creates a risk "
        "to health and safety, such as: verbal abuse, offensive conduct, humiliation, "
        "work interference, withholding information, setting impossible deadlines, "
        "or constantly criticizing without justification. "
        "Both peer-to-peer and hierarchical bullying are covered. "
        "Reports of bullying will trigger an immediate investigation and appropriate "
        "disciplinary action."
    ),
    "retaliation_protection": (
        "The company strictly prohibits retaliation against any employee who reports "
        "a complaint, participates in an investigation, or exercises their rights "
        "under company policy. Retaliation includes adverse employment actions, "
        "hostility, exclusion, or any negative treatment as a result of making a "
        "good-faith complaint. "
        "Any employee found engaging in retaliation will face disciplinary action "
        "up to and including termination."
    ),
}

# Keyword mapping for better search relevance
_KEYWORD_MAP: dict[str, list[str]] = {
    "probation_period": ["probation", "new employee", "new joiner", "joining", "trial"],
    "leave_policy_overview": ["leave", "lave", "pl", "paid leave", "annual", "encashment", "carry forward", "unpaid", "balance"],
    "sick_leave": ["sick", "medical", "ill", "illness", "health", "doctor", "certificate", "hospital"],
    "leave_intimation": ["intimation", "inform", "notify", "email", "mail", "approval", "permission", "cc", "team leader"],
    "leave_prior_notice": ["prior", "notice", "advance", "ahead", "days before", "how many days", "intimation days"],
    "quarterly_leave_limit": ["quarterly", "quarter", "maximum", "limit", "per quarter"],
    "leave_adjacent_to_weekoff": ["weekend", "friday", "monday", "week off", "holiday", "adjacent", "next to weekend"],
    "sandwich_leave": ["sandwich", "between", "gap", "friday monday", "consecutive"],
    "notice_period_leave": ["notice period", "resignation", "leaving", "resign", "quit", "last day"],
    "minimum_working_hours": ["working hours", "hours", "8 hours", "40 hours", "half day", "keka", "payroll", "overtime"],
    "work_from_home": ["wfh", "work from home", "remote", "work remotely", "home"],
    "policy_changes": ["policy change", "update", "revision", "review"],
    "posh_policy": ["sexual", "posh", "harassment", "unwelcome", "touch", "touching", "inappropriate", "stalking", "sexual harassment", "icc", "complaints committee", "sexual jokes", "advances", "molest", "groping", "misconduct"],
    "anti_harassment": ["harass", "harassment", "bully", "bullying", "intimidat", "hostile", "insult", "insulting", "humiliat", "threaten", "threat", "offensive", "abusive", "abuse", "slur"],
    "anti_discrimination": ["discrimination", "discriminat", "bias", "biased", "racist", "sexist", "casteist", "unfair treatment", "unequal", "prejudice", "favoritism"],
    "workplace_conduct": ["conduct", "misbehav", "unprofessional", "shout", "shouting", "yelling", "yell", "scream", "public humiliation", "insult", "demeaning", "rude", "disrespect", "dignity", "abuse of authority", "manager insult", "front of everyone", "in front of"],
    "anti_bullying": ["bully", "bullying", "picking on", "target", "targeting", "impossible deadline", "constant criticism", "work interference", "sabotag"],
    "retaliation_protection": ["retaliation", "retaliate", "revenge", "punish", "punished for complaining", "adverse action", "backlash"],
}


def search_policies(query: str, trace_id: str = "") -> str:
    """Search the policy knowledge base for relevant policies.

    Tries the DB-backed policies table first (if any rows exist).
    Falls back to the hardcoded ``_POLICIES`` dict otherwise.

    Args:
        query: Search query from the employee.
        trace_id: Request trace ID.

    Returns:
        Matching policy text.
    """
    logger.info(f"[{trace_id}] Searching policies for: {query[:80]}...")

    # ── Try DB-backed policies first ──────────────────────────────────
    try:
        from db.connection import get_db_session
        from db.models import PolicyModel

        db = get_db_session()
        try:
            active_policies = (
                db.query(PolicyModel)
                .filter(PolicyModel.is_active == True)
                .all()
            )
            if active_policies:
                return _search_db_policies(active_policies, query, trace_id)
        finally:
            db.close()
    except Exception as exc:
        logger.warning(f"[{trace_id}] DB policy lookup failed, using hardcoded: {exc}")

    # ── Fallback to hardcoded dict ────────────────────────────────────
    return _search_hardcoded_policies(query, trace_id)


def _search_db_policies(policies, query: str, trace_id: str) -> str:
    """Keyword-match against DB-stored policies."""
    query_lower = query.lower()

    scored: list[tuple[str, str, int]] = []
    for p in policies:
        keywords = [k.strip() for k in (p.keywords or "").split(",") if k.strip()]
        score = sum(1 for kw in keywords if kw.lower() in query_lower)
        if score > 0:
            scored.append((p.title, p.content, score))

    scored.sort(key=lambda x: x[2], reverse=True)

    if scored:
        results = []
        for title, text, _ in scored[:3]:
            results.append(f"**{title}**:\n{text}")
        return "\n\n---\n\n".join(results)

    # No keyword match — return all active policies
    logger.info(f"[{trace_id}] No keyword match in DB policies, returning all")
    results = []
    for p in policies:
        results.append(f"**{p.title}**:\n{p.content}")
    return "\n\n---\n\n".join(results)


def _search_hardcoded_policies(query: str, trace_id: str) -> str:
    """Original keyword-match against the hardcoded _POLICIES dict."""
    query_lower = query.lower()

    scored: list[tuple[str, str, int]] = []
    for key, keywords in _KEYWORD_MAP.items():
        score = sum(1 for kw in keywords if kw in query_lower)
        if score > 0:
            scored.append((key, _POLICIES[key], score))

    scored.sort(key=lambda x: x[2], reverse=True)

    if scored:
        results = []
        for key, text, _ in scored[:3]:
            title = key.replace("_", " ").title()
            results.append(f"**{title}**:\n{text}")
        return "\n\n---\n\n".join(results)

    logger.info(f"[{trace_id}] No keyword match, returning full policy")
    results = []
    for key, text in _POLICIES.items():
        title = key.replace("_", " ").title()
        results.append(f"**{title}**:\n{text}")
    return "\n\n---\n\n".join(results)
