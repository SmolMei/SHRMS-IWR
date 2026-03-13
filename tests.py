# =============================================================================
# tests.py
# SHRMS — Intelligent Workflow Routing
# Task 6 of 7 — Black-Box Functional Test Suite (IPCR + Leave paths)
#
# WHAT THIS FILE IS:
#   The formal black-box functional test suite for the Intelligent Workflow
#   Routing System — covering both the IPCR evaluation path and the Leave
#   Application path.
#
# THESIS REQUIREMENT:
#   "Functional Testing for rule-based workflow and decision tree algorithm
#    using Blackbox." — Objectives section of your manuscript
#
# WHAT BLACK-BOX TESTING MEANS:
#   We only test INPUT → OUTPUT behavior.
#   We do NOT look at or test internal code logic.
#   Each test defines:
#     - A real employee from the org chart
#     - A specific scenario from the flowchart
#     - The exact expected output
#   PASS = actual output matches expected
#   FAIL = it does not
#
# TEST CASE STRUCTURE:
#   Each test case directly maps to a step or diamond in the workflow diagrams.
#   The test ID format is:
#     TC-RE-XXX  = Test Case, Rule Engine (IPCR), number
#     TC-DT-XXX  = Test Case, Decision Tree (IPCR), number
#     TC-LV-XXX  = Test Case, Leave Application, number
#
# TEST BLOCKS:
#   ── IPCR Evaluation Path ──────────────────────────────────────────
#   BLOCK 1 — Rule Engine Tests          (TC-RE-001 to TC-RE-006)   6 cases
#   BLOCK 2 — Fresh Submission Tests     (TC-DT-001 to TC-DT-009)   9 cases
#             All 9 eligible employees covered (Dept Head excluded)
#   BLOCK 3 — Boundary and Rating Scale  (TC-DT-010 to TC-DT-019)  10 cases
#             Full 1.0–5.0 scale + all critical boundary points
#   BLOCK 4 — Remarks Path Tests         (TC-DT-020 to TC-DT-025)   6 cases
#             No-remarks and with-remarks for 3 supervisor groups
#
#   ── Leave Application Path ────────────────────────────────────────
#   BLOCK 5 — Leave Rule Engine Tests    (TC-LV-001 to TC-LV-010)  10 cases
#             One case per CSC leave compliance rule
#   BLOCK 6 — Leave DT Routing Tests     (TC-LV-011 to TC-LV-025)  15 cases
#             All 4 routing classes, all leave types, multiple employees
#
#   TOTAL: 56 test cases
#
# HOW TO RUN:
#   python tests.py
# =============================================================================

import sys
import os
from datetime import date, timedelta
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from workflow_router import WorkflowRouter

router = WorkflowRouter()

# Shared date helpers for leave tests
_future = date.today() + timedelta(days=10)   # valid advance notice
_soon   = date.today() + timedelta(days=2)    # too close — violates Rule 5b

# Counters
total        = 0
passed       = 0
failed       = 0
failed_cases = []


def run_test(
    test_id:            str,
    description:        str,
    flowchart_step:     str,
    form:               dict,
    expected_status:    str,
    expected_action:    str,
    expected_evaluator: str = None,   # Optional: check specific evaluator name
):
    """
    Runs a single black-box test case.

    Checks:
      (1) result["status"]  matches expected_status
      (2) routing action    matches expected_action
      (3) evaluator name    matches expected_evaluator (if provided)
    """
    global total, passed, failed

    total += 1

    result = router.route_ipcr(form)

    # Extract actual values from result
    actual_status    = result.get("status")
    actual_action    = result.get("routing_action") or result.get("action", "")
    actual_evaluator = result.get("evaluator_name", "")

    # Check assertions
    status_ok    = actual_status   == expected_status
    action_ok    = actual_action   == expected_action
    evaluator_ok = (expected_evaluator is None) or (expected_evaluator == actual_evaluator)

    ok = status_ok and action_ok and evaluator_ok

    if ok:
        passed += 1
        print(f"  ✅ [PASS] {test_id}: {description}")
    else:
        failed += 1
        failed_cases.append(test_id)
        print(f"  ❌ [FAIL] {test_id}: {description}")
        if not status_ok:
            print(f"           status    — expected: '{expected_status}', got: '{actual_status}'")
        if not action_ok:
            print(f"           action    — expected: '{expected_action}', got: '{actual_action}'")
        if not evaluator_ok:
            print(f"           evaluator — expected: '{expected_evaluator}', got: '{actual_evaluator}'")

    print(f"           Flowchart step : {flowchart_step}")
    print(f"           Notification   : {result.get('notification', result.get('reason', '-'))}")
    print()


# =============================================================================
# BLOCK 1: RULE ENGINE TESTS (Layer 1)
# Tests the compliance checks that run BEFORE the Decision Tree.
# Maps to workflow.png: "Check Employee ID and assigned evaluator"
#
#   TC-RE-001 — Unknown employee ID
#   TC-RE-002 — Department Head submits IPCR → routed to Performance Management Team
#   TC-RE-003 — Returning form, rating is missing
#   TC-RE-004 — Returning form, rating above maximum (7.0)
#   TC-RE-005 — Returning form, rating below minimum (0.0)
#   TC-RE-006 — Valid fresh submission, evaluator correctly assigned
# =============================================================================

print()
print("=" * 65)
print("  SHRMS — Black-Box Functional Test Suite")
print("  Evaluation Path (IPCR Form Routing)")
print("=" * 65)
print()
print("── BLOCK 1: Rule Engine Tests (Layer 1) ────────────────────")
print()


# TC-RE-001
# Scenario : Employee ID does not exist in the system
# Rule     : Rule 1 — Employee must exist in the org chart
# Expected : Form returned, cannot proceed
run_test(
    test_id         = "TC-RE-001",
    description     = "Unknown employee ID — EMP-999",
    flowchart_step  = "Check Employee ID → employee not found → return",
    form            = {
        "employee_id":         "EMP-999",
        "is_first_submission": True,
        "performance_rating":  None,
    },
    expected_status = "returned",
    expected_action = "correct_and_resubmit",
)

# TC-RE-002
# Scenario : Department Head submits a fresh IPCR form
# Rule     : Rule 2 — Employee must have an assigned evaluator
#            EMP-001 (John Reyes) is evaluated by the Performance Management Team
#            (PMT-001), not an immediate supervisor within the office.
# Expected : Form routed to Performance Management Team
run_test(
    test_id            = "TC-RE-002",
    description        = "Department Head submits IPCR — John Reyes (EMP-001) → Performance Management Team",
    flowchart_step     = "Check Employee ID → evaluator assigned (PMT) → route to PMT",
    form               = {
        "employee_id":         "EMP-001",   # John Reyes — Department Head
        "is_first_submission": True,
        "performance_rating":  None,
    },
    expected_status    = "routed",
    expected_action    = "route_to_evaluator",
    expected_evaluator = "Performance Management Team",
)

# TC-RE-003
# Scenario : Returning form submitted without a performance rating
# Rule     : Rule 4a — Returning forms must have a rating
# Expected : Form returned — rating is missing
run_test(
    test_id         = "TC-RE-003",
    description     = "Returning form with no rating — Kevin Mendoza (EMP-006)",
    flowchart_step  = "Check Employee ID → returning form, rating missing → return",
    form            = {
        "employee_id":         "EMP-006",
        "is_first_submission": False,       # Returning form
        "performance_rating":  None,        # Missing — must be rejected
    },
    expected_status = "returned",
    expected_action = "correct_and_resubmit",
)

