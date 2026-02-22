"""
Contract tracker — monitors contract lifecycle, expiry dates,
renewal windows, and approval pipelines.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from digital_employee.database.crud import DatabaseCRUD

logger = logging.getLogger(__name__)


class ContractStatus:
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    PENDING_SIGNATURE = "pending_signature"
    ACTIVE = "active"
    EXPIRING_SOON = "expiring_soon"
    EXPIRED = "expired"
    RENEWED = "renewed"
    TERMINATED = "terminated"


class ContractTracker:
    """
    Manages the full lifecycle of contracts:
    - Vendor/supplier agreements
    - Customer contracts
    - Employment contracts
    - NDAs and other legal documents

    Alert windows:
    - 30 days before expiry: initial alert
    - 14 days before expiry: second alert
    - 7 days before expiry: urgent alert
    - 1 day before expiry: critical alert
    """

    EXPIRY_ALERT_DAYS = [30, 14, 7, 1]

    def __init__(self, db: DatabaseCRUD):
        self.db = db

    # ─────────────────────────────────────────────
    # Contract CRUD
    # ─────────────────────────────────────────────

    def create_contract(
        self,
        title: str,
        contract_type: str,
        counterparty: str,
        owner_email: str,
        start_date: datetime,
        end_date: Optional[datetime] = None,
        value: float = 0.0,
        currency: str = "USD",
        auto_renewal: bool = False,
        renewal_notice_days: int = 30,
        signatories: list[str] = None,
        tags: list[str] = None,
        notes: str = "",
    ) -> dict:
        """Register a new contract to track."""
        contract = {
            "title": title,
            "contract_type": contract_type,  # vendor|customer|employment|nda|other
            "counterparty": counterparty,
            "owner_email": owner_email,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat() if end_date else None,
            "value": value,
            "currency": currency,
            "auto_renewal": auto_renewal,
            "renewal_notice_days": renewal_notice_days,
            "signatories": signatories or [],
            "tags": tags or [],
            "notes": notes,
            "status": ContractStatus.ACTIVE if end_date and end_date > datetime.utcnow() else ContractStatus.DRAFT,
            "alerts_sent": [],  # Track which alerts have been sent
            "signature_status": {},  # signatory_email -> status
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        # Initialize signature tracking
        if signatories:
            contract["signature_status"] = {s: "pending" for s in signatories}

        saved = self.db.create("contracts", contract)
        logger.info(f"Contract created: {title} (counterparty: {counterparty})")
        return saved

    def update_contract(self, contract_id: str, updates: dict) -> dict:
        updates["updated_at"] = datetime.utcnow().isoformat()
        return self.db.update("contracts", contract_id, updates)

    def record_signature(self, contract_id: str, signatory_email: str) -> dict:
        """Record that a signatory has signed the contract."""
        contract = self.db.get("contracts", contract_id)
        signature_status = contract.get("signature_status", {})
        signature_status[signatory_email] = "signed"

        update = {
            "signature_status": signature_status,
            "updated_at": datetime.utcnow().isoformat(),
        }

        # Check if all signatories have signed
        all_signed = all(s == "signed" for s in signature_status.values())
        if all_signed:
            update["status"] = ContractStatus.ACTIVE
            update["fully_executed_at"] = datetime.utcnow().isoformat()
            logger.info(f"Contract {contract_id} fully executed")

        return self.db.update("contracts", contract_id, update)

    def renew_contract(
        self,
        contract_id: str,
        new_end_date: datetime,
        new_value: float = None,
        notes: str = "",
    ) -> dict:
        """Renew a contract with a new end date."""
        contract = self.db.get("contracts", contract_id)
        update = {
            "status": ContractStatus.RENEWED,
            "end_date": new_end_date.isoformat(),
            "alerts_sent": [],  # Reset alerts for new term
            "renewal_notes": notes,
            "renewed_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        if new_value is not None:
            update["value"] = new_value

        logger.info(f"Contract {contract_id} renewed until {new_end_date}")
        return self.db.update("contracts", contract_id, update)

    # ─────────────────────────────────────────────
    # Expiry Monitoring
    # ─────────────────────────────────────────────

    def get_contracts_expiring_within(self, days: int) -> list[dict]:
        """Get contracts expiring within the next N days."""
        all_contracts = self.db.list("contracts")
        now = datetime.utcnow()
        cutoff = now + timedelta(days=days)
        expiring = []

        for contract in all_contracts:
            if contract.get("status") in (ContractStatus.EXPIRED, ContractStatus.TERMINATED):
                continue
            end_date_str = contract.get("end_date")
            if not end_date_str:
                continue
            end_dt = datetime.fromisoformat(end_date_str)
            if now <= end_dt <= cutoff:
                days_until_expiry = (end_dt - now).days
                contract["days_until_expiry"] = days_until_expiry
                expiring.append(contract)

        return sorted(expiring, key=lambda c: c.get("days_until_expiry", 999))

    def get_expired_contracts(self) -> list[dict]:
        """Get contracts that have already expired."""
        all_contracts = self.db.list("contracts")
        now = datetime.utcnow()
        expired = []

        for contract in all_contracts:
            end_date_str = contract.get("end_date")
            if not end_date_str:
                continue
            end_dt = datetime.fromisoformat(end_date_str)
            if end_dt < now and contract.get("status") not in (ContractStatus.TERMINATED, ContractStatus.RENEWED):
                days_expired = (now - end_dt).days
                contract["days_expired"] = days_expired
                expired.append(contract)
                # Auto-update status
                self.db.update("contracts", contract["id"], {"status": ContractStatus.EXPIRED})

        return expired

    def get_alerts_due(self) -> list[dict]:
        """
        Get contracts that need expiry alerts sent.
        Returns contracts where we haven't yet sent alerts at standard intervals.
        """
        expiring = self.get_contracts_expiring_within(31)
        alerts_due = []

        for contract in expiring:
            days_left = contract.get("days_until_expiry", 999)
            alerts_already_sent = contract.get("alerts_sent", [])

            for threshold in self.EXPIRY_ALERT_DAYS:
                if days_left <= threshold and threshold not in alerts_already_sent:
                    alerts_due.append({
                        **contract,
                        "alert_threshold_days": threshold,
                        "urgency": "critical" if threshold <= 1 else "high" if threshold <= 7 else "medium",
                    })
                    break  # Only one alert per check cycle

        return alerts_due

    def mark_alert_sent(self, contract_id: str, threshold_days: int):
        """Record that an expiry alert was sent for a threshold."""
        contract = self.db.get("contracts", contract_id)
        alerts_sent = contract.get("alerts_sent", [])
        if threshold_days not in alerts_sent:
            alerts_sent.append(threshold_days)
        self.db.update("contracts", contract_id, {"alerts_sent": alerts_sent})

    # ─────────────────────────────────────────────
    # Pending Signatures
    # ─────────────────────────────────────────────

    def get_pending_signatures(self) -> list[dict]:
        """Get contracts waiting for signatures."""
        all_contracts = self.db.list("contracts")
        pending = []

        for contract in all_contracts:
            if contract.get("status") not in (ContractStatus.PENDING_SIGNATURE, ContractStatus.ACTIVE):
                continue
            sig_status = contract.get("signature_status", {})
            pending_signatories = [email for email, status in sig_status.items() if status == "pending"]
            if pending_signatories:
                contract["pending_signatories"] = pending_signatories
                # Calculate wait time
                created_at = contract.get("created_at")
                if created_at:
                    wait_days = (datetime.utcnow() - datetime.fromisoformat(created_at)).days
                    contract["waiting_days"] = wait_days
                pending.append(contract)

        return sorted(pending, key=lambda c: c.get("waiting_days", 0), reverse=True)

    # ─────────────────────────────────────────────
    # Digest
    # ─────────────────────────────────────────────

    def generate_contracts_digest(self) -> dict:
        """Generate a summary of all contract status."""
        alerts_due = self.get_alerts_due()
        pending_sigs = self.get_pending_signatures()
        expired = self.get_expired_contracts()
        expiring_30 = self.get_contracts_expiring_within(30)

        return {
            "total_active": len(self.db.find("contracts", {"status": ContractStatus.ACTIVE})),
            "expiring_within_30_days": len(expiring_30),
            "expiring_details": [
                {
                    "id": c["id"],
                    "title": c["title"],
                    "counterparty": c["counterparty"],
                    "owner_email": c["owner_email"],
                    "days_until_expiry": c.get("days_until_expiry"),
                    "auto_renewal": c.get("auto_renewal"),
                }
                for c in expiring_30
            ],
            "alerts_due": len(alerts_due),
            "pending_signatures": len(pending_sigs),
            "pending_signature_details": [
                {
                    "id": c["id"],
                    "title": c["title"],
                    "pending_signatories": c.get("pending_signatories", []),
                    "waiting_days": c.get("waiting_days", 0),
                }
                for c in pending_sigs
            ],
            "recently_expired": len(expired),
        }
