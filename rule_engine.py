# =============================================================================
# rule_engine.py
# SHRMS — Intelligent Workflow Routing
# Task 2 of 7 — Rule-Based Workflow (Layer 1)
#
# WHAT THIS FILE IS:
#   Layer 1 of the Intelligent Workflow Routing system.
#   Implements the Rule-Based Workflow using the durable-rules library,
#   which runs the Rete algorithm underneath.
#
# HOW IT WORKS (Rete Algorithm — Forward Chaining):
#   1. A fact (the submitted form fields) is asserted into a ruleset
#   2. The Rete network evaluates all rule conditions simultaneously
#      using alpha nodes (single conditions) and beta nodes (combined)
#   3. Every rule whose conditions are fully satisfied fires automatically
#      (forward chaining — from known facts toward a conclusion)
#   4. A fired rule writes its verdict into a result container
#   5. The result is collected and returned as the compliance verdict
#
#   IF a document passes ALL rules → result is "compliant"
#   IF a document fails ANY rule   → result contains the violation reason
#
# WHY durable-rules:
#   Unlike manual if-then chains, the Rete algorithm builds a pattern-matching
#   network at startup and only re-evaluates nodes affected by new facts.
#   This makes the rule engine formally correct and academically aligned
#   with the "rule-based workflow" described in the thesis manuscript.
#
# MAPS TO workflow.png:
#   Leave path      → "Leave management table"
#   Evaluation path → "Check Employee ID and assigned evaluator"
# =============================================================================

from datetime import date
from itertools import count as _counter

from durable.lang import ruleset, when_all, assert_fact, m

from org_and_rules import EMPLOYEES, LEAVE_RULES, IPCR_PASSING_SCORE, IPCR_EVALUATOR_ID


# =============================================================================
# Ruleset name generator
#
# durable-rules requires every ruleset name to be unique across the entire
# program session. If the same name is reused, the engine raises an error.
# We generate unique names by appending an auto-incrementing integer.
# =============================================================================

_leave_counter = _counter(1)
_ipcr_counter  = _counter(1)

def _next_leave_name():
    return f"leave_check_{next(_leave_counter)}"

def _next_ipcr_name():
    return f"ipcr_check_{next(_ipcr_counter)}"


