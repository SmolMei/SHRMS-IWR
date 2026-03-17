# =============================================================================
# training_data.py
# SHRMS — Intelligent Workflow Routing
# Synthetic Training Data — IPCR Evaluation Form + Leave Application
#
# WHAT THIS FILE IS:
#   Generates the synthetic training datasets for BOTH Decision Trees:
#     generate_ipcr_data()  → data/ipcr_training_data.csv
#     generate_leave_data() → data/leave_training_data.csv
#
# WHY SYNTHETIC DATA:
#   Your thesis Scope and Limitations explicitly states:
#   "the researchers will use a synthetic HR dataset that resembles real
#    LGU employee data, based exclusively on the Admin Office employee data."
#
# HOW LABELS ARE ASSIGNED:
#   Each record's routing label is derived from the same logic in workflow.png.
#   The Decision Trees are trained to learn routing decisions that match the
#   flowchart exactly.
#
# ─────────────────────────────────────────────────────────────────────────────
# IPCR: THREE SCENARIOS (matching workflow.png — evaluation path)
#
#   Scenario A — Employee submits fresh form (no rating yet)
#                Label: 0 = route_to_evaluator
#
#   Scenario B — Evaluator fills form, rating >= 2.5 (Passed)
#                Label: 2 = save_data
#
#   Scenario C — Evaluator fills form, rating < 2.5 (Failed)
#                Label: 1 = return_for_remarks
#
# ─────────────────────────────────────────────────────────────────────────────
# LEAVE: FOUR SCENARIOS (matching workflow.png — leave path)
#
# CSC-aligned routing flow:
#   Employee submits → Rule Engine compliance check
#     FAIL → returned immediately (Rule Engine handles this, not the DT)
#     PASS ↓
#   Stage 1: Route to Department Head → DH approves or rejects
#     APPROVED → Stage 2: Route to HR Officer
#     REJECTED → Require rejection reason → Completed
#   Stage 2: Route to HR Officer → HR approves or rejects
#     APPROVED → Completed (leave recorded)
#     REJECTED → Require rejection reason → Completed
#
#   Scenario A — dh_decision=0  (DH has not decided yet)
#                Label: 0 = route_to_department_head
#
#   Scenario B — dh_decision=1, hr_decision=0  (DH approved, HR pending)
#                Label: 1 = route_to_hr
#
#   Scenario C — (dh_decision=2 OR hr_decision=2), has_rejection_reason=0
#                Label: 2 = require_rejection_reason
#
#   Scenario D — hr_decision=1  OR  (rejected AND has_rejection_reason=1)
#                Label: 3 = completed
#
# RUN THIS FILE:
#   python training_data.py          — generates both CSVs
#   python training_data.py ipcr     — generates ipcr_training_data.csv only
#   python training_data.py leave    — generates leave_training_data.csv only
# =============================================================================

import os
import sys
import pandas as pd
import numpy as np
from org_and_rules import (
    EMPLOYEES,
    IPCR_PASSING_SCORE,
    ROLE_ENCODING,
    LEAVE_RULES,
    LEAVE_TYPE_ENCODING,
)

# Reproducible results — same data generated every time you run this
np.random.seed(42)

# Always resolve paths relative to this file's location
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

# ─────────────────────────────────────────────────────────────────────────────
# Leave setup constants — derived from org_and_rules
# ─────────────────────────────────────────────────────────────────────────────

LEAVE_TYPES = list(LEAVE_TYPE_ENCODING.keys())   # 9 leave types

MAX_DAYS_BY_TYPE = {}
for _lt in LEAVE_TYPES:
    _rule = LEAVE_RULES.get(_lt, {})
    _cap  = _rule.get("max_days_per_year") or _rule.get("max_days", 15)
    MAX_DAYS_BY_TYPE[_lt] = _cap


# =============================================================================
# IPCR — Training Data Generator
# =============================================================================

