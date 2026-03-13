# =============================================================================
# main.py
# SHRMS — Intelligent Workflow Routing
# Interactive CLI Demo
#
# HOW TO RUN:
#   python -X utf8 main.py
# =============================================================================

from datetime import date, timedelta
from org_and_rules import EMPLOYEES, LEAVE_TYPE_ENCODING

from workflow_router import WorkflowRouter

router = WorkflowRouter()

_LINE = "-" * 50
_DEFAULT_START = date.today() + timedelta(days=10)

# Leave types in display order (matches LEAVE_TYPE_ENCODING)
_LEAVE_TYPES = [
    ("vacation_leave",          "Vacation Leave"),
    ("sick_leave",              "Sick Leave"),
    ("maternity_leave",         "Maternity Leave"),
    ("paternity_leave",         "Paternity Leave"),
    ("solo_parent_leave",       "Solo Parent Leave"),
    ("force_leave",             "Force Leave"),
    ("special_privilege_leave", "Special Privilege Leave"),
    ("wellness_leave",          "Wellness Leave"),
]

# Which leave types require an attachment and what it's called
_ATTACHMENTS = {
    "sick_leave":              ("has_medical_certificate",   "Medical Certificate"),
    "solo_parent_leave":       ("has_solo_parent_id",        "Solo Parent ID Card"),
    "special_privilege_leave": ("has_written_justification", "Written Justification"),
    "wellness_leave":          ("has_wellness_certificate",  "Wellness Certificate"),
}


# =============================================================================
# SECTION B — Display helpers
# =============================================================================

def divider():
    print(_LINE)

def header(title):
    print()
    divider()
    print(title.upper())
    divider()

def step_header(n, name):
    print(f"\nStep {n}: {name}")
    print("-" * 30)


# =============================================================================
# SECTION C — Input helpers
# =============================================================================

def ask_yn(prompt):
    """Ask a yes/no question; return True for 'y'."""
    while True:
        ans = input(prompt).strip().lower()
        if ans in ("y", "yes"):
            return True
        if ans in ("n", "no"):
            return False
        print("  Please enter y or n.")


def ask_employee_id():
    """Prompt for a valid Employee ID; reprompt until found in EMPLOYEES."""
    while True:
        eid = input("\nEnter Employee ID (e.g. EMP-005): ").strip().upper()
        if eid in EMPLOYEES:
            return eid
        print(f"  Employee ID '{eid}' not found. Please try again.")
        print("  Valid IDs: EMP-001 to EMP-021")


def ask_ipcr_inputs(employee_id):
    """Collect IPCR form inputs interactively. Returns a form dict."""
    print()
    first = ask_yn("Is this a first submission? (y/n): ")

    rating = None
    gave_remarks = False

    if not first:
        while True:
            try:
                rating = float(input("Enter performance rating (1.0 - 5.0): ").strip())
                if 1.0 <= rating <= 5.0:
                    break
                print("  Rating must be between 1.0 and 5.0.")
            except ValueError:
                print("  Please enter a valid number (e.g. 3.5).")

        if rating < 2.5:
            gave_remarks = ask_yn("Did the evaluator provide remarks? (y/n): ")

    return {
        "employee_id":            employee_id,
        "is_first_submission":    first,
        "performance_rating":     rating,
        "evaluator_gave_remarks": gave_remarks,
    }


