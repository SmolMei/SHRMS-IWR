# =============================================================================
# workflow_router.py
# SHRMS — Intelligent Workflow Routing
# Task 5 of 7 — Main Orchestrator (Evaluation + Leave Application paths)
#
# WHAT THIS FILE IS:
#   The main orchestrator for the IPCR evaluation routing.
#   This is what your web controller calls when a form is submitted.
#
# HOW IT WORKS:
#   It runs both layers in sequence:
#     Layer 1 → Rule Engine   (rule_engine.py)  — compliance check
#     Layer 2 → Decision Tree (decision_tree.py) — routing prediction
#
# STRICTLY FOLLOWS workflow.png (evaluation path — right side):
#
#   START
#     │
#     ▼
#   Submit Document
#     │
#     ▼
#   ┌─────────────────────────────────────────────────────┐
#   │  LAYER 1 — Rule Engine                              │
#   │  Check Employee ID and assigned Evaluator           │
#   └─────────────────────────────────────────────────────┘
#     │ FAIL → return document with reason (process ends here)
#     │ PASS ↓
#     ▼
#   ┌─────────────────────────────────────────────────────┐
#   │  LAYER 2 — Decision Tree                            │
#   │                                                     │
#   │  Is this a fresh submission?                        │
#   │    YES → Route to assigned Evaluator (Supervisor)   │
#   │                                                     │
#   │  Is rating >= 2.5?                                  │
#   │    YES → Passed → Save Data (forward to HR)         │
#   │                                                     │
#   │  Is rating < 2.5?                                   │
#   │    YES → Failed                                     │
#   │            Did evaluator give remarks?              │
#   │              YES → Save Data                        │
#   │              NO  → Route back to Evaluator          │
#   │                     → Give Remarks → Save Data      │
#   └─────────────────────────────────────────────────────┘
# =============================================================================

from org_and_rules import EMPLOYEES, ROLE_ENCODING, LEAVE_TYPE_ENCODING
from rule_engine import RuleEngine
from decision_tree import IPCRDecisionTree, LeaveDecisionTree


# =============================================================================
# WORKFLOW ROUTER
# =============================================================================

