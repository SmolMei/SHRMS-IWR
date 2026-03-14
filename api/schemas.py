from datetime import date
from pydantic import BaseModel


class IPCRRequest(BaseModel):
    employee_id: str
    performance_rating: float | None = None
    is_first_submission: bool
    evaluator_gave_remarks: bool


class LeaveRequest(BaseModel):
    employee_id: str
    leave_type: str
    days_requested: int
    days_remaining_balance: int
    start_date: date
    has_medical_certificate: bool
    has_solo_parent_id: bool
    has_marriage_certificate: bool
    dh_decision: int   # 0=pending, 1=approved, 2=rejected
    hr_decision: int   # 0=pending, 1=approved, 2=rejected
    has_rejection_reason: int  # 0 or 1
