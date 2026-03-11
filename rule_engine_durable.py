# =============================================================================
# rule_engine_durable.py
# SHRMS — Intelligent Workflow Routing
# Rule-Based Workflow — Correct durable-rules Implementation
#
# PURPOSE OF THIS FILE:
#   This is the academically complete durable-rules implementation of the
#   Rule Engine, prepared for thesis panel discussion and defense.
#
#   It demonstrates the correct pattern for using the Rete algorithm:
#     → durable-rules (Rete network) handles FAILURE detection only
#     → plain Python fallthrough handles SUCCESS (Compliant)
#
# WHY THIS PATTERN IS CORRECT:
#   The Rete algorithm is a forward-chaining inference mechanism. It is
#   designed to detect when specific conditions are violated — i.e., to
#   fire a rule when a known fact matches a failure condition. It is NOT
#   designed to confirm that ALL rules passed simultaneously, because the
#   network processes facts asynchronously and there is no guaranteed
#   ordering of rule firings.
#
#   Attempting to use a "compliant gate" rule (@when_all(m.all_passed==True))
#   introduces a timing dependency — the gate rule may not fire within the
#   execution window of the ruleset block, causing valid documents to be
#   incorrectly returned as non-compliant.
#
#   The correct pattern is:
#     1. Assert the document's fields as facts into the Rete network
#     2. Let the network fire any FAILURE rules whose conditions are met
#     3. After the network runs, check if any failure rule wrote a result
#        → if yes: return the failure reason
#        → if no:  return True, "Compliant"  ← plain Python, no Rete needed
#
#   This is identical to how check_ipcr() works in rule_engine.py, and
#   is the pattern now applied to check_leave() in this file.
#
# DIFFERENCE FROM rule_engine.py:
#   rule_engine.py  — check_leave() uses plain if-then (no durable-rules)
#                     This is the PRODUCTION version used by workflow_router.py
#
#   rule_engine_durable.py — check_leave() uses durable-rules correctly
#                            This is the ACADEMIC REFERENCE version for defense
#
# HOW TO RUN:
#   python rule_engine_durable.py
#   Runs a self-test of all 10 leave rules and prints results.
#
# ACADEMIC BASIS:
#   Reference [25] Gebremariam et al. (2024):
#     Rule-based expert systems use IF-THEN rules to mimic human decision-making.
#   Reference [26] Dami (2021):
#     Rule-based systems consist of: Knowledge Base, Inference Engine, User Interface.
#   The Rete algorithm is the Inference Engine referenced in both sources.
# =============================================================================

from datetime import date, timedelta
from itertools import count as _counter

from durable.lang import ruleset, when_all, assert_fact, m

from org_and_rules import EMPLOYEES, LEAVE_RULES, IPCR_PASSING_SCORE, IPCR_EVALUATOR_ID


# =============================================================================
# Ruleset name generators
# durable-rules requires every ruleset name to be globally unique per session
# =============================================================================

_leave_counter = _counter(1)
_ipcr_counter  = _counter(1)

def _next_leave_name():
    return f"leave_check_{next(_leave_counter)}"

def _next_ipcr_name():
    return f"ipcr_check_{next(_ipcr_counter)}"


