"""AI integration (Gemini) for workout plan generation."""
import json
import logging
import os
from typing import Union

from fastapi import HTTPException, status

import google.generativeai as genai  # type: ignore

from app.context_gemini.workout.sys_prompt import build_system_prompt
from app.schemas.item import AIGenerateRequest
from app.schemas.user import UserInfoContextResponse

logger = logging.getLogger(__name__)


def generate_workout_plan(
    req: AIGenerateRequest,
    user_ctx: Union[dict, UserInfoContextResponse],
) -> dict:
    """Build the system prompt, call Gemini, parse the JSON response.

    Returns the parsed dict (or list as wrapped) for /workout-plans/ai-generate-full.
    Raises HTTPException for misconfiguration, rate limits, API failure, or parse failure.
    """
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GEMINI_API_KEY is not configured",
        )

    base_dir = os.path.dirname(os.path.dirname(__file__))
    gemini_dir = os.path.join(base_dir, "context_gemini", "workout")

    try:
        sys_prompt = build_system_prompt(user_ctx, gemini_dir)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read context files or build system prompt: {str(e)}",
        )

    import google.api_core.exceptions

    genai.configure(api_key=gemini_key)  # type: ignore
    model = genai.GenerativeModel('gemini-3.1-flash-lite-preview', system_instruction=sys_prompt)  # type: ignore

    try:
        response = model.generate_content(
            req.prompt,
            generation_config=genai.types.GenerationConfig(  # type: ignore
                response_mime_type="application/json",
            ),
        )
    except google.api_core.exceptions.ResourceExhausted:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Gemini API rate limit exceeded. Please wait a moment and try again.",
        )
    except Exception as e:
        logger.exception("Gemini API call failed")
        raise HTTPException(status_code=502, detail="AI generation failed")

    try:
        raw_text = response.text.strip()
        start_idx = raw_text.find('{')
        if start_idx == -1:
            start_idx = raw_text.find('[')

        end_idx = raw_text.rfind('}')
        if end_idx == -1 or (raw_text.rfind(']') > end_idx):
            end_idx = raw_text.rfind(']')

        if start_idx != -1 and end_idx != -1:
            raw_text = raw_text[start_idx:end_idx + 1]

        data = json.loads(raw_text)
        if isinstance(data, dict):
            data["ai_generated"] = True
        elif isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
            data[0]["ai_generated"] = True

        return data
    except Exception:
        logger.exception("Failed to parse Gemini response")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to parse Gemini response: {response.text}",
        )