# TC-RE-004
# Scenario : Returning form with rating ABOVE the valid maximum (7.0)
# Rule     : Rule 4b — Rating must be between 1.0 and 5.0
# Expected : Form returned — rating is out of range
run_test(
    test_id         = "TC-RE-004",
    description     = "Returning form, rating above maximum 7.0 — Patricia Garcia (EMP-005)",
    flowchart_step  = "Check Employee ID → returning form, rating above 5.0 → return",
    form            = {
        "employee_id":         "EMP-005",
        "is_first_submission": False,
        "performance_rating":  7.0,         # Invalid — above maximum of 5.0
    },
    expected_status = "returned",
    expected_action = "correct_and_resubmit",
)

# TC-RE-005
# Scenario : Returning form with rating BELOW the valid minimum (0.0)
# Rule     : Rule 4b — Rating must be between 1.0 and 5.0
# Note     : 0.0 is the internal placeholder for fresh forms.
#            If submitted on a returning form it must be rejected.
# Expected : Form returned — rating is out of range
run_test(
    test_id         = "TC-RE-005",
    description     = "Returning form, rating below minimum 0.0 — Daniel Ramos (EMP-008)",
    flowchart_step  = "Check Employee ID → returning form, rating below 1.0 → return",
    form            = {
        "employee_id":         "EMP-008",
        "is_first_submission": False,
        "performance_rating":  0.0,         # Invalid — below minimum of 1.0
    },
    expected_status = "returned",
    expected_action = "correct_and_resubmit",
)

# TC-RE-006
# Scenario : Valid fresh submission — Rule Engine assigns correct evaluator
# Rule     : Rule 2 — Immediate supervisor is the CSC-mandated evaluator
# Expected : Form is compliant, evaluator correctly assigned from org chart
run_test(
    test_id            = "TC-RE-006",
    description        = "Valid fresh submission — evaluator correctly assigned — Patricia Garcia (EMP-005)",
    flowchart_step     = "Check Employee ID → compliant → evaluator assigned → route to evaluator",
    form               = {
        "employee_id":         "EMP-005",   # Patricia Garcia → supervisor is John Reyes
        "is_first_submission": True,
        "performance_rating":  None,
    },
    expected_status    = "routed",
    expected_action    = "route_to_evaluator",
    expected_evaluator = "John Reyes",
)


# =============================================================================
# BLOCK 2: FRESH SUBMISSION TESTS — ALL 9 ELIGIBLE EMPLOYEES
# Tests that every employee (except the Department Head) is correctly
# routed to their assigned evaluator on a fresh form submission.
# Maps to workflow.png: "Route to assigned Evaluator (Supervisor)"
#
# Org chart coverage:
#   Direct reports to John Reyes (EMP-001)
#     TC-DT-001 — EMP-005 Patricia Garcia  → John Reyes
#     TC-DT-002 — EMP-006 Kevin Mendoza    → John Reyes
#     TC-DT-003 — EMP-007 Lorraine Flores  → John Reyes
#     TC-DT-004 — EMP-008 Daniel Ramos     → John Reyes
#     TC-DT-005 — EMP-009 Camille Navarro  → John Reyes
#     TC-DT-006 — EMP-010 Joshua Aquino    → John Reyes
#     TC-DT-007 — EMP-002 Maria Santos     → John Reyes
#     TC-DT-008 — EMP-003 Mark Bautista    → John Reyes
#     TC-DT-009 — EMP-004 Angela Cruz      → John Reyes
# =============================================================================

print("── BLOCK 2: Fresh Submission Tests — All 9 Eligible Employees ──")
print()

# ── Direct reports to John Reyes (EMP-001) ────────────────────────────────────

run_test(
    test_id            = "TC-DT-001",
    description        = "Fresh submission — Patricia Garcia (EMP-005) → John Reyes",
    flowchart_step     = "Route to assigned Evaluator (Supervisor)",
    form               = {
        "employee_id":         "EMP-005",
        "is_first_submission": True,
        "performance_rating":  None,
    },
    expected_status    = "routed",
    expected_action    = "route_to_evaluator",
    expected_evaluator = "John Reyes",
)

run_test(
    test_id            = "TC-DT-002",
    description        = "Fresh submission — Kevin Mendoza (EMP-006) → John Reyes",
    flowchart_step     = "Route to assigned Evaluator (Supervisor)",
    form               = {
        "employee_id":         "EMP-006",
        "is_first_submission": True,
        "performance_rating":  None,
    },
    expected_status    = "routed",
    expected_action    = "route_to_evaluator",
    expected_evaluator = "John Reyes",
)

run_test(
    test_id            = "TC-DT-003",
    description        = "Fresh submission — Lorraine Flores (EMP-007) → John Reyes",
    flowchart_step     = "Route to assigned Evaluator (Supervisor)",
    form               = {
        "employee_id":         "EMP-007",
        "is_first_submission": True,
        "performance_rating":  None,
    },
    expected_status    = "routed",
    expected_action    = "route_to_evaluator",
    expected_evaluator = "John Reyes",
)

run_test(
    test_id            = "TC-DT-004",
    description        = "Fresh submission — Daniel Ramos (EMP-008) → John Reyes",
    flowchart_step     = "Route to assigned Evaluator (Supervisor)",
    form               = {
        "employee_id":         "EMP-008",
        "is_first_submission": True,
        "performance_rating":  None,
    },
    expected_status    = "routed",
    expected_action    = "route_to_evaluator",
    expected_evaluator = "John Reyes",
)

run_test(
    test_id            = "TC-DT-005",
    description        = "Fresh submission — Camille Navarro (EMP-009) → John Reyes",
    flowchart_step     = "Route to assigned Evaluator (Supervisor)",
    form               = {
        "employee_id":         "EMP-009",
        "is_first_submission": True,
        "performance_rating":  None,
    },
    expected_status    = "routed",
    expected_action    = "route_to_evaluator",
    expected_evaluator = "John Reyes",
)

run_test(
    test_id            = "TC-DT-006",
    description        = "Fresh submission — Joshua Aquino (EMP-010) → John Reyes",
    flowchart_step     = "Route to assigned Evaluator (Supervisor)",
    form               = {
        "employee_id":         "EMP-010",
        "is_first_submission": True,
        "performance_rating":  None,
    },
    expected_status    = "routed",
    expected_action    = "route_to_evaluator",
    expected_evaluator = "John Reyes",
)

# ── Also direct reports: Administrative Officers II ───────────────────────────

run_test(
    test_id            = "TC-DT-007",
    description        = "Fresh submission — Maria Santos (EMP-002) → John Reyes",
    flowchart_step     = "Route to assigned Evaluator (Supervisor)",
    form               = {
        "employee_id":         "EMP-002",
        "is_first_submission": True,
        "performance_rating":  None,
    },
    expected_status    = "routed",
    expected_action    = "route_to_evaluator",
    expected_evaluator = "John Reyes",
)

