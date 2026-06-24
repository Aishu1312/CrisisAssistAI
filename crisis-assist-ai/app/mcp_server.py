from mcp.server.fastmcp import FastMCP
import json

# Initialize FastMCP server
mcp = FastMCP("CrisisAssist MCP Server")

# Database representing external live disaster telemetry data sources
DISASTER_ALERTS_DB = {
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

SHELTER_STATUS_DB = {
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

EMERGENCY_CONTACTS_DB = {
    "mumbai": {
        "disaster_management": "022-22694725",
        "ambulance": "108",
        "police": "100",
        "fire": "101"
    },
    "pune": {
        "disaster_management": "020-25501269",
        "ambulance": "108",
        "police": "100",
        "fire": "101"
    },
    "delhi": {
        "disaster_management": "011-22307133",
        "ambulance": "108",
        "police": "100",
        "fire": "101"
    }
}

def _clean_location(location: str) -> str:
    loc = location.lower().strip()
    if "pune" in loc:
        return "pune"
    elif "delhi" in loc:
        return "delhi"
    return "mumbai" # default fallback

@mcp.tool()
def get_disaster_alerts(location: str) -> str:
    """Fetch active emergency and disaster hazard alerts for a location.

    Args:
        location: Name of the city (e.g. Mumbai, Pune, Delhi).
    """
    loc = _clean_location(location)
    alerts = DISASTER_ALERTS_DB.get(loc, [])
    return json.dumps({"alerts": alerts, "status": "success"})

@mcp.tool()
def search_shelters(location: str) -> str:
    """Query relief shelters, capacity limits, and current occupancies for a location.

    Args:
        location: Name of the city (e.g. Mumbai, Pune, Delhi).
    """
    loc = _clean_location(location)
    shelters = SHELTER_STATUS_DB.get(loc, [])
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

@mcp.tool()
def get_emergency_contacts(location: str) -> str:
    """Fetch verified emergency agency hotlines (disaster management, police, medical, fire) for a location.

    Args:
        location: Name of the city (e.g. Mumbai, Pune, Delhi).
    """
    loc = _clean_location(location)
    contacts = EMERGENCY_CONTACTS_DB.get(loc, {})
    return json.dumps({"contacts": contacts, "status": "success"})

if __name__ == "__main__":
    mcp.run(transport="stdio")
