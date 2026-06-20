import json
from google import genai
from core.a2a_protocol import AgentMessage
from tools.resource_tool import ResourceTool
from mcp_server.server import ModelContextProtocolServer

class WorkerAgent:
    """
    Worker Agent. Executes the steps defined by the Planner.
    Queries resource tools, simulated MCP endpoints, and compiles safety guidelines.
    """
    def __init__(self, gemini_client: genai.Client = None):
        self.client = gemini_client
        self.resource_tool = ResourceTool()
        self.mcp_server = ModelContextProtocolServer()

    def run(self, message: AgentMessage, user_profile: dict) -> AgentMessage:
        plan_payload = message.payload
        query = plan_payload.get("query", "")
        category = plan_payload.get("category", "General Support")
        priority = plan_payload.get("priority", "LOW")
        
        # Step 1: Location geocoding & resource searches
        detected_city = self.resource_tool.parse_location(query)
        coords = self.resource_tool.geocode(detected_city)
        raw_resources = self.resource_tool.search_resources(detected_city, category)
        
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
        verified_resources = self.resource_tool.verify_batch(raw_resources)
        
        # Merge MCP shelter status details
        for s in mcp_shelters:
            res_mapped = {
                "name": s["name"],
                "address": f"Coordinates: {s['location']}",
                "phone": "+91-22-2408-9999",
                "status": s["occupancy_status"],
                "verified_at": "2026-06-20",
                "details": f"Capacity: {s['occupied_seats']}/{s['capacity_total']} occupied."
            }
            v_res = self.resource_tool.verify_resource(res_mapped)
            res_mapped["verification"] = v_res
            verified_resources.append(res_mapped)

        # Step 4: Compile guidelines
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
        
        if self.client:
            try:
                system_instruction = (
                    "You are the Emergency Worker Agent. "
                    "Your role is to compile recommendations, actionable guidelines, and rescue listings. "
                    "You must follow the steps provided in the plan.\n"
                    "Format emergency guidelines as clear, numbered lists. "
                    "Do not hallucinate names or phone numbers. Only report resources from your lookup tools."
                )
                prompt = (
                    f"Create emergency safety guidelines for a {category} emergency. "
                    "Make sure the response is action-oriented and highly readable. "
                    "Limit to 4 core points.\n\n"
                    f"User Situation: '{query}'"
                )
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config={"system_instruction": system_instruction}
                )
                res_text = response.text.strip()
                if res_text:
                    selected_guide = res_text
            except Exception as e:
                print(f"WorkerAgent LLM guide generation failed: {e}. Using defaults.")

        # Step 5: Summarize checklist (inlined summarizer tool logic)
        summary_checklist = self._summarize(selected_guide)

        response_payload = {
            "query": query,
            "priority": priority,
            "category": category,
            "detected_city": detected_city,
            "coordinates": coords,
            "guidelines": selected_guide,
            "summary_checklist": summary_checklist,
            "verified_resources": verified_resources,
            "active_alerts": mcp_alerts,
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

    def _summarize(self, text: str) -> str:
        """Helper to summarize guidelines into 3-5 concise bullet steps."""
        if self.client:
            try:
                prompt = (
                    "Summarize the following emergency guidelines into a checklist of "
                    "exactly 3 to 5 clear, actionable, short steps. Use Markdown bullet points (-). "
                    "Prioritize life safety first. Do not add intro or outro text.\n\n"
                    f"Text:\n{text}"
                )
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt
                )
                summary = response.text.strip()
                if summary:
                    return summary
            except Exception:
                pass
                
        # Heuristic fallback
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