def generate_ipcr_data(samples_per_employee=100):
    """
    Generates synthetic IPCR routing records for every employee
    who has a supervisor (everyone except the Department Head).

    Parameters:
        samples_per_employee (int) — training records per employee.
                                     21 eligible employees x 100 = 2,100 total records.

    Returns:
        pandas DataFrame with columns:
            employee_id         — which employee this record belongs to
            role_encoded        — employee's role as an integer (from ROLE_ENCODING)
            performance_rating  — IPCR score (0.0 if first submission, 1.0–5.0 otherwise)
            is_first_submission — 1 = fresh form, 0 = returning form
            routing_action      — TARGET label the Decision Tree will learn
    """

    records = []

    for emp_id, emp in EMPLOYEES.items():

        # Skip the Department Head — he has no evaluator above him
        # This matches RULE 2 in rule_engine.py check_ipcr()
        if emp["supervisor_id"] is None:
            continue

        role_enc = ROLE_ENCODING[emp["role"]]

        for i in range(samples_per_employee):

            is_first = np.random.randint(0, 2)

            if is_first == 1:
                # Scenario A: Fresh form — route to evaluator
                rating = 0.0
                label  = 0   # route_to_evaluator

            else:
                rating = round(np.random.uniform(1.0, 5.0), 2)

                # Inject boundary sample at exactly 2.5 every 15 records
                # Ensures the tree learns 2.5 is the passing threshold precisely
                if i % 15 == 0:
                    rating = IPCR_PASSING_SCORE
                    label  = 2   # save_data

                elif rating >= IPCR_PASSING_SCORE:
                    # Scenario B: Passed
                    label = 2   # save_data

                else:
                    # Scenario C: Failed — remarks required
                    # The remarks check itself happens in workflow_router.py
                    label = 1   # return_for_remarks

            records.append({
                "employee_id":         emp_id,
                "role_encoded":        role_enc,
                "performance_rating":  rating,
                "is_first_submission": is_first,
                "routing_action":      label,
            })

    return pd.DataFrame(records)


# =============================================================================
# LEAVE — Label assignment helper (single source of truth)
# =============================================================================

def _assign_leave_label(dh_decision, hr_decision, has_rejection_reason):
    """
    Derives the correct routing label from the current leave decision state.

    This function is the single source of truth for leave label assignment.
    The same logic is replicated in workflow_router.py when interpreting
    the Decision Tree's prediction — ensuring training data and router are
    always consistent with each other.

    Maps to LEAVE_DT_ACTIONS in org_and_rules.py:
      dh=0                                  → 0  route_to_department_head
      dh=1, hr=0                            → 1  route_to_hr
      (dh=2 OR hr=2) AND reason=0           → 2  require_rejection_reason
      hr=1 OR ((dh=2 OR hr=2) AND reason=1) → 3  completed
    """
    if dh_decision == 0:
        return 0   # route_to_department_head

    if dh_decision == 1 and hr_decision == 0:
        return 1   # route_to_hr

    if hr_decision == 1:
        return 3   # completed

    rejected = (dh_decision == 2 or hr_decision == 2)
    if rejected and has_rejection_reason == 0:
        return 2   # require_rejection_reason

    if rejected and has_rejection_reason == 1:
        return 3   # completed

    return 0   # fallback — should not be reached


# =============================================================================
# LEAVE — Training Data Generator
# =============================================================================

