import json
import re
import os
from google import genai
from core.a2a_protocol import AgentMessage
from core.context_engineering import ContextEngineering
from tools.location_tool import LocationTool
from tools.translation_tool import TranslationTool
from mcp_server.server import ModelContextProtocolServer
from utils.gemini_helper import safe_generate_content

class WorkerAgent:
    """
    Worker Agent. Executes planned steps, searches/verifies resources, 
    and compiles localized emergency guidelines and checklists.
    """
    def __init__(self, gemini_client: genai.Client = None):
        self.client = gemini_client
        self.location_tool = LocationTool()
        self.translation_tool = TranslationTool(gemini_client)
        self.mcp_server = ModelContextProtocolServer()

    def run(self, message: AgentMessage, user_profile: dict) -> AgentMessage:
        plan_payload = message.payload
        query = plan_payload.get("query", "")
        category = plan_payload.get("category", "General Support")
        priority = plan_payload.get("priority", "LOW")
        lang_code = plan_payload.get("language", "en")
        lang_name = plan_payload.get("language_name", "English")
        rationale = plan_payload.get("rationale", "")
        priority_score = plan_payload.get("priority_score", 0.9)
        
        # Determine the user's location (manual profile or dynamic)
        detected_city = plan_payload.get("detected_city")
        if not detected_city:
            detected_city = self.location_tool.parse_location(query)
            if detected_city == "other":
                detected_city = user_profile.get("location") or user_profile.get("home_location") or "Mumbai"
        
        coords = plan_payload.get("coordinates")
        if not coords:
            coords = self.location_tool.geocode(detected_city)

        # Step 1: Resource searches
        raw_resources = self.location_tool.search_resources(detected_city, category, allow_fallback=False)
        
        # If the city is not hardcoded, dynamically generate realistic emergency resources using Gemini
        if not raw_resources and self.client:
            try:
                prompt = (
                    f"Generate 2 to 3 real or highly realistic emergency resources appropriate for a '{category}' emergency "
                    f"in the city of '{detected_city}'.\n"
                    f"For each resource, construct a JSON list of objects with keys:\n"
                    f"- 'name': name of the facility\n"
                    f"- 'address': address including street name, city, state, country\n"
                    f"- 'phone': contact phone number in format +91-XX-XXXX-XXXX\n"
                    f"- 'status': 'OPERATIONAL' or 'OPEN'\n"
                    f"- 'verified_at': '2026-06-20'\n"
                    f"- 'distance_km': a float simulated distance between 1.0 and 8.0\n"
                    f"- 'coordinates': a list of [latitude, longitude] representing its location\n"
                    f"Output ONLY a valid JSON array of objects. Do not include markdown formatting or tags."
                )
                response = safe_generate_content(
                    self.client,
                    model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
                    contents=prompt
                )
                text = response.text.strip()
                if text.startswith("```"):
                    text = re.sub(r"^```(?:json)?\n", "", text)
                    text = re.sub(r"\n```$", "", text)
                parsed = json.loads(text)
                if isinstance(parsed, list):
                    for r in parsed:
                        if "coordinates" in r and isinstance(r["coordinates"], list) and len(r["coordinates"]) == 2:
                            r["coordinates"] = tuple(r["coordinates"])
                        else:
                            r["coordinates"] = coords
                    raw_resources = parsed
            except Exception as e:
                print(f"Dynamic resource generation failed: {e}. Falling back to default list.")
        
        if not raw_resources:
            raw_resources = self.location_tool.search_resources(detected_city, category, allow_fallback=True)
        
        # Step 2: Query simulated MCP server for alerts & capacities
        mcp_alerts = []
        mcp_shelters = []
        try:
            alerts_json = self.mcp_server.call_tool("get_disaster_alerts", {"location": detected_city})
            mcp_alerts = json.loads(alerts_json).get("alerts", [])
            
            shelters_json = self.mcp_server.call_tool("search_shelters", {"location": detected_city})
            mcp_shelters = json.loads(shelters_json).get("shelters", [])
        except Exception as e:
            print(f"MCP server simulation error: {e}")

        # Step 3: Run resource verification checks
        verified_resources = self.location_tool.verify_batch(raw_resources)
        
        # Merge MCP shelters
        for s in mcp_shelters:
            res_mapped = {
                "name": s["name"],
                "address": f"Coordinates: {s['location']}",
                "phone": "+91-22-2408-9999",
                "status": s["occupancy_status"],
                "verified_at": "2026-06-20",
                "distance_km": 2.0,
                "coordinates": coords,
                "details": f"Capacity: {s['occupied_seats']}/{s['capacity_total']} occupied."
            }
            v_res = self.location_tool.verify_resource(res_mapped)
            res_mapped["verification"] = v_res
            verified_resources.append(res_mapped)

        # Translate resources and alerts if not English
        if lang_code != "en" and self.translation_tool:
            # Localize resource fields
            for r in verified_resources:
                try:
                    r["name"] = self.translation_tool.translate(r["name"], "en", lang_code)
                    r["address"] = self.translation_tool.translate(r["address"], "en", lang_code)
                    # Translate status label if needed
                    orig_status = r.get("status", "OPERATIONAL")
                    if orig_status in ["OPERATIONAL", "OPEN"]:
                        r["status"] = self.translation_tool.translate("OPERATIONAL", "en", lang_code)
                    else:
                        r["status"] = self.translation_tool.translate("CLOSED", "en", lang_code)
                except Exception as e:
                    print(f"Failed to translate resource fields: {e}")
                    
            # Localize MCP alerts
            for a in mcp_alerts:
                if "alert" in a:
                    try:
                        a["alert"] = self.translation_tool.translate(a["alert"], "en", lang_code)
                    except Exception as e:
                        print(f"Failed to translate alert: {e}")

        # Step 4: Compile guidelines in target language
        default_guidelines = {
            "Medical": (
                "1. Apply direct pressure to any bleeding wounds with clean cloth.\n"
                "2. Keep the patient warm and lying down if in shock.\n"
                "3. Do not give food or water if surgery might be required.\n"
                "4. Seek immediate emergency transportation."
            ),
            "Fire": (
                "1. Stay low to the ground to avoid inhaling toxic smoke.\n"
                "2. Feel doors with the back of your hand before opening; if hot, find another exit.\n"
                "3. Stop, Drop, and Roll if clothing catches fire.\n"
                "4. Evacuate immediately and never re-enter a burning structure."
            ),
            "Natural Disaster": (
                "1. Take cover under heavy furniture during earthquakes.\n"
                "2. Move to higher ground immediately if flooding occurs.\n"
                "3. Keep emergency kit close, stay away from window glasses.\n"
                "4. Disconnect electrical appliances to prevent short-circuit fire."
            ),
            "Search & Rescue": (
                "1. Signal rescuers using flashlights, whistle, or tapping sounds.\n"
                "2. Try to conserve phone battery and water.\n"
                "3. Stay in place if located in a secure pocket; do not crawl into unstable ruins.\n"
                "4. Make noise only when rescue teams are heard nearby."
            ),
            "General Support": (
                "1. Contact verified community organizers for water and food supplies.\n"
                "2. Stay tuned to disaster alerts via radio or SMS updates.\n"
                "3. Conserve water and dry rations.\n"
                "4. Follow guidance from civil defense responders."
            )
        }
        selected_guide = default_guidelines.get(category, default_guidelines["General Support"])
        
        # Inject personalized profile details into worker prompt context
        medical_alerts = user_profile.get("medical_alerts", "")
        user_name = user_profile.get("name", "")
        emergency_contact_name = user_profile.get("emergency_contact", {}).get("name", "")
        emergency_contact_phone = user_profile.get("emergency_contact", {}).get("phone", "")
        
        profile_context = ""
        if user_name or medical_alerts or emergency_contact_name:
            profile_context = (
                f"User Profile Info:\n"
                f"- Name: {user_name}\n"
                f"- Medical Alerts / Allergies: {medical_alerts if medical_alerts else 'None declared'}\n"
                f"- Emergency Contact:\n{emergency_contact_name}\n{emergency_contact_phone}\n"
                "Please tailor the guidelines specifically if the medical alerts are critical (e.g. allergies to watch, insulin dependencies, or contacting their specific contact)."
            )

        if self.client:
            try:
                system_instruction = ContextEngineering.build_system_instruction(
                    "worker", 
                    user_profile, 
                    lang_name, 
                    {"location": detected_city}
                )
                prompt = (
                    f"Create emergency safety guidelines for a {category} emergency.\n"
                    f"User Situation: '{query}'\n\n"
                    f"CRITICAL: You must output ONLY in the {lang_name} language. Do NOT output in English or any other language. Do NOT provide dual-language output like Hindi and English together. Just output pure {lang_name}. Make the response action-oriented."
                )
                response = safe_generate_content(
                    self.client,
                    model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
                    contents=prompt,
                    config={"system_instruction": system_instruction}
                )
                res_text = response.text.strip()
                if res_text:
                    selected_guide = res_text
            except Exception as e:
                print(f"WorkerAgent LLM guidelines failed: {e}. Translating default fallback.")
                if lang_code != "en" and self.translation_tool:
                    selected_guide = self.translation_tool.translate(selected_guide, "en", lang_code)

        # Step 5: Summarize checklist (in target language)
        summary_checklist = ""
        if self.client:
            try:
                prompt = (
                    f"Summarize the following emergency guidelines into a checklist of "
                    f"exactly 3 to 5 clear, actionable, short steps. Use Markdown bullet points (-).\n"
                    f"CRITICAL: You must output ONLY in the {lang_name} language. Do NOT output in English or any other language. Do NOT provide dual-language output like Hindi and English together. Just output pure {lang_name}.\n\n"
                    f"Guidelines:\n{selected_guide}"
                )
                response = safe_generate_content(
                    self.client,
                    model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
                    contents=prompt
                )
                summary_checklist = response.text.strip()
            except Exception as e:
                print(f"WorkerAgent LLM checklist failed: {e}.")
                
        if not summary_checklist:
            # Fallback heuristic summary, then translate
            summary_checklist = self._heuristic_summary(selected_guide)
            if lang_code != "en" and self.translation_tool:
                summary_checklist = self.translation_tool.translate(summary_checklist, "en", lang_code)

        response_payload = {
            "query": query,
            "priority": priority,
            "priority_score": priority_score,
            "rationale": rationale,
            "category": category,
            "detected_city": detected_city,
            "coordinates": coords,
            "guidelines": selected_guide,
            "summary_checklist": summary_checklist,
            "verified_resources": verified_resources,
            "active_alerts": mcp_alerts,
            "language": lang_code,
            "language_name": lang_name,
            "tool_execution_log": [
                {"step": "Location Lookup", "result": f"Parsed location: {detected_city} (Coords: {coords})"},
                {"step": "Resource Query", "result": f"Fetched {len(raw_resources)} database centers"},
                {"step": "MCP Server Fetch", "result": f"Found {len(mcp_alerts)} active alerts and {len(mcp_shelters)} shelters"},
                {"step": "Verification Run", "result": "Verified resource listings freshness and status"}
            ]
        }

        return AgentMessage(
            sender="WorkerAgent",
            receiver=message.sender,
            message_type="RESPONSE",
            payload=response_payload,
            trace_id=message.trace_id
        )

    def _heuristic_summary(self, text: str) -> str:
        """Helper to summarize guidelines into 3-5 concise bullet steps."""
        lines = text.split("\n")
        action_lines = []
        action_verbs = ["stay", "move", "evacuate", "call", "seek", "run", "cover", "hide", "stop", "check"]
        for line in lines:
            line_clean = line.strip().lstrip("-*•1234567890. ")
            if line_clean and (any(line_clean.lower().startswith(v) for v in action_verbs) or len(line_clean.split()) < 15):
                action_lines.append(f"- {line_clean}")
                if len(action_lines) >= 4:
                    break
        if not action_lines:
            action_lines = [f"- {l.strip()}" for l in lines if l.strip()][:3]
        return "\n".join(action_lines)
