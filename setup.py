# =============================================================================
# setup.py
# SHRMS — Intelligent Workflow Routing
# One-Command Setup Script
#
# WHAT THIS FILE IS:
#   A one-time setup script that prepares the system before first use.
#   Run this ONCE after copying the files to your machine.
#
# WHAT IT DOES (in order):
#   Step 1 — Creates the data/ and models/ folders
#   Step 2 — Generates IPCR synthetic training data CSV
#   Step 3 — Trains the IPCR Decision Tree and saves it to disk
#   Step 4 — Generates Leave Application synthetic training data CSV
#   Step 5 — Trains the Leave Decision Tree and saves it to disk
#   Step 6 — Runs a self-check to confirm everything works end-to-end
#
# HOW TO RUN:
#   python setup.py
#
# WHAT IT CREATES:
#   data/ipcr_training_data.csv  — IPCR synthetic training dataset
#   data/leave_training_data.csv — Leave Application synthetic training dataset
#   models/ipcr_dt.pkl           — trained IPCR Decision Tree model
#   models/leave_dt.pkl          — trained Leave Decision Tree model
#
# AFTER RUNNING THIS:
#   The system is fully ready. You never need to run this again
#   unless you want to retrain with new or updated data.
# =============================================================================

import sys
import os
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
DATA_DIR  = os.path.join(BASE_DIR, "data")
MODEL_DIR = os.path.join(BASE_DIR, "models")


def print_header(text):
    print()
    print("─" * 60)
    print(f"  {text}")
    print("─" * 60)