class RuleEngine:
    """
    Rule-Based Workflow — Layer 1 of the Intelligent Workflow Routing System.

    Uses the durable-rules library which implements the Rete algorithm
    (forward-chaining inference engine) for failure detection.

    CORRECT PATTERN (used in both check_leave and check_ipcr):
      → Rete network fires rules only for specific FAILURE conditions
      → If no failure rule fires, result_container stays None
      → Plain Python fallthrough returns (True, "Compliant")
      → Success path NEVER depends on the Rete network firing a rule
    """

    # =========================================================================
    # LEAVE APPLICATION — Compliance Check
    # Uses durable-rules (Rete) for failure detection
    # Plain Python fallthrough for success
    # =========================================================================

    def check_leave(self, application: dict) -> tuple:
        """
        Checks a leave application against 10 Civil Service rules
        using the Rete algorithm via durable-rules.

        HOW THE RETE NETWORK IS USED HERE:
          Each @when_all decorator defines one alpha node condition.
          When assert_fact() is called, the Rete network evaluates
          all conditions simultaneously using forward chaining.
          A rule fires only when ALL its conditions are satisfied.
          Only FAILURE conditions are expressed as rules.
          Success is determined by the absence of any fired failure rule.

        The Knowledge Base for leave compliance (from org_and_rules.py):
          LEAVE_RULES  — CSC-mandated rules per leave type
          EMPLOYEES    — LGU organizational hierarchy

        Parameters:
            application (dict):
                employee_id               (str)
                leave_type                (str)
                days_requested            (int)
                days_remaining_balance    (int)
                start_date                (date)
                has_medical_certificate   (bool)
                has_solo_parent_id        (bool)
                has_written_justification (bool)
                has_wellness_certificate  (bool)

        Returns:
            (True,  "Compliant")     — all rules passed
            (False, "<reason text>") — a rule failed
        """

        # ------------------------------------------------------------------
        # Extract and pre-compute all values before asserting into Rete
        # Pre-computation is necessary because the Rete network works on
        # simple boolean/numeric facts — not Python objects or method calls
        # ------------------------------------------------------------------
        employee_id  = application.get("employee_id", "")
        leave_type   = application.get("leave_type", "")
        days_req     = application.get("days_requested", 0)
        days_balance = application.get("days_remaining_balance", 0)
        start_date   = application.get("start_date", date.today())

        has_med_cert      = application.get("has_medical_certificate", False)
        has_solo_id       = application.get("has_solo_parent_id", False)
        has_justification = application.get("has_written_justification", False)
        has_wellness_cert = application.get("has_wellness_certificate", False)

        # Lookup leave rule from Knowledge Base
        leave_rule     = LEAVE_RULES.get(leave_type, {})
        max_days       = leave_rule.get("max_days_per_year") or leave_rule.get("max_days", 999)
        min_notice     = leave_rule.get("min_days_advance_notice", 5)
        cert_threshold = leave_rule.get("medical_cert_required_after", 3)

        days_until_start = (start_date - date.today()).days if start_date else 0

        # Pre-compute violation flags — one per rule
        # These become the facts asserted into the Rete network
        employee_missing  = employee_id not in EMPLOYEES
        leave_invalid     = leave_type not in LEAVE_RULES
        days_invalid      = days_req < 1

        # Rule 4: balance check (vacation/sick only)
        needs_balance     = leave_type in ("vacation_leave", "sick_leave")
        balance_exceeded  = needs_balance and (days_req > days_balance)

        # Rule 5a: annual cap check (fixed-entitlement types)
        needs_cap         = leave_type not in ("vacation_leave", "sick_leave")
        cap_exceeded      = needs_cap and (days_req > max_days) and leave_rule != {}

        # Rule 5b: advance notice (vacation leave only)
        needs_notice      = leave_type == "vacation_leave"
        notice_violated   = needs_notice and (days_until_start < min_notice)

        # Rule 6: medical certificate (sick leave > 3 days)
        needs_cert        = leave_type == "sick_leave" and days_req > cert_threshold
        cert_missing      = needs_cert and not has_med_cert

        # Rule 7: Solo Parent ID
        needs_solo_id     = leave_type == "solo_parent_leave"
        solo_id_missing   = needs_solo_id and not has_solo_id

        # Rule 9: written justification (Special Privilege Leave)
        needs_just        = leave_type == "special_privilege_leave"
        just_missing      = needs_just and not has_justification

        # Rule 10: wellness certificate
        needs_wellness    = leave_type == "wellness_leave"
        wellness_missing  = needs_wellness and not has_wellness_cert

        # ------------------------------------------------------------------
        # Result container — the first fired failure rule writes here
        # Stays None if no failure rule fires → success path
        # ------------------------------------------------------------------
        result_container = [None]
        rs_name = _next_leave_name()

        with ruleset(rs_name):

            # ------------------------------------------------------------------
            # RULE 1 — Employee must exist in the org chart
            # Knowledge Base source: EMPLOYEES (LGU Organizational Hierarchy)
            # IF employee_id not in EMPLOYEES THEN fail
            #
            # Alpha node: employee_missing == True
            # ------------------------------------------------------------------
            @when_all(m.employee_missing == True)
            def rule_1_unknown_employee(c):
                if result_container[0] is None:
                    result_container[0] = (
                        False,
                        f"Employee ID '{c.m.employee_id}' does not exist in the system."
                    )

            # ------------------------------------------------------------------
            # RULE 2 — Leave type must be a recognized CSC category
            # Knowledge Base source: LEAVE_RULES (Civil Service Rules)
            # IF leave_type not in LEAVE_RULES THEN fail
            #
            # Alpha node: leave_invalid == True
            #
            # NOTE: The chaining guard (employee_missing == False) is omitted
            # intentionally. If Rule 1 already fired, result_container[0] is
            # already set and the guard inside this function prevents
            # double-writing. Omitting the guard avoids a durable-rules
            # known limitation where == False conditions on boolean flags
            # are not reliably matched in some versions.
            # ------------------------------------------------------------------
            @when_all(m.leave_invalid == True)
            def rule_2_unknown_leave_type(c):
                if result_container[0] is None:
                    result_container[0] = (
                        False,
                        f"'{c.m.leave_type}' is not a recognized CSC leave type."
                    )

            # ------------------------------------------------------------------
            # RULE 3 — Days requested must be at least 1
            # IF days_requested < 1 THEN fail
            #
            # Alpha node: days_invalid == True
            #
            # NOTE: Same reasoning as Rule 2 — chaining guards omitted.
            # result_container[0] guard prevents double-writing if an earlier
            # rule already fired.
            # ------------------------------------------------------------------
            @when_all(m.days_invalid == True)
            def rule_3_invalid_days(c):
                if result_container[0] is None:
                    result_container[0] = (
                        False,
                        "Days requested must be at least 1."
                    )

            # ------------------------------------------------------------------
            # RULE 4 — Vacation/sick leave cannot exceed remaining balance
            # Knowledge Base source: CSC Omnibus Rules — leave credit system
            # IF leave_type in (vacation, sick)
            # AND days_requested > days_remaining_balance THEN fail
            #
            # Alpha node: balance_exceeded == True
            # ------------------------------------------------------------------
            @when_all(m.balance_exceeded == True)
            def rule_4_balance_exceeded(c):
                if result_container[0] is None:
                    result_container[0] = (
                        False,
                        f"Insufficient leave balance. "
                        f"You requested {c.m.days_requested} day(s) but only "
                        f"have {c.m.days_balance} day(s) remaining."
                    )

            # ------------------------------------------------------------------
            # RULE 5a — Fixed-entitlement leaves cannot exceed annual cap
            # Covers: maternity (105), paternity (7), solo parent (7),
            #         force (5), special privilege (3), wellness (5)
            # IF leave_type has fixed cap AND days_requested > max_days THEN fail
            #
            # Alpha node: cap_exceeded == True
            # ------------------------------------------------------------------
            @when_all(m.cap_exceeded == True)
            def rule_5a_cap_exceeded(c):
                if result_container[0] is None:
                    label = c.m.leave_type.replace("_", " ").title()
                    result_container[0] = (
                        False,
                        f"Days requested ({c.m.days_requested}) exceeds the "
                        f"maximum allowed ({c.m.max_days}) for {label}."
                    )

            # ------------------------------------------------------------------
            # RULE 5b — Vacation leave must be filed at least 5 days in advance
            # Knowledge Base source: CSC Omnibus Rules — leave filing rules
            # IF leave_type == vacation_leave
            # AND days_until_start < 5 THEN fail
            #
            # Alpha node: notice_violated == True
            # ------------------------------------------------------------------
            @when_all(m.notice_violated == True)
            def rule_5b_notice_violated(c):
                if result_container[0] is None:
                    result_container[0] = (
                        False,
                        f"Vacation leave must be filed at least "
                        f"{c.m.min_notice} days in advance. "
                        f"You filed only {c.m.days_until_start} day(s) before."
                    )

            # ------------------------------------------------------------------
            # RULE 6 — Sick leave exceeding 3 days requires a medical certificate
            # Knowledge Base source: CSC Omnibus Rules
            # IF leave_type == sick_leave AND days_requested > 3
            # AND has_medical_certificate == False THEN fail
            #
            # Alpha node: cert_missing == True
            # ------------------------------------------------------------------
            @when_all(m.cert_missing == True)
            def rule_6_cert_missing(c):
                if result_container[0] is None:
                    result_container[0] = (
                        False,
                        f"Sick leave exceeding {c.m.cert_threshold} days "
                        f"requires a medical certificate."
                    )

            # ------------------------------------------------------------------
            # RULE 7 — Solo Parent Leave requires a Solo Parent ID card
            # Knowledge Base source: Republic Act No. 8972 (Solo Parent Act)
            # IF leave_type == solo_parent_leave
            # AND has_solo_parent_id == False THEN fail
            #
            # Alpha node: solo_id_missing == True
            # ------------------------------------------------------------------
            @when_all(m.solo_id_missing == True)
            def rule_7_solo_id_missing(c):
                if result_container[0] is None:
                    result_container[0] = (
                        False,
                        "Solo Parent Leave requires a valid Solo Parent ID card."
                    )

            # ------------------------------------------------------------------
            # RULE 9 — Special Privilege Leave requires written justification
            # Knowledge Base source: CSC MC No. 6 s. 1996
            # IF leave_type == special_privilege_leave
            # AND has_written_justification == False THEN fail
            #
            # Alpha node: just_missing == True
            # ------------------------------------------------------------------
            @when_all(m.just_missing == True)
            def rule_9_justification_missing(c):
                if result_container[0] is None:
                    result_container[0] = (
                        False,
                        "Special Privilege Leave requires a written justification "
                        "stating the specific occasion (e.g., birthday, graduation)."
                    )

            # ------------------------------------------------------------------
            # RULE 10 — Wellness Leave requires a wellness certificate
            # Knowledge Base source: Agency wellness program policy
            # IF leave_type == wellness_leave
            # AND has_wellness_certificate == False THEN fail
            #
            # Alpha node: wellness_missing == True
            # ------------------------------------------------------------------
            @when_all(m.wellness_missing == True)
            def rule_10_wellness_cert_missing(c):
                if result_container[0] is None:
                    result_container[0] = (
                        False,
                        "Wellness Leave requires a certificate from the "
                        "agency wellness officer."
                    )

            # ------------------------------------------------------------------
            # CATCH-ALL: fires when the document is compliant.
            # durable-rules raises MessageNotHandledException if no rule fires.
            # This rule satisfies that requirement without writing a result —
            # success is handled by the plain Python fallthrough below.
            # ------------------------------------------------------------------
            @when_all(m.compliant == True)
            def all_rules_passed(c):
                pass

        # compliant is True only when all violation flags are False.
        # Asserted so the catch-all rule fires and prevents
        # MessageNotHandledException on valid documents.
        compliant_leave = (
            not employee_missing
            and not leave_invalid
            and not days_invalid
            and not balance_exceeded
            and not cap_exceeded
            and not notice_violated
            and not cert_missing
            and not solo_id_missing
            and not just_missing
            and not wellness_missing
        )

        # ------------------------------------------------------------------
        # Assert all pre-computed flags into the Rete network as facts.
        # The Rete network evaluates all alpha/beta node conditions and
        # fires any rule whose conditions are satisfied.
        # ------------------------------------------------------------------
        assert_fact(rs_name, {
            "employee_id":       employee_id,
            "leave_type":        leave_type,
            "days_requested":    days_req,
            "days_balance":      days_balance,
            "days_until_start":  days_until_start,
            "max_days":          max_days,
            "min_notice":        min_notice,
            "cert_threshold":    cert_threshold,

            # Violation flags — one per rule — these are the alpha node inputs
            "employee_missing":  employee_missing,
            "leave_invalid":     leave_invalid,
            "days_invalid":      days_invalid,
            "balance_exceeded":  balance_exceeded,
            "cap_exceeded":      cap_exceeded,
            "notice_violated":   notice_violated,
            "cert_missing":      cert_missing,
            "solo_id_missing":   solo_id_missing,
            "just_missing":      just_missing,
            "wellness_missing":  wellness_missing,
            "compliant":         compliant_leave,
        })

        # ------------------------------------------------------------------
        # SUCCESS PATH — plain Python fallthrough
        #
        # If no failure rule fired, result_container[0] is still None.
        # We do NOT rely on the Rete network to confirm success.
        # Success is simply the absence of any failure — confirmed here
        # in plain Python, completely outside the Rete network.
        #
        # This is the key architectural decision that makes the engine
        # reliable: Rete detects violations, Python confirms compliance.
        # ------------------------------------------------------------------
        if result_container[0] is not None:
            return result_container[0]   # a failure rule fired

        return True, "Compliant"         # no failure = compliant


    # =========================================================================
    # IPCR FORM — Compliance Check + Evaluator Assignment
    # (unchanged from rule_engine.py — already uses correct pattern)
    # =========================================================================

    def check_ipcr(self, form: dict) -> tuple:
        """
        Validates an IPCR form and assigns the evaluator per CSC rules
        using the Rete algorithm via durable-rules.

        Returns:
            (True,  "Compliant",     evaluator_dict) — valid, evaluator assigned
            (False, "<reason text>", None)           — invalid, return to submitter
        """

        employee_id = form.get("employee_id", "")
        is_first    = form.get("is_first_submission", True)
        rating      = form.get("performance_rating")

        employee      = EMPLOYEES.get(employee_id)
        supervisor_id = employee["supervisor_id"] if employee else None

        evaluator_id = IPCR_EVALUATOR_ID if IPCR_EVALUATOR_ID else supervisor_id
        supervisor   = EMPLOYEES.get(evaluator_id) if evaluator_id else None

        evaluator = None
        if supervisor:
            evaluator = {
                "employee_id": evaluator_id,
                "name":        supervisor["name"],
                "role":        supervisor["role"],
            }

        # Pre-compute flags — each True only when its rule genuinely applies
        has_supervisor = (employee is not None) and (supervisor_id is not None)
        supervisor_valid = (employee is not None) and (supervisor is not None)
        rating_missing = (
            (employee is not None)
            and (not is_first)
            and (rating is None)
        )
        rating_invalid = (
            (employee is not None)
            and (not is_first)
            and (rating is not None)
            and not (1.0 <= rating <= 5.0)
        )

        result_container = [None]
        rs_name = _next_ipcr_name()

        with ruleset(rs_name):

            @when_all(m.employee_valid == False)
            def unknown_employee(c):
                if result_container[0] is None:
                    result_container[0] = (
                        False,
                        f"Employee ID '{c.m.employee_id}' does not exist in the system.",
                        None
                    )

            @when_all(m.has_supervisor == False)
            def no_supervisor(c):
                if result_container[0] is None:
                    result_container[0] = (
                        False,
                        f"{c.m.employee_name} is the Department Head and cannot "
                        f"be evaluated through this system.",
                        None
                    )

            @when_all(m.supervisor_valid == False)
            def missing_supervisor(c):
                if result_container[0] is None:
                    result_container[0] = (
                        False,
                        f"Assigned evaluator for {c.m.employee_name} "
                        f"was not found in the system.",
                        None
                    )

            @when_all(m.rating_missing == True)
            def missing_rating(c):
                if result_container[0] is None:
                    result_container[0] = (
                        False,
                        "Performance rating is missing on the returning form.",
                        None
                    )

            @when_all(m.rating_invalid == True)
            def invalid_rating(c):
                if result_container[0] is None:
                    result_container[0] = (
                        False,
                        f"Performance rating {c.m.performance_rating} is invalid. "
                        f"Must be between 1.0 and 5.0.",
                        None
                    )

            # CATCH-ALL — same reason as check_leave above
            @when_all(m.compliant == True)
            def all_ipcr_rules_passed(c):
                pass

        compliant_ipcr = (
            (employee is not None)
            and has_supervisor
            and supervisor_valid
            and not rating_missing
            and not rating_invalid
        )

        assert_fact(rs_name, {
            "employee_id":        employee_id,
            "employee_name":      employee["name"] if employee else "",
            "supervisor_id":      supervisor_id or "",
            "performance_rating": rating,
            "is_first":           is_first,
            "employee_valid":     employee is not None,
            "has_supervisor":     has_supervisor,
            "supervisor_valid":   supervisor_valid,
            "rating_missing":     rating_missing,
            "rating_invalid":     rating_invalid,
            "compliant":          compliant_ipcr,
        })

        # Plain Python fallthrough — same pattern as check_leave
        if result_container[0] is not None:
            return result_container[0]

        return True, "Compliant", evaluator


