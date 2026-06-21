import streamlit as st
import os
import sys
import time
import re
import uuid
from typing import Dict, Any, List
from dotenv import load_dotenv
from PIL import Image
from google import genai
from streamlit_js_eval import get_geolocation

# Setup search path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from core.a2a_protocol import AgentMessage
from core.observability import Observability
from memory.session_memory import SessionMemory
from memory.user_profile import UserProfile
from tools.translation_tool import TranslationTool
from tools.voice_tool import VoiceTool
from tools.maps_tool import MapsTool
from tools.location_tool import LocationTool

from agents.planner import PlannerAgent
from agents.worker import WorkerAgent
from agents.evaluator import EvaluatorAgent

from dashboard.logs_dashboard import LogsDashboard
from utils.language_manager import LanguageManager
from utils.location_detector import LocationDetector

load_dotenv()

# Set up page configurations
st.set_page_config(
    page_title="CrisisAssist AI — Trustworthy Emergency Companion",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling (Vanilla CSS) for a premium dark-accented modern look
st.markdown("""
<style>
    .main-title {
        font-family: 'Outfit', 'Inter', sans-serif;
        color: #1E3A8A;
        font-weight: 800;
        text-align: center;
        margin-bottom: 0px;
    }
    .subtitle {
        font-family: 'Inter', sans-serif;
        color: #4B5563;
        font-size: 1.25rem;
        text-align: center;
        margin-bottom: 20px;
        font-style: italic;
    }
    .hero-container {
        background-color: #F8FAFC;
        padding: 25px;
        border-radius: 15px;
        border: 1px solid #E2E8F0;
        text-align: center;
        margin-bottom: 30px;
        color: #0F172A !important;
    }
    .hero-container h1, .hero-container h2, .hero-container h3, .hero-container h4, .hero-container h5, .hero-container h6 {
        color: #1E3A8A !important;
    }
    .hero-container p, .hero-container span, .hero-container div {
        color: #334155 !important;
    }
    .metric-card {
        background-color: #FFFFFF;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #E2E8F0;
        border-top: 5px solid #2563EB;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
        text-align: center;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: bold;
        color: #1E3A8A;
        margin-top: 5px;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .agent-status-container {
        display: flex;
        justify-content: space-around;
        align-items: center;
        background-color: #F1F5F9;
        padding: 15px;
        border-radius: 10px;
        margin-top: 15px;
        margin-bottom: 15px;
    }
    .agent-node {
        text-align: center;
        padding: 10px 15px;
        border-radius: 8px;
        font-weight: bold;
        font-size: 0.95rem;
        border: 1px solid #CBD5E1;
        background-color: #FFFFFF;
        color: #64748B;
        width: 28%;
    }
    .agent-node-active {
        background-color: #DBEAFE;
        color: #1E40AF;
        border: 2px solid #2563EB;
        box-shadow: 0 0 10px rgba(37, 99, 235, 0.2);
    }
    .agent-node-completed {
        background-color: #D1FAE5;
        color: #065F46;
        border: 2px solid #10B981;
    }
    .status-badge {
        font-size: 0.8rem;
        font-weight: bold;
        padding: 3px 8px;
        border-radius: 12px;
        display: inline-block;
    }
    .badge-ok { background-color: #D1FAE5; color: #065F46; }
    .badge-warn { background-color: #FEF3C7; color: #92400E; }
    .badge-fail { background-color: #FCE7F3; color: #9D174D; }
    
    .timeline-item {
        padding: 10px;
        border-left: 3px solid #E2E8F0;
        margin-left: 10px;
        margin-bottom: 10px;
    }
    .timeline-agent {
        font-weight: bold;
        color: #1E3A8A;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)


class MainAgentController:
    """
    Controller orchestrating Triage -> Planning -> Worker -> Evaluator agents.
    Now fully language and location aware.
    """
    def __init__(self, gemini_client):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.client = gemini_client
                
        # Initialize memory & logging
        self.session_memory = SessionMemory()
        self.user_memory = UserProfile()
        self.observability = Observability()
        
        # Initialize tools
        self.translation_tool = TranslationTool(self.client)
        self.voice_tool = VoiceTool()
        
        # Initialize agents
        self.planner_agent = PlannerAgent(self.client)
        self.worker_agent = WorkerAgent(self.client)
        self.evaluator_agent = EvaluatorAgent(self.client)

    def process_emergency_request(
        self, 
        user_query: str, 
        target_lang_code: str = "en", 
        location_details: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Coordinates the emergency response pipeline.
        """
        start_time = time.time()
        trace_id = str(uuid.uuid4())
        self.session_memory.clear()
        
        user_profile = self.user_memory.get_profile()
        stages_log = []
        
        # Parse active location details
        detected_city = location_details.get("city", "Mumbai") if location_details else "Mumbai"
        coords = location_details.get("coords", (19.0760, 72.8777)) if location_details else (19.0760, 72.8777)
        state_country = f"{location_details.get('state', '')}, {location_details.get('country', '')}" if location_details else "Maharashtra, India"
        
        # 1. Language Detection & Input Translation
        self.session_memory.add_step("MainController", "Language Detection", "STARTED")
        detected_lang = self.translation_tool.detect_language(user_query)
        self.session_memory.add_user_message(user_query, detected_lang)
        
        english_query = user_query
        if detected_lang != "en":
            english_query = self.translation_tool.translate(user_query, detected_lang, "en")
            self.session_memory.add_step(
                "MainController", 
                "Translating input", 
                "COMPLETED", 
                {"source": user_query, "translated": english_query}
            )
            stages_log.append({"stage": "Input Translation", "duration_ms": 100})
        else:
            self.session_memory.add_step("MainController", "Input is English", "COMPLETED")
            
        # 2. Planning (Priority Triage happens inside PlannerAgent)
        planning_start = time.time()
        self.session_memory.add_step("PlannerAgent", "Plan construction & Triage", "STARTED")
        
        plan_msg_in = AgentMessage(
            sender="MainController",
            receiver="PlannerAgent",
            message_type="REQUEST",
            payload={
                "query": english_query,
                "language": target_lang_code
            },
            trace_id=trace_id
        )
        plan_msg_out = self.planner_agent.run(plan_msg_in, user_profile)
        category = plan_msg_out.payload.get("category", "General Support")
        plan_steps = plan_msg_out.payload.get("steps", [])
        plan_rationale = plan_msg_out.payload.get("rationale", "")
        priority_tier = plan_msg_out.payload.get("priority", "LOW")
        priority_score = plan_msg_out.payload.get("priority_score", 0.0)
        triage_reason = plan_msg_out.payload.get("triage_reason", "")
        
        self.session_memory.set_emergency_meta(priority_tier, category, triage_reason)
        
        planning_duration = int((time.time() - planning_start) * 1000)
        self.session_memory.add_step(
            "PlannerAgent", 
            "Plan construction & Triage", 
            "COMPLETED", 
            {"category": category, "steps": plan_steps, "rationale": plan_rationale}
        )
        stages_log.append({"stage": "Planning", "duration_ms": planning_duration})

        # 3. Worker Execution
        worker_start = time.time()
        self.session_memory.add_step("WorkerAgent", "Execution of plan steps", "STARTED")
        
        worker_payload_in = plan_msg_out.payload.copy()
        worker_payload_in["detected_city"] = detected_city
        worker_payload_in["coordinates"] = coords
        
        worker_msg_in = AgentMessage(
            sender="MainController",
            receiver="WorkerAgent",
            message_type="REQUEST",
            payload=worker_payload_in,
            trace_id=trace_id
        )
        worker_msg_out = self.worker_agent.run(worker_msg_in, user_profile)
        worker_payload = worker_msg_out.payload
        draft_guidelines = worker_payload.get("guidelines", "")
        verified_resources = worker_payload.get("verified_resources", [])
        tool_logs = worker_payload.get("tool_execution_log", [])
        
        for log in tool_logs:
            self.session_memory.add_step("WorkerAgent:Tool", log["step"], "COMPLETED", log["result"])
            
        worker_duration = int((time.time() - worker_start) * 1000)
        self.session_memory.add_step("WorkerAgent", "Draft compiled", "COMPLETED")
        stages_log.append({"stage": "Worker Execution", "duration_ms": worker_duration})

        # 4. Evaluation Loop
        eval_start = time.time()
        self.session_memory.add_step("EvaluatorAgent", "Response safety review", "STARTED")
        
        eval_msg_in = AgentMessage(
            sender="MainController",
            receiver="EvaluatorAgent",
            message_type="REQUEST",
            payload=worker_payload,
            trace_id=trace_id
        )
        eval_msg_out = self.evaluator_agent.run(eval_msg_in)
        eval_score = eval_msg_out.payload.get("score", 0.0)
        eval_approved = eval_msg_out.payload.get("approved", False)
        eval_feedback = eval_msg_out.payload.get("feedback", "")
        
        # Self-correction check
        if not eval_approved:
            self.session_memory.add_step("EvaluatorAgent", "Review FAILED", "REJECTED", {"score": eval_score, "feedback": eval_feedback})
            self.session_memory.add_step("WorkerAgent", "Refining draft based on feedback", "STARTED")
            
            worker_msg_in.payload["steps"].append(f"REFINEMENT: {eval_feedback}")
            worker_msg_out = self.worker_agent.run(worker_msg_in, user_profile)
            worker_payload = worker_msg_out.payload
            draft_guidelines = worker_payload.get("guidelines", "")
            verified_resources = worker_payload.get("verified_resources", [])
            
            self.session_memory.add_step("EvaluatorAgent", "Second review pass", "STARTED")
            eval_msg_in = AgentMessage(sender="MainController", receiver="EvaluatorAgent", message_type="REQUEST", payload=worker_payload, trace_id=trace_id)
            eval_msg_out = self.evaluator_agent.run(eval_msg_in)
            eval_score = eval_msg_out.payload.get("score", 0.0)
            eval_approved = eval_msg_out.payload.get("approved", True)
            eval_feedback = eval_msg_out.payload.get("feedback", "Refinement complete.")
            self.session_memory.add_step("EvaluatorAgent", "Review completed", "APPROVED")
        else:
            self.session_memory.add_step("EvaluatorAgent", "Review APPROVED", "COMPLETED", {"score": eval_score, "feedback": eval_feedback})
            
        eval_duration = int((time.time() - eval_start) * 1000)
        stages_log.append({"stage": "Safety Review", "duration_ms": eval_duration})

        self.session_memory.set_verified_resources(verified_resources)

        # 5. Localized Output Construction & TTS
        translation_start = time.time()
        final_text = (
            f"### Immediate Actions:\n{draft_guidelines}\n\n"
            f"### Checklist:\n{worker_payload.get('summary_checklist', '')}"
        )
        
        # Translate decision explanation context to selected language
        decision_raw = (
            f"- User message detected as '{detected_lang.upper()}' language.\n"
            f"- Emergency priority classified as **{priority_tier}** (Score: {priority_score}).\n"
            f"- Situation mapped to category: **{category}**.\n"
            f"- Geocoded coordinates: {coords} ({detected_city.upper()}).\n"
            f"- Safety Validation Score: **{eval_score * 100}%**."
        )
        
        decision_translated = decision_raw
        if target_lang_code != "en":
            try:
                decision_translated = self.translation_tool.translate(decision_raw, "en", target_lang_code)
            except Exception as e:
                print(f"Decision explanation translation failed: {e}")
            
        # TTS synthesis with translated prefix
        self.session_memory.add_step("VoiceTool", "Generating voice file", "STARTED")
        prefix_en = f"Emergency category {category} resolved. Here is your action checklist:"
        
        prefix_translated = prefix_en
        if target_lang_code != "en":
            try:
                prefix_translated = self.translation_tool.translate(prefix_en, "en", target_lang_code)
            except Exception as e:
                print(f"TTS prefix translation failed: {e}")
                
        tts_text = f"{prefix_translated}\n{worker_payload.get('summary_checklist', '')}"
        audio_file = self.voice_tool.text_to_speech(tts_text, target_lang_code)
        
        if audio_file:
            self.session_memory.add_step("VoiceTool", "TTS Complete", "COMPLETED", {"path": audio_file})
        else:
            self.session_memory.add_step("VoiceTool", "TTS Failed", "ERROR")

        output_duration = int((time.time() - translation_start) * 1000)
        stages_log.append({"stage": "Output Synthesis", "duration_ms": output_duration})

        # Save context to long-term user memory
        summary_short = f"Emergency type {category} classified as {priority_tier}. Location: {detected_city}."
        self.user_memory.add_past_request(user_query, priority_tier, category, summary_short)

        self.session_memory.add_agent_message("CrisisAssistAgent", final_text, target_lang_code, audio_file)
        
        total_duration = int((time.time() - start_time) * 1000)
        
        # Log telemetry metrics
        self.observability.log_run(
            trace_id=trace_id,
            query=user_query,
            priority=priority_tier,
            category=category,
            duration_ms=total_duration,
            stages=stages_log,
            eval_score=eval_score,
            success=eval_approved
        )

        return {
            "trace_id": trace_id,
            "response": final_text,
            "priority": priority_tier,
            "priority_score": priority_score,
            "category": category,
            "detected_lang": detected_lang,
            "detected_city": detected_city,
            "coordinates": coords,
            "audio_path": audio_file,
            "verified_resources": verified_resources,
            "eval_score": eval_score,
            "duration_ms": total_duration,
            "decision_explanation": decision_translated
        }


# Initialize singletons
trans = LanguageManager()
api_key = os.getenv("GEMINI_API_KEY")
gemini_client = None
if api_key:
    try:
        gemini_client = genai.Client(api_key=api_key)
    except Exception as e:
        print(f"Failed to initialize Gemini Client: {e}")

detector = LocationDetector(gemini_client)
maps_tool = MapsTool()

if "controller" not in st.session_state:
    st.session_state.controller = MainAgentController(gemini_client)

if "result" not in st.session_state:
    st.session_state.result = None

controller = st.session_state.controller

# ==================================================
# DYNAMIC LOCATION & LANGUAGE DETECTION (PRIORITIES)
# ==================================================

# Priority 1 & 2: Browser/device location permission
browser_coords = None
geo_data = get_geolocation()
if geo_data and "coords" in geo_data:
    browser_coords = (float(geo_data["coords"]["latitude"]), float(geo_data["coords"]["longitude"]))
    st.session_state.browser_coords = browser_coords

# Initialize Active geolocated info
if "active_location" not in st.session_state:
    if st.session_state.browser_coords:
        st.session_state.active_location = detector.reverse_geocode(
            st.session_state.browser_coords[0], 
            st.session_state.browser_coords[1]
        )
    else:
        # Priority 3: IP based location
        st.session_state.active_location = detector.detect_from_ip()

# ==================================================
# SIDEBAR BRANDING & CONFIGURATION
# ==================================================
with st.sidebar:
    # 1. 28 Languages selection setup
    lang_map = trans.get_supported_languages()
    if "lang_code" not in st.session_state:
        st.session_state.lang_code = "en"
    lang_code = st.session_state.lang_code

    # Render custom logo
    logo_path = "assets/logo.png"
    if os.path.exists(logo_path):
        st.image(logo_path, width=80)
    else:
        st.image("https://img.icons8.com/color/96/emergency-siren.png", width=64)
        
    st.title(trans.get("title", lang_code))
    st.caption(trans.get("tagline", lang_code))
    st.markdown("---")

    selected_lang_name = st.selectbox(
        f"🌐 {trans.get('lang_selector', lang_code)}",
        list(lang_map.values()),
        index=list(lang_map.values()).index(lang_map[lang_code])
    )
    
    # Retrieve lang code and update state
    new_lang_code = [k for k, v in lang_map.items() if v == selected_lang_name][0]
    if new_lang_code != lang_code:
        st.session_state.lang_code = new_lang_code
        st.rerun()
        
    # Load localized labels
    labels = trans.loader.get_labels(lang_code)

    st.markdown(f"### ⚙️ {trans.get('pref_header', lang_code)}")
    
    # Read user profile memory
    profile = controller.user_memory.get_profile()
    
    user_name = st.text_input(trans.get("name_label", lang_code), value=profile.get("name", "Aisha"))
    
    # Priority 4: Manual location input fallback
    default_manual_location = profile.get("home_location", f"{st.session_state.active_location['city']}, {st.session_state.active_location['state']}")
    home_loc = st.text_input(trans.get("default_loc_label", lang_code), value=default_manual_location)
    
    # If the user changed the location input manually, update our geocoded location status
    if home_loc != default_manual_location:
        st.session_state.active_location = detector.parse_manual_location(home_loc)
        controller.user_memory.update_profile({"home_location": home_loc})
        st.toast(f"Location updated manually to {home_loc}")
        
    medical_alerts = st.text_area(trans.get("medical_alerts_label", lang_code), value=profile.get("medical_alerts", "Penicillin Allergy"))
    
    st.markdown(f"**{trans.get('contact_name_label', lang_code)} / Contact:**")
    contact_name = st.text_input(trans.get("contact_name_label", lang_code), value=profile.get("emergency_contact", {}).get("name", "Rahul"))
    contact_phone = st.text_input(trans.get("contact_phone_label", lang_code), value=profile.get("emergency_contact", {}).get("phone", "+91-98765-43210"))
    
    # Save profile parameters
    if st.button(trans.get("btn_save_profile", lang_code), use_container_width=True):
        controller.user_memory.update_profile({
            "name": user_name,
            "preferred_language": selected_lang_name,
            "home_location": home_loc,
            "medical_alerts": medical_alerts,
            "emergency_contact": {
                "name": contact_name,
                "phone": contact_phone
            }
        })
        st.toast("Profile updated in memory!")
        
    # API Status Check
    api_loaded = controller.api_key is not None
    if api_loaded:
        st.success(trans.get("api_connected", lang_code))
    else:
        st.warning(trans.get("api_offline", lang_code))
        
    if st.sidebar.button(trans.get("btn_clear_session", lang_code), use_container_width=True):
        controller.session_memory.clear()
        st.session_state.result = None
        st.rerun()

# ==================================================
# MAIN PAGE BRANDING HERO
# ==================================================
st.markdown(f"<h1 class='main-title'>🚨 {trans.get('title', lang_code)}</h1>", unsafe_allow_html=True)
st.markdown(f"<p class='subtitle'>{trans.get('tagline', lang_code)}</p>", unsafe_allow_html=True)

# Landing Hero Container
st.markdown(f"""
<div class='hero-container'>
    <h3>🌟 Trustworthy Emergency Companion</h3>
    <p>{trans.get('hero_desc', lang_code)}</p>
</div>
""", unsafe_allow_html=True)

# ==================================================
# CURRENT DETECTED STATUS (LOCATION & LANGUAGE)
# ==================================================
location_str = f"{st.session_state.active_location['city']}, {st.session_state.active_location['state']}"
status_html = f"""
<div style='background-color: #EEF2F6; color: #1F2937; padding: 12px 20px; border-radius: 8px; margin-bottom: 25px; display: flex; justify-content: space-around; font-weight: bold; border: 1px solid #D1D5DB;'>
    <span>📍 Current Location: <code style='color: #1E3A8A; font-size: 1rem;'>{location_str}</code></span>
    <span>🌐 Selected Language: <code style='color: #1E3A8A; font-size: 1rem;'>{selected_lang_name}</code></span>
</div>
"""
st.markdown(status_html, unsafe_allow_html=True)


tab_console, tab_dashboard = st.tabs([
    f"🎮 {trans.get('input_header', lang_code)}", 
    f"📊 {trans.get('logs_header', lang_code)}"
])

# ==================================================
# CONSOLE TAB
# ==================================================
with tab_console:
    col_input, col_response = st.columns([2, 3])
    
    with col_input:
        st.subheader(trans.get("input_header", lang_code))
        
        # Audio voice recording widgets
        audio_file = None
        if hasattr(st, "audio_input"):
            audio_file = st.audio_input(trans.get("audio_record", lang_code))
            
        uploaded_audio = st.file_uploader(trans.get("upload_audio", lang_code), type=["wav", "mp3"])
        
        # Text input fallback
        user_text = st.text_area(
            f"{trans.get('input_header', lang_code)}:", 
            height=100, 
            placeholder=trans.get("input_placeholder", lang_code)
        )
        
        btn_submit = st.button(trans.get("btn_process", lang_code), type="primary", use_container_width=True)
        
        if btn_submit:
            query = ""
            if audio_file:
                temp_path = "temp_uploaded.wav"
                with open(temp_path, "wb") as f:
                    f.write(audio_file.read())
                st.info(trans.get("transcribing_voice", lang_code))
                query = controller.voice_tool.speech_to_text(temp_path)
                if not query:
                    st.error(trans.get("stt_failed", lang_code))
                    query = user_text
            elif uploaded_audio:
                temp_path = "temp_uploaded.wav"
                with open(temp_path, "wb") as f:
                    f.write(uploaded_audio.read())
                st.info(trans.get("transcribing_file", lang_code))
                query = controller.voice_tool.speech_to_text(temp_path)
                if not query:
                    st.error(trans.get("audio_failed", lang_code))
                    query = user_text
            else:
                query = user_text
                
            if not query:
                st.error(trans.get("err_empty_query", lang_code))
            else:
                with st.spinner(trans.get("processing_request", lang_code)):
                    # Process via orchestrator passing active coordinates & city
                    result = controller.process_emergency_request(
                        user_query=query, 
                        target_lang_code=lang_code,
                        location_details=st.session_state.active_location
                    )
                    st.session_state.result = result
                    st.rerun()

        # Render Memory status Card
        st.markdown(f"### 💾 {trans.get('memory_header', lang_code)}")
        profile = controller.user_memory.get_profile()
        st.markdown(f"**{trans.get('name_label', lang_code)}:** {profile.get('name')}")
        st.markdown(f"**{trans.get('default_loc_label', lang_code)}:** `{profile.get('home_location')}`")
        st.markdown(f"**{trans.get('medical_alerts_label', lang_code)}:** `{profile.get('medical_alerts')}`")
        
        past_queries = profile.get("past_emergency_summaries", [])
        if past_queries:
            st.markdown(f"**{trans.get('past_mem_context', lang_code)}**")
            for q in past_queries:
                cat_raw = q.get('category', 'General Support')
                cat_key = "category_" + cat_raw.lower().replace(" & ", "_").replace(" ", "_")
                cat_translated = trans.get(cat_key, lang_code)
                st.markdown(f"- *{cat_translated}* ({trans.get('priority_label', lang_code)}: `{q.get('priority')}`): {q.get('summary')}")

    with col_response:
        res = st.session_state.result
        
        # Real-time Agent workflow nodes visualization
        st.markdown(f"### {trans.get('agent_pipeline_status', lang_code)}")
        active_state = controller.session_memory.active_agent
        
        # Calculate states
        planner_class = "agent-node-active" if active_state == "planning" else ("agent-node-completed" if res else "agent-node")
        worker_class = "agent-node-active" if active_state == "executing" else ("agent-node-completed" if res else "agent-node")
        evaluator_class = "agent-node-active" if active_state == "validating" else ("agent-node-completed" if res else "agent-node")
        
        st.markdown(f"""
        <div class='agent-status-container'>
            <div class='agent-node {planner_class}'>📝 {trans.get('planner_agent_node', lang_code)}</div>
            <div style='font-size: 1.2rem; color: #64748B;'>➡️</div>
            <div class='agent-node {worker_class}'>⚙️ {trans.get('worker_agent_node', lang_code)}</div>
            <div style='font-size: 1.2rem; color: #64748B;'>➡️</div>
            <div class='agent-node {evaluator_class}'>🛡️ {trans.get('evaluator_agent_node', lang_code)}</div>
        </div>
        """, unsafe_allow_html=True)

        if not res:
            st.info(trans.get("prompt_submit_request", lang_code))
        else:
            # 1. Main Actionable Advice
            st.markdown(f"### {trans.get('actionable_advice', lang_code)}")
            st.markdown(res["response"])
            
            # Speech player
            if res.get("audio_path") and os.path.exists(res["audio_path"]):
                st.audio(res["audio_path"])

            st.markdown("---")

            # 2. Key Observability Status Cards
            st.markdown(f"### {trans.get('telemetry_cards', lang_code)}")
            sc1, sc2 = st.columns(2)
            with sc1:
                st.markdown(f"""
                <div class='metric-card'>
                    <div class='metric-label'>{trans.get('status_label', lang_code)}</div>
                    <div class='metric-value' style='color: #059669;'>{trans.get('status_verified', lang_code)}</div>
                </div>
                """, unsafe_allow_html=True)
            with sc2:
                # Color code priority
                p_tier = res["priority"]
                p_color = "#DC2626" if p_tier in ["CRITICAL", "HIGH"] else "#D97706"
                st.markdown(f"""
                <div class='metric-card' style='border-top: 5px solid {p_color};'>
                    <div class='metric-label'>{trans.get('priority_label', lang_code)}</div>
                    <div class='metric-value' style='color: {p_color};'>{p_tier}</div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("---")

            # 3. Verified Resources List with interactive cards (clickable Google Maps and direct dialing links)
            st.markdown(f"### {trans.get('resources_header', lang_code)}")
            resources = res.get("verified_resources", [])
            
            current_coords = st.session_state.active_location.get("coords", (19.0760, 72.8777))
            
            if resources:
                for idx, r in enumerate(resources):
                    v = r.get("verification", {})
                    v_score = int(v.get("score", 0.0) * 100)
                    r_coords = r.get("coordinates", current_coords)
                    
                    status_badge = "badge-ok" if r['status'] in ["OPERATIONAL", "OPEN", "AVAILABLE", "सत्यापित", "चालू", "सक्रिय"] else "badge-fail"
                    fresh_badge = "badge-ok" if v.get("checks", {}).get("freshness_ok", True) else "badge-warn"
                    phone_badge = "badge-ok" if v.get("checks", {}).get("phone_valid", True) else "badge-fail"
                    
                    # Generate Map URL and Directions URL
                    map_url = maps_tool.get_maps_url(r['name'], r_coords)
                    directions_url = maps_tool.get_directions_url(current_coords, r_coords)
                    
                    # Ensure clean phone number for tel: link
                    phone_clean = re.sub(r"[^\d+]", "", r['phone'])
                    
                    # Labels translated dynamically for card
                    addr_label = trans.get("default_loc_label", lang_code)
                    
                    st.markdown(f"""
                    <div style='background-color: #F8FAFC; color: #0F172A; padding: 15px; border-radius: 8px; margin-bottom: 10px; border-left: 4px solid #10B981; border: 1px solid #E2E8F0;'>
                        <a href="{map_url}" target="_blank" style="text-decoration: none; color: inherit; cursor: pointer;">
                            <strong style='color: #1E3A8A; font-size: 1.1rem; text-decoration: underline;'>🏥 {idx+1}. {r['name']}</strong>
                        </a>
                        <span style='color: #0F172A; font-weight: bold; background-color: #E2E8F0; padding: 2px 6px; border-radius: 4px; font-size: 0.85rem; margin-left: 8px;'>Score: {v_score}%</span><br>
                        <span style='color: #334155; display: block; margin-top: 5px;'>{addr_label}: {r['address']}</span>
                        <div style="margin-top: 5px; font-size: 0.95rem;">
                            <span style='color: #475569; font-weight: 500;'>Contact:</span> 
                            <a href="tel:{phone_clean}" style="color: #2563EB; font-weight: bold; text-decoration: underline;">{r['phone']}</a>
                            | <a href="{directions_url}" target="_blank" style="color: #059669; font-weight: bold; text-decoration: underline;">📍 View Directions on Map</a>
                        </div>
                        <div style="margin-top: 8px;">
                            <span style='color: #475569; font-weight: 500;'>Status:</span> <span class='status-badge {status_badge}'>{r['status']}</span> | 
                            <span style='color: #475569; font-weight: 500;'>Freshness:</span> <span class='status-badge {fresh_badge}'>FRESH</span> | 
                            <span style='color: #475569; font-weight: 500;'>Contact Format:</span> <span class='status-badge {phone_badge}'>VERIFIED</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info(trans.get("no_resources", lang_code))

            st.markdown("---")

            # 4. Explainable AI panel
            st.markdown(f"### {trans.get('decision_header', lang_code)}")
            st.markdown(res["decision_explanation"])

            st.markdown("---")

            # 5. Timeline execution logs
            st.markdown(f"### {trans.get('timeline_header', lang_code)}")
            timeline = controller.session_memory.get_timeline()
            for step in timeline:
                agent = step.get("agent", "System")
                action = step.get("action", "")
                status = step.get("status", "")
                details = step.get("details", "")
                
                status_color = "#1E40AF" if status == "STARTED" else ("#047857" if status in ["COMPLETED", "APPROVED"] else "#B91C1C")
                details_lbl = f" | Details: <code>{details}</code>" if details else ""
                st.markdown(f"""
                <div class='timeline-item'>
                    <span class='timeline-agent'>[{agent}]</span> 
                    <strong>{action}</strong> 
                    (<span style='color: {status_color}; font-weight: bold;'>{status}</span>){details_lbl}
                </div>
                """, unsafe_allow_html=True)

# ==================================================
# TELEMETRY LOGS DASHBOARD TAB
# ==================================================
with tab_dashboard:
    dashboard = LogsDashboard()
    dashboard.render(lang_code)
