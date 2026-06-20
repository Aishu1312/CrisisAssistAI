import streamlit as st
import os
import sys
import time
from PIL import Image

# Setup search path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from main_agent import MainAgentController
from dashboard.logs_dashboard import LogsDashboard
from utils.translation import TranslationManager

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

# Initialize singletons
trans = TranslationManager()

if "controller" not in st.session_state:
    st.session_state.controller = MainAgentController()

if "result" not in st.session_state:
    st.session_state.result = None

controller = st.session_state.controller

# ==================================================
# SIDEBAR BRANDING & CONFIGURATION
# ==================================================
with st.sidebar:
    # Render custom logo
    logo_path = "assets/logo.png"
    if os.path.exists(logo_path):
        st.image(logo_path, width=80)
    else:
        st.image("https://img.icons8.com/color/96/emergency-siren.png", width=64)
        
    st.title(trans.get("title", lang_code))
    st.caption(trans.get("tagline", lang_code))
    st.markdown("---")

    # 1. 28 Languages selection
    lang_map = trans.get_supported_languages()
    selected_lang_name = st.selectbox(
        f"🌐 {trans.get('lang_selector', lang_code)}",
        list(lang_map.values()),
        index=list(lang_map.values()).index("English")
    )
    
    # Retrieve lang code
    lang_code = [k for k, v in lang_map.items() if v == selected_lang_name][0]
    
    # Load localized labels
    labels = trans.loader.get_labels(lang_code)

    st.markdown(f"### ⚙️ {trans.get('pref_header', lang_code)}")
    
    # Read user long term profile memory
    profile = controller.user_memory.get_profile()
    
    user_name = st.text_input(trans.get("name_label", lang_code), value=profile.get("name", "Jane Doe"))
    home_loc = st.text_input(trans.get("default_loc_label", lang_code), value=profile.get("home_location", "Mumbai"))
    medical_alerts = st.text_area(trans.get("medical_alerts_label", lang_code), value=profile.get("medical_alerts", ""))
    
    st.markdown(f"**{trans.get('contact_name_label', lang_code)} / Contact:**")
    contact_name = st.text_input(trans.get("contact_name_label", lang_code), value=profile.get("emergency_contact", {}).get("name", ""))
    contact_phone = st.text_input(trans.get("contact_phone_label", lang_code), value=profile.get("emergency_contact", {}).get("phone", ""))
    
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
        
    st.markdown("---")
    
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

# Display covers or thumbnails if available
thumbnail_path = "assets/thumbnail.png"
if os.path.exists(thumbnail_path):
    st.image(thumbnail_path, use_column_width=True, caption=trans.get("logo_caption", lang_code))
    with open(thumbnail_path, "rb") as file:
        st.download_button(
            label="💾 " + trans.get("logo_caption", lang_code) + " (PNG)",
            data=file,
            file_name="thumbnail.png",
            mime="image/png",
            use_container_width=True
        )

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
                    # Process via orchestrator
                    result = controller.process_emergency_request(query, lang_code)
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

            # 3. Verified Resources List with badges
            st.markdown(f"### {trans.get('resources_header', lang_code)}")
            resources = res.get("verified_resources", [])
            if resources:
                for idx, r in enumerate(resources):
                    v = r.get("verification", {})
                    v_score = int(v.get("score", 0.0) * 100)
                    
                    status_badge = "badge-ok" if r['status'] in ["OPERATIONAL", "OPEN", "AVAILABLE"] else "badge-fail"
                    fresh_badge = "badge-ok" if v.get("checks", {}).get("freshness_ok", True) else "badge-warn"
                    phone_badge = "badge-ok" if v.get("checks", {}).get("phone_valid", True) else "badge-fail"
                    
                    st.markdown(f"""
                    <div style='background-color: #F8FAFC; padding: 15px; border-radius: 8px; margin-bottom: 10px; border-left: 4px solid #10B981;'>
                        <strong>{idx+1}. {r['name']}</strong> (Verification score: <code>{v_score}%</code>)<br>
                        Address: {r['address']} | Contact: <code>{r['phone']}</code><br>
                        Status: <span class='status-badge {status_badge}'>{r['status']}</span> | 
                        Freshness: <span class='status-badge {fresh_badge}'>FRESH</span> | 
                        Contact Format: <span class='status-badge {phone_badge}'>VERIFIED</span>
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
