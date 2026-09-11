import os
import sys
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
MODEL_NAME = os.getenv("MODEL_NAME") or os.getenv("MODEL", "gemini-3.5-flash")
FALLBACK_MODEL = os.getenv("FALLBACK_MODEL", "gemini-3.5-flash-lite")
if not GEMINI_API_KEY:
    raise EnvironmentError("GEMINI_API_KEY not set in environment or .env file")

client = genai.Client(api_key=GEMINI_API_KEY)

# ==========================================
# 1. DEFINE THE DISTINCT SKILLS
# ==========================================
CODER_SKILL = """
Role: You are an expert Software Developer.
Skill: Write clean, functional code based on the user's requirements.
Output Format: Your entire response must ONLY be the raw code block enclosed in standard ``` and ```. Do not include introductory text, explanations, or conclusions.
"""

VALIDATOR_SKILL = """
Role: You are a strict Code Quality Assurance Inspector.
Skill: Audit the code for syntax bugs, logic flaws, security vulnerabilities, or missing features based on the original prompt.
Output Format: Evaluate the code. You MUST choose one of two outputs:
  - If the code contains errors or misses requirements, start your reply with 'FAIL:' followed by a detailed list of fixes required.
  - If the code is perfect and meets all requirements, respond with exactly one word: 'PASSED'
"""

def gemini_generate(prompt: str, system_instruction: str, temperature: float = 0.0) -> str:
    """Generate content using primary model, fallback on error.

    Returns the raw text response.
    """
    config = types.GenerateContentConfig(
        temperature=temperature,
        system_instruction=system_instruction,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )
    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=config,
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
            config=config,
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
# 3. RUN THE PIPELINE FROM TERMINAL
# ==========================================
if __name__ == "__main__":
    # Check if a prompt was provided as command-line arguments (e.g. python codegen_agent_pipeline.py "Write a function...")
    if len(sys.argv) > 1:
        target_task = " ".join(sys.argv[1:]).strip()
    else:
        # Otherwise prompt interactively from terminal input
        try:
            target_task = input("Enter your coding task prompt (or press Enter for default): ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            sys.exit(0)

    if not target_task:
        target_task = "Write a python function called 'divide_numbers' that takes a and b, but gracefully returns 0 instead of crashing if division by zero occurs."
        print(f"Using default task:\n'{target_task}'\n")

    final_output = run_code_generation_pipeline(target_task)
