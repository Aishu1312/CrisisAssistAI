import re
import json
from google import genai
from core.a2a_protocol import AgentMessage

class PriorityAgent:
    """
    Triage Classifier. Urgency assessment from LOW to CRITICAL.
    Uses rule-based checks and Gemini LLM.
    """
    def __init__(self, gemini_client: genai.Client = None):
        self.client = gemini_client
        self.rules = {
            "CRITICAL": [
                r"\btrapped\b", r"\bburning\b", r"\bbleeding\b", r"\bheart attack\b", 
                r"\bchoking\b", r"\bdrowning\b", r"\bcant breathe\b", r"\bcan't breathe\b",
                r"\bbachao\b", r"\bmar gaya\b", r"\bkoil nahi hai\b", r"\bvaachva\b"
            ],
            "HIGH": [
                r"\bfire\b", r"\baag\b", r"\binjured\b", r"\baccident\b", r"\bstorm\b", 
                r"\bflood\b", r"\bbhukamp\b", r"\bearthquake\b", r"\bchot\b", r"\bdanger\b"
            ],
            "MEDIUM": [
                r"\bclinic\b", r"\bpharmacy\b", r"\bmedicine\b", r"\bpower cut\b", 
                r"\bdawa\b", r"\bpower outage\b", r"\bwater logging\b", r"\broad block\b"
            ]
        }

    def run(self, message: AgentMessage, user_profile: dict) -> AgentMessage:
        query = message.payload.get("query", "")
        priority_tier = "LOW"
        priority_score = 0.1
        reasoning = "Query contains standard general inquiry keywords."
        
        query_lower = query.lower()
        matched = False
        for tier, patterns in self.rules.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    priority_tier = tier
                    matched = True
                    if tier == "CRITICAL":
                        priority_score = 0.95
                        reasoning = f"Critical indicator keyword match detected: '{pattern}'"
                    elif tier == "HIGH":
                        priority_score = 0.75
                        reasoning = f"High priority indicator keyword match detected: '{pattern}'"
                    elif tier == "MEDIUM":
                        priority_score = 0.45
                        reasoning = f"Medium urgency keyword match detected: '{pattern}'"
                    break
            if matched:
                break
                
        if self.client:
            try:
                system_instruction = (
                    "You are an expert Emergency Priority Triage Agent. "
                    "Classify user input queries into one of four categories: LOW, MEDIUM, HIGH, or CRITICAL.\n"
                    "- LOW: General inquiries, advice, packing guides (non-urgent).\n"
                    "- MEDIUM: Urgent but not life-threatening (e.g. looking for clinics, open shops, power cuts).\n"
                    "- HIGH: Impending danger, safety hazards (e.g. fire nearby, minor injury, storm approaching).\n"
                    "- CRITICAL: Active life-or-death crisis (e.g. trapped, severe bleeding, actively burning house).\n"
                    "Return a JSON format response containing priority_tier, priority_score (0.0 to 1.0), and reasoning. "
                )
                prompt = (
                    "Analyze this query and classify it. Output ONLY a valid JSON string "
                    "with keys: 'priority_tier', 'priority_score', and 'reasoning'.\n\n"
                    f"User Query: '{query}'"
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
                if parsed.get("priority_tier") in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]:
                    priority_tier = parsed["priority_tier"]
                    priority_score = float(parsed.get("priority_score", 0.5))
                    reasoning = parsed.get("reasoning", "LLM classified priority.")
            except Exception as e:
                print(f"PriorityAgent LLM triage failed: {e}. Falling back to rules.")

        response_payload = {
            "query": query,
            "priority_tier": priority_tier,
            "priority_score": priority_score,
            "reasoning": reasoning
        }
        
        return AgentMessage(
            sender="PriorityAgent",
            receiver=message.sender,
            message_type="RESPONSE",
            payload=response_payload,
            trace_id=message.trace_id
        )
