# =============================================================================
# org_and_rules_no_pmt.py
# SHRMS — Intelligent Workflow Routing
# Knowledge Base — Backup (No PMT Evaluator for Department Head)
#
# WHAT THIS FILE IS:
#   A backup of org_and_rules.py saved before the PMT (Performance Management
#   Team) evaluator was assigned to the Department Head (EMP-001).
#
#   In this version:
#     - EMP-001 (John Reyes) has supervisor_id = None
#     - The Department Head cannot submit an IPCR through this system
#     - Rule 2 in check_ipcr() blocks EMP-001 with:
#       "John Reyes is the Department Head and cannot be evaluated
#        through this system."
#
# WHEN TO USE:
#   Swap this file in as org_and_rules.py if the LGU decides that the
#   Department Head's performance evaluation is handled outside the system
#   (e.g., manually or through a separate provincial-level process) and
#   does not need to be routed through the Smart HRMS.
#
# HOW TO SWAP IN:
#   1. Rename the current org_and_rules.py → org_and_rules_pmt.py
#   2. Rename this file → org_and_rules.py
#   3. Run python tests.py to confirm TC-RE-002 passes as expected
#      (expects status=returned for EMP-001 submission)
#   No retraining of Decision Tree models is needed.
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
#        ├── Maria Santos     (Administrative Officer II)
#        ├── Mark Bautista    (Administrative Officer II)
#        ├── Angela Cruz      (Administrative Officer II)
#        ├── Patricia Garcia  (Administrative Aide I)
#        ├── Kevin Mendoza    (Administrative Aide I)
#        ├── Lorraine Flores  (Administrative Aide I)
#        ├── Daniel Ramos     (Administrative Aide I)
#        ├── Camille Navarro  (Administrative Aide I)
#        ├── Joshua Aquino    (Administrative Aide I)
#        ├── Ana Dela Cruz    (Administrative Aide I)
#        ├── Ramon Villanueva (Administrative Aide I)
#        ├── Josephine Pascual(Administrative Aide I)
#        ├── Michael Torres   (Administrative Aide I)
#        ├── Liza Castillo    (Administrative Aide I)
#        ├── Roberto Jimenez  (Administrative Aide I)
#        ├── Christine Morales(Administrative Aide I)
#        ├── Ferdinand Aguilar(Administrative Aide I)
#        ├── Maricel Dela Rosa(Administrative Aide I)
#        ├── Benedict Mercado (Administrative Aide I)
#        └── Theresa Evangelista (Administrative Aide I)
#
#    Each entry has:
#      "name"          — employee full name
#      "role"          — position title
#      "supervisor_id" — employee_id of their direct superior
#                        None = top of hierarchy, no one above them
# -----------------------------------------------------------------------------

