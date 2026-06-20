import re
import json
from google import genai
from core.a2a_protocol import AgentMessage

class PlannerAgent:
    """
    Planner Agent. Analyzes crisis requests and outlines sequential action plans.
    """
    def __init__(self, gemini_client: genai.Client = None):
        self.client = gemini_client

    def run(self, message: AgentMessage, user_profile: dict) -> AgentMessage:
        query = message.payload.get("query", "")
        priority = message.payload.get("priority_tier", "LOW")
        
        category = "General Support"
        query_lower = query.lower()
        if any(w in query_lower for w in ["hospital", "medical", "blood", "doctor", "injured", "bimar", "chot", "pain"]):
            category = "Medical"
        elif any(w in query_lower for w in ["fire", "smoke", "burning", "aag", "explosion"]):
            category = "Fire"
        elif any(w in query_lower for w in ["flood", "rain", "storm", "earthquake", "cyclone", "bhukamp", "tsunami"]):
            category = "Natural Disaster"
        elif any(w in query_lower for w in ["trapped", "rescue", "drowning", "stuck", "bachao", "save"]):
            category = "Search & Rescue"

        steps = [
            f"Geocode user location for {query}",
            f"Search nearby {category} resource databases",
            f"Filter and verify resource availability status",
            "Generate actionable safety instruction checklist"
        ]
        rationale = f"Detected category as '{category}' based on emergency terms in query."

        if self.client:
            try:
                system_instruction = (
                    "You are the Crisis Planner Agent. "
                    "Analyze the request, identify the category (Medical, Fire, Natural Disaster, Search & Rescue, General Support), "
                    "and draft a precise action plan (list of steps) for the worker agent to execute.\n"
                    "Plan steps must be clean and focus on looking up coordinates, verifying resources, and compiling instructions.\n"
                    "Return your plan as a structured JSON object with keys: category, rationale, and steps (list of strings)."
                )
                prompt = (
                    "Create an emergency plan. Output ONLY a valid JSON string "
                    "with keys: 'category', 'rationale', and 'steps'.\n\n"
                    f"User Query: '{query}'\n"
                    f"Classified Priority: {priority}"
                )
                
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config={"system_instruction": system_instruction}
                )
                
                response_text = response.text.strip()
                if response_text.startswith("```"):
                    response_text = re.sub(r"^```(?:json)?\n", "", response_text)
                    response_text = re.sub(r"\n```$", "", response_text)
                    
                parsed = json.loads(response_text)
                if parsed.get("category") and parsed.get("steps"):
                    category = parsed["category"]
                    steps = parsed["steps"]
                    rationale = parsed.get("rationale", "LLM-synthesized action steps.")
            except Exception as e:
                print(f"PlannerAgent LLM planning failed: {e}. Falling back to rules.")

        response_payload = {
            "query": query,
            "priority": priority,
            "category": category,
            "rationale": rationale,
            "steps": steps
        }
        
        return AgentMessage(
            sender="PlannerAgent",
            receiver=message.sender,
            message_type="PLAN",
            payload=response_payload,
            trace_id=message.trace_id
        )
