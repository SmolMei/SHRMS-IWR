# =============================================================================
# main.py
# SHRMS — Intelligent Workflow Routing
# Thesis Adviser Presentation — CLI Demo
#
# HOW TO RUN:
#   python -X utf8 main.py
#
# WHAT THIS DOES:
#   A menu-driven demo that walks through 10 pre-scripted scenarios
#   (5 IPCR + 5 Leave) and visually exposes the two-layer pipeline:
#     Layer 1 — Rule Engine (Rete Algorithm / Forward Chaining)
#     Layer 2 — Decision Tree (sklearn / Supervised Classification)
# =============================================================================

from datetime import date, timedelta
from org_and_rules import EMPLOYEES, ROLE_ENCODING, LEAVE_TYPE_ENCODING
from workflow_router import WorkflowRouter

router = WorkflowRouter()   # loads both .pkl models once at startup

_W = 62   # box width (characters)
_FUTURE = date.today() + timedelta(days=10)


# =============================================================================
# SECTION B — Display helpers
# =============================================================================

def _hline(char="─"):
    print("  " + char * _W)

def box(title, lines):
    print()
    print("  ┌" + "─" * _W + "┐")
    print("  │  " + title.upper().ljust(_W - 2) + "  │")
    print("  ├" + "─" * _W + "┤")
    for line in lines:
        print("  │  " + str(line).ljust(_W - 2) + "  │")
    print("  └" + "─" * _W + "┘")

def section_header(text):
    print()
    print()
    print("  ╔" + "═" * _W + "╗")
    label = f"  SCENARIO: {text}"
    print("  ║" + label.ljust(_W) + "║")
    print("  ╚" + "═" * _W + "╝")

def layer_banner(n, name):
    print()
    tag = f"  [ LAYER {n} — {name} ]"
    print(tag)
    _hline()

def pause():
    input("\n  Press Enter to continue...\n")


# =============================================================================
# SECTION C — IPCR Scenarios
# =============================================================================

IPCR_SCENARIOS = [
    {
        "label":       "A — Fresh Submission",
        "description": "Patricia Garcia submits her IPCR for the first time. No rating yet.",
        "form": {
            "employee_id":            "EMP-005",
            "is_first_submission":    True,
            "performance_rating":     None,
            "evaluator_gave_remarks": False,
        },
    },
    {
        "label":       "B — Returning Form, Passing Rating (3.5)",
        "description": "Patricia Garcia's form returns with a passing rating of 3.5.",
        "form": {
            "employee_id":            "EMP-005",
            "is_first_submission":    False,
            "performance_rating":     3.5,
            "evaluator_gave_remarks": False,
        },
    },
    {
        "label":       "C — Failing Rating (1.8), No Remarks",
        "description": "Daniel Ramos received a failing rating. Evaluator has not added remarks yet.",
        "form": {
            "employee_id":            "EMP-008",
            "is_first_submission":    False,
            "performance_rating":     1.8,
            "evaluator_gave_remarks": False,
        },
    },
    {
        "label":       "D — Failing Rating (1.8), With Remarks",
        "description": "Daniel Ramos — same failing rating, evaluator has now added remarks.",
        "form": {
            "employee_id":            "EMP-008",
            "is_first_submission":    False,
            "performance_rating":     1.8,
            "evaluator_gave_remarks": True,
        },
    },
    {
        "label":       "E — Compliance Fail: Unknown Employee",
        "description": "A form submitted with an employee ID that does not exist in the system.",
        "form": {
            "employee_id":            "EMP-999",
            "is_first_submission":    True,
            "performance_rating":     None,
            "evaluator_gave_remarks": False,
        },
    },
]


# =============================================================================
# SECTION D — Leave Scenarios
# =============================================================================

