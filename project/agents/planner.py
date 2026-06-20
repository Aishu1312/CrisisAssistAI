import re
import json
from google import genai
from core.context_engineering import ContextEngineering
from core.a2a_protocol import AgentMessage

class PlannerAgent:
    """
    Analyzes crisis queries, detects categories, and defines execution task lists.
    Collaborates with Worker Agent via structured plans.
    """
    def __init__(self, gemini_client: genai.Client = None):
        self.client = gemini_client

    def run(self, message: AgentMessage, user_profile: dict) -> AgentMessage:
        """
        Generates a task sequence matching the user's emergency.
        """
        query = message.payload.get("query", "")
        priority = message.payload.get("priority_tier", "LOW")
        
        # Default heuristic classification
        category = "General Support"
        query_lower = query.lower()
        
        # Simple string-matching category classifiers
        if any(w in query_lower for w in ["hospital", "medical", "blood", "doctor", "injured", "bimar", "chot", "pain"]):
            category = "Medical"
        elif any(w in query_lower for w in ["fire", "smoke", "burning", "aag", "explosion"]):
            category = "Fire"
        elif any(w in query_lower for w in ["flood", "rain", "storm", "earthquake", "cyclone", "bhukamp", "tsunami"]):
            category = "Natural Disaster"
        elif any(w in query_lower for w in ["trapped", "rescue", "drowning", "stuck", "bachao", "save"]):
            category = "Search & Rescue"

        # Heuristic steps based on category
        steps = [
            f"Geocode user location for {query}",
            f"Search nearby {category} resource databases",
            f"Filter and verify resource availability status",
            "Generate actionable safety instruction checklist"
        ]
        rationale = f"Detected category as '{category}' based on emergency terms in query."

        # Leverage Gemini for more precise planning if available
        if self.client:
            try:
                system_instruction = ContextEngineering.build_system_instruction("planner", user_profile)
                prompt = (
                    "Create an emergency plan. Output ONLY a valid JSON string (no markdown ticks, no preamble) "
                    "with keys: 'category' (Medical, Fire, Natural Disaster, Search & Rescue, General Support), 'rationale' (string), and 'steps' (list of strings).\n\n"
                    f"User Query: '{query}'\n"
                    f"Classified Priority: {priority}"
                )
                
                response = self.client.models.generate_content(
                    model="gemini-1.5-flash",
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
                print(f"PlannerAgent LLM planning failed: {e}. Falling back to default steps.")

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
