import json
import os
from datetime import datetime, timezone
from config import LOG_FILE


def log_interaction(question: str, tier: str, response: str) -> None:
    """
    Append a structured record of this interaction to the audit log (logs/audit.jsonl).
    Creates the logs/ directory if it doesn't exist.
    """
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "tier": tier,
        "question": question[:300],
        "response_preview": response[:200],
        "question_length": len(question),
        "response_length": len(response),
    }

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")

    print(f'[LOGGED] tier={tier} | "{question[:60]}" → {len(response)} chars')
