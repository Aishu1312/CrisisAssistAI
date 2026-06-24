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
from memory.user_memory import UserMemory
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
from main_agent import MainAgentController


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
    profile_loc = controller.user_memory.get_profile().get("location")
    if profile_loc:
        st.session_state.active_location = detector.parse_manual_location(profile_loc)
    elif st.session_state.browser_coords:
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
    labels = trans.get_labels(lang_code)

    st.markdown(f"### ⚙️ {trans.get('pref_header', lang_code)}")
    
    # Read user profile memory
    profile = controller.user_memory.get_profile()
    
    # Initialize session state keys for reactive updates
    if "profile_name" not in st.session_state:
        st.session_state.profile_name = profile.get("name", "")
    if "profile_location" not in st.session_state:
        st.session_state.profile_location = profile.get("location", "")
        
    if "profile_allergies" not in st.session_state:
        allergies_list = profile.get("allergies", [])
        if isinstance(allergies_list, list):
            st.session_state.profile_allergies = ", ".join(allergies_list) if allergies_list else ""
        else:
            st.session_state.profile_allergies = str(allergies_list)
            
    if "profile_conditions" not in st.session_state:
        conditions_list = profile.get("medical_conditions", [])
        if isinstance(conditions_list, list):
            st.session_state.profile_conditions = ", ".join(conditions_list) if conditions_list else ""
        else:
            st.session_state.profile_conditions = str(conditions_list)
            
    if "profile_contact_name" not in st.session_state:
        st.session_state.profile_contact_name = profile.get("emergency_contact", {}).get("name", "")
    if "profile_contact_phone" not in st.session_state:
        st.session_state.profile_contact_phone = profile.get("emergency_contact", {}).get("phone", "")
        
    def on_profile_change():
        raw_name = st.session_state.get("profile_name", "")
        raw_loc = st.session_state.get("profile_location", "")
        raw_allergies = st.session_state.get("profile_allergies", "")
        raw_conditions = st.session_state.get("profile_conditions", "")
        raw_contact_name = st.session_state.get("profile_contact_name", "")
        raw_contact_phone = st.session_state.get("profile_contact_phone", "")
        
        parsed_allergies = [a.strip() for a in raw_allergies.split(",") if a.strip()]
        parsed_conditions = [c.strip() for c in raw_conditions.split(",") if c.strip()]
        
        # Immediate location update and geocoding
        if raw_loc.strip():
            st.session_state.active_location = detector.parse_manual_location(raw_loc)
        else:
            st.session_state.active_location = detector.detect_from_ip()
            
        controller.user_memory.update_profile({
            "name": raw_name,
            "location": raw_loc,
            "allergies": parsed_allergies,
            "medical_alerts": raw_allergies,
            "medical_conditions": parsed_conditions,
            "contact_name": raw_contact_name,
            "contact_phone": raw_contact_phone,
            "emergency_contact": {
                "name": raw_contact_name,
                "phone": raw_contact_phone
            }
        })
        st.toast(trans.get("status_completed", lang_code))

    user_name = st.text_input(
        trans.get("name_label", lang_code), 
        placeholder=trans.get("placeholder_name", lang_code), 
        key="profile_name", 
        on_change=on_profile_change
    )
    
    home_loc = st.text_input(
        trans.get("default_loc_label", lang_code), 
        placeholder=trans.get("placeholder_location", lang_code), 
        key="profile_location", 
        on_change=on_profile_change
    )
    
    medical_alerts = st.text_area(
        trans.get("medical_alerts_label", lang_code), 
        placeholder=trans.get("placeholder_allergies", lang_code), 
        key="profile_allergies", 
        on_change=on_profile_change
    )
    
    conditions_label = trans.get("medical_conditions_label", lang_code)
    if conditions_label == "medical_conditions_label":
        conditions_label = "Medical Conditions"
    medical_conditions_input = st.text_area(
        conditions_label, 
        placeholder=trans.get("placeholder_conditions", lang_code), 
        key="profile_conditions", 
        on_change=on_profile_change
    )
    
    st.markdown(f"**{trans.get('contact_name_label', lang_code)} / Contact:**")
    contact_name = st.text_input(
        trans.get("contact_name_label", lang_code), 
        placeholder=trans.get("placeholder_contact_name", lang_code), 
        key="profile_contact_name", 
        on_change=on_profile_change
    )
    contact_phone = st.text_input(
        trans.get("contact_phone_label", lang_code), 
        placeholder=trans.get("placeholder_contact_phone", lang_code), 
        key="profile_contact_phone", 
        on_change=on_profile_change
    )
    
    # Save profile parameters with stacked buttons: Save Profile and Update Profile
    btn_save_lbl = "💾 " + trans.get("btn_save_profile", lang_code)
    btn_update_lbl = trans.get("btn_update_profile", lang_code)
    
    if st.button(btn_save_lbl, use_container_width=True):
        on_profile_change()
        st.success("✅ " + trans.get("status_completed", lang_code))
        
    if st.button(btn_update_lbl, use_container_width=True):
        on_profile_change()
        st.toast(trans.get("status_completed", lang_code))
        time.sleep(0.5)
        st.rerun()
        
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
hero_title_text = trans.get("hero_title", lang_code)
loc_status_text = trans.get("status_current_location", lang_code)
lang_status_text = trans.get("status_selected_language", lang_code)

