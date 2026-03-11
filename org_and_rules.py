# =============================================================================
# org_and_rules.py
# SHRMS — Intelligent Workflow Routing
# Task 1 of 7 — Knowledge Base
#
# WHAT THIS FILE IS:
#   The Knowledge Base of the Rule-Based Expert System.
#   It contains ONLY facts — no logic, no conditions, no functions.
#   Every other file in the system reads from this one.
#
# CONTAINS:
#   1. Admin Office org chart   (from Admin_Office_Structure.png)
#   2. Civil Service leave rules (from CSC Omnibus Rules on Leave)
#   3. IPCR passing threshold   (from CSC Performance Evaluation guidelines)
#   4. Decision Tree encodings  (maps text values to integers for the ML model)
# =============================================================================


# -----------------------------------------------------------------------------
# 1. ADMIN OFFICE ORG CHART
#    Source: Admin_Office_Structure.png
#
#    Hierarchy:
#      John Reyes (Department Head)
#        ├── Maria Santos (Administrative Officer II)
#        │     ├── Patricia Garcia  (Administrative Aide I)
#        │     ├── Kevin Mendoza    (Administrative Aide I)
#        │     └── Lorraine Flores  (Administrative Aide I)
#        ├── Mark Bautista (Administrative Officer II)
#        │     ├── Daniel Ramos     (Administrative Aide I)
#        │     └── Camille Navarro  (Administrative Aide I)
#        └── Angela Cruz (Administrative Officer II)
#              └── Joshua Aquino    (Administrative Aide I)
#
#    Each entry has:
#      "name"          — employee full name
#      "role"          — position title
#      "supervisor_id" — employee_id of their direct superior
#                        None = top of hierarchy, no one above them
# -----------------------------------------------------------------------------

EMPLOYEES = {

    # --- Performance Management Team (evaluates the Department Head) ---

    "PMT-001": {
        "name":          "Performance Management Team",
        "role":          "Performance Management Team",
        "supervisor_id": None,        # External evaluator — no supervisor in this office
    },

    "EMP-001": {
        "name":          "John Reyes",
        "role":          "Department Head",
        "supervisor_id": "PMT-001",   # Evaluated by the Performance Management Team
    },

    # --- Administrative Officers II (report directly to John Reyes) ---

    "EMP-002": {
        "name":          "Maria Santos",
        "role":          "Administrative Officer II",
        "supervisor_id": "EMP-001",   # Reports to John Reyes
    },
    "EMP-003": {
        "name":          "Mark Bautista",
        "role":          "Administrative Officer II",
        "supervisor_id": "EMP-001",   # Reports to John Reyes
    },
    "EMP-004": {
        "name":          "Angela Cruz",
        "role":          "Administrative Officer II",
        "supervisor_id": "EMP-001",   # Reports to John Reyes
    },

    # --- Administrative Aides I under Maria Santos ---

    "EMP-005": {
        "name":          "Patricia Garcia",
        "role":          "Administrative Aide I",
        "supervisor_id": "EMP-002",   # Reports to Maria Santos
    },
    "EMP-006": {
        "name":          "Kevin Mendoza",
        "role":          "Administrative Aide I",
        "supervisor_id": "EMP-002",   # Reports to Maria Santos
    },
    "EMP-007": {
        "name":          "Lorraine Flores",
        "role":          "Administrative Aide I",
        "supervisor_id": "EMP-002",   # Reports to Maria Santos
    },

    # --- Administrative Aides I under Mark Bautista ---

    "EMP-008": {
        "name":          "Daniel Ramos",
        "role":          "Administrative Aide I",
        "supervisor_id": "EMP-003",   # Reports to Mark Bautista
    },
    "EMP-009": {
        "name":          "Camille Navarro",
        "role":          "Administrative Aide I",
        "supervisor_id": "EMP-003",   # Reports to Mark Bautista
    },

    # --- Administrative Aide I under Angela Cruz ---

    "EMP-010": {
        "name":          "Joshua Aquino",
        "role":          "Administrative Aide I",
        "supervisor_id": "EMP-004",   # Reports to Angela Cruz
    },
}


# -----------------------------------------------------------------------------
# 2. CIVIL SERVICE LEAVE RULES
#    Source: CSC Omnibus Rules on Leave
#
#    These are the non-negotiable rules the Rule Engine (Task 2) enforces.
#    If a leave application breaks any of these, it is returned immediately.
# -----------------------------------------------------------------------------

LEAVE_RULES = {

    "vacation_leave": {
        "max_days_per_year":       15,
        "min_days_advance_notice": 5,   # Must file at least 5 days before start date
    },

    "sick_leave": {
        "max_days_per_year":           15,
        "medical_cert_required_after": 3,  # Medical cert needed if sick leave exceeds 3 days
    },

    "maternity_leave": {
        "max_days": 105,
    },

    "paternity_leave": {
        "max_days": 7,
    },

    "solo_parent_leave": {
        "max_days":                     7,
        "requires_solo_parent_id_card": True,   # Solo Parent ID card must be attached
    },

    "force_leave": {
        "max_days_per_year":      5,            # Mandatory leave ordered by the agency head
        "admin_initiated":        True,         # Filed by HR/management, not the employee
    },

    "special_privilege_leave": {
        "max_days_per_year":      3,            # CSC MC No. 6 s. 1996 — birthday, graduation, etc.
        "requires_justification": True,         # Employee must state the specific occasion
    },

    "wellness_leave": {
        "max_days_per_year":      5,            # Agency wellness program — mental health / medical
        "requires_wellness_cert": True,         # Certificate from agency wellness officer required
    },

}


