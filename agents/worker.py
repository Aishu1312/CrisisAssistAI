from google import genai
from core.context_engineering import ContextEngineering
from core.a2a_protocol import AgentMessage
from tools.location_tool import LocationTool
from tools.verification_tool import VerificationTool
from tools.summarizer import Summarizer
from mcp_server.server import ModelContextProtocolServer
import json

class WorkerAgent:
    """
    Executes planning steps by orchestrating available tools:
    geocodes location, fetches local database listings, runs verification, and builds guidelines.
    """
    def __init__(self, gemini_client: genai.Client = None):
        self.client = gemini_client
        self.location_tool = LocationTool()
        self.verification_tool = VerificationTool()
        self.summarizer = Summarizer(gemini_client)
        self.mcp_server = ModelContextProtocolServer()

    def run(self, message: AgentMessage, user_profile: dict) -> AgentMessage:
        """
        Coordinates the execution of tools to fulfill the plan steps.
        """
        plan_payload = message.payload
        query = plan_payload.get("query", "")
        category = plan_payload.get("category", "General Support")
        priority = plan_payload.get("priority", "LOW")
        steps = plan_payload.get("steps", [])

        # Step 1: Location geocoding
        detected_city = self.location_tool.parse_location(query)
        coords = self.location_tool.geocode(detected_city)
        
        # Step 2: Database resource queries
        raw_resources = self.location_tool.search_resources(detected_city, category)
        
        # Step 3: MCP external telemetry queries (live disaster alerts & shelter capacities)
        mcp_alerts = []
        mcp_shelters = []
        try:
            alerts_json = self.mcp_server.call_tool("get_disaster_alerts", {"location": detected_city})
            mcp_alerts = json.loads(alerts_json).get("alerts", [])
            
            shelters_json = self.mcp_server.call_tool("search_shelters", {"location": detected_city})
            mcp_shelters = json.loads(shelters_json).get("shelters", [])
        except Exception as e:
            print(f"MCP server simulation error: {e}")

        # Step 4: Verification layer execution
        verified_resources = self.verification_tool.verify_batch(raw_resources)
        
        # Combine database resources and MCP shelters
        for s in mcp_shelters:
            # Map MCP structure to standard resource format for verification
            res_mapped = {
                "name": s["name"],
                "address": f"Coordinates: {s['location']}",
                "phone": "+91-22-2408-9999",  # Mock shelter control phone
                "status": s["occupancy_status"],
                "verified_at": "2026-06-20",
                "details": f"Capacity: {s['occupied_seats']}/{s['capacity_total']} occupied."
            }
            v_res = self.verification_tool.verify_resource(res_mapped)
            res_mapped["verification"] = v_res
            verified_resources.append(res_mapped)

        # Step 5: Construct emergency guidelines and action items
        # Heuristic default guidance database
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
        
        # If client is online, customize guidelines using Gemini
        if self.client:
            try:
                system_instruction = ContextEngineering.build_system_instruction("worker", user_profile)
                prompt = (
                    f"Create emergency safety guidelines for a {category} emergency. "
                    "Make sure the response is action-oriented and highly readable. "
                    "Limit to 4 core points.\n\n"
                    f"User Situation: '{query}'"
                )
                response = self.client.models.generate_content(
                    model="gemini-1.5-flash",
                    contents=prompt,
                    config={"system_instruction": system_instruction}
                )
                res_text = response.text.strip()
                if res_text:
                    selected_guide = res_text
            except Exception as e:
                print(f"WorkerAgent LLM guide generation failed: {e}. Falling back to default guide.")

        # Compute summary checklist for quick lookups
        summary_checklist = self.summarizer.summarize(selected_guide)

        # Assemble final response markdown draft
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
