"""Trust Ledger — append-only record of every decision with SHA-256 hash chain."""

import json
import hashlib
import os
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from typing import Optional
import config


@dataclass
class LedgerEntry:
    """A single trust ledger entry — records every agent's contribution."""
    timestamp: str
    entry_id: int
    analyst_summary: Optional[dict]   # Analyst agent's market assessment
    strategist_proposal: Optional[dict]  # Strategist agent's trade proposal
    intent: dict                    # What the agent wanted to do
    risk_check: dict                # Risk Manager's evaluation
    decision: str                   # "EXECUTE" or "REFUSE"
    result: Optional[dict]          # Execution result (if executed)
    refusal_proof: Optional[str]    # Why it refused (if refused)
    refusal_impact: Optional[dict]  # Impact score (filled later)
    prev_hash: str                  # Hash of previous entry
    entry_hash: str                 # Hash of this entry


class TrustLedger:
    """Append-only trust ledger with SHA-256 hash chain."""

    def __init__(self, ledger_dir: str = None):
        self.ledger_dir = ledger_dir or config.LEDGER_DIR
        os.makedirs(self.ledger_dir, exist_ok=True)
        self.entries: list[LedgerEntry] = []
        self.entry_counter = 0
        self._load_existing()

    def _load_existing(self):
        """Load existing ledger entries from disk."""
        ledger_file = os.path.join(self.ledger_dir, "ledger.jsonl")
        if os.path.exists(ledger_file):
            with open(ledger_file, "r") as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        self.entries.append(LedgerEntry(**data))
                        self.entry_counter = max(self.entry_counter, data["entry_id"])
            self.entry_counter += 1

    def _compute_hash(self, data: dict) -> str:
        """Compute SHA-256 hash of entry data."""
        serialized = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode()).hexdigest()

    def _get_prev_hash(self) -> str:
        """Get hash of the last entry, or genesis hash."""
        if self.entries:
            return self.entries[-1].entry_hash
        return hashlib.sha256(b"CROSSMIND_GENESIS").hexdigest()

    def record_execution(self, intent: dict, risk_check: dict,
                         result: dict,
                         analyst_summary: dict = None,
                         strategist_proposal: dict = None) -> LedgerEntry:
        """Record a successful trade execution."""
        prev_hash = self._get_prev_hash()
        entry_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "entry_id": self.entry_counter,
            "analyst_summary": analyst_summary,
            "strategist_proposal": strategist_proposal,
            "intent": intent,
            "risk_check": risk_check,
            "decision": "EXECUTE",
            "result": result,
            "refusal_proof": None,
            "refusal_impact": None,
            "prev_hash": prev_hash,
        }
        entry_hash = self._compute_hash(entry_data)
        entry_data["entry_hash"] = entry_hash

        entry = LedgerEntry(**entry_data)
        self._append(entry)
        return entry

    def record_refusal(self, intent: dict, risk_check: dict,
                       refusal_proof: str,
                       analyst_summary: dict = None,
                       strategist_proposal: dict = None) -> LedgerEntry:
        """Record a trade refusal with proof."""
        prev_hash = self._get_prev_hash()
        entry_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "entry_id": self.entry_counter,
            "analyst_summary": analyst_summary,
            "strategist_proposal": strategist_proposal,
            "intent": intent,
            "risk_check": risk_check,
            "decision": "REFUSE",
            "result": None,
            "refusal_proof": refusal_proof,
            "refusal_impact": None,
            "prev_hash": prev_hash,
        }
        entry_hash = self._compute_hash(entry_data)
        entry_data["entry_hash"] = entry_hash

        entry = LedgerEntry(**entry_data)
        self._append(entry)
        return entry

    def update_refusal_impact(self, entry_id: int, price_after: float,
                              would_have_lost: float) -> None:
        """Update a refusal entry with impact score (what would have happened)."""
        for entry in self.entries:
            if entry.entry_id == entry_id and entry.decision == "REFUSE":
                entry.refusal_impact = {
                    "price_after": price_after,
                    "would_have_lost": round(would_have_lost, 2),
                    "saved_by_refusal": would_have_lost > 0,
                    "measured_at": datetime.now(timezone.utc).isoformat(),
                }
                self._save_all()
                break

    def _append(self, entry: LedgerEntry):
        """Append entry to ledger."""
        self.entries.append(entry)
        self.entry_counter += 1

        # Append to JSONL file
        ledger_file = os.path.join(self.ledger_dir, "ledger.jsonl")
        with open(ledger_file, "a") as f:
            f.write(json.dumps(asdict(entry), default=str) + "\n")

        # Also write individual file for easy inspection
        entry_file = os.path.join(
            self.ledger_dir,
            f"{entry.timestamp[:10]}_{entry.entry_id:04d}_{entry.decision.lower()}.json"
        )
        with open(entry_file, "w") as f:
            json.dump(asdict(entry), f, indent=2, default=str)

    def _save_all(self):
        """Rewrite entire ledger (used for impact updates)."""
        ledger_file = os.path.join(self.ledger_dir, "ledger.jsonl")
        with open(ledger_file, "w") as f:
            for entry in self.entries:
                f.write(json.dumps(asdict(entry), default=str) + "\n")

    def get_stats(self) -> dict:
        """Get ledger statistics."""
        executions = [e for e in self.entries if e.decision == "EXECUTE"]
        refusals = [e for e in self.entries if e.decision == "REFUSE"]
        impacts = [e.refusal_impact for e in refusals if e.refusal_impact]
        total_saved = sum(i["would_have_lost"] for i in impacts if i.get("saved_by_refusal"))

        return {
            "total_entries": len(self.entries),
            "executions": len(executions),
            "refusals": len(refusals),
            "refusal_rate": round(len(refusals) / max(1, len(self.entries)) * 100, 1),
            "total_capital_saved_by_refusals": round(total_saved, 2),
            "chain_valid": self.verify_chain(),
        }

    def verify_chain(self) -> bool:
        """Verify the SHA-256 hash chain integrity."""
        if not self.entries:
            return True

        genesis = hashlib.sha256(b"CROSSMIND_GENESIS").hexdigest()
        expected_prev = genesis

        for entry in self.entries:
            if entry.prev_hash != expected_prev:
                return False
            # Recompute hash — exclude refusal_impact (added after initial hash)
            data = asdict(entry)
            del data["entry_hash"]
            data["refusal_impact"] = None  # Impact is added later, not part of original hash
            computed = self._compute_hash(data)
            if computed != entry.entry_hash:
                return False
            expected_prev = entry.entry_hash

        return True
