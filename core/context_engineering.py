from typing import Dict, Any, List

class ContextEngineering:
    """
    Constructs high-quality context-infused system instructions and prompts.
    Injects user profile details (name, location, allergies, conditions, contacts)
    and target language mandates into agent instructions.
    """
    @staticmethod
    def build_system_instruction(
        role: str, 
        user_profile: Dict[str, Any], 
        target_lang_name: str = "English",
        extra_context: Dict[str, Any] = None
    ) -> str:
        """
        Creates custom instruction sets injecting user profile info, medical limits, and language mandates.
        """
        extra = extra_context or {}
        
        # User details with fallbacks
        name = user_profile.get("name", "Jane Doe")
        location = user_profile.get("location") or user_profile.get("home_location") or extra.get("location", "Pune, Maharashtra")
        
        # Allergies: handle list or comma-separated string
        allergies_raw = user_profile.get("allergies", ["None declared"])
        if isinstance(allergies_raw, list):
            allergies = ", ".join(allergies_raw) if allergies_raw else "None declared"
        else:
            allergies = str(allergies_raw)
            
        # Medical Conditions
        conditions_raw = user_profile.get("medical_conditions", [])
        if isinstance(conditions_raw, list):
            conditions = ", ".join(conditions_raw) if conditions_raw else "None"
        else:
            conditions = str(conditions_raw)

        contact = user_profile.get("emergency_contact", {})
        contact_name = contact.get("name", "John Doe")
        contact_phone = contact.get("phone", "+91-98765-43210")

        common_rules = (
            "SAFETY MANDATE: Never suggest unverified or dangerous actions. "
            "Never mock response contacts. Focus on actionable details. "
            "You must prioritize the safety of the user above all else. "
            f"IMPORTANT: You must output your thoughts, plans, rationales, guidelines, checklists, and safety feedback completely in {target_lang_name}. Do not output in English."
        )

        user_context = (
            f"User Profile Info:\n"
            f"- User Name: {name}\n"
            f"- Current Location Context: {location}\n"
            f"- User Allergies / Medical Alerts: {allergies}\n"
            f"- Medical Conditions: {conditions}\n"
            f"- Emergency Contact: {contact_name} ({contact_phone})\n"
        )
        
        # Allergy safety rule
        allergy_safety = (
            f"CRITICAL MEDICAL CHECK: The user is allergic to {allergies}. "
            "You must NEVER recommend any medications, treatments, or substances that trigger or conflict with these allergies (for example, if they are allergic to Penicillin, do not suggest administering penicillin, etc.). "
            "Customize emergency guidelines to ensure compliance with this allergy restriction."
        )

        if role == "priority":
            return (
                "You are an expert Emergency Priority Triage Agent. "
                "Classify user input queries into one of four categories: LOW, MEDIUM, HIGH, or CRITICAL.\n"
                "- LOW: General inquiries, advice, packing guides (non-urgent).\n"
                "- MEDIUM: Urgent but not life-threatening (e.g. looking for clinics, open shops, power cuts).\n"
                "- HIGH: Impending danger, safety hazards (e.g. fire nearby, minor injury, storm approaching).\n"
                "- CRITICAL: Active life-or-death crisis (e.g. trapped, severe bleeding, actively burning house).\n"
                "Return a JSON format response containing priority_tier, priority_score (0.0 to 1.0), and reasoning. "
                f"\n{common_rules}"
            )
            
        elif role == "planner":
            return (
                "You are the Crisis Planner Agent. "
                "Analyze the request, identify the category (Medical, Fire, Natural Disaster, Search & Rescue, General Support), "
                "and draft a precise action plan (list of steps) for the worker agent to execute.\n"
                "Plan steps must focus on looking up coordinates, verifying resources, and compiling instructions.\n"
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
                "Personalize the response by mentioning the user name, referring to their location, and reminding them to contact their emergency contact if necessary.\n"
                f"\n{user_context}\n{allergy_safety}\n{common_rules}"
            )
            
        elif role == "evaluator":
            return (
                "You are the emergency Response Evaluator Agent. "
                "Review the draft response prepared by the Worker Agent against safety criteria.\n"
                "Check for:\n"
                "1. Safety: No dangerous instructions. Specifically verify that the worker did not recommend any treatments violating the user's allergies.\n"
                "2. Grounding: Resource phone numbers and details must be present and verified.\n"
                "3. Conciseness: Responses must be highly readable and readable in seconds.\n"
                "Provide a rating between 0.0 (Unacceptable) and 1.0 (Flawless). "
                "If score is < 0.85, reject the response and give constructive feedback in your output JSON.\n"
                "Return a JSON block containing score (float), approved (boolean), and feedback (string)."
                f"\n{user_context}\n{allergy_safety}\n{common_rules}"
            )
            
        return f"You are a helpful emergency companion. Please communicate in {target_lang_name}."