LEAVE_SCENARIOS = [
    {
        "label":       "A — Fresh Vacation Leave",
        "description": "Patricia Garcia files vacation leave. No decisions yet.",
        "application": {
            "employee_id":               "EMP-005",
            "leave_type":                "vacation_leave",
            "days_requested":            3,
            "days_remaining_balance":    10,
            "start_date":                _FUTURE,
            "has_medical_certificate":   False,
            "has_solo_parent_id":        False,
            "has_written_justification": False,
            "has_wellness_certificate":  False,
            "dh_decision":               0,
            "hr_decision":               0,
            "has_rejection_reason":      0,
        },
    },
    {
        "label":       "B — Department Head Approved",
        "description": "Department Head approved. Application forwarded to HR Officer.",
        "application": {
            "employee_id":               "EMP-005",
            "leave_type":                "vacation_leave",
            "days_requested":            3,
            "days_remaining_balance":    10,
            "start_date":                _FUTURE,
            "has_medical_certificate":   False,
            "has_solo_parent_id":        False,
            "has_written_justification": False,
            "has_wellness_certificate":  False,
            "dh_decision":               1,
            "hr_decision":               0,
            "has_rejection_reason":      0,
        },
    },
    {
        "label":       "C — HR Officer Approved",
        "description": "HR Officer approved. Application complete. Leave credits deducted.",
        "application": {
            "employee_id":               "EMP-005",
            "leave_type":                "vacation_leave",
            "days_requested":            3,
            "days_remaining_balance":    10,
            "start_date":                _FUTURE,
            "has_medical_certificate":   False,
            "has_solo_parent_id":        False,
            "has_written_justification": False,
            "has_wellness_certificate":  False,
            "dh_decision":               1,
            "hr_decision":               1,
            "has_rejection_reason":      0,
        },
    },
    {
        "label":       "D — DH Rejected, No Reason Recorded",
        "description": "Daniel Ramos' leave was rejected by the Department Head. No reason yet.",
        "application": {
            "employee_id":               "EMP-008",
            "leave_type":                "vacation_leave",
            "days_requested":            2,
            "days_remaining_balance":    10,
            "start_date":                _FUTURE,
            "has_medical_certificate":   False,
            "has_solo_parent_id":        False,
            "has_written_justification": False,
            "has_wellness_certificate":  False,
            "dh_decision":               2,
            "hr_decision":               0,
            "has_rejection_reason":      0,
        },
    },
    {
        "label":       "E — Compliance Fail: Sick Leave >3 Days, No Certificate",
        "description": "Patricia Garcia files 5 days sick leave without a medical certificate.",
        "application": {
            "employee_id":               "EMP-005",
            "leave_type":                "sick_leave",
            "days_requested":            5,
            "days_remaining_balance":    10,
            "start_date":                _FUTURE,
            "has_medical_certificate":   False,
            "has_solo_parent_id":        False,
            "has_written_justification": False,
            "has_wellness_certificate":  False,
            "dh_decision":               0,
            "hr_decision":               0,
            "has_rejection_reason":      0,
        },
    },
]


# =============================================================================
# SECTION E — Demo runner functions
# =============================================================================

def _decision_label(d):
    return {0: "Pending (0)", 1: "Approved (1)", 2: "Rejected (2)"}.get(d, str(d))


