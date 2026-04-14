import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

try:
    from google import genai
    GENAI_AVAILABLE = True
except ImportError:
    genai = None
    GENAI_AVAILABLE = False

try:
    from anthropic import AsyncAnthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    AsyncAnthropic = None
    ANTHROPIC_AVAILABLE = False

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import Student, Prediction
from backend.config import (
    LLM_PROVIDER, GEMINI_API_KEY, GEMINI_MODEL,
    CLAUDE_API_KEY, CLAUDE_MODEL, LLM_TEMPERATURE, LLM_MAX_TOKENS,
)
from backend.core.security import security_manager

PROMPTS_DIR = 'prompts'

# Thread pool for blocking operations (file I/O, sync SDK calls)
_executor = ThreadPoolExecutor(max_workers=4)

# Async LLM clients
async_anthropic_client: Optional[AsyncAnthropic] = None

if LLM_PROVIDER == "claude" and ANTHROPIC_AVAILABLE and CLAUDE_API_KEY:
    async_anthropic_client = AsyncAnthropic(api_key=CLAUDE_API_KEY)


async def _load_prompt_template(prompt_name: str, use_hardened: bool = True) -> str:
    """
    Load prompt template from file.
    Wrapped in executor since file I/O is blocking.
    """
    template_suffix = "_hardened" if use_hardened else ""
    prompt_file = os.path.join(PROMPTS_DIR, f"{prompt_name}_advice{template_suffix}.txt")

    # Fallback to standard template if hardened doesn't exist
    if use_hardened and not os.path.exists(prompt_file):
        prompt_file = os.path.join(PROMPTS_DIR, f"{prompt_name}_advice.txt")

    if not os.path.exists(prompt_file):
        raise FileNotFoundError(f"Prompt file not found at {prompt_file}")

    # Run blocking file I/O in thread pool
    loop = asyncio.get_event_loop()
    with open(prompt_file, 'r') as f:
        return await loop.run_in_executor(_executor, f.read)


async def get_ai_advice(  # noqa: C901
    student_id: str,
    prompt_name: str,
    db: AsyncSession,
    use_hardened: bool = True
) -> str:
    """
    Generate AI advice for a student using hardened prompt templates.
    Fully async implementation for use in FastAPI async routes.

    Args:
        student_id: Student ID to generate advice for
        prompt_name: Name of the prompt template (faculty or marketing)
        db: AsyncSession for database queries
        use_hardened: Whether to use hardened templates (default: True for security)

    Returns:
        AI-generated advice string, or error message if generation fails
    """
    # Fetch student data asynchronously
    result = await db.execute(
        select(Student).where(Student.id == student_id)
    )
    student = result.scalar_one_or_none()

    if not student:
        return f"Error: Student '{student_id}' not found"

    # Fetch latest prediction asynchronously
    pred_result = await db.execute(
        select(Prediction)
        .where(Prediction.student_id == student_id)
        .order_by(Prediction.prediction_timestamp.desc())
    )
    latest_prediction = pred_result.scalar_one_or_none()

    if not latest_prediction:
        return "Error: No prediction data available for this student."

    # Load prompt template (blocking I/O wrapped in executor)
    try:
        prompt_template = await _load_prompt_template(prompt_name, use_hardened)
    except FileNotFoundError as e:
        return f"Error: {e}"

    # SANITIZE ALL STUDENT DATA BEFORE INJECTING INTO PROMPT
    # This prevents prompt injection attacks via student data fields
    prompt_data = {
        "student_name": security_manager.sanitize_student_name(
            f"{student.first_name or ''} {student.last_name or ''}".strip() or student.id
        ),
        "risk_score": security_manager.sanitize_for_llm(
            f"{latest_prediction.risk_score:.2f}%", max_length=50
        ),
        "retention_likelihood": security_manager.sanitize_for_llm(
            str(latest_prediction.retention_likelihood), max_length=100
        ),
        "grades": security_manager.sanitize_for_llm(
            f"{latest_prediction.grades:.2f}", max_length=50
        ),
        "attendance": security_manager.sanitize_for_llm(
            f"{latest_prediction.attendance:.2f}%", max_length=50
        ),
        "engagement_score": security_manager.sanitize_for_llm(
            f"{latest_prediction.engagement_score:.2f}%", max_length=50
        ),
    }
    formatted_prompt = prompt_template.format(**prompt_data)

    # System message is trusted - no user input here
    system_message = f"You are an AI assistant providing advice to a {prompt_name} team regarding student retention."

    try:
        if LLM_PROVIDER == "gemini":
            if not GENAI_AVAILABLE:
                return "Error: AI service unavailable - google-generativeai package not installed"
            if not GEMINI_API_KEY:
                return "Error: GEMINI_API_KEY environment variable not set"

            # Gemini SDK is synchronous - wrap in executor to not block event loop
            # This allows other FastAPI requests to be handled during the LLM call
            loop = asyncio.get_event_loop()

            def _gemini_generate():
                client = genai.Client(api_key=GEMINI_API_KEY)
                return client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=f"{system_message}\n\n{formatted_prompt}"
                )

            response = await loop.run_in_executor(_executor, _gemini_generate)
            return response.text

        elif LLM_PROVIDER == "claude":
            if not ANTHROPIC_AVAILABLE:
                return "Error: AI service unavailable - anthropic package not installed"
            if not CLAUDE_API_KEY:
                return "Error: CLAUDE_API_KEY environment variable not set"
            if async_anthropic_client is None:
                return "Error: Claude client not initialized."

            # Use native async Anthropic client (non-blocking)
            message = await async_anthropic_client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=LLM_MAX_TOKENS,
                temperature=LLM_TEMPERATURE,
                system=system_message,
                messages=[
                    {"role": "user", "content": formatted_prompt}
                ]
            )
            return message.content[0].text

        else:
            return f"Error: Unsupported LLM_PROVIDER: {LLM_PROVIDER}"

    except Exception as e:
        return f"Error: Could not get AI advice - {e}"


async def main_test():
    """Async test function for the AI advisor."""
    from backend.database.connection import AsyncSessionLocal

    print("Testing the AI Advisor service (async)...")

    async with AsyncSessionLocal() as db:
        # Fetch first student
        result = await db.execute(select(Student))
        test_student = result.scalar_one_or_none()

        if test_student:
            print(f"\n--- Generating 'Faculty' advice for student: {test_student.id} ---")
            faculty_prompt = await get_ai_advice(test_student.id, 'faculty', db)
            print(faculty_prompt)

            print(f"\n--- Generating 'Marketing' advice for student: {test_student.id} ---")
            marketing_prompt = await get_ai_advice(test_student.id, 'marketing', db)
            print(marketing_prompt)
        else:
            print("No students found in the database to test the AI Advisor.")


if __name__ == '__main__':
    # Run async test
    asyncio.run(main_test())