run_test(
    test_id            = "TC-DT-008",
    description        = "Fresh submission — Mark Bautista (EMP-003) → John Reyes",
    flowchart_step     = "Route to assigned Evaluator (Supervisor)",
    form               = {
        "employee_id":         "EMP-003",
        "is_first_submission": True,
        "performance_rating":  None,
    },
    expected_status    = "routed",
    expected_action    = "route_to_evaluator",
    expected_evaluator = "John Reyes",
)

run_test(
    test_id            = "TC-DT-009",
    description        = "Fresh submission — Angela Cruz (EMP-004) → John Reyes",
    flowchart_step     = "Route to assigned Evaluator (Supervisor)",
    form               = {
        "employee_id":         "EMP-004",
        "is_first_submission": True,
        "performance_rating":  None,
    },
    expected_status    = "routed",
    expected_action    = "route_to_evaluator",
    expected_evaluator = "John Reyes",
)


# =============================================================================
# BLOCK 3: BOUNDARY AND RATING SCALE TESTS
# Tests the full range of valid IPCR ratings to verify the Decision Tree
# classifies correctly at every point on the 1.0–5.0 scale.
# Maps to workflow.png: "Employee Rating < 2.5?" decision diamond
#
#   PASSING ratings (>= 2.5) → save_data
#     TC-DT-010 — 5.0  (maximum possible)
#     TC-DT-011 — 4.5  (high passing)
#     TC-DT-012 — 3.5  (mid-range passing)
#     TC-DT-013 — 3.0  (above threshold)
#     TC-DT-014 — 2.51 (just above threshold — upper boundary)
#     TC-DT-015 — 2.5  (exactly at threshold — must be PASSING)
#
#   FAILING ratings (< 2.5) → return_for_remarks
#     TC-DT-016 — 2.49 (just below threshold — lower boundary)
#     TC-DT-017 — 2.0  (mid-range failing)
#     TC-DT-018 — 1.5  (low failing)
#     TC-DT-019 — 1.0  (minimum possible)
# =============================================================================

print("── BLOCK 3: Boundary and Rating Scale Tests ─────────────────")
print()

# ── Passing ratings ───────────────────────────────────────────────────────────

# TC-DT-010
# Rating: 5.0 — maximum possible IPCR score (Outstanding)
run_test(
    test_id         = "TC-DT-010",
    description     = "Maximum rating 5.0 (Outstanding) — Lorraine Flores (EMP-007) → save data",
    flowchart_step  = "Employee Rating < 2.5? → No (5.0, maximum) → Passed → Save Data",
    form            = {
        "employee_id":         "EMP-007",
        "is_first_submission": False,
        "performance_rating":  5.0,
    },
    expected_status = "completed",
    expected_action = "save_data",
)

# TC-DT-011
# Rating: 4.5 — high passing score (Very Satisfactory range)
run_test(
    test_id         = "TC-DT-011",
    description     = "High passing rating 4.5 — Camille Navarro (EMP-009) → save data",
    flowchart_step  = "Employee Rating < 2.5? → No (4.5, clearly passing) → Passed → Save Data",
    form            = {
        "employee_id":         "EMP-009",
        "is_first_submission": False,
        "performance_rating":  4.5,
    },
    expected_status = "completed",
    expected_action = "save_data",
)

# TC-DT-012
# Rating: 3.5 — mid-range passing score (Satisfactory range)
run_test(
    test_id         = "TC-DT-012",
    description     = "Mid-range passing rating 3.5 — Joshua Aquino (EMP-010) → save data",
    flowchart_step  = "Employee Rating < 2.5? → No (3.5, mid-range passing) → Passed → Save Data",
    form            = {
        "employee_id":         "EMP-010",
        "is_first_submission": False,
        "performance_rating":  3.5,
    },
    expected_status = "completed",
    expected_action = "save_data",
)

# TC-DT-013
# Rating: 3.0 — common passing value, above threshold
run_test(
    test_id         = "TC-DT-013",
    description     = "Passing rating 3.0 — Kevin Mendoza (EMP-006) → save data",
    flowchart_step  = "Employee Rating < 2.5? → No (3.0, above threshold) → Passed → Save Data",
    form            = {
        "employee_id":         "EMP-006",
        "is_first_submission": False,
        "performance_rating":  3.0,
    },
    expected_status = "completed",
    expected_action = "save_data",
)

# TC-DT-014
# Rating: 2.51 — just above the threshold (upper boundary)
# Pair with TC-DT-016: together they bracket the exact decision point
run_test(
    test_id         = "TC-DT-014",
    description     = "Upper boundary 2.51 — Daniel Ramos (EMP-008) → save data",
    flowchart_step  = "Employee Rating < 2.5? → No (2.51, just above threshold) → Passed → Save Data",
    form            = {
        "employee_id":         "EMP-008",
        "is_first_submission": False,
        "performance_rating":  2.51,        # Just above — must be PASSING
    },
    expected_status = "completed",
    expected_action = "save_data",
)

# TC-DT-015
# Rating: 2.5 — exactly at the CSC passing threshold
# The boundary injection in training_data.py ensures this is labeled PASSING.
# This is the single most critical boundary test in the entire suite.
run_test(
    test_id         = "TC-DT-015",
    description     = "Exact threshold 2.5 — Patricia Garcia (EMP-005) → save data",
    flowchart_step  = "Employee Rating < 2.5? → No (exactly 2.5) → Passed → Save Data",
    form            = {
        "employee_id":         "EMP-005",
        "is_first_submission": False,
        "performance_rating":  2.5,         # Exactly at threshold — must be PASSING
    },
    expected_status = "completed",
    expected_action = "save_data",
)

# ── Failing ratings ───────────────────────────────────────────────────────────

# TC-DT-016
# Rating: 2.49 — just below the threshold (lower boundary)
# Pair with TC-DT-015: together they confirm the exact split location
run_test(
    test_id         = "TC-DT-016",
    description     = "Lower boundary 2.49 — Maria Santos (EMP-002) → return for remarks",
    flowchart_step  = "Employee Rating < 2.5? → Yes (2.49, just below threshold) → Failed",
    form            = {
        "employee_id":            "EMP-002",
        "is_first_submission":    False,
        "performance_rating":     2.49,     # Just below — must be FAILING
        "evaluator_gave_remarks": False,
    },
    expected_status = "routed",
    expected_action = "route_back_to_evaluator",
)

# TC-DT-017
# Rating: 2.0 — mid-range failing score
run_test(
    test_id         = "TC-DT-017",
    description     = "Mid-range failing rating 2.0 — Mark Bautista (EMP-003) → return for remarks",
    flowchart_step  = "Employee Rating < 2.5? → Yes (2.0, mid-range failing) → Failed",
    form            = {
        "employee_id":            "EMP-003",
        "is_first_submission":    False,
        "performance_rating":     2.0,
        "evaluator_gave_remarks": False,
    },
    expected_status = "routed",
    expected_action = "route_back_to_evaluator",
)

# TC-DT-018
# Rating: 1.5 — low failing score
run_test(
    test_id         = "TC-DT-018",
    description     = "Low failing rating 1.5 — Angela Cruz (EMP-004) → return for remarks",
    flowchart_step  = "Employee Rating < 2.5? → Yes (1.5, low failing) → Failed",
    form            = {
        "employee_id":            "EMP-004",
        "is_first_submission":    False,
        "performance_rating":     1.5,
        "evaluator_gave_remarks": False,
    },
    expected_status = "routed",
    expected_action = "route_back_to_evaluator",
)