def run_ipcr_scenario(s):
    form = s["form"]

    section_header(s["label"])
    print(f"\n  {s['description']}")

    # ── Input Form ──────────────────────────────────────────────────────────
    box("Input Form — IPCR Evaluation", [
        f"Employee ID           : {form['employee_id']}",
        f"First Submission      : {'Yes' if form['is_first_submission'] else 'No'}",
        f"Performance Rating    : {form['performance_rating'] if form['performance_rating'] is not None else 'None (not yet rated)'}",
        f"Evaluator Gave Remarks: {'Yes' if form.get('evaluator_gave_remarks') else 'No'}",
    ])
    pause()

    # ── Layer 1: Rule Engine ─────────────────────────────────────────────────
    layer_banner(1, "Rule Engine — Rete Algorithm (Forward Chaining)")
    passed, reason, evaluator = router.rules.check_ipcr(form)

    if passed:
        print(f"  Result    : PASSED — Document is compliant")
        print(f"  Evaluator : {evaluator['name']} ({evaluator['role']})")
        print(f"  (Layer 2 will now classify the routing action)")
    else:
        print(f"  Result    : FAILED — Document rejected")
        print(f"  Reason    : {reason}")
        print(f"  (Layer 2 is NOT called — process ends here)")
        result = router.route_ipcr(form)
        box("Final Result — Rejected by Layer 1", [
            f"Status          : {result.get('status')}",
            f"Action          : {result.get('routing_action') or result.get('action')}",
            f"Notification    : {result.get('notification')}",
        ])
        return
    pause()

    # ── Layer 2: Decision Tree ───────────────────────────────────────────────
    layer_banner(2, "Decision Tree — sklearn (Supervised Classification)")
    employee = EMPLOYEES[form["employee_id"]]
    role_enc = ROLE_ENCODING[employee["role"]]
    rating   = form["performance_rating"] if form["performance_rating"] is not None else 0.0
    features = {
        "role_encoded":        role_enc,
        "performance_rating":  rating,
        "is_first_submission": 1 if form["is_first_submission"] else 0,
    }
    dt = router.ipcr_dt.predict(features)

    print(f"  Feature Vector:")
    print(f"    role_encoded        = {features['role_encoded']}  ({employee['role']})")
    print(f"    performance_rating  = {features['performance_rating']}")
    print(f"    is_first_submission = {features['is_first_submission']}")
    print()
    print(f"  Predicted Class : {dt['routing_action_label']}")
    print(f"  Confidence      : {dt['confidence_pct']}%")
    pause()

    # ── Final Routing Decision ───────────────────────────────────────────────
    result = router.route_ipcr(form)
    action = result.get("routing_action") or result.get("action", "N/A")
    lines  = [
        f"Status          : {result.get('status')}",
        f"Routing Action  : {action}",
        f"Stage           : {result.get('stage')}",
        f"Employee        : {result.get('employee_name', '—')}",
    ]
    if result.get("evaluator_name"):
        lines.append(f"Evaluator       : {result['evaluator_name']} ({result.get('evaluator_role', '')})")
    if result.get("rating") is not None:
        lines.append(f"Rating          : {result['rating']}")
    if result.get("confidence_pct") is not None:
        lines.append(f"DT Confidence   : {result['confidence_pct']}%")
    lines.append(f"Notification    : {result.get('notification', result.get('reason', '—'))}")
    box("Final Routing Decision", lines)


def run_leave_scenario(s):
    app = s["application"]

    section_header(s["label"])
    print(f"\n  {s['description']}")

    # ── Input Form ──────────────────────────────────────────────────────────
    box("Input Form — Leave Application", [
        f"Employee ID      : {app['employee_id']}",
        f"Leave Type       : {app['leave_type'].replace('_', ' ').title()}",
        f"Days Requested   : {app['days_requested']}",
        f"Days Balance     : {app['days_remaining_balance']}",
        f"Start Date       : {app['start_date']}",
        f"DH Decision      : {_decision_label(app['dh_decision'])}",
        f"HR Decision      : {_decision_label(app['hr_decision'])}",
        f"Rejection Reason : {'Recorded' if app['has_rejection_reason'] else 'Not recorded'}",
    ])
    pause()

    # ── Layer 1: Rule Engine ─────────────────────────────────────────────────
    layer_banner(1, "Rule Engine — Rete Algorithm (Forward Chaining)")
    passed, reason = router.rules.check_leave(app)

    if passed:
        print(f"  Result    : PASSED — Application is compliant")
        print(f"  (Layer 2 will now classify the routing action)")
    else:
        print(f"  Result    : FAILED — Application rejected")
        print(f"  Reason    : {reason}")
        print(f"  (Layer 2 is NOT called — process ends here)")
        result = router.route_leave(app)
        box("Final Result — Rejected by Layer 1", [
            f"Status          : {result.get('status')}",
            f"Routing Action  : {result.get('routing_action')}",
            f"Notification    : {result.get('notification', result.get('reason', '—'))}",
        ])
        return
    pause()

    # ── Layer 2: Decision Tree ───────────────────────────────────────────────
    layer_banner(2, "Decision Tree — sklearn (Supervised Classification)")
    leave_type      = app["leave_type"]
    attachment_types = ("sick_leave", "solo_parent_leave", "special_privilege_leave", "wellness_leave")
    has_att = (
        (leave_type == "sick_leave"                and app.get("has_medical_certificate"))
        or (leave_type == "solo_parent_leave"      and app.get("has_solo_parent_id"))
        or (leave_type == "special_privilege_leave" and app.get("has_written_justification"))
        or (leave_type == "wellness_leave"         and app.get("has_wellness_certificate"))
        or leave_type not in attachment_types
    )
    features = {
        "leave_type_encoded":      LEAVE_TYPE_ENCODING[leave_type],
        "days_requested":          app["days_requested"],
        "days_balance":            app["days_remaining_balance"],
        "has_required_attachment": 1 if has_att else 0,
        "dh_decision":             app["dh_decision"],
        "hr_decision":             app["hr_decision"],
        "has_rejection_reason":    app["has_rejection_reason"],
    }
    dt = router.leave_dt.predict(features)

    print(f"  Feature Vector:")
    print(f"    leave_type_encoded      = {features['leave_type_encoded']}  ({leave_type})")
    print(f"    days_requested          = {features['days_requested']}")
    print(f"    days_balance            = {features['days_balance']}")
    print(f"    has_required_attachment = {features['has_required_attachment']}")
    print(f"    dh_decision             = {features['dh_decision']}")
    print(f"    hr_decision             = {features['hr_decision']}")
    print(f"    has_rejection_reason    = {features['has_rejection_reason']}")
    print()
    print(f"  Predicted Class : {dt['routing_action_label']}")
    print(f"  Confidence      : {dt['confidence_pct']}%")
    pause()

    # ── Final Routing Decision ───────────────────────────────────────────────
    result = router.route_leave(app)
    lines  = [
        f"Status          : {result.get('status')}",
        f"Routing Action  : {result.get('routing_action')}",
        f"Stage           : {result.get('stage')}",
        f"Employee        : {result.get('employee_name', '—')}",
    ]
    if result.get("approver_name"):
        lines.append(f"Next Approver   : {result['approver_name']} ({result.get('approver_role', '')})")
    lines.append(f"Notification    : {result.get('notification', result.get('reason', '—'))}")
    box("Final Routing Decision", lines)


