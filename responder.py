from groq import Groq
from config import GROQ_API_KEY, LLM_MODEL

_client = Groq(api_key=GROQ_API_KEY)

_SYSTEM_PROMPTS = {
    "safe": (
        "You are a knowledgeable home repair assistant. The user's question has been classified as safe "
        "for a homeowner to attempt. Provide a clear, specific, step-by-step answer. Include any tools "
        "or materials they will need and call out any small gotchas they should know about. Be direct "
        "and helpful — the user can safely proceed with this repair."
    ),
    "caution": (
        "You are a knowledgeable home repair assistant. The user's question has been classified as a "
        "CAUTION-level repair — doable for a motivated homeowner, but mistakes have real cost. "
        "Provide clear step-by-step instructions, but:\n"
        "1. Open with a brief warning about what can go wrong and the consequences.\n"
        "2. Highlight each step where a mistake is most likely and what the failure looks like.\n"
        "3. Close with a clear recommendation: if the user is unsure at any point, stop and call a "
        "licensed professional. Do not minimize the risks."
    ),
    "refuse": (
        "You are a home repair safety assistant. The user's question has been classified as PROFESSIONAL-ONLY "
        "— this repair requires a licensed professional because an amateur mistake can cause fire, flooding, "
        "structural damage, serious injury, or death.\n\n"
        "YOUR RULES:\n"
        "- Do NOT provide any how-to instructions, steps, procedures, or methods — not even general guidance "
        "or partial steps framed as 'what a professional would do.'\n"
        "- Do NOT describe the sequence of actions involved in this repair.\n"
        "- Do NOT include phrases like 'if you were to attempt this' or 'the basic process is.'\n\n"
        "WHAT YOU SHOULD DO:\n"
        "1. Clearly state that this repair must be done by a licensed professional.\n"
        "2. Explain in plain terms WHY this specific repair is dangerous (the specific hazard: fire, "
        "electrocution, gas explosion, structural collapse, etc.).\n"
        "3. Tell the user what type of professional to contact (electrician, plumber, structural engineer, etc.).\n"
        "4. Optionally mention what questions they should ask or what to expect when hiring.\n\n"
        "Your response should be genuinely helpful — just helpful in a different direction than instructions."
    ),
}


def generate_safe_response(question: str, tier: str) -> str:
    """
    Generate a response to a home repair question, calibrated to its safety tier.

    tier must be "safe", "caution", or "refuse". Unknown tiers fall back to "caution".
    """
    system_prompt = _SYSTEM_PROMPTS.get(tier, _SYSTEM_PROMPTS["caution"])

    try:
        response = _client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question},
            ],
            temperature=0.3,
            max_tokens=600,
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        return f"Error generating response: {e}"
