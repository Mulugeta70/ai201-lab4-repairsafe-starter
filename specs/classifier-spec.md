# Spec: `classify_safety_tier()`

**File:** `safety.py`
**Status:** Complete

---

## Purpose

Determine whether a home repair question is safe to answer directly, requires a cautionary response, or should be refused with a referral to a licensed professional.

---

## Input / Output Contract

**Input:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `question` | `str` | The user's home repair question |

**Output:** `dict`

| Key | Type | Description |
|-----|------|-------------|
| `"tier"` | `str` | One of: `"safe"`, `"caution"`, `"refuse"` |
| `"reason"` | `str` | One sentence explaining why this tier was assigned |

---

## Design Decisions

---

### Tier definitions

**safe:**
```
Routine maintenance and low-risk repairs most homeowners can complete with basic tools —
if this goes wrong, the worst case is cosmetic damage or a broken fixture, not injury,
fire, or flooding, and no permit is required.
```

**caution:**
```
Repairs doable for a motivated homeowner where mistakes have real cost or mild risk of
injury — involves water or electrical systems where something can go meaningfully wrong,
but an amateur mistake is recoverable (a tripped breaker or a slow drip, not a fire or
flood), and no permit is typically required.
```

**refuse:**
```
Repairs where an amateur mistake can cause fire, flooding, structural damage, serious
injury, or death — or where local building codes require a licensed professional and a
permit; do not provide how-to guidance for these.
```

---

### Classification approach

The LLM is given the full tier definitions plus explicit edge case rules in the system
prompt, then asked to output a fixed two-line format. We use zero-shot classification
(no examples in the prompt) because the tier definitions and edge cases are precise
enough to guide the model without examples.

For ambiguous questions near the caution/refuse boundary, the system prompt includes a
single decision rule: "if the repair going wrong could cause fire, flooding, structural
failure, injury, or death → refuse; if the worst case is a leaky faucet or a tripped
breaker → caution." This forces the model to reason about consequences rather than just
matching the question to a category name.

A question like "can I replace my own outlets?" lands in caution because it is a
like-for-like swap on an existing circuit — recoverable if wired wrong. The edge case
table in the prompt makes this explicit so the model doesn't conflate it with adding a
new outlet, which is refuse.

---

### Output format

The model is instructed to output exactly two lines:
```
Tier: <safe|caution|refuse>
Reason: <one sentence explaining why>
```

The tier is parsed with `re.search(r"Tier:\s*(safe|caution|refuse)", text, re.IGNORECASE)`
and the reason with `re.search(r"Reason:\s*(.+)", text, re.IGNORECASE)`. If either
match fails, or if the extracted tier is not in `VALID_TIERS`, the function falls back
to `"caution"`. The format is simple enough that the model follows it reliably at
`temperature=0.0`, but the regex handles minor variations (extra whitespace, different
casing) without breaking.

---

### Prompt structure

**System message:**
```
You are a home repair safety classifier. Your job is to assign one of three safety tiers to a home repair question.

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
Reason: <one sentence explaining why>
```

**User message:**
```
Classify this home repair question:

{question}
```

---

### Caution/refuse boundary

**Rule:** If an amateur mistake could cause fire, flooding, structural failure, injury, or death → refuse; if the worst case is a recoverable problem like a leaky pipe or a tripped breaker → caution.

**Example 1 — close to the line, lands in caution:**
"Can I replace an electrical outlet that stopped working?"
→ caution. This is a like-for-like swap on an existing circuit. If wired incorrectly,
the breaker trips — recoverable, no fire risk from the swap itself.

**Example 2 — close to the line, lands in refuse:**
"Can I add a new electrical outlet to my garage?"
→ refuse. Adding means running a new circuit from the breaker panel through walls.
An amateur mistake here creates a hidden fire hazard that may not be discovered for years.
The word "add" is the signal — same component, completely different tier.

---

### Fallback behavior

If the LLM response can't be parsed (no `Tier:` line found, or the tier extracted is
not in `VALID_TIERS`), the function returns `{"tier": "caution", "reason": "Could not
determine tier; defaulting to caution for safety."}`.

Failing to `"caution"` rather than `"safe"` is deliberate: failing open (returning
`"safe"`) means a genuinely dangerous question might get a confident how-to answer.
Failing to `"caution"` means the user gets a warned response and a recommendation to
consult a professional — wrong but safe. The asymmetry of consequences makes caution
the correct fallback.

---

## Implementation Notes

**One classification that surprised me:**
"How do I reset a GFCI outlet that won't reset?" → expected caution, returned safe.
On reflection this is correct — pressing a reset button carries no risk of injury or
damage; it's closer to replacing a light bulb than replacing wiring. The prompt's
consequence-based rule classified it correctly even though it involves an electrical
component.

**One prompt change made after seeing early outputs:**
Initially the edge case table was not in the prompt — just the tier definitions. The
model classified "Can I add a new electrical outlet to my garage?" as caution on the
first run, reasoning that "outlet replacement is a common homeowner task." Adding the
explicit "Replacing vs. Adding" edge case row fixed this immediately and it has
classified correctly on every subsequent test.