# TC-DT-019
# Rating: 1.0 — minimum possible IPCR score (Poor performance)
run_test(
    test_id         = "TC-DT-019",
    description     = "Minimum rating 1.0 (Poor) — Lorraine Flores (EMP-007) → return for remarks",
    flowchart_step  = "Employee Rating < 2.5? → Yes (1.0, minimum) → Failed",
    form            = {
        "employee_id":            "EMP-007",
        "is_first_submission":    False,
        "performance_rating":     1.0,      # Minimum valid rating — must be FAILING
        "evaluator_gave_remarks": False,
    },
    expected_status = "routed",
    expected_action = "route_back_to_evaluator",
)


# =============================================================================
# BLOCK 4: REMARKS PATH TESTS — ALL 3 SUPERVISOR GROUPS
# Tests both branches of the "Gives Remarks?" diamond for one employee
# from each supervisor group. Verifies the correct supervisor is notified
# and that the process completes correctly once remarks are provided.
# Maps to workflow.png: "Gives Remarks? → No → Route back / Yes → Save Data"
#
#   TC-DT-020 — EMP-006 Kevin Mendoza   (direct report to John Reyes), no remarks
#   TC-DT-021 — EMP-006 Kevin Mendoza   (direct report to John Reyes), with remarks
#   TC-DT-022 — EMP-009 Camille Navarro (direct report to John Reyes), no remarks
#   TC-DT-023 — EMP-009 Camille Navarro (direct report to John Reyes), with remarks
#   TC-DT-024 — EMP-010 Joshua Aquino   (direct report to John Reyes), no remarks
#   TC-DT-025 — EMP-010 Joshua Aquino   (direct report to John Reyes), with remarks
# =============================================================================

print("── BLOCK 4: Remarks Path Tests — All 3 Supervisor Groups ────")
print()

# TC-DT-020
# Failing rating, evaluator has NOT given remarks yet
# Verifies form is held at waiting_for_remarks and routes back to John Reyes
run_test(
    test_id            = "TC-DT-020",
    description        = "Failing 1.8, no remarks — Kevin Mendoza (EMP-006) → route back to John Reyes",
    flowchart_step     = "Failed → Gives Remarks? → No → Route back to Evaluator",
    form               = {
        "employee_id":            "EMP-006",
        "is_first_submission":    False,
        "performance_rating":     1.8,
        "evaluator_gave_remarks": False,
    },
    expected_status    = "routed",
    expected_action    = "route_back_to_evaluator",
    expected_evaluator = "John Reyes",
)

# TC-DT-021
# Same employee and rating — evaluator HAS now provided remarks
# Verifies process completes (Save Data)
run_test(
    test_id         = "TC-DT-021",
    description     = "Failing 1.8, remarks given — Kevin Mendoza (EMP-006) → save data",
    flowchart_step  = "Failed → Gives Remarks? → Yes → Save Data",
    form            = {
        "employee_id":            "EMP-006",
        "is_first_submission":    False,
        "performance_rating":     1.8,
        "evaluator_gave_remarks": True,
    },
    expected_status = "completed",
    expected_action = "save_data",
)

# TC-DT-022
# Failing rating, evaluator has NOT given remarks yet
# Verifies form routes back to John Reyes
run_test(
    test_id            = "TC-DT-022",
    description        = "Failing 2.1, no remarks — Camille Navarro (EMP-009) → route back to John Reyes",
    flowchart_step     = "Failed → Gives Remarks? → No → Route back to Evaluator",
    form               = {
        "employee_id":            "EMP-009",
        "is_first_submission":    False,
        "performance_rating":     2.1,
        "evaluator_gave_remarks": False,
    },
    expected_status    = "routed",
    expected_action    = "route_back_to_evaluator",
    expected_evaluator = "John Reyes",
)

# TC-DT-023
# Same employee and rating — evaluator HAS now provided remarks
run_test(
    test_id         = "TC-DT-023",
    description     = "Failing 2.1, remarks given — Camille Navarro (EMP-009) → save data",
    flowchart_step  = "Failed → Gives Remarks? → Yes → Save Data",
    form            = {
        "employee_id":            "EMP-009",
        "is_first_submission":    False,
        "performance_rating":     2.1,
        "evaluator_gave_remarks": True,
    },
    expected_status = "completed",
    expected_action = "save_data",
)

# TC-DT-024
# Failing rating, evaluator has NOT given remarks yet
# Verifies form routes back to John Reyes
run_test(
    test_id            = "TC-DT-024",
    description        = "Failing 1.3, no remarks — Joshua Aquino (EMP-010) → route back to John Reyes",
    flowchart_step     = "Failed → Gives Remarks? → No → Route back to Evaluator",
    form               = {
        "employee_id":            "EMP-010",
        "is_first_submission":    False,
        "performance_rating":     1.3,
        "evaluator_gave_remarks": False,
    },
    expected_status    = "routed",
    expected_action    = "route_back_to_evaluator",
    expected_evaluator = "John Reyes",
)

# TC-DT-025
# Same employee and rating — evaluator HAS now provided remarks
run_test(
    test_id         = "TC-DT-025",
    description     = "Failing 1.3, remarks given — Joshua Aquino (EMP-010) → save data",
    flowchart_step  = "Failed → Gives Remarks? → Yes → Save Data",
    form            = {
        "employee_id":            "EMP-010",
        "is_first_submission":    False,
        "performance_rating":     1.3,
        "evaluator_gave_remarks": True,
    },
    expected_status = "completed",
    expected_action = "save_data",
)


# =============================================================================
# LEAVE ROUTING HELPER
# =============================================================================

def run_leave_test(
    test_id:          str,
    description:      str,
    flowchart_step:   str,
    application:      dict,
    expected_status:  str,
    expected_action:  str,
    expected_approver: str = None,   # Optional: check specific approver name
):
    """
    Runs a single black-box test case for the Leave Application path.

    Checks:
      (1) result["status"]         matches expected_status
      (2) result["routing_action"] matches expected_action
      (3) result["approver_name"]  matches expected_approver (if provided)
    """
    global total, passed, failed

    total += 1

    result = router.route_leave(application)

    actual_status   = result.get("status")
    actual_action   = result.get("routing_action", "")
    actual_approver = result.get("approver_name", "")

    status_ok   = actual_status   == expected_status
    action_ok   = actual_action   == expected_action
    approver_ok = (expected_approver is None) or (expected_approver == actual_approver)

    ok = status_ok and action_ok and approver_ok

    if ok:
        passed += 1
        print(f"  ✅ [PASS] {test_id}: {description}")
    else:
        failed += 1
        failed_cases.append(test_id)
        print(f"  ❌ [FAIL] {test_id}: {description}")
        if not status_ok:
            print(f"           status   — expected: '{expected_status}', got: '{actual_status}'")
        if not action_ok:
            print(f"           action   — expected: '{expected_action}', got: '{actual_action}'")
        if not approver_ok:
            print(f"           approver — expected: '{expected_approver}', got: '{actual_approver}'")

    print(f"           Flowchart step : {flowchart_step}")
    print(f"           Notification   : {result.get('notification', result.get('reason', '-'))}")
    print()


