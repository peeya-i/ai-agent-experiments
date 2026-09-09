import os
from google import genai
from google.genai import types
import logging
# Load environment variables from .env if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Configuration from .env
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "gemini-3.5-flash")
FALLBACK_MODEL = os.getenv("FALLBACK_MODEL", "gemini-3.6-flash")
if not GEMINI_API_KEY:
    raise EnvironmentError("GEMINI_API_KEY not set in environment or .env file")

genai.configure(api_key=GEMINI_API_KEY)
client = genai.Client()

# ==========================================
# 1. DEFINE THE DISTINCT SKILLS
# ==========================================
CODER_SKILL = """
Role: You are an expert Python Developer.
Skill: Write clean, functional Python code based on the user's requirements.
Output Format: Your entire response must ONLY be the raw Python code block enclosed in standard ```python and ```. Do not include introductory text, explanations, or conclusions.
"""

VALIDATOR_SKILL = """
Role: You are a strict Code Quality Assurance Inspector.
Skill: Audit python code for syntax bugs, logic flaws, security vulnerabilities, or missing features based on the original prompt.
Output Format: Evaluate the code. You MUST choose one of two outputs:
  - If the code contains errors or misses requirements, start your reply with 'FAIL:' followed by a detailed list of fixes required.
  - If the code is perfect and meets all requirements, respond with exactly one word: 'PASSED'
"""

def gemini_generate(prompt: str, system_instruction: str, temperature: float = 0.0) -> str:
    """Generate content using primary model, fallback on error.

    Returns the raw text response.
    """
    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            generation_config=types.GenerationConfig(
                temperature=temperature,
            ),
            system_instruction=system_instruction,
        )
    except Exception as exc:
        logging.getLogger("pipeline_logger").warning(
            "Primary model %s failed (%s); falling back to %s",
            MODEL_NAME,
            exc,
            FALLBACK_MODEL,
        )
        response = client.models.generate_content(
            model=FALLBACK_MODEL,
            contents=prompt,
            generation_config=types.GenerationConfig(
                temperature=temperature,
            ),
            system_instruction=system_instruction,
        )
    return response.text.strip()

# ==========================================
# 2. RUN THE AUTOMATED VALIDATION PIPELINE
# ==========================================
def run_code_generation_pipeline(user_request: str, max_retries: int = 3):
    print(f"🚀 Pipeline Initiated for: '{user_request}'\n")
    
    # Track the active conversation flow between the two agents
    current_code = ""
    feedback = "Initial Request"
    
    # Core loop simulating the pipeline
    for attempt in range(1, max_retries + 1):
        print(f"--- [Pipeline Iteration {attempt}] ---")
        
        # Step A: The Coder Agent executes its writing skill
        # It takes into account the original request AND any negative feedback from last turn
        coder_prompt = f"Original Request: {user_request}\nPrevious Feedback/Context: {feedback}\nGenerate the updated Python code:"
        
        print("💻 Coder Agent is writing/refining code...")
        current_code = gemini_generate(
    prompt=coder_prompt,
    system_instruction=CODER_SKILL,
    temperature=0.4,
)
        print(f"\n[Generated Code Output]:\n{current_code}\n")
        
        # Step B: The Validator Agent executes its evaluation skill
        validator_prompt = f"Original Request Target: {user_request}\nCode to Inspect:\n{current_code}"
        
        print("🔍 Validator Agent is auditing the code...")
        feedback = gemini_generate(
    prompt=validator_prompt,
    system_instruction=VALIDATOR_SKILL,
    temperature=0.0,
)
        print(f"[Validator Verdict]: {feedback}\n")
        
        # Step C: Evaluate loop breaking conditions
        if feedback.upper() == "PASSED":
            print(f"✅ Pipeline Success! Code passed validation on attempt {attempt}.")
            return current_code
            
        print("❌ Code validation failed. Routing feedback back to Coder Agent for correction...")
    
    print("⚠️ Pipeline stopped. Reached maximum retry limits without full approval.")
    return current_code

# ==========================================
# 3. TEST THE PIPELINE
# ==========================================
# We give a tricky request to force a scenario where a validation rule might check logic
target_task = "Write a python function called 'divide_numbers' that takes a and b, but gracefully returns 0 instead of crashing if division by zero occurs."

final_output = run_code_generation_pipeline(target_task)
