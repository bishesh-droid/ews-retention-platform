import os
try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    genai = None
    GENAI_AVAILABLE = False

from backend.database import Student, Prediction

PROMPTS_DIR = 'prompts'
GEMINI_MODEL = "gemini-pro"

if GENAI_AVAILABLE and os.getenv("GEMINI_API_KEY"):
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
def get_ai_advice(student: Student, prompt_name: str) -> str:
    if not GENAI_AVAILABLE:
        return "Error: AI service unavailable - google-generativeai package not installed"

    if not os.getenv("GEMINI_API_KEY"):
        return "Error: GEMINI_API_KEY environment variable not set"

    prompt_file = f"{prompt_name}_advice.txt"
    prompt_path = os.path.join(PROMPTS_DIR, prompt_file)
    if not os.path.exists(prompt_path):
        return f"Error: Prompt file not found at {prompt_path}"
    with open(prompt_path, 'r') as f:
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
    try:
        model = genai.GenerativeModel(GEMINI_MODEL)
        response = model.generate_content(
            [
                f"You are an AI assistant providing advice to a {prompt_name} team regarding student retention.",
                formatted_prompt
            ]
        )
        return response.text
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