if __name__ == "__main__":

    print()
    print("=" * 60)
    print("  SHRMS — Intelligent Workflow Routing")
    print("  Setup Script")
    print("=" * 60)

    # ------------------------------------------------------------------
    # STEP 1: Create required folders
    # ------------------------------------------------------------------
    print_header("Step 1: Creating folders")

    os.makedirs(DATA_DIR,  exist_ok=True)
    os.makedirs(MODEL_DIR, exist_ok=True)

    print(f"  ✅ data/   → {DATA_DIR}")
    print(f"  ✅ models/ → {MODEL_DIR}")

    # ------------------------------------------------------------------
    # STEP 2: Generate IPCR synthetic training data
    # ------------------------------------------------------------------
    print_header("Step 2: Generating IPCR synthetic training data")

    import pandas as pd
    from training_data import generate_ipcr_data

    ipcr_df   = generate_ipcr_data(samples_per_employee=100)
    ipcr_path = os.path.join(DATA_DIR, "ipcr_training_data.csv")
    ipcr_df.to_csv(ipcr_path, index=False)

    ipcr_label_names = {
        0: "route_to_evaluator",
        1: "return_for_remarks",
        2: "save_data",
    }
    print(f"  ✅ {len(ipcr_df)} records — "
          f"{ipcr_df['employee_id'].nunique()} employees (Department Head excluded)")
    print(f"  ✅ Label distribution:")
    for code, count in ipcr_df["routing_action"].value_counts().sort_index().items():
        print(f"       [{code}] {ipcr_label_names[code]}: {count} records")
    print(f"  ✅ Saved → {ipcr_path}")

    # ------------------------------------------------------------------
    # STEP 3: Train the IPCR Decision Tree
    # ------------------------------------------------------------------
    print_header("Step 3: Training IPCR Decision Tree")

    from decision_tree import IPCRDecisionTree

    ipcr_dt = IPCRDecisionTree()
    ipcr_dt.train()

    # ------------------------------------------------------------------
    # STEP 4: Generate Leave Application synthetic training data
    # ------------------------------------------------------------------
    print_header("Step 4: Generating Leave Application synthetic training data")

    from training_data import generate_leave_data

    leave_df   = generate_leave_data(samples_per_employee=100)
    leave_path = os.path.join(DATA_DIR, "leave_training_data.csv")
    leave_df.to_csv(leave_path, index=False)

    leave_label_names = {
        0: "route_to_department_head",
        1: "route_to_hr",
        2: "require_rejection_reason",
        3: "completed",
    }
    print(f"  ✅ {len(leave_df)} records — "
          f"{leave_df['employee_id'].nunique()} employees (all employees)")
    print(f"  ✅ Label distribution:")
    for code, count in leave_df["routing_action"].value_counts().sort_index().items():
        pct = count / len(leave_df) * 100
        print(f"       [{code}] {leave_label_names[code]}: {count} records ({pct:.1f}%)")
    print(f"  ✅ Saved → {leave_path}")

    # ------------------------------------------------------------------
    # STEP 5: Train the Leave Decision Tree
    # ------------------------------------------------------------------
    print_header("Step 5: Training Leave Application Decision Tree")

    from decision_tree import LeaveDecisionTree

    leave_dt = LeaveDecisionTree()
    leave_dt.train()

    # ------------------------------------------------------------------
    # STEP 6: Self-check — run key paths for both routing systems
    # ------------------------------------------------------------------
    print_header("Step 6: Self-check")

    from workflow_router import WorkflowRouter
    router = WorkflowRouter()
    future = date.today() + timedelta(days=10)

    checks = [
        # ── IPCR checks ──────────────────────────────────────────────
        {
            "type":   "ipcr",
            "desc":   "IPCR: Fresh submission → route to evaluator",
            "form":   {"employee_id": "EMP-008", "is_first_submission": True,
                       "performance_rating": None},
            "expect_status": "routed",
            "expect_action": "route_to_evaluator",
        },
        {
            "type":   "ipcr",
            "desc":   "IPCR: Passing rating → save data",
            "form":   {"employee_id": "EMP-009", "is_first_submission": False,
                       "performance_rating": 4.0},
            "expect_status": "completed",
            "expect_action": "save_data",
        },
        {
            "type":   "ipcr",
            "desc":   "IPCR: Failing rating, no remarks → route back",
            "form":   {"employee_id": "EMP-007", "is_first_submission": False,
                       "performance_rating": 1.5, "evaluator_gave_remarks": False},
            "expect_status": "routed",
            "expect_action": "route_back_to_evaluator",
        },
        {
            "type":   "ipcr",
            "desc":   "IPCR: Failing rating + remarks → save data",
            "form":   {"employee_id": "EMP-007", "is_first_submission": False,
                       "performance_rating": 1.5, "evaluator_gave_remarks": True},
            "expect_status": "completed",
            "expect_action": "save_data",
        },
        # ── Leave checks ─────────────────────────────────────────────
        {
            "type": "leave",
            "desc": "Leave: Fresh application → route to DH",
            "form": {"employee_id": "EMP-005", "leave_type": "vacation_leave",
                     "days_requested": 3, "days_remaining_balance": 10,
                     "start_date": future,
                     "dh_decision": 0, "hr_decision": 0, "has_rejection_reason": 0},
            "expect_status": "routed",
            "expect_action": "route_to_department_head",
        },
        {
            "type": "leave",
            "desc": "Leave: DH approved → route to HR",
            "form": {"employee_id": "EMP-005", "leave_type": "vacation_leave",
                     "days_requested": 3, "days_remaining_balance": 10,
                     "start_date": future,
                     "dh_decision": 1, "hr_decision": 0, "has_rejection_reason": 0},
            "expect_status": "routed",
            "expect_action": "route_to_hr",
        },
        {
            "type": "leave",
            "desc": "Leave: DH rejected, no reason → require reason",
            "form": {"employee_id": "EMP-005", "leave_type": "vacation_leave",
                     "days_requested": 3, "days_remaining_balance": 10,
                     "start_date": future,
                     "dh_decision": 2, "hr_decision": 0, "has_rejection_reason": 0},
            "expect_status": "action_required",
            "expect_action": "require_rejection_reason",
        },
        {
            "type": "leave",
            "desc": "Leave: HR approved → completed",
            "form": {"employee_id": "EMP-005", "leave_type": "vacation_leave",
                     "days_requested": 3, "days_remaining_balance": 10,
                     "start_date": future,
                     "dh_decision": 1, "hr_decision": 1, "has_rejection_reason": 0},
            "expect_status": "completed",
            "expect_action": "completed",
        },
        {
            "type": "leave",
            "desc": "Leave: Rule Engine fail → returned",
            "form": {"employee_id": "EMP-005", "leave_type": "vacation_leave",
                     "days_requested": 5, "days_remaining_balance": 0,
                     "start_date": future,
                     "dh_decision": 0, "hr_decision": 0, "has_rejection_reason": 0},
            "expect_status": "returned",
            "expect_action": "returned",
        },
    ]

    all_ok = True
    for c in checks:
        if c["type"] == "ipcr":
            result = router.route_ipcr(c["form"])
        else:
            result = router.route_leave(c["form"])

        status_ok = result.get("status") == c["expect_status"]
        action_ok = (
            result.get("routing_action") or result.get("action", "")
        ) == c["expect_action"]
        ok = status_ok and action_ok
        icon = "✅" if ok else "❌"
        print(f"  {icon} {c['desc']}")
        if not ok:
            all_ok = False
            print(f"       Expected: status={c['expect_status']}, "
                  f"action={c['expect_action']}")
            print(f"       Got     : status={result.get('status')}, "
                  f"action={result.get('routing_action', result.get('action'))}")

    # ------------------------------------------------------------------
    # Done
    # ------------------------------------------------------------------
    print()
    print("=" * 60)
    if all_ok:
        print("  ✅ Setup complete. System is ready.")
        print()
        print("  Next steps:")
        print("   • Run  python tests.py  to run the full test suite")
        print("   • Integrate WorkflowRouter into your web controller")
    else:
        print("  ❌ Setup completed with errors.")
        print("     Review the output above before proceeding.")
    print("=" * 60)
    print()