class WorkflowRouter:
    """
    Main entry point for the Intelligent Workflow Routing — Evaluation path.

    Usage from your controller:
        router = WorkflowRouter()
        result = router.route_ipcr(form)

    The result dict tells your controller:
        status          — "routed", "completed", or "returned"
        stage           — which step of the flowchart was reached
        routing_action  — what the system decided to do
        evaluator info  — who handles the form next (assigned by Rule Engine)
        notification    — message to display to the user
    """

    def __init__(self):
        self.rules   = RuleEngine()        # Layer 1 — Rule-Based Workflow
        self.ipcr_dt = IPCRDecisionTree()  # Layer 2 — IPCR Decision Tree
        self.leave_dt = LeaveDecisionTree() # Layer 2 — Leave Decision Tree

        # Load both trained Decision Tree models from disk on startup.
        # If setup.py has not been run yet, this will print a clear error.
        try:
            self.ipcr_dt.load()
        except FileNotFoundError as e:
            print(f"\n[ERROR] {e}\n")

        try:
            self.leave_dt.load()
        except FileNotFoundError as e:
            print(f"\n[ERROR] {e}\n")

    # =========================================================================
    # ROUTE IPCR
    # Maps to: workflow.png — RIGHT (Evaluation) path
    # =========================================================================

    def route_ipcr(self, form: dict) -> dict:
        """
        Routes an IPCR evaluation form through the full two-layer pipeline.

        Parameters:
            form (dict):
                employee_id            (str)        — e.g. "EMP-007"
                performance_rating     (float|None) — 1.0 to 5.0, or None if fresh
                is_first_submission    (bool)       — True = employee just submitted
                evaluator_gave_remarks (bool)       — True if evaluator added remarks
                                                      after a failing rating

        Returns:
            dict — routing result your controller reads and saves to the database
        """

        employee_id = form.get("employee_id")
        is_first    = form.get("is_first_submission", True)
        rating      = form.get("performance_rating")

        # ==================================================================
        # LAYER 1 — Rule Engine
        # Maps to workflow.png:
        #   "Check Employee ID and assigned evaluator (Supervisor ID)"
        #
        # The Rule Engine does two things here:
        #   1. Validates compliance (employee exists, rating valid, etc.)
        #   2. Assigns the evaluator per CSC rules (immediate supervisor = rater)
        #
        # If ANY rule fails, the form is returned right here.
        # Layer 2 (Decision Tree) is never called on a failed form.
        # ==================================================================
        passed, reason, evaluator = self.rules.check_ipcr(form)
        # evaluator is now the CSC-assigned rater returned by the Rule Engine
        # It is None if the form failed compliance

        if not passed:
            return {
                "status":       "returned",
                "stage":        "compliance_check",
                "employee_id":  employee_id,
                "reason":       reason,
                "action":       "correct_and_resubmit",
                "notification": f"Form returned. Reason: {reason}",
            }

        # Compliance passed — get the employee record
        employee = EMPLOYEES[employee_id]

        # ==================================================================
        # LAYER 2 — Decision Tree
        # Maps to workflow.png: "Employee Rating" decision diamond
        #
        # Build the feature vector and ask the Decision Tree to classify
        # the correct routing action for this form.
        # ==================================================================
        role_enc = ROLE_ENCODING[employee["role"]]

        features = {
            "role_encoded":        role_enc,
            "performance_rating":  rating if rating is not None else 0.0,
            "is_first_submission": 1 if is_first else 0,
        }

        # The Decision Tree traverses Root → Decision Nodes → Leaf Node
        dt_result = self.ipcr_dt.predict(features)
        action    = dt_result["routing_action_label"]

        # ==================================================================
        # BRANCH 1: Fresh form submission
        # Maps to workflow.png:
        #   "Route to assigned Evaluator (Supervisor)"
        #
        # The employee just submitted the form. No rating yet.
        # The evaluator was assigned by the Rule Engine above.
        # ==================================================================
        if action == "route_to_evaluator":
            return {
                "status":          "routed",
                "stage":           "sent_to_evaluator",
                "employee_id":     employee_id,
                "employee_name":   employee["name"],
                "routing_action":  action,
                "evaluator_id":    evaluator["employee_id"],
                "evaluator_name":  evaluator["name"],
                "evaluator_role":  evaluator["role"],
                "confidence_pct":  dt_result["confidence_pct"],
                "notification": (
                    f"IPCR form for {employee['name']} has been sent to "
                    f"{evaluator['name']} ({evaluator['role']}) for evaluation."
                ),
            }

        # ==================================================================
        # BRANCH 2: Passing rating (>= 2.5)
        # Maps to workflow.png:
        #   "Employee Rating < 3? → No → Passed → Save Data"
        # ==================================================================
        if action == "save_data":
            return {
                "status":          "completed",
                "stage":           "data_saved",
                "employee_id":     employee_id,
                "employee_name":   employee["name"],
                "routing_action":  action,
                "rating":          rating,
                "evaluator_id":    evaluator["employee_id"],
                "evaluator_name":  evaluator["name"],
                "evaluator_role":  evaluator["role"],
                "confidence_pct":  dt_result["confidence_pct"],
                "notification": (
                    f"IPCR for {employee['name']} passed with a rating of {rating}. "
                    f"Data saved."
                ),
            }

        # ==================================================================
        # BRANCH 3: Failing rating (< 2.5)
        # Maps to workflow.png:
        #   "Employee Rating < 3? → Yes → Failed → Gives Remarks?"
        #
        # The "Gives Remarks?" diamond is NOT handled by the Decision Tree.
        # It is a follow-up condition checked here in the orchestrator.
        # ==================================================================
        if action == "return_for_remarks":

            gave_remarks = form.get("evaluator_gave_remarks", False)

            # --------------------------------------------------------------
            # SUB-BRANCH A: Evaluator has NOT given remarks yet
            # Maps to workflow.png:
            #   "Gives Remarks? → No → Route back to assigned Evaluator
            #                       → Give Remarks"
            # --------------------------------------------------------------
            if not gave_remarks:
                return {
                    "status":          "routed",
                    "stage":           "waiting_for_remarks",
                    "employee_id":     employee_id,
                    "employee_name":   employee["name"],
                    "routing_action":  "route_back_to_evaluator",
                    "rating":          rating,
                    "evaluator_id":    evaluator["employee_id"],
                    "evaluator_name":  evaluator["name"],
                    "evaluator_role":  evaluator["role"],
                    "notification": (
                        f"Routed back to {evaluator['name']} to provide remarks."
                    ),
                }

            # --------------------------------------------------------------
            # SUB-BRANCH B: Evaluator HAS given remarks
            # Maps to workflow.png:
            #   "Gives Remarks? → Yes → Save Data"
            # --------------------------------------------------------------
            else:
                return {
                    "status":          "completed",
                    "stage":           "remarks_saved",
                    "employee_id":     employee_id,
                    "employee_name":   employee["name"],
                    "routing_action":  "save_data",
                    "rating":          rating,
                    "evaluator_id":    evaluator["employee_id"],
                    "evaluator_name":  evaluator["name"],
                    "evaluator_role":  evaluator["role"],
                    "notification": (
                        f"IPCR for {employee['name']} — failing rating of {rating}. "
                        f"Evaluator remarks recorded. Data saved."
                    ),
                }

        # ==================================================================
        # Fallback — should never reach here if Decision Tree is working correctly
        # ==================================================================
        return {
            "status": "error",
            "reason": f"Unexpected routing action from Decision Tree: '{action}'",
        }

    # =========================================================================
    # ROUTE LEAVE
    # Maps to: workflow.png — LEFT (Leave Application) path
    # =========================================================================

    def route_leave(self, application: dict) -> dict:
        """
        Routes a leave application through the full two-layer pipeline.

        Call this method whenever the application state changes:
          - When the employee submits               (fresh application)
          - When the Department Head makes a decision
          - When the HR Officer makes a decision
          - When a rejection reason is recorded

        Parameters:
            application (dict):

            # --- Who filed and what ---
            employee_id               (str)   e.g. "EMP-005"
            leave_type                (str)   e.g. "vacation_leave"
            days_requested            (int)   number of days applied for
            days_remaining_balance    (int)   remaining credits (0 for fixed-entitlement)
            start_date                (date)  planned start date — used by Rule Engine

            # --- Attachments (for Rule Engine compliance check) ---
            has_medical_certificate   (bool)  required: sick leave > 3 days
            has_solo_parent_id        (bool)  required: solo_parent_leave
            has_written_justification (bool)  required: special_privilege_leave
            has_wellness_certificate  (bool)  required: wellness_leave

            # --- Current decision state (updated by controller after each step) ---
            dh_decision               (int)   0=pending, 1=approved, 2=rejected
            hr_decision               (int)   0=pending, 1=approved, 2=rejected
            has_rejection_reason      (int)   1=recorded, 0=not yet

        Returns:
            dict — routing result your controller reads and saves to the database:
                status          "routed" | "action_required" | "completed" | "returned"
                stage           current pipeline step label
                routing_action  DT output label (human-readable)
                approver info   who handles the application next (if applicable)
                notification    message to display / log / send as notification

        CSC-ALIGNED ROUTING FLOW (matching workflow.png — leave path):

          Layer 1 — Rule Engine compliance check
            FAIL → returned immediately
            PASS ↓

          Layer 2 — Decision Tree reads decision state fields and classifies:
            Class 0 → route_to_department_head  (fresh application)
            Class 1 → route_to_hr               (DH approved)
            Class 2 → require_rejection_reason  (DH or HR rejected, no reason yet)
            Class 3 → completed                 (HR approved OR reason recorded)
        """

        employee_id = application.get("employee_id")
        leave_type  = application.get("leave_type")

        # ==================================================================
        # LAYER 1 — Rule Engine (compliance check)
        #
        # Rules checked:
        #   Rule 1  — Employee must exist in the system
        #   Rule 2  — Leave type must be a recognized CSC category
        #   Rule 3  — Days requested must be >= 1
        #   Rule 4  — Vacation/sick leave cannot exceed remaining balance
        #   Rule 5  — Fixed-entitlement leaves cannot exceed annual cap
        #   Rule 6  — Vacation leave must be filed >= 5 days in advance
        #   Rule 7  — Sick leave > 3 days requires a medical certificate
        #   Rule 8  — Solo Parent Leave requires a Solo Parent ID card
        #   Rule 9  — Special Privilege Leave requires written justification
        #   Rule 10 — Wellness Leave requires a wellness certificate
        #
        # If ANY rule fails, the application is returned immediately.
        # Layer 2 is never called on a non-compliant application.
        # ==================================================================
        passed, reason = self.rules.check_leave(application)

        if not passed:
            return {
                "status":         "returned",
                "stage":          "compliance_check",
                "employee_id":    employee_id,
                "leave_type":     leave_type,
                "days_requested": application.get("days_requested"),
                "routing_action": "returned",
                "reason":         reason,
                "notification":   f"Leave application returned. Reason: {reason}",
            }

        # Compliance passed — get full employee record
        employee = EMPLOYEES[employee_id]

        # ==================================================================
        # LAYER 2 — Leave Decision Tree
        #
        # Build the 7-feature vector:
        #   Features 1–4 describe the application itself.
        #   Features 5–7 describe the current decision state.
        # ==================================================================

        # Determine has_required_attachment from the relevant leave type
        # (Rule Engine already confirmed the attachment is present if required)
        required_checks = {
            "sick_leave":              application.get("has_medical_certificate", False),
            "solo_parent_leave":       application.get("has_solo_parent_id", False),
            "special_privilege_leave": application.get("has_written_justification", False),
            "wellness_leave":          application.get("has_wellness_certificate", False),
        }
        has_attachment = int(required_checks.get(leave_type, True))

        features = {
            "leave_type_encoded":      LEAVE_TYPE_ENCODING.get(leave_type, 0),
            "days_requested":          application.get("days_requested", 1),
            "days_balance":            application.get("days_remaining_balance", 0),
            "has_required_attachment": has_attachment,
            "dh_decision":             int(application.get("dh_decision", 0)),
            "hr_decision":             int(application.get("hr_decision", 0)),
            "has_rejection_reason":    int(application.get("has_rejection_reason", 0)),
        }

        dt_result = self.leave_dt.predict(features)
        action    = dt_result["routing_action_label"]

        # Shared fields for all result branches
        base = {
            "employee_id":    employee_id,
            "employee_name":  employee["name"],
            "leave_type":     leave_type,
            "days_requested": application.get("days_requested"),
            "routing_action": action,
            "confidence_pct": dt_result["confidence_pct"],
        }

        # ==================================================================
        # BRANCH 0 — Route to Department Head (or HR if applicant IS the DH)
        # Trigger: dh_decision == 0 (DH has not reviewed yet)
        #
        # SPECIAL CASE — Department Head as applicant:
        #   When EMP-001 (John Reyes) submits a leave application, routing
        #   it back to himself for approval is not valid. Per CSC guidelines,
        #   when the head of office is the applicant, the application is
        #   escalated directly to the HR Officer for processing.
        # ==================================================================
        if action == "route_to_department_head":

            if employee_id == "EMP-001":
                # Department Head is the applicant — DH approval stage is
                # skipped entirely. Evaluate the HR decision state directly.

                hr_dec = int(application.get("hr_decision", 0))
                has_reason = int(application.get("has_rejection_reason", 0))

                # HR already approved → completed
                if hr_dec == 1:
                    return {
                        **base,
                        "routing_action": "completed",
                        "status":        "completed",
                        "stage":         "completed",
                        "approver_id":   None,
                        "approver_name": None,
                        "approver_role": None,
                        "notification": (
                            f"Leave application for {employee['name']} "
                            f"({leave_type.replace('_', ' ').title()}, "
                            f"{application.get('days_requested')} day(s)) "
                            f"has been approved. Leave credits have been deducted."
                        ),
                    }

                # HR rejected and reason recorded → completed
                if hr_dec == 2 and has_reason == 1:
                    return {
                        **base,
                        "routing_action": "completed",
                        "status":        "completed",
                        "stage":         "completed",
                        "approver_id":   None,
                        "approver_name": None,
                        "approver_role": None,
                        "notification": (
                            f"Leave application for {employee['name']} was rejected "
                            f"by the HR Officer. Rejection reason recorded. "
                            f"Application closed."
                        ),
                    }

                # HR rejected but no reason yet → require reason
                if hr_dec == 2 and has_reason == 0:
                    return {
                        **base,
                        "routing_action": "rejection_reason_pending",
                        "status":        "action_required",
                        "stage":         "rejection_reason_pending",
                        "approver_id":   "HR",
                        "approver_name": "HR Officer",
                        "approver_role": "Human Resource Personnel",
                        "notification": (
                            f"Leave application for {employee['name']} was rejected "
                            f"by the HR Officer. A rejection reason must be recorded "
                            f"before this application can be closed."
                        ),
                    }

                # HR has not decided yet (hr_decision == 0) → escalate to HR
                return {
                    **base,
                    "routing_action": "route_to_hr",
                    "status":        "routed",
                    "stage":         "sent_to_hr",
                    "approver_id":   "HR",
                    "approver_name": "HR Officer",
                    "approver_role": "Human Resource Personnel",
                    "notification": (
                        f"Leave application for {employee['name']} "
                        f"({leave_type.replace('_', ' ').title()}, "
                        f"{application.get('days_requested')} day(s)) "
                        f"has been escalated directly to the HR Officer "
                        f"for processing."
                    ),
                }

            dept_head = EMPLOYEES["EMP-001"]
            return {
                **base,
                "status":        "routed",
                "stage":         "sent_to_department_head",
                "approver_id":   "EMP-001",
                "approver_name": dept_head["name"],
                "approver_role": dept_head["role"],
                "notification": (
                    f"Leave application for {employee['name']} "
                    f"({leave_type.replace('_', ' ').title()}, "
                    f"{application.get('days_requested')} day(s)) "
                    f"has been sent to {dept_head['name']} for review."
                ),
            }

        # ==================================================================
        # BRANCH 1 — Route to HR Officer
        # Trigger: dh_decision == 1 (DH approved), hr_decision == 0
        # ==================================================================
        if action == "route_to_hr":
            return {
                **base,
                "status":        "routed",
                "stage":         "sent_to_hr",
                "approver_id":   "HR",
                "approver_name": "HR Officer",
                "approver_role": "Human Resource Personnel",
                "notification": (
                    f"Leave application for {employee['name']} "
                    f"({leave_type.replace('_', ' ').title()}) "
                    f"approved by Department Head. "
                    f"Forwarded to HR Officer for final processing."
                ),
            }

        # ==================================================================
        # BRANCH 2 — Require Rejection Reason
        # Trigger: DH or HR rejected, has_rejection_reason == 0
        # ==================================================================
        if action == "require_rejection_reason":
            dh_dec = int(application.get("dh_decision", 0))
            if dh_dec == 2:
                rejector_name = EMPLOYEES["EMP-001"]["name"]
                rejector_role = "Department Head"
                approver_id   = "EMP-001"
            else:
                rejector_name = "HR Officer"
                rejector_role = "Human Resource Personnel"
                approver_id   = "HR"

            return {
                **base,
                "status":        "action_required",
                "stage":         "rejection_reason_pending",
                "approver_id":   approver_id,
                "approver_name": rejector_name,
                "approver_role": rejector_role,
                "notification": (
                    f"Leave application for {employee['name']} was rejected by "
                    f"{rejector_name} ({rejector_role}). "
                    f"A rejection reason must be recorded before this "
                    f"application can be closed."
                ),
            }

        # ==================================================================
        # BRANCH 3 — Completed
        # Trigger A: hr_decision == 1 (HR approved)
        # Trigger B: rejected AND has_rejection_reason == 1
        # ==================================================================
        if action == "completed":
            hr_dec = int(application.get("hr_decision", 0))
            dh_dec = int(application.get("dh_decision", 0))

            if hr_dec == 1:
                msg = (
                    f"Leave application for {employee['name']} "
                    f"({leave_type.replace('_', ' ').title()}, "
                    f"{application.get('days_requested')} day(s)) "
                    f"has been approved. Leave credits have been deducted."
                )
            elif dh_dec == 2:
                msg = (
                    f"Leave application for {employee['name']} was rejected by "
                    f"the Department Head. Rejection reason recorded. "
                    f"Application closed."
                )
            else:
                msg = (
                    f"Leave application for {employee['name']} was rejected by "
                    f"the HR Officer. Rejection reason recorded. "
                    f"Application closed."
                )

            return {
                **base,
                "status":        "completed",
                "stage":         "completed",
                "approver_id":   None,
                "approver_name": None,
                "approver_role": None,
                "notification":  msg,
            }

        # ==================================================================
        # Fallback — should never reach here
        # ==================================================================
        return {
            "status": "error",
            "reason": f"Unexpected routing action from Decision Tree: '{action}'",
        }