def ask_leave_inputs(employee_id):
    """Collect leave application inputs interactively. Returns an application dict."""
    # --- Leave type ---
    print()
    print("Leave Types:")
    for i, (_, label) in enumerate(_LEAVE_TYPES, 1):
        print(f"  [{i}] {label}")

    while True:
        try:
            choice = int(input("\nEnter leave type number (1-8): ").strip())
            if 1 <= choice <= 8:
                leave_type, _ = _LEAVE_TYPES[choice - 1]
                break
            print("  Please enter a number between 1 and 8.")
        except ValueError:
            print("  Please enter a valid number.")

    # --- Days requested ---
    while True:
        try:
            days = int(input("Days requested: ").strip())
            if days >= 1:
                break
            print("  Must request at least 1 day.")
        except ValueError:
            print("  Please enter a whole number.")

    # --- Remaining balance ---
    while True:
        try:
            balance = int(input("Remaining leave balance: ").strip())
            if balance >= 0:
                break
            print("  Balance cannot be negative.")
        except ValueError:
            print("  Please enter a whole number.")

    # --- Start date ---
    default_str = _DEFAULT_START.strftime("%Y-%m-%d")
    raw = input(f"Start date (YYYY-MM-DD) [default: {default_str}]: ").strip()
    if raw == "":
        start_date = _DEFAULT_START
    else:
        while True:
            try:
                start_date = date.fromisoformat(raw)
                break
            except ValueError:
                raw = input("  Invalid date. Enter YYYY-MM-DD: ").strip()
                if raw == "":
                    start_date = _DEFAULT_START
                    break

    # --- Attachment (conditional) ---
    attachment_fields = {
        "has_medical_certificate":   False,
        "has_solo_parent_id":        False,
        "has_written_justification": False,
        "has_wellness_certificate":  False,
    }
    if leave_type in _ATTACHMENTS:
        field_key, cert_name = _ATTACHMENTS[leave_type]
        has_cert = ask_yn(f"Do you have the required {cert_name}? (y/n): ")
        attachment_fields[field_key] = has_cert

    return {
        "employee_id":               employee_id,
        "leave_type":                leave_type,
        "days_requested":            days,
        "days_remaining_balance":    balance,
        "start_date":                start_date,
        **attachment_fields,
        # Fresh submission — decision state always starts at 0
        "dh_decision":               0,
        "hr_decision":               0,
        "has_rejection_reason":      0,
    }


# =============================================================================
# SECTION D — Result display
# =============================================================================

def display_ipcr_result(form, result):
    """Show the full two-layer pipeline output for an IPCR form."""
    header("Form Submitted")

    # --- Layer 1: Rule Engine ---
    step_header(1, "Rule Engine Check  (Rete Algorithm / Forward Chaining)")
    passed, reason, evaluator = router.rules.check_ipcr(form)

    if not passed:
        print(f"Result : FAILED")
        print(f"Reason : {reason}")
        print()
        print(">>> Form returned. Layer 2 (Decision Tree) was NOT called.")
        divider()
        return

    print(f"Result    : PASSED")
    print(f"Evaluator : {evaluator['name']} ({evaluator['role']})")

    # --- Layer 2: Decision Tree ---
    from org_and_rules import ROLE_ENCODING
    employee = EMPLOYEES[form["employee_id"]]
    features = {
        "role_encoded":        ROLE_ENCODING[employee["role"]],
        "performance_rating":  form["performance_rating"] if form["performance_rating"] is not None else 0.0,
        "is_first_submission": 1 if form["is_first_submission"] else 0,
    }
    dt = router.ipcr_dt.predict(features)

    step_header(2, "Decision Tree Prediction  (sklearn / Supervised Classification)")
    print(f"Predicted Routing Action : {dt['routing_action_label']}")
    print(f"Confidence               : {dt['confidence_pct']}%")

    # --- Routing Result ---
    action = result.get("routing_action") or result.get("action", "N/A")
    print()
    divider()
    print("ROUTING RESULT")
    divider()
    print(f"Status         : {result.get('status', '').title()}")
    print(f"Routing Action : {action}")
    if result.get("evaluator_name"):
        print(f"Routed to      : {result['evaluator_name']} ({result.get('evaluator_role', '')})")
    if result.get("rating") is not None:
        print(f"Rating         : {result['rating']}")
    if result.get("confidence_pct") is not None:
        print(f"DT Confidence  : {result['confidence_pct']}%")
    print(f"Notification   : {result.get('notification', result.get('reason', ''))}")
    divider()