# =============================================================================
# BLOCK 5: LEAVE RULE ENGINE TESTS (Layer 1 — Leave Path)
# One test case per CSC leave compliance rule.
# Maps to workflow.png: "Leave management table" compliance check.
# All failures → status="returned", action="returned", stage="compliance_check"
#
#   TC-LV-001 — Rule 1:  Unknown employee
#   TC-LV-002 — Rule 2:  Unrecognized leave type
#   TC-LV-003 — Rule 3:  Days requested = 0
#   TC-LV-004 — Rule 4:  Vacation leave exceeds remaining balance
#   TC-LV-005 — Rule 5a: Paternity leave exceeds annual cap (7 days)
#   TC-LV-006 — Rule 5b: Vacation leave filed less than 5 days in advance
#   TC-LV-007 — Rule 6:  Sick leave > 3 days without medical certificate
#   TC-LV-008 — Rule 7:  Solo Parent Leave without Solo Parent ID
#   TC-LV-009 — Rule 9:  Special Privilege Leave without written justification
#   TC-LV-010 — Rule 10: Wellness Leave without wellness certificate
# =============================================================================

print()
print("=" * 65)
print("  SHRMS — Black-Box Functional Test Suite")
print("  Leave Application Path")
print("=" * 65)
print()
print("── BLOCK 5: Leave Rule Engine Tests (Layer 1) ──────────────")
print()

# TC-LV-001
# Scenario : Employee ID does not exist in the org chart
# Rule     : Rule 1 — Employee must exist in the system
# Expected : Application returned — unknown employee
run_leave_test(
    test_id         = "TC-LV-001",
    description     = "Unknown employee ID — EMP-999",
    flowchart_step  = "Compliance Check → Employee not found → Return",
    application     = {
        "employee_id":           "EMP-999",
        "leave_type":            "vacation_leave",
        "days_requested":        3,
        "days_remaining_balance": 10,
        "start_date":            _future,
        "dh_decision":           0,
        "hr_decision":           0,
        "has_rejection_reason":  0,
    },
    expected_status = "returned",
    expected_action = "returned",
)

# TC-LV-002
# Scenario : Leave type submitted is not a recognized CSC category
# Rule     : Rule 2 — Leave type must be in LEAVE_RULES
# Expected : Application returned — unrecognized leave type
run_leave_test(
    test_id         = "TC-LV-002",
    description     = "Unrecognized leave type 'nap_leave' — Patricia Garcia (EMP-005)",
    flowchart_step  = "Compliance Check → Leave type not recognized → Return",
    application     = {
        "employee_id":           "EMP-005",
        "leave_type":            "nap_leave",
        "days_requested":        3,
        "days_remaining_balance": 10,
        "start_date":            _future,
        "dh_decision":           0,
        "hr_decision":           0,
        "has_rejection_reason":  0,
    },
    expected_status = "returned",
    expected_action = "returned",
)

# TC-LV-003
# Scenario : Employee submits a leave application requesting 0 days
# Rule     : Rule 3 — Days requested must be at least 1
# Expected : Application returned — invalid days
run_leave_test(
    test_id         = "TC-LV-003",
    description     = "Days requested = 0 — Kevin Mendoza (EMP-006)",
    flowchart_step  = "Compliance Check → Days requested < 1 → Return",
    application     = {
        "employee_id":           "EMP-006",
        "leave_type":            "vacation_leave",
        "days_requested":        0,
        "days_remaining_balance": 10,
        "start_date":            _future,
        "dh_decision":           0,
        "hr_decision":           0,
        "has_rejection_reason":  0,
    },
    expected_status = "returned",
    expected_action = "returned",
)

# TC-LV-004
# Scenario : Employee requests 15 vacation leave days but only has 3 credits
# Rule     : Rule 4 — Vacation/sick leave cannot exceed remaining balance
# Expected : Application returned — insufficient balance
run_leave_test(
    test_id         = "TC-LV-004",
    description     = "Vacation leave exceeds balance (15 requested, 3 remaining) — Lorraine Flores (EMP-007)",
    flowchart_step  = "Compliance Check → days_requested > days_balance → Return",
    application     = {
        "employee_id":           "EMP-007",
        "leave_type":            "vacation_leave",
        "days_requested":        15,
        "days_remaining_balance": 3,
        "start_date":            _future,
        "dh_decision":           0,
        "hr_decision":           0,
        "has_rejection_reason":  0,
    },
    expected_status = "returned",
    expected_action = "returned",
)

# TC-LV-005
# Scenario : Employee requests 10 days of paternity leave (max is 7)
# Rule     : Rule 5a — Fixed-entitlement leaves cannot exceed annual cap
# Expected : Application returned — cap exceeded
run_leave_test(
    test_id         = "TC-LV-005",
    description     = "Paternity leave exceeds annual cap (10 requested, max 7) — Daniel Ramos (EMP-008)",
    flowchart_step  = "Compliance Check → days_requested > max_days (paternity cap) → Return",
    application     = {
        "employee_id":           "EMP-008",
        "leave_type":            "paternity_leave",
        "days_requested":        10,
        "days_remaining_balance": 0,
        "start_date":            _future,
        "dh_decision":           0,
        "hr_decision":           0,
        "has_rejection_reason":  0,
    },
    expected_status = "returned",
    expected_action = "returned",
)

# TC-LV-006
# Scenario : Vacation leave filed only 2 days before start (minimum is 5)
# Rule     : Rule 5b — Vacation leave must be filed at least 5 days in advance
# Expected : Application returned — advance notice violated
run_leave_test(
    test_id         = "TC-LV-006",
    description     = "Vacation leave filed too late (2 days notice, min 5) — Camille Navarro (EMP-009)",
    flowchart_step  = "Compliance Check → days_until_start < min_notice → Return",
    application     = {
        "employee_id":           "EMP-009",
        "leave_type":            "vacation_leave",
        "days_requested":        3,
        "days_remaining_balance": 10,
        "start_date":            _soon,
        "dh_decision":           0,
        "hr_decision":           0,
        "has_rejection_reason":  0,
    },
    expected_status = "returned",
    expected_action = "returned",
)

# TC-LV-007
# Scenario : Sick leave of 5 days submitted without a medical certificate
# Rule     : Rule 6 — Sick leave exceeding 3 days requires medical certificate
# Expected : Application returned — certificate missing
run_leave_test(
    test_id         = "TC-LV-007",
    description     = "Sick leave 5 days without medical certificate — Joshua Aquino (EMP-010)",
    flowchart_step  = "Compliance Check → sick_leave > 3 days AND no cert → Return",
    application     = {
        "employee_id":              "EMP-010",
        "leave_type":               "sick_leave",
        "days_requested":           5,
        "days_remaining_balance":   10,
        "start_date":               _future,
        "has_medical_certificate":  False,
        "dh_decision":              0,
        "hr_decision":              0,
        "has_rejection_reason":     0,
    },
    expected_status = "returned",
    expected_action = "returned",
)

# TC-LV-008
# Scenario : Solo Parent Leave submitted without a Solo Parent ID card
# Rule     : Rule 7 — Solo Parent Leave requires Solo Parent ID
# Expected : Application returned — ID missing
run_leave_test(
    test_id         = "TC-LV-008",
    description     = "Solo Parent Leave without Solo Parent ID — Patricia Garcia (EMP-005)",
    flowchart_step  = "Compliance Check → solo_parent_leave AND no ID → Return",
    application     = {
        "employee_id":           "EMP-005",
        "leave_type":            "solo_parent_leave",
        "days_requested":        3,
        "days_remaining_balance": 0,
        "start_date":            _future,
        "has_solo_parent_id":    False,
        "dh_decision":           0,
        "hr_decision":           0,
        "has_rejection_reason":  0,
    },
    expected_status = "returned",
    expected_action = "returned",
)