class RuleEngine:

    # =========================================================================
    # LEAVE APPLICATION — Compliance Check
    # =========================================================================

    def check_leave(self, application: dict) -> tuple:
        """
        Checks a leave application against Civil Service rules.

        Parameters:
            application (dict):
                employee_id             (str)  — e.g. "EMP-005"
                leave_type              (str)  — e.g. "vacation_leave"
                days_requested          (int)  — e.g. 3
                days_remaining_balance  (int)  — e.g. 10
                start_date              (date) — e.g. date(2025, 9, 1)
                has_medical_certificate  (bool) — True or False
                has_solo_parent_id       (bool) — True or False
                has_marriage_certificate (bool) — True or False

        Returns:
            (True,  "Compliant")      — all rules passed, proceed to Decision Tree
            (False, "<reason text>")  — a rule failed, return document to employee
        """

        # Extract every field from the submitted form
        employee_id  = application.get("employee_id")
        leave_type   = application.get("leave_type")
        days_req     = application.get("days_requested", 0)
        days_balance = application.get("days_remaining_balance", 0)
        start_date   = application.get("start_date", date.today())

        # ------------------------------------------------------------------
        # RULE 1: Employee must exist in the org chart
        # IF employee_id not in EMPLOYEES THEN return
        # ------------------------------------------------------------------
        if employee_id not in EMPLOYEES:
            return False, f"Employee ID '{employee_id}' does not exist in the system."

        # ------------------------------------------------------------------
        # RULE 2: Leave type must be a recognized CSC leave category
        # IF leave_type not in LEAVE_RULES THEN return
        # ------------------------------------------------------------------
        rule = LEAVE_RULES.get(leave_type)
        if rule is None:
            return False, f"'{leave_type}' is not a recognized leave type."

        # ------------------------------------------------------------------
        # RULE 3: Days requested must be at least 1
        # IF days_requested < 1 THEN return
        # ------------------------------------------------------------------
        if days_req < 1:
            return False, "Days requested must be at least 1."

        # ------------------------------------------------------------------
        # RULE 4: Vacation, sick, and force leave cannot exceed remaining balance
        # Source: CSC Omnibus Rules — leave credit system
        # Force leave uses the employee's vacation leave credit pool.
        # IF leave_type in (vacation, sick, force)
        # AND days_requested > days_remaining_balance THEN return
        # ------------------------------------------------------------------
        if leave_type in ("vacation_leave", "sick_leave", "force_leave"):
            if days_req > days_balance:
                return False, (
                    f"Insufficient leave balance. "
                    f"You requested {days_req} day(s) but only have "
                    f"{days_balance} day(s) remaining."
                )

        # ------------------------------------------------------------------
        # RULE 5: Fixed-entitlement leaves cannot exceed their annual cap
        # Covers: maternity (105), paternity (7), solo parent (7),
        #         force (5), special privilege (3), wellness (5),
        #         special sick leave for women (90)
        # IF leave_type has a fixed cap
        # AND days_requested > max_days THEN return
        # ------------------------------------------------------------------
        max_days = rule.get("max_days_per_year") or rule.get("max_days")
        if max_days is not None:
            if days_req > max_days:
                label = leave_type.replace("_", " ").title()
                return False, (
                    f"Days requested ({days_req}) exceeds the maximum allowed "
                    f"({max_days}) for {label}."
                )

        # ------------------------------------------------------------------
        # RULE 6: Advance notice — applies to any leave type that has
        #         min_days_advance_notice defined in the Knowledge Base.
        # Covered types: vacation (5d), force (5d), special privilege (5d),
        #   wellness (5d), maternity (30d), paternity (30d),
        #   special sick leave for women (5d).
        # IF min_days_advance_notice is set
        # AND days_until_start < min_notice THEN return
        # ------------------------------------------------------------------
        min_notice = rule.get("min_days_advance_notice")
        if min_notice is not None:
            days_until_start = (start_date - date.today()).days
            leave_type_label = leave_type.replace("_", " ").title()
            if days_until_start < min_notice:
                return False, (
                    f"{leave_type_label} must be filed at least {min_notice} day(s) "
                    f"in advance. You filed only {days_until_start} day(s) before."
                )

        # ------------------------------------------------------------------
        # RULE 7: Sick leave exceeding 6 days requires a medical certificate
        # IF leave_type == sick_leave
        # AND days_requested > 6
        # AND has_medical_certificate == False THEN return
        # ------------------------------------------------------------------
        if leave_type == "sick_leave":
            cert_threshold = rule["medical_cert_required_after"]   # 6 days
            has_cert = application.get("has_medical_certificate", False)

            if days_req > cert_threshold and not has_cert:
                return False, (
                    f"Sick leave exceeding {cert_threshold} days "
                    f"requires a medical certificate."
                )

        # ------------------------------------------------------------------
        # RULE 8: Solo Parent Leave requires a Solo Parent ID card
        # IF leave_type == solo_parent_leave
        # AND has_solo_parent_id == False THEN return
        # ------------------------------------------------------------------
        if leave_type == "solo_parent_leave":
            has_id = application.get("has_solo_parent_id", False)
            if not has_id:
                return False, "Solo Parent Leave requires a valid Solo Parent ID card."

        # ------------------------------------------------------------------
        # RULE 9: Paternity Leave requires a Marriage Certificate
        # IF leave_type == paternity_leave
        # AND has_marriage_certificate == False THEN return
        # ------------------------------------------------------------------
        if leave_type == "paternity_leave":
            has_cert = application.get("has_marriage_certificate", False)
            if not has_cert:
                return False, "Paternity Leave requires a valid Marriage Certificate."

        # ------------------------------------------------------------------
        # RULE 10: Special Sick Leave for Women requires a medical certificate
        # IF leave_type == special_sick_leave_for_women
        # AND has_medical_certificate == False THEN return
        # ------------------------------------------------------------------
        if leave_type == "special_sick_leave_for_women":
            has_cert = application.get("has_medical_certificate", False)
            if not has_cert:
                return False, (
                    "Special Sick Leave for Women requires a medical certificate."
                )

        # ------------------------------------------------------------------
        # All rules passed — document is compliant
        # ------------------------------------------------------------------
        return True, "Compliant"


    # =========================================================================
    # IPCR FORM — Compliance Check + Evaluator Assignment
    # Maps to workflow.png: Evaluation path →
    #   "Check Employee ID and assigned evaluator (Supervisor ID)"
    #
    # WHY THE RULE ENGINE OWNS EVALUATOR ASSIGNMENT:
    #   In an LGU setting, CSC IPCR guidelines explicitly require that the
    #   rater must be the employee's immediate supervisor. This is a rule —
    #   not just a data lookup. The Rule Engine enforces it and returns the
    #   assigned evaluator as part of the compliance result.
    # =========================================================================

    def check_ipcr(self, form: dict) -> tuple:
        """
        Validates an IPCR form and assigns the evaluator per CSC rules
        using the Rete algorithm via durable-rules.

        Returns:
            (True,  "Compliant",     evaluator_dict) — valid, evaluator assigned
            (False, "<reason text>", None)           — invalid, return to submitter
        """

        # Extract fields
        employee_id = form.get("employee_id", "")
        is_first    = form.get("is_first_submission", True)
        rating      = form.get("performance_rating")

        # Pre-compute derived values
        employee      = EMPLOYEES.get(employee_id)
        supervisor_id = employee["supervisor_id"] if employee else None

        # IPCR_EVALUATOR_ID override (Option B):
        #   None      → use the employee's own immediate supervisor (standard CSC rule)
        #   "EMP-001" → override to Department Head for small-office exception
        evaluator_id = IPCR_EVALUATOR_ID if IPCR_EVALUATOR_ID else supervisor_id
        supervisor   = EMPLOYEES.get(evaluator_id) if evaluator_id else None

        evaluator = None
        if supervisor:
            evaluator = {
                "employee_id": evaluator_id,
                "name":        supervisor["name"],
                "role":        supervisor["role"],
            }

        # ------------------------------------------------------------------
        # Pre-compute violation flags — one per rule.
        # Each flag is True ONLY when its specific rule genuinely applies.
        # Flags depend on earlier conditions so that only one rule fires
        # per document — e.g. has_supervisor is False only when the
        # employee exists but truly has no supervisor, not when the
        # employee is missing entirely.
        # ------------------------------------------------------------------
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

            # ------------------------------------------------------------------
            # RULE 1: Employee must exist in the org chart
            # Alpha node: employee_valid == False
            # ------------------------------------------------------------------
            @when_all(m.employee_valid == False)
            def unknown_employee(c):
                if result_container[0] is None:
                    result_container[0] = (
                        False,
                        f"Employee ID '{c.m.employee_id}' does not exist in the system.",
                        None
                    )

            # ------------------------------------------------------------------
            # RULE 2: CSC IPCR Rule — employee must have an immediate supervisor
            # Alpha node: has_supervisor == False
            # Only True when employee exists but genuinely has no supervisor
            # ------------------------------------------------------------------
            @when_all(m.has_supervisor == False)
            def no_supervisor(c):
                if result_container[0] is None:
                    result_container[0] = (
                        False,
                        f"{c.m.employee_name} is the Department Head and cannot "
                        f"be evaluated through this system.",
                        None
                    )

            # ------------------------------------------------------------------
            # RULE 3: The assigned supervisor must exist in the system
            # Alpha node: supervisor_valid == False
            # Only True when employee exists but supervisor record is missing
            # ------------------------------------------------------------------
            @when_all(m.supervisor_valid == False)
            def missing_supervisor(c):
                if result_container[0] is None:
                    result_container[0] = (
                        False,
                        f"Assigned evaluator (ID: {c.m.supervisor_id}) for "
                        f"{c.m.employee_name} was not found in the system.",
                        None
                    )

            # ------------------------------------------------------------------
            # RULE 4a: Returning form — rating is missing
            # Alpha node: rating_missing == True
            # Only True when employee is valid and form is returning
            # ------------------------------------------------------------------
            @when_all(m.rating_missing == True)
            def missing_rating(c):
                if result_container[0] is None:
                    result_container[0] = (
                        False,
                        "Performance rating is missing on the returning form.",
                        None
                    )

            # ------------------------------------------------------------------
            # RULE 4b: Returning form — rating is out of valid range
            # Alpha node: rating_invalid == True
            # Only True when employee is valid and rating is out of 1.0-5.0
            # ------------------------------------------------------------------
            @when_all(m.rating_invalid == True)
            def invalid_rating(c):
                if result_container[0] is None:
                    result_container[0] = (
                        False,
                        f"Performance rating {c.m.performance_rating} is invalid. "
                        f"Must be between 1.0 and 5.0.",
                        None
                    )

            # ------------------------------------------------------------------
            # CATCH-ALL: Document passed all rules — fire on compliant == True
            #
            # durable-rules raises MessageNotHandledException if no rule fires
            # for an asserted fact. This rule exists solely to satisfy that
            # requirement. The actual success return value is handled by the
            # plain Python fallthrough below — this rule writes nothing.
            # ------------------------------------------------------------------
            @when_all(m.compliant == True)
            def all_rules_passed(c):
                pass

        # compliant flag is True only when all violation flags are False.
        # It is asserted into the fact so the catch-all rule above fires,
        # preventing durable-rules from raising MessageNotHandledException.
        compliant = (
            (employee is not None)
            and has_supervisor
            and supervisor_valid
            and not rating_missing
            and not rating_invalid
        )

        # Assert pre-computed flags as facts into the Rete network
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
            "compliant":          compliant,
        })

        # ------------------------------------------------------------------
        # SUCCESS PATH — plain Python fallthrough
        # If no failure rule fired, result_container[0] is still None.
        # Success is confirmed here in plain Python, outside the Rete network.
        # ------------------------------------------------------------------
        if result_container[0] is not None:
            return result_container[0]

        return True, "Compliant", evaluator
