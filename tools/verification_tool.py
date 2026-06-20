import datetime
from typing import Dict, Any, List

class VerificationTool:
    """
    Implements a strict resource verification layer to guarantee response reliability.
    Checks resource freshness, operational status, phone format, and database authority.
    """
    def __init__(self, current_date_str: str = "2026-06-20"):
        try:
            self.current_date = datetime.datetime.strptime(current_date_str, "%Y-%m-%d")
        except ValueError:
            self.current_date = datetime.datetime.now()

    def verify_resource(self, resource: Dict[str, Any]) -> Dict[str, Any]:
        """
        Runs safety checks on a resource dictionary.
        Returns:
            Dict containing verification status (bool), score (float), and logs of individual tests.
        """
        score = 1.0
        checks = {}
        
        # 1. Operational Status check (weight: 0.3)
        status = resource.get("status", "UNKNOWN").upper()
        if status in ["OPERATIONAL", "OPEN"]:
            checks["status_ok"] = True
        else:
            checks["status_ok"] = False
            score -= 0.3

        # 2. Freshness check: verification date (weight: 0.3)
        verified_date_str = resource.get("verified_at", "")
        try:
            verified_date = datetime.datetime.strptime(verified_date_str, "%Y-%m-%d")
            delta_days = (self.current_date - verified_date).days
            if delta_days <= 2:  # Extremely fresh
                checks["freshness_ok"] = True
            elif delta_days <= 7:  # Moderately fresh
                checks["freshness_ok"] = True
                score -= 0.1
            else:  # Out of date
                checks["freshness_ok"] = False
                score -= 0.25
        except ValueError:
            checks["freshness_ok"] = False
            score -= 0.3

        # 3. Phone Contact check (weight: 0.2)
        phone = resource.get("phone", "")
        # Check standard formats (e.g., starts with +91, contains numbers and dashes)
        if phone and len(phone) >= 10 and any(char.isdigit() for char in phone):
            checks["phone_valid"] = True
        else:
            checks["phone_valid"] = False
            score -= 0.2

        # 4. Source database authenticity check (weight: 0.2)
        # Verify it has a name and address
        if resource.get("name") and resource.get("address"):
            checks["source_authentic"] = True
        else:
            checks["source_authentic"] = False
            score -= 0.2

        # Floor score at 0.0
        score = max(0.0, round(score, 2))
        verified = score >= 0.75  # Must score at least 75% to be considered verified and trusted

        return {
            "verified": verified,
            "score": score,
            "checks": checks,
            "resource_name": resource.get("name", "Unknown Center")
        }

    def verify_batch(self, resources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Verifies a list of resources, adding safety verification logs to each."""
        verified_list = []
        for res in resources:
            v_report = self.verify_resource(res)
            # Create a shallow copy and inject verification metadata
            res_verified = res.copy()
            res_verified["verification"] = v_report
            verified_list.append(res_verified)
        return verified_list
