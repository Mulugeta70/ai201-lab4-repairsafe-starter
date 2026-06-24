import re
from groq import Groq
from config import GROQ_API_KEY, LLM_MODEL, VALID_TIERS

_client = Groq(api_key=GROQ_API_KEY)

_SYSTEM_PROMPT = """You are a home repair safety classifier. Your job is to assign one of three safety tiers to a home repair question.

TIER DEFINITIONS:
- safe: Routine maintenance and low-risk repairs most homeowners can complete with basic tools. If this goes wrong, the worst case is cosmetic damage or a broken fixture — not injury, fire, or flooding. No permit required.
- caution: Repairs doable for a motivated homeowner, but mistakes have real cost or mild risk of injury. Involves water or electrical systems where something can go meaningfully wrong, but an amateur mistake is recoverable (e.g., a tripped breaker or a slow drip rather than a flood or fire). No permit typically required.
- refuse: Repairs where an amateur mistake can cause fire, flooding, structural damage, serious injury, or death — or where local building codes require a licensed professional and a permit. Do NOT provide how-to guidance for these.

CRITICAL EDGE CASES:
- "Replacing" an existing outlet/switch at the same location → caution (same circuit, no new wiring)
- "Adding" a new outlet/switch anywhere → refuse (new circuit from panel, permit required)
- Any gas line work (even "just a small fix") → refuse
- Any electrical panel work → refuse
- Removing any wall → refuse (load-bearing risk)
- Water heater replacement → refuse (permit required in most jurisdictions)

CLASSIFICATION RULE: If the repair going wrong could cause fire, flooding, structural failure, injury, or death → refuse. If the worst case is a leaky faucet or a tripped breaker → caution.

OUTPUT FORMAT (use exactly this format, nothing else):
Tier: <safe|caution|refuse>
Reason: <one sentence explaining why>"""


def classify_safety_tier(question: str) -> dict:
    """
    Classify a home repair question into one of three safety tiers.

    Returns a dict with:
      - "tier"   : str — one of "safe", "caution", "refuse"
      - "reason" : str — a brief explanation of why this tier was assigned
    """
    try:
        response = _client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": f"Classify this home repair question:\n\n{question}"},
            ],
            temperature=0.0,
            max_tokens=150,
        )
        text = response.choices[0].message.content.strip()

        tier_match = re.search(r"Tier:\s*(safe|caution|refuse)", text, re.IGNORECASE)
        reason_match = re.search(r"Reason:\s*(.+)", text, re.IGNORECASE)

        tier = tier_match.group(1).lower() if tier_match else None
        reason = reason_match.group(1).strip() if reason_match else ""

        if tier not in VALID_TIERS:
            tier = "caution"
            reason = reason or "Could not determine tier; defaulting to caution for safety."

        return {"tier": tier, "reason": reason}

    except Exception as e:
        return {
            "tier": "caution",
            "reason": f"Classification unavailable (error: {e}); defaulting to caution.",
        }
