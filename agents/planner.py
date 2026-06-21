import re
import json
from google import genai
from core.a2a_protocol import AgentMessage

class PlannerAgent:
    """
    Planner Agent. Performs Priority Triage and creates localized workflow plans.
    """
    def __init__(self, gemini_client: genai.Client = None):
        self.client = gemini_client
        self.triage_rules = {
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
        payload = message.payload
        query = payload.get("query", "")
        lang_code = payload.get("language", "en")
        
        # Languages mapping
        lang_map = {
            "en": "English", "hi": "Hindi", "mr": "Marathi", "bn": "Bengali", "te": "Telugu",
            "ta": "Tamil", "gu": "Gujarati", "kn": "Kannada", "ml": "Malayalam", "pa": "Punjabi",
            "ur": "Urdu", "or": "Odia", "as": "Assamese", "ne": "Nepali", "sa": "Sanskrit",
            "es": "Spanish", "fr": "French", "de": "German", "it": "Italian", "pt": "Portuguese",
            "zh": "Chinese", "ja": "Japanese", "ko": "Korean", "ar": "Arabic", "ru": "Russian",
            "tr": "Turkish", "id": "Indonesian", "vi": "Vietnamese"
        }
        lang_name = lang_map.get(lang_code, "English")

        # 1. Classify Priority (Triage)
        priority_tier = "LOW"
        priority_score = 0.1
        triage_reason = "Query contains standard general inquiry keywords."
        
        query_lower = query.lower()
        matched = False
        for tier, patterns in self.triage_rules.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    priority_tier = tier
                    matched = True
                    if tier == "CRITICAL":
                        priority_score = 0.95
                        triage_reason = f"Critical indicator keyword match detected: '{pattern}'"
                    elif tier == "HIGH":
                        priority_score = 0.75
                        triage_reason = f"High priority indicator keyword match detected: '{pattern}'"
                    elif tier == "MEDIUM":
                        priority_score = 0.45
                        triage_reason = f"Medium urgency keyword match detected: '{pattern}'"
                    break
            if matched:
                break

        # Triage LLM check
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
                text = response.text.strip()
                if text.startswith("```"):
                    text = re.sub(r"^```(?:json)?\n", "", text)
                    text = re.sub(r"\n```$", "", text)
                parsed = json.loads(text)
                if parsed.get("priority_tier") in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]:
                    priority_tier = parsed["priority_tier"]
                    priority_score = float(parsed.get("priority_score", 0.5))
                    triage_reason = parsed.get("reasoning", "LLM classified priority.")
            except Exception as e:
                print(f"Priority Triage LLM failed: {e}. Using rules.")

        # 2. Planning Steps and Category
        category = "General Support"
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
        rationale = f"Detected category as '{category}' based on emergency terms."

        if self.client:
            try:
                system_instruction = (
                    "You are the Crisis Planner Agent. "
                    f"Analyze the request, identify the category (Medical, Fire, Natural Disaster, Search & Rescue, General Support), "
                    f"and draft a precise action plan (list of steps) for the worker agent to execute. "
                    f"IMPORTANT: You must write the rationale and all steps in the plan completely in {lang_name}. Do not output in English. "
                    f"Return your plan as a structured JSON object with keys: category, rationale, and steps (list of strings)."
                )
                prompt = (
                    "Create an emergency plan. Output ONLY a valid JSON string "
                    "with keys: 'category', 'rationale', and 'steps'.\n\n"
                    f"User Query: '{query}'\n"
                    f"Classified Priority: {priority_tier}"
                )
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config={"system_instruction": system_instruction}
                )
                text = response.text.strip()
                if text.startswith("```"):
                    text = re.sub(r"^```(?:json)?\n", "", text)
                    text = re.sub(r"\n```$", "", text)
                parsed = json.loads(text)
                if parsed.get("category") and parsed.get("steps"):
                    category = parsed["category"]
                    steps = parsed["steps"]
                    rationale = parsed.get("rationale", "LLM-synthesized action steps.")
            except Exception as e:
                print(f"Planner LLM planning failed: {e}. Using rule fallback.")

        response_payload = {
            "query": query,
            "priority": priority_tier,
            "priority_score": priority_score,
            "triage_reason": triage_reason,
            "category": category,
            "rationale": rationale,
            "steps": steps,
            "language": lang_code,
            "language_name": lang_name
        }

        return AgentMessage(
            sender="PlannerAgent",
            receiver=message.sender,
            message_type="PLAN",
            payload=response_payload,
            trace_id=message.trace_id
        )