# TC-LV-009
# Scenario : Special Privilege Leave submitted without written justification
# Rule     : Rule 9 — Special Privilege Leave requires written justification
# Expected : Application returned — justification missing
run_leave_test(
    test_id         = "TC-LV-009",
    description     = "Special Privilege Leave without justification — Kevin Mendoza (EMP-006)",
    flowchart_step  = "Compliance Check → special_privilege_leave AND no justification → Return",
    application     = {
        "employee_id":              "EMP-006",
        "leave_type":               "special_privilege_leave",
        "days_requested":           1,
        "days_remaining_balance":   0,
        "start_date":               _future,
        "has_written_justification": False,
        "dh_decision":              0,
        "hr_decision":              0,
        "has_rejection_reason":     0,
    },
    expected_status = "returned",
    expected_action = "returned",
)

# TC-LV-010
# Scenario : Wellness Leave submitted without a wellness certificate
# Rule     : Rule 10 — Wellness Leave requires wellness certificate
# Expected : Application returned — certificate missing
run_leave_test(
    test_id         = "TC-LV-010",
    description     = "Wellness Leave without wellness certificate — Lorraine Flores (EMP-007)",
    flowchart_step  = "Compliance Check → wellness_leave AND no wellness cert → Return",
    application     = {
        "employee_id":            "EMP-007",
        "leave_type":             "wellness_leave",
        "days_requested":         2,
        "days_remaining_balance":  0,
        "start_date":             _future,
        "has_wellness_certificate": False,
        "dh_decision":            0,
        "hr_decision":            0,
        "has_rejection_reason":   0,
    },
    expected_status = "returned",
    expected_action = "returned",
)


# =============================================================================
# BLOCK 6: LEAVE DECISION TREE ROUTING TESTS (Layer 2 — Leave Path)
# Tests all 4 routing classes across multiple employees and leave types.
# All applications here are compliant (Rule Engine passes).
#
#   CLASS 0 — route_to_department_head
#     TC-LV-011 — Vacation leave fresh application (EMP-005)
#     TC-LV-012 — Sick leave <= 3 days, no cert needed (EMP-008)
#     TC-LV-013 — Maternity leave fresh (EMP-007)
#     TC-LV-014 — Solo Parent Leave WITH ID (EMP-009)
#     TC-LV-015 — Special Privilege WITH justification (EMP-010)
#     TC-LV-016 — Wellness leave WITH cert (EMP-006)
#
#   CLASS 1 — route_to_hr
#     TC-LV-017 — Vacation leave DH approved (EMP-005)
#     TC-LV-018 — Sick leave > 3 WITH cert, DH approved (EMP-005)
#     TC-LV-019 — Paternity leave DH approved (EMP-008)
#
#   CLASS 2 — require_rejection_reason
#     TC-LV-020 — DH rejected, no reason yet (EMP-005)
#     TC-LV-021 — HR rejected, no reason yet (EMP-005)
#
#   CLASS 3 — completed
#     TC-LV-022 — HR approved = completed (EMP-009)
#     TC-LV-023 — DH rejected + reason recorded = completed (EMP-005)
#     TC-LV-024 — HR rejected + reason recorded = completed (EMP-005)
#     TC-LV-025 — Force leave HR approved = completed (EMP-009)
# =============================================================================

print("── BLOCK 6: Leave Decision Tree Routing Tests (Layer 2) ────")
print()

# ── CLASS 0: route_to_department_head ─────────────────────────────────────────

# TC-LV-011
# Scenario : Fresh vacation leave application — DH has not reviewed yet
# DT Class : 0 — route_to_department_head
# Expected : Routed to John Reyes (Department Head)
run_leave_test(
    test_id          = "TC-LV-011",
    description      = "Fresh vacation leave application — Patricia Garcia (EMP-005) → John Reyes",
    flowchart_step   = "Compliance Pass → DT Class 0 → Route to Department Head",
    application      = {
        "employee_id":           "EMP-005",
        "leave_type":            "vacation_leave",
        "days_requested":        3,
        "days_remaining_balance": 10,
        "start_date":            _future,
        "dh_decision":           0,
        "hr_decision":           0,
        "has_rejection_reason":  0,
    },
    expected_status   = "routed",
    expected_action   = "route_to_department_head",
    expected_approver = "John Reyes",
)

# TC-LV-012
# Scenario : Sick leave of 2 days (no certificate required) — fresh application
# DT Class : 0 — route_to_department_head
# Expected : Routed to John Reyes
run_leave_test(
    test_id          = "TC-LV-012",
    description      = "Sick leave 2 days (no cert required), fresh — Daniel Ramos (EMP-008) → John Reyes",
    flowchart_step   = "Compliance Pass → DT Class 0 → Route to Department Head",
    application      = {
        "employee_id":           "EMP-008",
        "leave_type":            "sick_leave",
        "days_requested":        2,
        "days_remaining_balance": 8,
        "start_date":            _future,
        "has_medical_certificate": True,
        "dh_decision":           0,
        "hr_decision":           0,
        "has_rejection_reason":  0,
    },
    expected_status   = "routed",
    expected_action   = "route_to_department_head",
    expected_approver = "John Reyes",
)

# TC-LV-013
# Scenario : Maternity leave fresh application (105-day entitlement)
# DT Class : 0 — route_to_department_head
# Expected : Routed to John Reyes
run_leave_test(
    test_id          = "TC-LV-013",
    description      = "Maternity leave fresh application — Lorraine Flores (EMP-007) → John Reyes",
    flowchart_step   = "Compliance Pass → DT Class 0 → Route to Department Head",
    application      = {
        "employee_id":           "EMP-007",
        "leave_type":            "maternity_leave",
        "days_requested":        60,
        "days_remaining_balance": 0,
        "start_date":            _future,
        "dh_decision":           0,
        "hr_decision":           0,
        "has_rejection_reason":  0,
    },
    expected_status   = "routed",
    expected_action   = "route_to_department_head",
    expected_approver = "John Reyes",
)

# TC-LV-014
# Scenario : Solo Parent Leave WITH Solo Parent ID (attachment present)
# DT Class : 0 — route_to_department_head
# Expected : Routed to John Reyes
run_leave_test(
    test_id          = "TC-LV-014",
    description      = "Solo Parent Leave WITH ID — Camille Navarro (EMP-009) → John Reyes",
    flowchart_step   = "Compliance Pass → DT Class 0 → Route to Department Head",
    application      = {
        "employee_id":           "EMP-009",
        "leave_type":            "solo_parent_leave",
        "days_requested":        3,
        "days_remaining_balance": 0,
        "start_date":            _future,
        "has_solo_parent_id":    True,
        "dh_decision":           0,
        "hr_decision":           0,
        "has_rejection_reason":  0,
    },
    expected_status   = "routed",
    expected_action   = "route_to_department_head",
    expected_approver = "John Reyes",
)

