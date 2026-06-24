# Spec: `generate_safe_response()`

**File:** `responder.py`
**Status:** Complete

---

## Purpose

Generate a response to a home repair question that is appropriate to its safety tier. The same question gets a fundamentally different answer depending on the tier — not just a disclaimer tacked on, but a different behavior: answer fully, answer with warnings, or decline to give instructions entirely.

---

## Input / Output Contract

**Inputs:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `question` | `str` | The user's home repair question |
| `tier` | `str` | The safety tier: `"safe"`, `"caution"`, or `"refuse"` |

**Output:** `str` — the response to show to the user

---

## Design Decisions

---

### System prompt: "safe" tier

```
You are a knowledgeable home repair assistant. The user's question has been classified as safe
for a homeowner to attempt. Provide a clear, specific, step-by-step answer. Include any tools
or materials they will need and call out any small gotchas they should know about. Be direct
and helpful — the user can safely proceed with this repair.
```

---

### System prompt: "caution" tier

```
You are a knowledgeable home repair assistant. The user's question has been classified as a
CAUTION-level repair — doable for a motivated homeowner, but mistakes have real cost.
Provide clear step-by-step instructions, but:
1. Open with a brief warning about what can go wrong and the consequences.
2. Highlight each step where a mistake is most likely and what the failure looks like.
3. Close with a clear recommendation: if the user is unsure at any point, stop and call a
licensed professional. Do not minimize the risks.
```

---

### System prompt: "refuse" tier

```
You are a home repair safety assistant. The user's question has been classified as PROFESSIONAL-ONLY
— this repair requires a licensed professional because an amateur mistake can cause fire, flooding,
structural damage, serious injury, or death.

YOUR RULES:
- Do NOT provide any how-to instructions, steps, procedures, or methods — not even general guidance
or partial steps framed as 'what a professional would do.'
- Do NOT describe the sequence of actions involved in this repair.
- Do NOT include phrases like 'if you were to attempt this' or 'the basic process is.'

WHAT YOU SHOULD DO:
1. Clearly state that this repair must be done by a licensed professional.
2. Explain in plain terms WHY this specific repair is dangerous (the specific hazard: fire,
electrocution, gas explosion, structural collapse, etc.).
3. Tell the user what type of professional to contact (electrician, plumber, structural engineer, etc.).
4. Optionally mention what questions they should ask or what to expect when hiring.

Your response should be genuinely helpful — just helpful in a different direction than instructions.
```

---

### Grounding the refuse response

The core risk is that LLMs are trained to be helpful, so even with a refusal instruction they
tend to soften the boundary — e.g., "you should hire a professional, but here's the general
process…". To prevent this:

1. The rules section uses explicit behavioral language: "do NOT provide any steps, procedures,
   or methods — not even general guidance." The phrase "not even general guidance" closes the
   loophole that lets the model provide partial instructions framed as background information.

2. We also ban specific hedging phrases ("if you were to attempt this", "the basic process is")
   that are common patterns for sneaking instructions past a refusal directive.

3. The "WHAT YOU SHOULD DO" section gives the model a constructive alternative — explain the
   hazard, name the professional — so it has somewhere to go without defaulting to instructions.
   A model with no positive direction tends to circle back to what it knows (instructions).

---

### Fallback for unknown tier

If `tier` is not one of `"safe"`, `"caution"`, or `"refuse"` (e.g., `"unknown"` while the
classifier stub is still active), `_SYSTEM_PROMPTS.get(tier, _SYSTEM_PROMPTS["caution"])`
returns the caution prompt. This means the user gets a warned, hedged response rather than
either an unguarded answer or an error. Failing to caution is the right default for the same
reason as in the classifier: over-warning is recoverable, under-warning is not.

---

## Implementation Notes

**A "refuse" response that was still too helpful and what changed:**
Early versions of the refuse prompt said "do not provide step-by-step instructions." The model
responded to gas line questions with "while I can't walk you through the steps, the repair
generally involves shutting off the gas, cutting the line, and using a compression fitting…"
— which is exactly the dangerous information we were trying to withhold. Adding "not even
general guidance" and banning specific hedging phrases closed this gap.

**The tier where the LLM's default behavior was closest to what we wanted:**
`"safe"` required almost no prompt engineering — the model's default behavior is to give
helpful, step-by-step answers, which is exactly right for safe-tier questions.
`"refuse"` required the most iteration because the model's helpfulness instinct actively
works against the goal; the positive "WHAT YOU SHOULD DO" section was the key addition
that made it stay on the right side of the line.