st.markdown(f"""
<div class='hero-container'>
    <h3>{hero_title_text}</h3>
    <p>{trans.get('hero_desc', lang_code)}</p>
</div>
""", unsafe_allow_html=True)

# ==================================================
# CURRENT DETECTED STATUS (LOCATION & LANGUAGE)
# ==================================================
location_str = f"{st.session_state.active_location['city']}, {st.session_state.active_location['state']}"
status_html = f"""
<div style='background-color: #EEF2F6; color: #1F2937; padding: 12px 20px; border-radius: 8px; margin-bottom: 25px; display: flex; justify-content: space-around; font-weight: bold; border: 1px solid #D1D5DB;'>
    <span>{loc_status_text} <code style='color: #1E3A8A; font-size: 1rem;'>{location_str}</code></span>
    <span>{lang_status_text} <code style='color: #1E3A8A; font-size: 1rem;'>{selected_lang_name}</code></span>
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
                   # Render Memory status Card directly from user memory profile for immediate UI updates
        profile_data = controller.user_memory.get_profile()
        name = profile_data.get("name", "").strip()
        location = profile_data.get("location", "").strip()
        
        allergies = profile_data.get("medical_alerts", "").strip()
        if not allergies:
            allergies_list = profile_data.get("allergies", [])
            if isinstance(allergies_list, list):
                allergies = ", ".join(allergies_list)
            else:
                allergies = str(allergies_list)
        allergies = allergies.strip()
        
        conditions_list = profile_data.get("medical_conditions", [])
        if isinstance(conditions_list, list):
            conditions = ", ".join(conditions_list) if conditions_list else ""
        else:
            conditions = str(conditions_list)
        conditions = conditions.strip()
        
        contact_name = profile_data.get("contact_name", "").strip() or profile_data.get("emergency_contact", {}).get("name", "").strip()
        contact_phone = profile_data.get("contact_phone", "").strip() or profile_data.get("emergency_contact", {}).get("phone", "").strip()
        
        # Combine contact name and phone into Emergency Contact
        emergency_contact = ""
        if contact_name and contact_phone:
            phone_val = contact_phone
            digits_only = "".join(c for c in phone_val if c.isdigit())
            if not phone_val.startswith("+") and len(digits_only) == 10:
                phone_val = f"+91-{digits_only}"
            emergency_contact = f"{contact_name} ({phone_val})"
        elif contact_name:
            emergency_contact = contact_name
        elif contact_phone:
            phone_val = contact_phone
            digits_only = "".join(c for c in phone_val if c.isdigit())
            if not phone_val.startswith("+") and len(digits_only) == 10:
                phone_val = f"+91-{digits_only}"
            emergency_contact = phone_val

        # Retrieve translation strings
        title_lbl = trans.get("current_user_memory_title", lang_code)
        if title_lbl == "current_user_memory_title":
            title_lbl = "Current User Memory"
            
        name_lbl = trans.get("name_label", lang_code)
        alerts_lbl = trans.get("medical_alerts_label", lang_code)
        
        conditions_lbl = trans.get("medical_conditions_label", lang_code)
        if conditions_lbl == "medical_conditions_label":
            conditions_lbl = "Medical Conditions"
            
        default_loc_lbl = trans.get("default_loc_label", lang_code)
        if default_loc_lbl == "default_loc_label":
            default_loc_lbl = "Default Location"

        emergency_contact_lbl = trans.get("emergency_contact_label", lang_code).replace(":", "").strip()
        if emergency_contact_lbl == "emergency_contact_label":
            emergency_contact_lbl = "Emergency Contact"

        memory_lines = []
        if name:
            memory_lines.append(f"""
                <div style="margin-bottom: 8px; display: flex; flex-flow: row wrap; align-items: baseline;">
                    <span style="font-weight: bold; color: #475569; margin-right: 6px; min-width: 180px; display: inline-block;">{name_lbl}:</span>
                    <span style="color: #0F172A; flex: 1; min-width: 150px; word-break: break-word;">{name}</span>
                </div>
            """)
        if location:
            memory_lines.append(f"""
                <div style="margin-bottom: 8px; display: flex; flex-flow: row wrap; align-items: baseline;">
                    <span style="font-weight: bold; color: #475569; margin-right: 6px; min-width: 180px; display: inline-block;">{default_loc_lbl}:</span>
                    <span style="color: #0F172A; flex: 1; min-width: 150px; word-break: break-word;">{location}</span>
                </div>
            """)
        if allergies:
            memory_lines.append(f"""
                <div style="margin-bottom: 8px; display: flex; flex-flow: row wrap; align-items: baseline;">
                    <span style="font-weight: bold; color: #475569; margin-right: 6px; min-width: 180px; display: inline-block;">{alerts_lbl}:</span>
                    <span style="color: #DC2626; font-weight: bold; flex: 1; min-width: 150px; word-break: break-word;">{allergies}</span>
                </div>
            """)
        if conditions:
            memory_lines.append(f"""
                <div style="margin-bottom: 8px; display: flex; flex-flow: row wrap; align-items: baseline;">
                    <span style="font-weight: bold; color: #475569; margin-right: 6px; min-width: 180px; display: inline-block;">{conditions_lbl}:</span>
                    <span style="color: #0F172A; flex: 1; min-width: 150px; word-break: break-word;">{conditions}</span>
                </div>
            """)
        if emergency_contact:
            memory_lines.append(f"""
                <div style="margin-bottom: 8px; display: flex; flex-flow: row wrap; align-items: baseline;">
                    <span style="font-weight: bold; color: #475569; margin-right: 6px; min-width: 180px; display: inline-block;">{emergency_contact_lbl}:</span>
                    <span style="color: #0F172A; flex: 1; min-width: 150px; word-break: break-word;">{emergency_contact}</span>
                </div>
            """)
            
        memory_card_html = f"""
        <div style="background-color: #F8FAFC; color: #0F172A; padding: 15px; border-radius: 8px; border: 1px solid #E2E8F0; margin-bottom: 15px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
            <h4 style="margin-top: 0; color: #1E3A8A; display: flex; align-items: center; gap: 8px; font-size: 1.1rem; border-bottom: 1px solid #E2E8F0; padding-bottom: 8px; margin-bottom: 10px;">👤 {title_lbl}</h4>
            <div style="font-size: 0.95rem; margin-top: 10px; line-height: 1.6;">
                {"".join(memory_lines) if memory_lines else '<div style="color: #64748B; font-style: italic;">No profile data saved in memory.</div>'}
            </div>
        </div>
        """
        st.markdown(memory_card_html, unsafe_allow_html=True)
        
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
        
        # Display detected priority level dynamically inside Agent Pipeline Status
        detected_p = controller.session_memory.current_priority
        if detected_p and detected_p != "UNKNOWN":
            p_color = "#DC2626" if detected_p in ["CRITICAL", "HIGH"] else "#D97706"
            st.markdown(f"**{trans.get('priority_label', lang_code)}:** <span style='color:{p_color}; font-weight:bold; font-size:1.15rem;'>{detected_p}</span>", unsafe_allow_html=True)
            
        active_state = controller.session_memory.active_agent
        
        # Determine states
        if active_state == "planning":
            planner_state, worker_state, evaluator_state = "active", "pending", "pending"
        elif active_state == "executing":
            planner_state, worker_state, evaluator_state = "completed", "active", "pending"
        elif active_state == "validating":
            planner_state, worker_state, evaluator_state = "completed", "completed", "active"
        elif res is not None:
            planner_state, worker_state, evaluator_state = "completed", "completed", "completed"
        else:
            planner_state, worker_state, evaluator_state = "pending", "pending", "pending"
            
        def get_agent_card_html(title, status_label, icon, state):
            if state == 'active':
                bg = "#EFF6FF"
                border = "2px dashed #2563EB"
                color = "#1E3A8A"
                status_color = "#2563EB"
                status_text = status_label
            elif state == 'completed':
                bg = "#ECFDF5"
                border = "2px solid #10B981"
                color = "#065F46"
                status_color = "#10B981"
                status_text = "Completed"
            else:
                bg = "#F8FAFC"
                border = "1px solid #E2E8F0"
                color = "#64748B"
                status_color = "#94A3B8"
                status_text = "Pending"
                
            return f"""
            <div style="background-color: {bg}; border: {border}; border-radius: 8px; padding: 12px; text-align: center; box-shadow: 0 1px 2px rgba(0,0,0,0.05); min-height: 100px;">
                <div style="font-size: 1.4rem; margin-bottom: 2px;">{icon}</div>
                <div style="font-weight: bold; font-size: 0.95rem; color: {color};">{title}</div>
                <div style="margin-top: 5px; font-size: 0.8rem; font-weight: bold; color: {status_color}; text-transform: uppercase; letter-spacing: 0.5px;">
                    {status_text}
                </div>
            </div>
            """
            
        col_p, col_w, col_e = st.columns(3)
        with col_p:
            st.markdown(get_agent_card_html(trans.get('planner_agent_node', lang_code), "Planning", "📝", planner_state), unsafe_allow_html=True)
        with col_w:
            st.markdown(get_agent_card_html(trans.get('worker_agent_node', lang_code), "Executing", "⚙️", worker_state), unsafe_allow_html=True)
        with col_e:
            st.markdown(get_agent_card_html(trans.get('evaluator_agent_node', lang_code), "Validating", "🛡️", evaluator_state), unsafe_allow_html=True)

        if not res:
            st.info(trans.get("prompt_submit_request", lang_code))
        elif res.get("status") == "AWAITING_APPROVAL":
            st.warning(f"🚨 **Awaiting Approval:** {res['response']}")
            
            confirm_input = st.text_input("Type 'approve' to confirm emergency dispatch:", key="confirm_dispatch_input")
            if st.button("Confirm Approval", type="primary", use_container_width=True):
                if confirm_input.strip().lower() == "approve":
                    st.session_state.dispatch_response = "approve"
                    with st.spinner("Processing dispatch approval..."):
                        result = controller.process_emergency_request(
                            user_query="",
                            target_lang_code=lang_code,
                            location_details=st.session_state.active_location
                        )
                        st.session_state.result = result
                        st.rerun()
                else:
                    st.error("Approval text must be 'approve'.")
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
                    
                    status_badge = "badge-ok" if v.get("checks", {}).get("status_ok", True) else "badge-fail"
                    fresh_badge = "badge-ok" if v.get("checks", {}).get("freshness_ok", True) else "badge-warn"
                    phone_badge = "badge-ok" if v.get("checks", {}).get("phone_valid", True) else "badge-fail"
                    
                    # Generate Map URL and Directions URL
                    map_url = maps_tool.get_maps_url(r['name'], r_coords)
                    directions_url = maps_tool.get_directions_url(current_coords, r_coords)
                    
                    # Ensure clean phone number for tel: link
                    phone_clean = re.sub(r"[^\d+]", "", r['phone'])
                    
                    # Labels translated dynamically for card
                    addr_label = trans.get("default_loc_label", lang_code)
                    fresh_badge_text = trans.get("status_badge_fresh", lang_code)
                    verified_badge_text = trans.get("status_badge_verified", lang_code)
                    lbl_status_text = trans.get("lbl_status", lang_code)
                    lbl_freshness_text = trans.get("lbl_freshness", lang_code)
                    lbl_contact_format_text = trans.get("lbl_contact_format", lang_code)
                    view_directions_text = trans.get("view_directions", lang_code)
                    lbl_contact_text = trans.get("emergency_contact_label", lang_code).replace("Emergency ", "").strip()
                    
                    st.markdown(f"""
                    <div style='background-color: #F8FAFC; color: #0F172A; padding: 15px; border-radius: 8px; margin-bottom: 10px; border-left: 4px solid #10B981; border: 1px solid #E2E8F0;'>
                        <a href="{map_url}" target="_blank" style="text-decoration: none; color: inherit; cursor: pointer;">
                            <strong style='color: #1E3A8A; font-size: 1.1rem; text-decoration: underline;'>🏥 {idx+1}. {r['name']}</strong>
                        </a>
                        <span style='color: #0F172A; font-weight: bold; background-color: #E2E8F0; padding: 2px 6px; border-radius: 4px; font-size: 0.85rem; margin-left: 8px;'>Score: {v_score}%</span><br>
                        <span style='color: #334155; display: block; margin-top: 5px;'>{addr_label}: {r['address']}</span>
                        <div style="margin-top: 5px; font-size: 0.95rem;">
                            <span style='color: #475569; font-weight: 500;'>{lbl_contact_text}:</span> 
                            <a href="tel:{phone_clean}" style="color: #2563EB; font-weight: bold; text-decoration: underline;">{r['phone']}</a>
                            | <a href="{directions_url}" target="_blank" style="color: #059669; font-weight: bold; text-decoration: underline;">{view_directions_text}</a>
                        </div>
                        <div style="margin-top: 8px;">
                            <span style='color: #475569; font-weight: 500;'>{lbl_status_text}:</span> <span class='status-badge {status_badge}'>{r['status']}</span> | 
                            <span style='color: #475569; font-weight: 500;'>{lbl_freshness_text}:</span> <span class='status-badge {fresh_badge}'>{fresh_badge_text}</span> | 
                            <span style='color: #475569; font-weight: 500;'>{lbl_contact_format_text}:</span> <span class='status-badge {phone_badge}'>{verified_badge_text}</span>
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
                details_header = trans.get("lbl_details", lang_code)
                details_lbl = f" | {details_header} <code>{details}</code>" if details else ""
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
