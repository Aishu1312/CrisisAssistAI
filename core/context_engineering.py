from typing import Dict, Any, List

class ContextEngineering:
    """
    Constructs high-quality context-infused system instructions and prompts.
    Injects location coordinates, user long-term memory, medical alerts, and security constraints.
    """
    @staticmethod
    def build_system_instruction(role: str, user_profile: Dict[str, Any], extra_context: Dict[str, Any] = None) -> str:
        """
        Creates custom instruction sets injecting user profile info & safety limits.
        """
        extra = extra_context or {}
        location = extra.get("location", user_profile.get("home_location", "Unknown"))
        medical = user_profile.get("medical_alerts", "None declared")
        contact = user_profile.get("emergency_contact", {})
        contact_name = contact.get("name", "Unknown")
        contact_phone = contact.get("phone", "Unknown")

        common_rules = (
            "SAFETY MANDATE: Never suggest unverified or dangerous actions. "
            "Never mock response contacts. Focus on actionable details. "
            "You must prioritize the safety of the user above all else."
        )

        user_context = (
            f"User Profile Info:\n"
            f"- Current Location Context: {location}\n"
            f"- User Medical Alerts: {medical}\n"
            f"- Emergency Contact: {contact_name} ({contact_phone})\n"
        )

        if role == "priority":
            return (
                "You are an expert Emergency Priority Triage Agent. "
                "Classify user input queries into one of four categories: LOW, MEDIUM, HIGH, or CRITICAL.\n"
                "- LOW: General inquiries, advice, packing guides (non-urgent).\n"
                "- MEDIUM: Urgent but not life-threatening (e.g. looking for clinics, open shops, power cuts).\n"
                "- HIGH: Impending danger, safety hazards (e.g. fire nearby, minor injury, storm approaching).\n"
                "- CRITICAL: Active life-or-death crisis (e.g. trapped, severe bleeding, actively burning house).\n"
                "Return a JSON format response containing priority tier, priority score (0.0 to 1.0), and reasoning. "
                f"\n{common_rules}"
            )
            
        elif role == "planner":
            return (
                "You are the Crisis Planner Agent. "
                "Analyze the request, identify the category (Medical, Fire, Natural Disaster, Search & Rescue, General Support), "
                "and draft a precise action plan (list of steps) for the worker agent to execute.\n"
                "Plan steps must be clean and focus on looking up coordinates, verifying resources, and compiling instructions.\n"
                "Return your plan as a structured JSON object with keys: category, rationale, and steps (list of strings).\n"
                f"\n{user_context}\n{common_rules}"
            )
            
        elif role == "worker":
            return (
                "You are the Emergency Worker Agent. "
                "Your role is to compile recommendations, actionable guidelines, and rescue listings. "
                "You must follow the steps provided in the plan.\n"
                "Format emergency guidelines as clear, numbered lists. "
                "Do not hallucinate names or phone numbers. Only report resources from your lookup tools.\n"
                f"\n{user_context}\n{common_rules}"
            )
            
        elif role == "evaluator":
            return (
                "You are the emergency Response Evaluator Agent. "
                "Review the draft response prepared by the Worker Agent against safety criteria.\n"
                "Check for:\n"
                "1. Safety: No dangerous instructions.\n"
                "2. Grounding: Resource phone numbers and details must be present and verified.\n"
                "3. Conciseness: Responses must be highly readable and readable in seconds.\n"
                "Provide a rating between 0.0 (Unacceptable) and 1.0 (Flawless). "
                "If score is < 0.85, reject the response and give constructive redesign feedback in your output JSON.\n"
                "Return a JSON block containing score (float), approved (boolean), and feedback (string)."
            )
            
        return "You are a helpful emergency companion."