EMPLOYEES = {

    "EMP-001": {
        "name":          "John Reyes",
        "role":          "Department Head",
        "supervisor_id": None,        # Top of the office — no supervisor above him
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

    # --- Administrative Aides I (all report directly to John Reyes) ---

    "EMP-005": {
        "name":          "Patricia Garcia",
        "role":          "Administrative Aide I",
        "supervisor_id": "EMP-001",   # Reports to John Reyes
    },
    "EMP-006": {
        "name":          "Kevin Mendoza",
        "role":          "Administrative Aide I",
        "supervisor_id": "EMP-001",   # Reports to John Reyes
    },
    "EMP-007": {
        "name":          "Lorraine Flores",
        "role":          "Administrative Aide I",
        "supervisor_id": "EMP-001",   # Reports to John Reyes
    },
    "EMP-008": {
        "name":          "Daniel Ramos",
        "role":          "Administrative Aide I",
        "supervisor_id": "EMP-001",   # Reports to John Reyes
    },
    "EMP-009": {
        "name":          "Camille Navarro",
        "role":          "Administrative Aide I",
        "supervisor_id": "EMP-001",   # Reports to John Reyes
    },
    "EMP-010": {
        "name":          "Joshua Aquino",
        "role":          "Administrative Aide I",
        "supervisor_id": "EMP-001",   # Reports to John Reyes
    },

    # --- Additional Administrative Aides I (all report directly to John Reyes) ---

    "EMP-011": {
        "name":          "Ana Dela Cruz",
        "role":          "Administrative Aide I",
        "supervisor_id": "EMP-001",   # Reports to John Reyes
    },
    "EMP-012": {
        "name":          "Ramon Villanueva",
        "role":          "Administrative Aide I",
        "supervisor_id": "EMP-001",   # Reports to John Reyes
    },
    "EMP-013": {
        "name":          "Josephine Pascual",
        "role":          "Administrative Aide I",
        "supervisor_id": "EMP-001",   # Reports to John Reyes
    },
    "EMP-014": {
        "name":          "Michael Torres",
        "role":          "Administrative Aide I",
        "supervisor_id": "EMP-001",   # Reports to John Reyes
    },
    "EMP-015": {
        "name":          "Liza Castillo",
        "role":          "Administrative Aide I",
        "supervisor_id": "EMP-001",   # Reports to John Reyes
    },
    "EMP-016": {
        "name":          "Roberto Jimenez",
        "role":          "Administrative Aide I",
        "supervisor_id": "EMP-001",   # Reports to John Reyes
    },
    "EMP-017": {
        "name":          "Christine Morales",
        "role":          "Administrative Aide I",
        "supervisor_id": "EMP-001",   # Reports to John Reyes
    },
    "EMP-018": {
        "name":          "Ferdinand Aguilar",
        "role":          "Administrative Aide I",
        "supervisor_id": "EMP-001",   # Reports to John Reyes
    },
    "EMP-019": {
        "name":          "Maricel Dela Rosa",
        "role":          "Administrative Aide I",
        "supervisor_id": "EMP-001",   # Reports to John Reyes
    },
    "EMP-020": {
        "name":          "Benedict Mercado",
        "role":          "Administrative Aide I",
        "supervisor_id": "EMP-001",   # Reports to John Reyes
    },
    "EMP-021": {
        "name":          "Theresa Evangelista",
        "role":          "Administrative Aide I",
        "supervisor_id": "EMP-001",   # Reports to John Reyes
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
        "medical_cert_required_after": 6,  # Medical cert needed if sick leave exceeds 6 days
    },

    "maternity_leave": {
        "max_days":               105,
        "min_days_advance_notice": 30,  # Must file at least 30 days before expected delivery
    },

    "paternity_leave": {
        "max_days":                    7,
        "min_days_advance_notice":     30,   # Must file at least 30 days before expected delivery
        "requires_marriage_certificate": True,  # Marriage Certificate must be attached
    },

    "solo_parent_leave": {
        "max_days":                     7,
        "requires_solo_parent_id_card": True,   # Solo Parent ID card must be attached
    },

    "force_leave": {
        "max_days_per_year":      5,            # Uses vacation leave credits
        "min_days_advance_notice": 5,           # Must file at least 5 days before start date
    },

    "special_privilege_leave": {
        "max_days_per_year":      3,            # CSC MC No. 6 s. 1996 — birthday, graduation, etc.
        "min_days_advance_notice": 5,           # Must file at least 5 days before start date
    },

    "wellness_leave": {
        "max_days_per_year":      5,            # Agency wellness program — mental health / medical
        "min_days_advance_notice": 5,           # Must file at least 5 days before start date
    },

    "special_sick_leave_for_women": {
        "max_days":                    90,      # 3 months fixed entitlement
        "min_days_advance_notice":      5,      # Must file at least 5 days before start date
        "requires_medical_certificate": True,   # Medical certificate always required
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
    "vacation_leave":               0,
    "sick_leave":                   1,
    "maternity_leave":              2,
    "paternity_leave":              3,
    "solo_parent_leave":            4,
    "force_leave":                  5,
    "special_privilege_leave":      6,
    "wellness_leave":               7,
    "special_sick_leave_for_women": 8,
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
    2: "save_data",                  # Rating >= 2.5 → passed, save directly
}

# Feature column names for the Leave Application Decision Tree
# Must exactly match the column headers in leave_training_data.csv
#
# The first 4 features describe the APPLICATION itself (what was filed).
# The last 3 features describe the current DECISION STATE (what has happened so far).
# The Decision Tree uses all 7 together to determine the next routing action.
LEAVE_FEATURES = [
    # --- Application fields ---
    "leave_type_encoded",      # int   — encoded leave type (0–8)
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