# =============================================================================
# SELF-TEST — Run directly to verify all 10 leave rules fire correctly
# =============================================================================

if __name__ == "__main__":

    from datetime import date, timedelta

    engine = RuleEngine()
    future = date.today() + timedelta(days=10)
    past   = date.today() + timedelta(days=2)   # too close — violates Rule 5b

    tests = [
        # (description, application dict, expected_passed, expected_reason_contains)

        ("Rule 1 — Unknown employee",
         {"employee_id": "EMP-999", "leave_type": "vacation_leave",
          "days_requested": 3, "days_remaining_balance": 10, "start_date": future},
         False, "does not exist"),

        ("Rule 2 — Invalid leave type",
         {"employee_id": "EMP-005", "leave_type": "nap_leave",
          "days_requested": 3, "days_remaining_balance": 10, "start_date": future},
         False, "not a recognized"),

        ("Rule 3 — Days requested = 0",
         {"employee_id": "EMP-005", "leave_type": "vacation_leave",
          "days_requested": 0, "days_remaining_balance": 10, "start_date": future},
         False, "at least 1"),

        ("Rule 4 — Insufficient balance",
         {"employee_id": "EMP-005", "leave_type": "vacation_leave",
          "days_requested": 10, "days_remaining_balance": 3, "start_date": future},
         False, "Insufficient leave balance"),

        ("Rule 5a — Exceeds annual cap (paternity)",
         {"employee_id": "EMP-005", "leave_type": "paternity_leave",
          "days_requested": 10, "days_remaining_balance": 0, "start_date": future},
         False, "exceeds the maximum"),

        ("Rule 5b — Vacation leave filed too late",
         {"employee_id": "EMP-005", "leave_type": "vacation_leave",
          "days_requested": 3, "days_remaining_balance": 10, "start_date": past},
         False, "in advance"),

        ("Rule 6 — Sick leave > 3 days, no cert",
         {"employee_id": "EMP-005", "leave_type": "sick_leave",
          "days_requested": 5, "days_remaining_balance": 10, "start_date": future,
          "has_medical_certificate": False},
         False, "medical certificate"),

        ("Rule 7 — Solo Parent, no ID",
         {"employee_id": "EMP-005", "leave_type": "solo_parent_leave",
          "days_requested": 3, "days_remaining_balance": 0, "start_date": future,
          "has_solo_parent_id": False},
         False, "Solo Parent ID"),

        ("Rule 9 — Special Privilege, no justification",
         {"employee_id": "EMP-005", "leave_type": "special_privilege_leave",
          "days_requested": 1, "days_remaining_balance": 0, "start_date": future,
          "has_written_justification": False},
         False, "justification"),

        ("Rule 10 — Wellness Leave, no certificate",
         {"employee_id": "EMP-005", "leave_type": "wellness_leave",
          "days_requested": 1, "days_remaining_balance": 0, "start_date": future,
          "has_wellness_certificate": False},
         False, "wellness officer"),

        ("Compliant — valid vacation leave",
         {"employee_id": "EMP-005", "leave_type": "vacation_leave",
          "days_requested": 3, "days_remaining_balance": 10, "start_date": future},
         True, "Compliant"),

        ("Compliant — sick leave <= 3 days, no cert needed",
         {"employee_id": "EMP-005", "leave_type": "sick_leave",
          "days_requested": 2, "days_remaining_balance": 10, "start_date": future},
         True, "Compliant"),

        ("Compliant — sick leave > 3 days WITH cert",
         {"employee_id": "EMP-005", "leave_type": "sick_leave",
          "days_requested": 5, "days_remaining_balance": 10, "start_date": future,
          "has_medical_certificate": True},
         True, "Compliant"),

        ("Compliant — solo parent WITH ID",
         {"employee_id": "EMP-005", "leave_type": "solo_parent_leave",
          "days_requested": 3, "days_remaining_balance": 0, "start_date": future,
          "has_solo_parent_id": True},
         True, "Compliant"),

        ("Compliant — wellness WITH certificate",
         {"employee_id": "EMP-005", "leave_type": "wellness_leave",
          "days_requested": 2, "days_remaining_balance": 0, "start_date": future,
          "has_wellness_certificate": True},
         True, "Compliant"),
    ]

    passed_count = 0
    failed_count = 0

    print()
    print("=" * 65)
    print("  rule_engine_durable.py — Leave Rule Self-Test")
    print("  Pattern: Rete (durable-rules) for failures + Python fallthrough")
    print("=" * 65)

    for desc, app, expect_pass, expect_contains in tests:
        result = engine.check_leave(app)
        actual_pass, actual_reason = result[0], result[1]

        ok = (actual_pass == expect_pass) and (expect_contains in actual_reason)
        icon = "✅" if ok else "❌"

        if ok:
            passed_count += 1
        else:
            failed_count += 1

        print(f"  {icon} {desc}")
        if not ok:
            print(f"       Expected : passed={expect_pass}, contains='{expect_contains}'")
            print(f"       Got      : passed={actual_pass}, reason='{actual_reason}'")

    print()
    print(f"  RESULTS: {passed_count} PASSED | {failed_count} FAILED | {len(tests)} TOTAL")
    print("=" * 65)
    print()

    if failed_count == 0:
        print("  All rules fire correctly using durable-rules Rete network.")
        print("  Pattern confirmed: Rete for failures, Python for success.")
    print()
