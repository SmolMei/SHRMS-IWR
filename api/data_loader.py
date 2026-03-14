import os
import logging
import requests
from org_and_rules import EMPLOYEES, LEAVE_RULES

logger = logging.getLogger(__name__)


def load_from_hrms() -> bool:
    """
    Fetch employee and leave-rule data from Smart-HRMS and overwrite
    the in-memory EMPLOYEES and LEAVE_RULES dicts in-place.

    Returns True if loaded from HRMS, False if falling back to hardcoded data.
    """
    base_url = os.getenv("HRMS_API_URL", "").rstrip("/")
    api_key  = os.getenv("HRMS_API_KEY", "")

    if not base_url:
        logger.warning("HRMS_API_URL not set — using hardcoded org_and_rules data")
        return False

    try:
        headers  = {"X-API-Key": api_key} if api_key else {}
        response = requests.get(
            f"{base_url}/api/iwr-config",
            headers=headers,
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()

        employees   = data.get("employees",   {})
        leave_rules = data.get("leave_rules", {})

        if not employees:
            raise ValueError("HRMS returned empty employees dict")

        # Mutate in-place so all existing imports see the new data immediately
        EMPLOYEES.clear()
        EMPLOYEES.update(employees)
        LEAVE_RULES.clear()
        LEAVE_RULES.update(leave_rules)

        logger.info(
            "Loaded %d employees and %d leave rules from Smart-HRMS",
            len(EMPLOYEES),
            len(LEAVE_RULES),
        )
        return True

    except Exception as e:
        logger.warning(
            "Could not load from Smart-HRMS (%s) — using hardcoded data", e
        )
        return False
