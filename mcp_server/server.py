import json
from typing import Dict, Any, List

class ModelContextProtocolServer:
    """
    Simulates a Model Context Protocol (MCP) server for emergency systems.
    Provides external standardized resources and tools to agents via JSON schemas.
    """
    def __init__(self):
        # Database representing external live disaster telemetry data sources
        self.disaster_alerts_db = {
            "mumbai": [
                {"alert_id": "AL-1092", "event": "Heavy Rainfall & Waterlogging", "severity": "HIGH", "issued_at": "2026-06-20T18:00:00", "instructions": "Stay indoors, avoid low-lying subways."}
            ],
            "pune": [
                {"alert_id": "AL-1093", "event": "None", "severity": "LOW", "issued_at": "2026-06-20T10:00:00", "instructions": "Normal conditions."}
            ],
            "delhi": [
                {"alert_id": "AL-1094", "event": "Heatwave Warning", "severity": "MEDIUM", "issued_at": "2026-06-20T12:00:00", "instructions": "Avoid direct sun exposure between 12 PM and 4 PM."}
            ]
        }
        
        self.shelter_status_db = {
            "mumbai": [
                {"name": "Dharavi Shelter A", "capacity": 500, "occupied": 412, "coordinates": (19.0380, 72.8538)},
                {"name": "Chembur School Hall B", "capacity": 200, "occupied": 195, "coordinates": (19.0618, 72.8996)}
            ],
            "pune": [
                {"name": "Shivajinagar Hall", "capacity": 300, "occupied": 120, "coordinates": (18.5308, 73.8474)}
            ],
            "delhi": [
                {"name": "Chanakyapuri Relief Hall", "capacity": 400, "occupied": 380, "coordinates": (28.5921, 77.1945)}
            ]
        }

    def list_tools(self) -> List[Dict[str, Any]]:
        """Returns JSON schemas defining available tools on this MCP server."""
        return [
            {
                "name": "get_disaster_alerts",
                "description": "Fetch active emergency and disaster hazard alerts for a location.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string", "description": "Name of the city (e.g. Mumbai, Pune, Delhi)."}
                    },
                    "required": ["location"]
                }
            },
            {
                "name": "search_shelters",
                "description": "Query relief shelters, capacity limits, and current occupancies.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string", "description": "Name of the city (e.g. Mumbai, Pune, Delhi)."}
                    },
                    "required": ["location"]
                }
            }
        ]

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """
        Executes a registered tool.
        Returns:
            JSON-formatted string containing tool response.
        """
        location = arguments.get("location", "mumbai").lower().strip()
        
        # Simple string matching to clean location inputs
        matched_location = "mumbai"
        if "pune" in location:
            matched_location = "pune"
        elif "delhi" in location:
            matched_location = "delhi"
            
        if tool_name == "get_disaster_alerts":
            alerts = self.disaster_alerts_db.get(matched_location, [])
            return json.dumps({"alerts": alerts, "status": "success"})
            
        elif tool_name == "search_shelters":
            shelters = self.shelter_status_db.get(matched_location, [])
            results = []
            for shelter in shelters:
                available = shelter["capacity"] - shelter["occupied"]
                status = "CRITICAL" if available < 10 else "AVAILABLE"
                results.append({
                    "name": shelter["name"],
                    "capacity_total": shelter["capacity"],
                    "occupied_seats": shelter["occupied"],
                    "available_seats": available,
                    "occupancy_status": status,
                    "location": shelter["coordinates"]
                })
            return json.dumps({"shelters": results, "status": "success"})
            
        else:
            return json.dumps({"error": f"Tool '{tool_name}' not found.", "status": "error"})
