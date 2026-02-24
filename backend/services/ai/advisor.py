import os
try:
    from google import genai
    GENAI_AVAILABLE = True
except ImportError:
    genai = None
    GENAI_AVAILABLE = False

try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    Anthropic = None
    ANTHROPIC_AVAILABLE = False

from backend.database import Student, Prediction
from backend.config import LLM_PROVIDER, GEMINI_API_KEY, GEMINI_MODEL, CLAUDE_API_KEY, CLAUDE_MODEL, LLM_TEMPERATURE, LLM_MAX_TOKENS

PROMPTS_DIR = 'prompts'

# Initialize LLM client based on configuration
gemini_client = None
claude_client = None

if LLM_PROVIDER == "gemini" and GENAI_AVAILABLE and GEMINI_API_KEY:
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)
elif LLM_PROVIDER == "claude" and ANTHROPIC_AVAILABLE and CLAUDE_API_KEY:
    claude_client = Anthropic(api_key=CLAUDE_API_KEY)

def get_ai_advice(student: Student, prompt_name: str) -> str:
    prompt_file = os.path.join(PROMPTS_DIR, f"{prompt_name}_advice.txt")
    if not os.path.exists(prompt_file):
        return f"Error: Prompt file not found at {prompt_file}"

    with open(prompt_file, 'r') as f:
        prompt_template = f.read()

    latest_prediction = student.predictions[0] if student.predictions else None
    if not latest_prediction:
        return "Error: No prediction data available for this student."

    prompt_data = {
        "student_name": f"Student {student.id}",
        "risk_score": f"{latest_prediction.risk_score:.2f}%",
        "retention_likelihood": latest_prediction.retention_likelihood,
        "grades": f"{latest_prediction.grades:.2f}",
        "attendance": f"{latest_prediction.attendance:.2f}%",
        "engagement_score": f"{latest_prediction.engagement_score:.2f}%"
    }
    formatted_prompt = prompt_template.format(**prompt_data)
    
    system_message = f"You are an AI assistant providing advice to a {prompt_name} team regarding student retention."

    try:
        if LLM_PROVIDER == "gemini":
            if not GENAI_AVAILABLE:
                return "Error: AI service unavailable - google-generativeai package not installed"
            if not GEMINI_API_KEY:
                return "Error: GEMINI_API_KEY environment variable not set"
            
            response = gemini_client.models.generate_content(
                model=GEMINI_MODEL,
                contents=f"{system_message}\n\n{formatted_prompt}"
            )
            return response.text
        elif LLM_PROVIDER == "claude":
            if not ANTHROPIC_AVAILABLE:
                return "Error: AI service unavailable - anthropic package not installed"
            if not CLAUDE_API_KEY:
                return "Error: CLAUDE_API_KEY environment variable not set"
            if claude_client is None:
                return "Error: Claude client not initialized."

            message = claude_client.messages.create(
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
if __name__ == '__main__':
    from database import SessionLocal
    print("Testing the AI Advisor service...")
    db = SessionLocal()
    test_student = db.query(Student).first()
    if test_student:
        print(f"\n--- Generating 'Faculty' advice for student: {test_student.id} ---")
        faculty_prompt = get_ai_advice(test_student, 'faculty')
        print(faculty_prompt)
        print(f"\n--- Generating 'Marketing' advice for student: {test_student.id} ---")
        marketing_prompt = get_ai_advice(test_student, 'marketing')
        print(marketing_prompt)
    else:
        print("No students found in the database to test the AI Advisor.")
    db.close()