# -----------------------------------------------------------------------------
# 3. IPCR PASSING THRESHOLD
#    Source: CSC Performance Evaluation Guidelines
#
#    IMPORTANT NOTE FOR YOUR THESIS DEFENSE:
#    Your draft flowchart (workflow.png) shows "Rating < 3 = Failed".
#    The correct CSC standard is 2.5 — Satisfactory is the minimum passing mark.
#    This code uses 2.5 to match your thesis manuscript and CSC guidelines.
#    You should update your flowchart to say "< 2.5" before your final defense.
# -----------------------------------------------------------------------------

IPCR_PASSING_SCORE = 2.5   # Ratings >= 2.5 are passing (Satisfactory and above)

# IPCR Evaluator Override (Option B)
#
# None   → each employee is evaluated by their own immediate supervisor
#          (standard CSC rule, correct for large offices)
#
# "EMP-001" → every employee in this office is evaluated by the Department Head
#             (set this when your LGU confirms a small-office exception)
#
# Change this one value to switch the entire office routing behavior.
IPCR_EVALUATOR_ID = None


# -----------------------------------------------------------------------------
# 4. DECISION TREE ENCODINGS
#    The ML Decision Tree only understands numbers, not strings.
#    These dictionaries convert text values into integers.
#
#    IMPORTANT: Use these same encodings in BOTH:
#      - training_data.py (when generating training records)
#      - workflow_router.py (when preparing a prediction request)
#    If the encodings don't match, the model will predict incorrectly.
# -----------------------------------------------------------------------------

# Maps leave type text → integer
LEAVE_TYPE_ENCODING = {
    "vacation_leave":          0,
    "sick_leave":              1,
    "maternity_leave":         2,
    "paternity_leave":         3,
    "solo_parent_leave":       4,
    "force_leave":             5,
    "special_privilege_leave": 6,
    "wellness_leave":          7,
}

# Maps employee role text → integer
ROLE_ENCODING = {
    "Administrative Aide I":      0,
    "Administrative Officer II":  1,
    "Department Head":            2,
}

# Maps Decision Tree output integer → human-readable routing action
# Used in the Leave Application routing
#
# Full CSC-aligned routing flow:
#
#   Employee submits → Rule Engine compliance check
#     FAIL → returned immediately (Rule Engine handles this, not the DT)
#     PASS ↓
#
#   Stage 1: Route to Department Head for initial review
#     DH APPROVED  → Stage 2: Route to HR for final processing
#     DH REJECTED  → Require rejection reason → Completed (notify employee)
#
#   Stage 2: Route to HR Officer for final approval
#     HR APPROVED  → Completed (leave recorded)
#     HR REJECTED  → Require rejection reason → Completed (notify employee)
#
# The Decision Tree classifies which action the system should take NEXT
# based on the current state of the application (dh_decision, hr_decision,
# has_rejection_reason fields):
#
#   Class 0 → route_to_department_head   fresh app, DH has not decided yet
#   Class 1 → route_to_hr               DH approved, HR has not decided yet
#   Class 2 → require_rejection_reason  DH or HR rejected, no reason given yet
#   Class 3 → completed                 HR approved OR rejection reason recorded
LEAVE_DT_ACTIONS = {
    0: "route_to_department_head",   # Stage 1 — DH initial review
    1: "route_to_hr",                # Stage 2 — HR final processing
    2: "require_rejection_reason",   # Rejected — reason must be recorded
    3: "completed",                  # HR approved OR reason recorded → done
}

# Maps Decision Tree output integer → human-readable routing action
# Used in the IPCR Form routing
IPCR_DT_ACTIONS = {
    0: "route_to_evaluator",         # Fresh form → send to assigned evaluator
    1: "return_for_remarks",         # Rating < 2.5 → evaluator must add remarks
    2: "forward_to_hr",              # Rating >= 2.5 → passed, send to HR
}

# Feature column names for the Leave Application Decision Tree
# Must exactly match the column headers in leave_training_data.csv
#
# The first 4 features describe the APPLICATION itself (what was filed).
# The last 3 features describe the current DECISION STATE (what has happened so far).
# The Decision Tree uses all 7 together to determine the next routing action.
LEAVE_FEATURES = [
    # --- Application fields ---
    "leave_type_encoded",      # int   — encoded leave type (0–7)
    "days_requested",          # int   — number of days filed
    "days_balance",            # int   — remaining leave credits (0 for fixed-entitlement)
    "has_required_attachment", # int   — 1 if required document attached, 0 if not

    # --- Decision state fields ---
    # 0 = pending (no decision yet)
    # 1 = approved
    # 2 = rejected
    "dh_decision",             # int   — Department Head's decision (0/1/2)
    "hr_decision",             # int   — HR Officer's decision (0/1/2)
    "has_rejection_reason",    # int   — 1 if rejection reason was recorded, 0 if not
]

# Feature column names for the IPCR Form Decision Tree
# Must exactly match the column headers in ipcr_training_data.csv
IPCR_FEATURES = [
    "role_encoded",          # int   — employee's role tier
    "performance_rating",    # float — IPCR score 1.0 to 5.0
    "is_first_submission",   # int   — 1 = fresh form, 0 = returning form
]
