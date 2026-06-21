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
    
    user_name = st.text_input(trans.get("name_label", lang_code), value=profile.get("name", ""), placeholder="E.g., Aishwarya")
    
    # Manual location input without fake/hardcoded default value
    profile_loc = profile.get("location", "")
    home_loc = st.text_input(trans.get("default_loc_label", lang_code), value=profile_loc, placeholder="E.g., Pune, Maharashtra")
    
    # If the user changed the location input manually, update our geocoded location status
    if home_loc != profile_loc:
        if home_loc.strip():
            st.session_state.active_location = detector.parse_manual_location(home_loc)
        else:
            st.session_state.active_location = detector.detect_from_ip()
        controller.user_memory.update_profile({"location": home_loc})
        st.toast(f"Location updated manually to {home_loc if home_loc else 'Not provided'}")
        
    # Allergies
    allergies_list = profile.get("allergies", [])
    if isinstance(allergies_list, list):
        allergies_str = ", ".join(allergies_list) if allergies_list else ""
    else:
        allergies_str = str(allergies_list)
    medical_alerts = st.text_area(trans.get("medical_alerts_label", lang_code), value=allergies_str, placeholder="E.g., Asthma")
    
    # Medical conditions
    conditions_list = profile.get("medical_conditions", [])
    if isinstance(conditions_list, list):
        conditions_str = ", ".join(conditions_list) if conditions_list else ""
    else:
        conditions_str = str(conditions_list)
        
    conditions_label = trans.get("medical_conditions_label", lang_code)
    if conditions_label == "medical_conditions_label":
        conditions_label = "Medical Conditions"
    medical_conditions_input = st.text_area(conditions_label, value=conditions_str, placeholder="E.g., Diabetes")
    
    st.markdown(f"**{trans.get('contact_name_label', lang_code)} / Contact:**")
    contact_name = st.text_input(trans.get("contact_name_label", lang_code), value=profile.get("emergency_contact", {}).get("name", ""), placeholder="E.g., Rahul")
    contact_phone = st.text_input(trans.get("contact_phone_label", lang_code), value=profile.get("emergency_contact", {}).get("phone", ""), placeholder="E.g., 9999999999")
    
    # Save profile parameters with stacked buttons: Save Profile and Update Profile
    if st.button("💾 Save Profile", use_container_width=True):
        parsed_allergies = [a.strip() for a in medical_alerts.split(",") if a.strip()]
        parsed_conditions = [c.strip() for c in medical_conditions_input.split(",") if c.strip()]
        controller.user_memory.update_profile({
            "name": user_name,
            "preferred_language": selected_lang_name,
            "location": home_loc,
            "allergies": parsed_allergies,
            "medical_conditions": parsed_conditions,
            "emergency_contact": {
                "name": contact_name,
                "phone": contact_phone
            }
        })
        st.success("✅ Profile saved successfully")
        
    if st.button("🔄 Update Profile", use_container_width=True):
        parsed_allergies = [a.strip() for a in medical_alerts.split(",") if a.strip()]
        parsed_conditions = [c.strip() for c in medical_conditions_input.split(",") if c.strip()]
        controller.user_memory.update_profile({
            "name": user_name,
            "preferred_language": selected_lang_name,
            "location": home_loc,
            "allergies": parsed_allergies,
            "medical_conditions": parsed_conditions,
            "emergency_contact": {
                "name": contact_name,
                "phone": contact_phone
            }
        })
        st.toast("Profile updated in memory!")
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
        profile = controller.user_memory.get_profile()
        name = (profile.get("name") or "").strip() or "Not provided"
        location = (profile.get("location") or profile.get("home_location") or "").strip() or "Not provided"
        
        # Allergies / Medical Alerts
        allergies_raw = profile.get("allergies", [])
        if isinstance(allergies_raw, list):
            allergies = ", ".join(allergies_raw).strip() if allergies_raw else "Not provided"
        else:
            allergies = str(allergies_raw).strip() or "Not provided"
            
        # Medical Conditions
        conditions_raw = profile.get("medical_conditions", [])
        if isinstance(conditions_raw, list):
            conditions = ", ".join(conditions_raw).strip() if conditions_raw else "Not provided"
        else:
            conditions = str(conditions_raw).strip() or "Not provided"
            
        contact = profile.get("emergency_contact", {})
        contact_name = (contact.get("name") or "").strip()
        contact_phone = (contact.get("phone") or "").strip()
        
        if contact_name and contact_phone:
            contact_display = f"{contact_name} ({contact_phone})"
        elif contact_name:
            contact_display = contact_name
        elif contact_phone:
            contact_display = contact_phone
        else:
            contact_display = "Not provided"
        
        # Retrieve translation strings
        title_lbl = trans.get("current_user_memory_title", lang_code)
        if title_lbl == "current_user_memory_title":
            title_lbl = "Current User Memory"
            
        name_lbl = trans.get("name_label", lang_code)
        loc_lbl = trans.get("default_loc_label", lang_code)
        alerts_lbl = trans.get("medical_alerts_label", lang_code)
        
        conditions_lbl = trans.get("medical_conditions_label", lang_code)
        if conditions_lbl == "medical_conditions_label":
            conditions_lbl = "Medical Conditions"
            
        memory_card_html = f"""
        <div style="background-color: #F8FAFC; color: #0F172A; padding: 15px; border-radius: 8px; border: 1px solid #E2E8F0; margin-bottom: 15px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
            <h4 style="margin-top: 0; color: #1E3A8A; display: flex; align-items: center; gap: 8px; font-size: 1.1rem; border-bottom: 1px solid #E2E8F0; padding-bottom: 8px; margin-bottom: 10px;">👤 {title_lbl}</h4>
            <div style="display: grid; grid-template-columns: auto 1fr; gap: 8px 12px; font-size: 0.95rem; margin-top: 10px;">
                <span style="font-weight: bold; color: #475569;">{name_lbl}:</span>
                <span style="color: #0F172A;">{name}</span>
                <span style="font-weight: bold; color: #475569;">{loc_lbl}:</span>
                <span style="color: #0F172A;">{location}</span>
                <span style="font-weight: bold; color: #475569;">{alerts_lbl}:</span>
                <span style="color: #DC2626; font-weight: bold;">{allergies}</span>
                <span style="font-weight: bold; color: #475569;">{conditions_lbl}:</span>
                <span style="color: #0F172A;">{conditions}</span>
                <span style="font-weight: bold; color: #475569;">Emergency Contact:</span>
                <span style="color: #0F172A;">{contact_display}</span>
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