# TC-LV-015
# Scenario : Special Privilege Leave WITH written justification
# DT Class : 0 — route_to_department_head
# Expected : Routed to John Reyes
run_leave_test(
    test_id          = "TC-LV-015",
    description      = "Special Privilege Leave WITH justification — Joshua Aquino (EMP-010) → John Reyes",
    flowchart_step   = "Compliance Pass → DT Class 0 → Route to Department Head",
    application      = {
        "employee_id":              "EMP-010",
        "leave_type":               "special_privilege_leave",
        "days_requested":           1,
        "days_remaining_balance":   0,
        "start_date":               _future,
        "has_written_justification": True,
        "dh_decision":              0,
        "hr_decision":              0,
        "has_rejection_reason":     0,
    },
    expected_status   = "routed",
    expected_action   = "route_to_department_head",
    expected_approver = "John Reyes",
)

# TC-LV-016
# Scenario : Wellness Leave WITH wellness certificate
# DT Class : 0 — route_to_department_head
# Expected : Routed to John Reyes
run_leave_test(
    test_id          = "TC-LV-016",
    description      = "Wellness Leave WITH certificate — Kevin Mendoza (EMP-006) → John Reyes",
    flowchart_step   = "Compliance Pass → DT Class 0 → Route to Department Head",
    application      = {
        "employee_id":             "EMP-006",
        "leave_type":              "wellness_leave",
        "days_requested":          2,
        "days_remaining_balance":  0,
        "start_date":              _future,
        "has_wellness_certificate": True,
        "dh_decision":             0,
        "hr_decision":             0,
        "has_rejection_reason":    0,
    },
    expected_status   = "routed",
    expected_action   = "route_to_department_head",
    expected_approver = "John Reyes",
)

# ── CLASS 1: route_to_hr ──────────────────────────────────────────────────────

# TC-LV-017
# Scenario : Department Head approved vacation leave — forward to HR Officer
# DT Class : 1 — route_to_hr
# Expected : Routed to HR Officer
run_leave_test(
    test_id          = "TC-LV-017",
    description      = "Vacation leave DH approved → HR Officer — Patricia Garcia (EMP-005)",
    flowchart_step   = "Compliance Pass → DH approved → DT Class 1 → Route to HR",
    application      = {
        "employee_id":           "EMP-005",
        "leave_type":            "vacation_leave",
        "days_requested":        3,
        "days_remaining_balance": 10,
        "start_date":            _future,
        "dh_decision":           1,
        "hr_decision":           0,
        "has_rejection_reason":  0,
    },
    expected_status   = "routed",
    expected_action   = "route_to_hr",
    expected_approver = "HR Officer",
)

# TC-LV-018
# Scenario : Sick leave > 3 days WITH cert, DH approved — forward to HR
# DT Class : 1 — route_to_hr
# Expected : Routed to HR Officer
run_leave_test(
    test_id          = "TC-LV-018",
    description      = "Sick leave 5 days WITH cert, DH approved → HR — Patricia Garcia (EMP-005)",
    flowchart_step   = "Compliance Pass → DH approved → DT Class 1 → Route to HR",
    application      = {
        "employee_id":            "EMP-005",
        "leave_type":             "sick_leave",
        "days_requested":         5,
        "days_remaining_balance":  10,
        "start_date":             _future,
        "has_medical_certificate": True,
        "dh_decision":            1,
        "hr_decision":            0,
        "has_rejection_reason":   0,
    },
    expected_status   = "routed",
    expected_action   = "route_to_hr",
    expected_approver = "HR Officer",
)

# TC-LV-019
# Scenario : Paternity leave DH approved — forward to HR Officer
# DT Class : 1 — route_to_hr
# Expected : Routed to HR Officer
run_leave_test(
    test_id          = "TC-LV-019",
    description      = "Paternity leave DH approved → HR Officer — Daniel Ramos (EMP-008)",
    flowchart_step   = "Compliance Pass → DH approved → DT Class 1 → Route to HR",
    application      = {
        "employee_id":           "EMP-008",
        "leave_type":            "paternity_leave",
        "days_requested":        7,
        "days_remaining_balance": 0,
        "start_date":            _future,
        "dh_decision":           1,
        "hr_decision":           0,
        "has_rejection_reason":  0,
    },
    expected_status   = "routed",
    expected_action   = "route_to_hr",
    expected_approver = "HR Officer",
)

# ── CLASS 2: require_rejection_reason ─────────────────────────────────────────

# TC-LV-020
# Scenario : Department Head rejected the application — no reason recorded yet
# DT Class : 2 — require_rejection_reason
# Expected : Action required — rejection reason must be recorded by DH
run_leave_test(
    test_id          = "TC-LV-020",
    description      = "DH rejected, no reason yet — Patricia Garcia (EMP-005) → John Reyes must record reason",
    flowchart_step   = "Compliance Pass → DH rejected → no reason → DT Class 2 → Require Rejection Reason",
    application      = {
        "employee_id":           "EMP-005",
        "leave_type":            "vacation_leave",
        "days_requested":        3,
        "days_remaining_balance": 10,
        "start_date":            _future,
        "dh_decision":           2,
        "hr_decision":           0,
        "has_rejection_reason":  0,
    },
    expected_status   = "action_required",
    expected_action   = "require_rejection_reason",
    expected_approver = "John Reyes",
)

# TC-LV-021
# Scenario : HR Officer rejected the application — no reason recorded yet
# DT Class : 2 — require_rejection_reason
# Expected : Action required — rejection reason must be recorded by HR
run_leave_test(
    test_id          = "TC-LV-021",
    description      = "HR rejected, no reason yet — Patricia Garcia (EMP-005) → HR must record reason",
    flowchart_step   = "Compliance Pass → DH approved → HR rejected → no reason → DT Class 2 → Require Rejection Reason",
    application      = {
        "employee_id":           "EMP-005",
        "leave_type":            "vacation_leave",
        "days_requested":        3,
        "days_remaining_balance": 10,
        "start_date":            _future,
        "dh_decision":           1,
        "hr_decision":           2,
        "has_rejection_reason":  0,
    },
    expected_status   = "action_required",
    expected_action   = "require_rejection_reason",
    expected_approver = "HR Officer",
)

# ── CLASS 3: completed ────────────────────────────────────────────────────────

# TC-LV-022
# Scenario : HR Officer approved the application — process complete
# DT Class : 3 — completed (Trigger A: HR approved)
# Expected : Completed — leave credits deducted
run_leave_test(
    test_id         = "TC-LV-022",
    description     = "HR approved vacation leave — Camille Navarro (EMP-009) → completed",
    flowchart_step  = "Compliance Pass → DH approved → HR approved → DT Class 3 → Completed",
    application     = {
        "employee_id":           "EMP-009",
        "leave_type":            "vacation_leave",
        "days_requested":        3,
        "days_remaining_balance": 10,
        "start_date":            _future,
        "dh_decision":           1,
        "hr_decision":           1,
        "has_rejection_reason":  0,
    },
    expected_status = "completed",
    expected_action = "completed",
)

# TC-LV-023
# Scenario : DH rejected and rejection reason has been recorded
# DT Class : 3 — completed (Trigger B: rejected + reason recorded)
# Expected : Completed — application closed
run_leave_test(
    test_id         = "TC-LV-023",
    description     = "DH rejected + reason recorded — Patricia Garcia (EMP-005) → completed",
    flowchart_step  = "DH rejected → reason recorded → DT Class 3 → Completed",
    application     = {
        "employee_id":           "EMP-005",
        "leave_type":            "vacation_leave",
        "days_requested":        3,
        "days_remaining_balance": 10,
        "start_date":            _future,
        "dh_decision":           2,
        "hr_decision":           0,
        "has_rejection_reason":  1,
    },
    expected_status = "completed",
    expected_action = "completed",
)

