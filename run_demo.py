import os
import sys
import time
import io

# Set standard output encoding to UTF-8 to support emojis on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
elif hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# Add project folder to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "project")))

from main_agent import MainAgentController

def print_separator(char="=", length=60):
    print(char * length)

def run_demo():
    print_separator()
    print("🚨 CRISISASSIST AI — MULTI-AGENT EMERGENCY CLI DEMO 🚨")
    print_separator()
    
    controller = MainAgentController()
    
    # Pre-populate user profile memory
    controller.user_memory.update_profile({
        "name": "Arjun Mehta",
        "preferred_language": "Hindi",
        "home_location": "Mumbai, Maharashtra",
        "medical_alerts": "Severe Asthma, Penicillin Allergy",
        "emergency_contact": {
            "name": "Deepa Mehta (Wife)",
            "phone": "+91-98989-12345"
        }
    })
    
    print(f"Memory Loaded:")
    print(f"- User Name: {controller.user_memory.get_profile()['name']}")
    print(f"- Home Location: {controller.user_memory.get_profile()['home_location']}")
    print(f"- Medical Alerts: {controller.user_memory.get_profile()['medical_alerts']}")
    print_separator("-")

    # Sample queries covering Hindi, Marathi, and English with various priorities
    demo_queries = [
        "I am trapped on the second floor of a burning apartment in Mumbai and cannot breathe, send help!",
        "Mujhe madad chahiye, rasta block ho gaya hai Pune me.",
        "pune me hospital aur doctor ka number chahiye, patient ko chot lagi hai",
        "What should I keep in my basic earthquake survival backpack?"
    ]

    for idx, query in enumerate(demo_queries, 1):
        print(f"\nQUERY #{idx}: '{query}'")
        print_separator(".")
        
        # Process emergency pipeline
        result = controller.process_emergency_request(query)
        
        # Display output results
        print(f"✅ Language Detected: {result['detected_lang'].upper()}")
        print(f"✅ Priority Class:    {result['priority']} (Score: {result['priority_score']})")
        print(f"✅ Category:         {result['category']}")
        print(f"✅ Location:         {result['detected_city'].upper()} (Coords: {result['coordinates']})")
        print(f"✅ Evaluator Score:  {int(result['eval_score'] * 100)}%")
        print(f"✅ Total Duration:   {result['duration_ms']} ms")
        
        print("\n--- DECISION EXPLANATION ---")
        print(result["decision_explanation"])
        
        print("\n--- ACTIONABLE ADVICE ---")
        print(result["response"])
        
        print("\n--- VERIFIED RESOURCES ---")
        resources = result.get("verified_resources", [])
        if resources:
            for idx_r, r in enumerate(resources, 1):
                v_score = int(r.get("verification", {}).get("score", 0.0) * 100)
                status = r.get("status")
                print(f"  [{idx_r}] {r['name']} | Coords/Address: {r['address']} | Phone: {r['phone']} | Status: {status} | Score: {v_score}%")
        else:
            print("  No resource listings located.")
            
        print("\n--- MULTI-AGENT TELEMETRY TIMELINE ---")
        timeline = controller.session_memory.get_timeline()
        for step in timeline:
            agent = step.get("agent", "System")
            action = step.get("action", "")
            status = step.get("status", "")
            print(f"  [{agent}] {action} ({status})")
            
        print_separator("=")
        time.sleep(1)

if __name__ == "__main__":
    run_demo()
