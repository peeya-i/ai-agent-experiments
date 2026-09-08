import json

# ==========================================
# 1. THE TOOL (The Action)
# ==========================================
def calculate_square_footage(dimensions: str) -> str:
    """Calculates the area given a string like '10x12'."""
    try:
        width, height = map(int, dimensions.lower().split('x'))
        return f"{width * height} sq ft"
    except Exception:
        return "Error: Invalid dimensions format. Use 'WidthxHeight'."

# Available tools mapping
TOOLS = {
    "calculate_square_footage": calculate_square_footage
}

# ==========================================
# 2. THE SKILL / SYSTEM PROMPT (The Strategy)
# ==========================================
# A skill dictates the exact protocol the agent must follow to solve a task.
# Basic folder structure for the skill is:
# ------------------------------------------
# PROJECT ROOT
# ------------------------------------------
# floorplan-skill/
# ├── SKILL.md
# ├── SKILL.py        <-- Our Python skill code
# ├── requirements.txt
# └── tools/
#     └── __init__.py
#     └── calcuate_square_footage.py
# ------------------------------------------

FLOORPLAN_ANALYSIS_SKILL = """
## Identity
 - Name: FloorPlanAnalysisSkill
 - Version: 1.0
 - Owner: Peeya
 - Description: Floor plan analysis skills for determining room sizes.

## CRITICAL RULES:
1. Always calculate the square footage using the 'calculate_square_footage' tool first.
2. Standard comfort rule: Any room below 100 sq ft is considered 'Small'. 100 sq ft or above is 'Spacious'.
3. You must respond in one of two formats:
   
   If you need to call a tool, respond with EXACTLY this JSON structure:
   {"action": "TOOL_NAME", "argument": "ARGUMENT_VALUE"}
   
   If you have the final answer, respond with EXACTLY this JSON structure:
   {"final_answer": "YOUR_DETAILED_EVALUATION"}
"""

# ==========================================
# 3. MOCK LLM (Simulating Brain Output)
# ==========================================
def mock_llm_response(messages: list) -> str:
    """Simulates how an LLM would think across multiple turns."""
    print("LLM Input messages ", messages)
    user_query = messages[1]["content"]
    history_len = len(messages)
    print("LLM history_len ", history_len)
    
    # Turn 1: LLM parses the user query and decides to use a tool
    if history_len == 2: 
        return json.dumps({
            "action": "calculate_square_footage",
            "argument": "12x8"
        })
    
    # Turn 2: LLM receives the tool output and applies its Skill logic
    elif history_len == 4:
        tool_output = messages[-1]["content"] # "96 sq ft"
        return json.dumps({
            "final_answer": f"The room is {tool_output}. According to our comfort standards, because it is under 100 sq ft, it is classified as 'Small'."
        })
    
    return json.dumps({"final_answer": "I am unsure how to proceed."})

# ==========================================
# 4. THE AGENT REASONING LOOP (Plan -> Act -> Observe)
# ==========================================
def run_agent(user_query: str):
    print(f"🚀 User Query: '{user_query}'\n")
    
    # Initialize agent memory with its assigned Skill and the User Request
    messages = [
        {"role": "system", "content": FLOORPLAN_ANALYSIS_SKILL},
        {"role": "user", "content": user_query}
    ]
    
    max_steps = 5
    for step in range(max_steps):
        print(f"--- 🧠 Agent Loop Step {step + 1} ---")
        
        # Step 1: Brain evaluates current state (Plan)
        llm_output = mock_llm_response(messages)
        messages.append({"role": "assistant", "content": llm_output})
        
        response_data = json.loads(llm_output)
        
        # Step 2: Check if final answer is reached
        if "final_answer" in response_data:
            print(f"🎯 Final Agent Response:\n{response_data['final_answer']}")
            break
            
        # Step 3: Execute tool action if requested (Act)
        elif "action" in response_data:
            tool_name = response_data["action"]
            tool_arg = response_data["argument"]
            
            print(f"🔧 [Tool Call] Invoking '{tool_name}' with argument '{tool_arg}'...")
            
            if tool_name in TOOLS:
                # Step 4: Capture tool result (Observe)
                observation = TOOLS[tool_name](tool_arg)
                print(f"👁️ [Observation] Tool returned: '{observation}'\n")
                
                # Feed observation back to memory so the agent knows what happened
                messages.append({"role": "tool", "content": observation})
            else:
                print(f"❌ Error: Tool {tool_name} not found.")
                break

# Run the agent
run_agent("Evaluate the master bedroom layout which has dimensions of 12x8.")