# =============================================================================
# SECTION F — Menu functions
# =============================================================================

_IPCR_MENU = [
    "[A]  Fresh Submission                   -> route_to_evaluator",
    "[B]  Returning Form, Passing Rating     -> forward_to_hr",
    "[C]  Failing Rating, No Remarks         -> route_back_to_evaluator",
    "[D]  Failing Rating, With Remarks       -> save_data",
    "[E]  Compliance Fail: Unknown Employee  -> returned (Layer 1)",
    "",
    "[0]  Back to Main Menu",
]

_LEAVE_MENU = [
    "[A]  Fresh Vacation Leave               -> route_to_department_head",
    "[B]  Department Head Approved           -> route_to_hr",
    "[C]  HR Officer Approved               -> completed",
    "[D]  DH Rejected, No Reason            -> require_rejection_reason",
    "[E]  Compliance Fail: No Med. Cert.    -> returned (Layer 1)",
    "",
    "[0]  Back to Main Menu",
]

_IPCR_MAP  = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4}
_LEAVE_MAP = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4}


def ipcr_menu():
    while True:
        box("IPCR Evaluation Form — Demo Scenarios", _IPCR_MENU)
        choice = input("\n  Select scenario: ").strip().upper()
        if choice == "0":
            break
        elif choice in _IPCR_MAP:
            run_ipcr_scenario(IPCR_SCENARIOS[_IPCR_MAP[choice]])
        else:
            print("  Invalid choice. Please enter A-E or 0.")


def leave_menu():
    while True:
        box("Leave Application — Demo Scenarios", _LEAVE_MENU)
        choice = input("\n  Select scenario: ").strip().upper()
        if choice == "0":
            break
        elif choice in _LEAVE_MAP:
            run_leave_scenario(LEAVE_SCENARIOS[_LEAVE_MAP[choice]])
        else:
            print("  Invalid choice. Please enter A-E or 0.")


_MAIN_MENU = [
    "SHRMS — Smart Human Resource Management System",
    "Intelligent Workflow Routing (IWR)",
    "Thesis Adviser Presentation Demo",
    "",
    "[1]  IPCR Evaluation Form Routing",
    "[2]  Leave Application Routing",
    "",
    "[0]  Exit",
]


def main_menu():
    print()
    print("  Loading models...", end=" ", flush=True)
    print("Ready.")

    while True:
        box("Main Menu", _MAIN_MENU)
        choice = input("\n  Select: ").strip()
        if choice == "0":
            print("\n  Exiting demo. Good luck with your presentation!\n")
            break
        elif choice == "1":
            ipcr_menu()
        elif choice == "2":
            leave_menu()
        else:
            print("  Invalid choice. Please enter 1, 2, or 0.")


# =============================================================================
# SECTION G — Entry point
# =============================================================================

if __name__ == "__main__":
    main_menu()