def display_leave_result(application, result):
    """Show the full two-layer pipeline output for a leave application."""
    header("Form Submitted")

    # --- Layer 1: Rule Engine ---
    step_header(1, "Rule Engine Check  (Rete Algorithm / Forward Chaining)")
    passed, reason = router.rules.check_leave(application)

    if not passed:
        print(f"Result : FAILED")
        print(f"Reason : {reason}")
        print()
        print(">>> Application returned. Layer 2 (Decision Tree) was NOT called.")
        divider()
        return

    print(f"Result : PASSED")

    # --- Layer 2: Decision Tree ---
    leave_type = application["leave_type"]
    attachment_types = ("sick_leave", "solo_parent_leave", "special_privilege_leave", "wellness_leave")
    has_att = (
        (leave_type == "sick_leave"                and application.get("has_medical_certificate"))
        or (leave_type == "solo_parent_leave"      and application.get("has_solo_parent_id"))
        or (leave_type == "special_privilege_leave" and application.get("has_written_justification"))
        or (leave_type == "wellness_leave"         and application.get("has_wellness_certificate"))
        or leave_type not in attachment_types
    )
    features = {
        "leave_type_encoded":      LEAVE_TYPE_ENCODING[leave_type],
        "days_requested":          application["days_requested"],
        "days_balance":            application["days_remaining_balance"],
        "has_required_attachment": 1 if has_att else 0,
        "dh_decision":             application["dh_decision"],
        "hr_decision":             application["hr_decision"],
        "has_rejection_reason":    application["has_rejection_reason"],
    }
    dt = router.leave_dt.predict(features)

    step_header(2, "Decision Tree Prediction  (sklearn / Supervised Classification)")
    print(f"Predicted Routing Action : {dt['routing_action_label']}")
    print(f"Confidence               : {dt['confidence_pct']}%")

    # --- Routing Result ---
    print()
    divider()
    print("ROUTING RESULT")
    divider()
    print(f"Status         : {result.get('status', '').title()}")
    print(f"Routing Action : {result.get('routing_action', 'N/A')}")
    if result.get("approver_name"):
        print(f"Next Approver  : {result['approver_name']} ({result.get('approver_role', '')})")
    if result.get("confidence_pct") is not None:
        print(f"DT Confidence  : {result['confidence_pct']}%")
    print(f"Notification   : {result.get('notification', result.get('reason', ''))}")
    divider()


# =============================================================================
# SECTION E — Run handlers
# =============================================================================

def run_ipcr(employee_id):
    form   = ask_ipcr_inputs(employee_id)
    result = router.route_ipcr(form)
    display_ipcr_result(form, result)


def run_leave(employee_id):
    application = ask_leave_inputs(employee_id)
    result      = router.route_leave(application)
    display_leave_result(application, result)


# =============================================================================
# SECTION F — Menus
# =============================================================================

def action_menu(employee_id, display_name):
    """Action loop for a logged-in employee."""
    employee = EMPLOYEES[employee_id]
    print(f"\nWelcome, {display_name} ({employee['role']})")

    while True:
        print()
        divider()
        print("AVAILABLE ACTIONS")
        divider()
        print("  [1] Submit Evaluation Form (IPCR)")
        print("  [2] Submit Leave Application")
        print("  [3] Exit")
        divider()

        choice = input("Select action: ").strip()
        if choice == "1":
            run_ipcr(employee_id)
        elif choice == "2":
            run_leave(employee_id)
        elif choice == "3":
            print("\nGoodbye!\n")
            break
        else:
            print("  Invalid choice. Please enter 1, 2, or 3.")


def main():
    print()
    divider()
    print("SHRMS — Smart Human Resource Management System")
    print("Intelligent Workflow Routing (IWR)")
    divider()
    print("  Loading models...", end=" ", flush=True)
    print("Ready.")

    employee_id = ask_employee_id()
    expected    = EMPLOYEES[employee_id]["name"]
    while True:
        entered = input("Enter your name: ").strip()
        if entered.lower() == expected.lower():
            break
        print(f"  Name does not match records. Expected: {expected}")
    display_name = expected

    action_menu(employee_id, display_name)


# =============================================================================
# SECTION G — Entry point
# =============================================================================

if __name__ == "__main__":
    main()