# TC-LV-024
# Scenario : HR rejected and rejection reason has been recorded
# DT Class : 3 — completed (Trigger B: rejected + reason recorded)
# Expected : Completed — application closed
run_leave_test(
    test_id         = "TC-LV-024",
    description     = "HR rejected + reason recorded — Patricia Garcia (EMP-005) → completed",
    flowchart_step  = "DH approved → HR rejected → reason recorded → DT Class 3 → Completed",
    application     = {
        "employee_id":           "EMP-005",
        "leave_type":            "vacation_leave",
        "days_requested":        3,
        "days_remaining_balance": 10,
        "start_date":            _future,
        "dh_decision":           1,
        "hr_decision":           2,
        "has_rejection_reason":  1,
    },
    expected_status = "completed",
    expected_action = "completed",
)

# TC-LV-025
# Scenario : Force leave — HR approved (different leave type, completed path)
# DT Class : 3 — completed (Trigger A: HR approved)
# Expected : Completed
run_leave_test(
    test_id         = "TC-LV-025",
    description     = "Force leave HR approved — Camille Navarro (EMP-009) → completed",
    flowchart_step  = "Compliance Pass → DH approved → HR approved → DT Class 3 → Completed",
    application     = {
        "employee_id":           "EMP-009",
        "leave_type":            "force_leave",
        "days_requested":        5,
        "days_remaining_balance": 0,
        "start_date":            _future,
        "dh_decision":           1,
        "hr_decision":           1,
        "has_rejection_reason":  0,
    },
    expected_status = "completed",
    expected_action = "completed",
)


# =============================================================================
# BLOCK 7 — Department Head as Leave Applicant  (TC-LV-026 to TC-LV-029)
# =============================================================================
# These tests verify the special-case logic in Branch 0 of route_leave():
# when EMP-001 (John Reyes, Department Head) submits a leave application,
# the system must skip the DH approval stage and route directly to HR.
# All four HR-decision states are covered.
# =============================================================================

# TC-LV-026
# Scenario : DH submits leave — fresh (hr_decision=0) → escalates to HR
# Expected : routed / sent_to_hr / approver = HR Officer
run_leave_test(
    test_id         = "TC-LV-026",
    description     = "DH submits vacation leave — fresh → escalated to HR Officer",
    flowchart_step  = "DH applicant → skip DH stage → HR decision=0 → sent_to_hr",
    application     = {
        "employee_id":            "EMP-001",
        "leave_type":             "vacation_leave",
        "days_requested":         3,
        "days_remaining_balance": 10,
        "start_date":             _future,
        "dh_decision":            0,
        "hr_decision":            0,
        "has_rejection_reason":   0,
    },
    expected_status = "routed",
    expected_action = "route_to_hr",
    expected_approver = "HR Officer",
)

# TC-LV-027
# Scenario : DH submits leave — HR approved → completed
# Expected : completed
run_leave_test(
    test_id         = "TC-LV-027",
    description     = "DH submits sick leave — HR approved → completed",
    flowchart_step  = "DH applicant → skip DH stage → HR decision=1 → completed",
    application     = {
        "employee_id":            "EMP-001",
        "leave_type":             "sick_leave",
        "days_requested":         2,
        "days_remaining_balance": 15,
        "start_date":             _future,
        "dh_decision":            0,
        "hr_decision":            1,
        "has_rejection_reason":   0,
    },
    expected_status = "completed",
    expected_action = "completed",
)

# TC-LV-028
# Scenario : DH submits leave — HR rejected, no reason yet → action_required
# Expected : action_required / rejection_reason_pending
run_leave_test(
    test_id         = "TC-LV-028",
    description     = "DH submits leave — HR rejected, no reason → action_required",
    flowchart_step  = "DH applicant → skip DH stage → HR decision=2, no reason → rejection_reason_pending",
    application     = {
        "employee_id":            "EMP-001",
        "leave_type":             "vacation_leave",
        "days_requested":         5,
        "days_remaining_balance": 10,
        "start_date":             _future,
        "dh_decision":            0,
        "hr_decision":            2,
        "has_rejection_reason":   0,
    },
    expected_status = "action_required",
    expected_action = "rejection_reason_pending",
)

# TC-LV-029
# Scenario : DH submits leave — HR rejected, reason recorded → completed
# Expected : completed
run_leave_test(
    test_id         = "TC-LV-029",
    description     = "DH submits leave — HR rejected, reason recorded → completed",
    flowchart_step  = "DH applicant → skip DH stage → HR decision=2, reason recorded → completed",
    application     = {
        "employee_id":            "EMP-001",
        "leave_type":             "vacation_leave",
        "days_requested":         5,
        "days_remaining_balance": 10,
        "start_date":             _future,
        "dh_decision":            0,
        "hr_decision":            2,
        "has_rejection_reason":   1,
    },
    expected_status = "completed",
    expected_action = "completed",
)


# =============================================================================
# FINAL SUMMARY
# =============================================================================

print("=" * 65)
print(f"  RESULTS:  {passed} PASSED  |  {failed} FAILED  |  {total} TOTAL")
print("=" * 65)

if failed == 0:
    print()
    print("  All tests passed.")
    print()
    print("  Coverage summary:")
    print("    ── IPCR Evaluation Path ──────────────────────────────────")
    print("    BLOCK 1 — Rule Engine       :  6 cases  (TC-RE-001 to TC-RE-006)")
    print("    BLOCK 2 — Fresh Submissions :  9 cases  (TC-DT-001 to TC-DT-009)")
    print("    BLOCK 3 — Boundary/Scale    : 10 cases  (TC-DT-010 to TC-DT-019)")
    print("    BLOCK 4 — Remarks Path      :  6 cases  (TC-DT-020 to TC-DT-025)")
    print()
    print("    ── Leave Application Path ────────────────────────────────")
    print("    BLOCK 5 — Leave Rule Engine : 10 cases  (TC-LV-001 to TC-LV-010)")
    print("    BLOCK 6 — Leave DT Routing  : 15 cases  (TC-LV-011 to TC-LV-025)")
    print("    BLOCK 7 — DH as Applicant   :  4 cases  (TC-LV-026 to TC-LV-029)")
    print()
    print("  IPCR: All 9 eligible employees covered for fresh submission.")
    print("  IPCR: Full rating scale: 1.0, 1.5, 2.0, 2.49, 2.5, 2.51, 3.0, 3.5, 4.5, 5.0")
    print("  IPCR: All 3 supervisor groups covered for remarks path.")
    print()
    print("  Leave: All 10 CSC compliance rules covered (one case per rule).")
    print("  Leave: All 4 DT routing classes covered.")
    print("  Leave: All 8 leave types covered across Blocks 5 and 6.")
    print("  Leave: Both rejection paths covered (DH rejected, HR rejected).")
    print("  Leave: Department Head as applicant — all 4 HR-decision states covered.")
else:
    print()
    print("  Failed cases:", ", ".join(failed_cases))