def generate_leave_data(samples_per_employee=100):
    """
    Generates synthetic leave application routing records for every
    employee in the org chart (including the Department Head, since
    even the DH can file a leave request).

    Parameters:
        samples_per_employee (int) — training records per employee.
                                     22 employees x 100 = 2,200 total records.

    Returns:
        pandas DataFrame with columns matching LEAVE_FEATURES + routing_action.
    """

    records = []

    for emp_id in EMPLOYEES:

        for i in range(samples_per_employee):

            # Cycle through all 9 leave types evenly
            leave_type = LEAVE_TYPES[i % len(LEAVE_TYPES)]
            leave_enc  = LEAVE_TYPE_ENCODING[leave_type]
            max_days   = MAX_DAYS_BY_TYPE[leave_type]

            days_req = int(np.random.randint(1, max_days + 1))

            # Always 1 (compliant) — Rule Engine already rejected non-compliant apps
            # Occasional 0 (5% chance) so DT learns this field alone doesn't drive routing
            has_attachment = 1 if np.random.random() > 0.05 else 0

            # Generate decision state — balanced 25% per scenario
            # i % 4 guarantees all 4 classes appear for every leave type and employee
            scenario = i % 4

            if scenario == 0:
                # Scenario A: Fresh — DH has not decided yet
                dh_decision          = 0
                hr_decision          = 0
                has_rejection_reason = 0

            elif scenario == 1:
                # Scenario B: DH approved, HR has not decided yet
                dh_decision          = 1
                hr_decision          = 0
                has_rejection_reason = 0

            elif scenario == 2:
                # Scenario C: Rejected, no reason recorded yet
                if np.random.random() > 0.5:
                    dh_decision = 2; hr_decision = 0   # DH rejected
                else:
                    dh_decision = 1; hr_decision = 2   # HR rejected
                has_rejection_reason = 0

            else:
                # Scenario D: Completed
                if np.random.random() > 0.5:
                    dh_decision = 1; hr_decision = 1   # HR approved
                    has_rejection_reason = 0
                else:
                    if np.random.random() > 0.5:
                        dh_decision = 2; hr_decision = 0
                    else:
                        dh_decision = 1; hr_decision = 2
                    has_rejection_reason = 1            # Reason recorded

            label = _assign_leave_label(dh_decision, hr_decision, has_rejection_reason)

            records.append({
                "employee_id":             emp_id,
                "leave_type_encoded":      leave_enc,
                "days_requested":          days_req,
                "has_required_attachment": has_attachment,
                "dh_decision":             dh_decision,
                "hr_decision":             hr_decision,
                "has_rejection_reason":    has_rejection_reason,
                "routing_action":          label,
            })

    return pd.DataFrame(records)


# =============================================================================
# MAIN
# =============================================================================

def _print_ipcr_summary(df, path):
    label_names = {
        0: "route_to_evaluator  (Scenario A — fresh submission)",
        1: "return_for_remarks  (Scenario C — failed rating)",
        2: "save_data       (Scenario B — passing rating)",
    }
    print("IPCR Training Data Generated")
    print(f"  Saved to         : {path}")
    print(f"  Total records    : {len(df)}")
    print(f"  Employees covered: {df['employee_id'].nunique()} (Department Head excluded)")
    print()
    print("  Label distribution:")
    for code, count in df["routing_action"].value_counts().sort_index().items():
        print(f"    Label [{code}] {label_names[code]}: {count} records")
    print()


def _print_leave_summary(df, path):
    label_names = {
        0: "route_to_department_head  (Scenario A — fresh)",
        1: "route_to_hr               (Scenario B — DH approved)",
        2: "require_rejection_reason  (Scenario C — rejected, no reason)",
        3: "completed                 (Scenario D — HR approved or reason recorded)",
    }
    enc_to_name = {v: k for k, v in LEAVE_TYPE_ENCODING.items()}
    print("Leave Application Training Data Generated")
    print(f"  Saved to         : {path}")
    print(f"  Total records    : {len(df)}")
    print(f"  Employees covered: {df['employee_id'].nunique()} (all employees)")
    print()
    print("  Label distribution:")
    for code, count in df["routing_action"].value_counts().sort_index().items():
        pct = count / len(df) * 100
        print(f"    Label [{code}] {label_names[code]}: {count} records ({pct:.1f}%)")
    print()
    print("  Leave type distribution:")
    for enc, count in df["leave_type_encoded"].value_counts().sort_index().items():
        print(f"    [{enc}] {enc_to_name[enc]:<26}: {count} records")
    print()


if __name__ == "__main__":

    os.makedirs(DATA_DIR, exist_ok=True)

    mode = sys.argv[1] if len(sys.argv) > 1 else "both"

    if mode in ("ipcr", "both"):
        ipcr_df   = generate_ipcr_data(samples_per_employee=100)
        ipcr_path = os.path.join(DATA_DIR, "ipcr_training_data.csv")
        ipcr_df.to_csv(ipcr_path, index=False)
        _print_ipcr_summary(ipcr_df, ipcr_path)

    if mode in ("leave", "both"):
        leave_df   = generate_leave_data(samples_per_employee=100)
        leave_path = os.path.join(DATA_DIR, "leave_training_data.csv")
        leave_df.to_csv(leave_path, index=False)
        _print_leave_summary(leave_df, leave_path)

