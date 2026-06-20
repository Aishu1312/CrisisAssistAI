import streamlit as st
import os
import sys
import time

# Ensure parent directory is in path for relative imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from main_agent import MainAgentController
from dashboard.logs_dashboard import LogsDashboard

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
        font-size: 1.15rem;
        text-align: center;
        margin-bottom: 30px;
    }
    .metric-card {
        background-color: #F3F4F6;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #2563EB;
        margin-bottom: 10px;
    }
    .agent-tag {
        font-weight: bold;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 0.85rem;
    }
    .tag-planner { background-color: #DBEAFE; color: #1E40AF; }
    .tag-worker { background-color: #FEF3C7; color: #92400E; }
    .tag-evaluator { background-color: #D1FAE5; color: #065F46; }
    .tag-priority { background-color: #FCE7F3; color: #9D174D; }
    
    .status-badge {
        font-size: 0.8rem;
        font-weight: bold;
        padding: 2px 6px;
        border-radius: 12px;
    }
    .badge-ok { background-color: #10B981; color: white; }
    .badge-warn { background-color: #F59E0B; color: white; }
    .badge-fail { background-color: #EF4444; color: white; }
</style>
""", unsafe_allow_html=True)

# Initialize Controller in Streamlit Session State
if "controller" not in st.session_state:
    st.session_state.controller = MainAgentController()

if "result" not in st.session_state:
    st.session_state.result = None

controller = st.session_state.controller

# ==================================================
# SIDEBAR CONTENT
# ==================================================
with st.sidebar:
    st.image("https://img.icons8.com/color/96/emergency-siren.png", width=64)
    st.title("CrisisAssist AI")
    st.caption("Version 1.0.0 (Top 12 Kaggle Candidate)")
    
    st.markdown("---")
    
    # 1. API Status Indicators
    api_loaded = controller.api_key is not None
    if api_loaded:
        st.success("🤖 Gemini API: CONNECTED")
    else:
        st.warning("⚠️ Running in offline Heuristic Mode")
        
    st.markdown("### ⚙️ User Profile & Medical Memory")
    
    # Read profile
    profile = controller.user_memory.get_profile()
    
    user_name = st.text_input("Name", value=profile.get("name", "Jane Doe"))
    pref_lang = st.selectbox(
        "Communication Language",
        ["English", "Hindi", "Marathi"],
        index=["English", "Hindi", "Marathi"].index(profile.get("preferred_language", "English"))
    )
    home_loc = st.text_input("Default Location", value=profile.get("home_location", "Mumbai"))
    medical_alerts = st.text_area("Medical Alerts / Allergies", value=profile.get("medical_alerts", ""))
    
    st.markdown("**Emergency Contact:**")
    contact_name = st.text_input("Contact Name", value=profile.get("emergency_contact", {}).get("name", ""))
    contact_phone = st.text_input("Contact Phone", value=profile.get("emergency_contact", {}).get("phone", ""))
    
    # Save button
    if st.button("Save Profile to Memory"):
        controller.user_memory.update_profile({
            "name": user_name,
            "preferred_language": pref_lang,
            "home_location": home_loc,
            "medical_alerts": medical_alerts,
            "emergency_contact": {
                "name": contact_name,
                "phone": contact_phone
            }
        })
        st.toast("Profile updated in memory!")
        
    st.markdown("---")
    if st.sidebar.button("Clear Session Memory"):
        controller.session_memory.clear()
        st.session_state.result = None
        st.rerun()

# ==================================================
# MAIN PAGE HERO SECTION
# ==================================================
st.markdown("<h1 class='main-title'>🚨 CrisisAssist AI</h1>", unsafe_allow_html=True)
st.markdown("<p class='subtitle'>Trustworthy Multi-Agent Emergency Response Companion</p>", unsafe_allow_html=True)

# Main container layout
tab_console, tab_dashboard = st.tabs(["🎮 Emergency Console", "📊 Telemetry Dashboard"])

with tab_console:
    col_input, col_response = st.columns([2, 3])
    
    with col_input:
        st.subheader("Send Emergency Request")
        
        # Audio Input support (Streamlit native audio recording)
        audio_file = None
        if hasattr(st, "audio_input"):
            audio_file = st.audio_input("🎤 Record emergency request (voice input)")
            
        # File upload backup for speech files
        uploaded_audio = st.file_uploader("Upload audio file (.wav)", type=["wav", "mp3"])
        
        # Text input
        user_text = st.text_area("Or type emergency details:", height=100, placeholder="E.g., mujhe madad chahiye, dharavi me flood hai.")
        
        btn_submit = st.button("🚨 Process Request", type="primary", use_container_width=True)
        
        # Action execution logic
        if btn_submit:
            query = ""
            if audio_file:
                # Save uploaded file
                temp_path = "temp_uploaded.wav"
                with open(temp_path, "wb") as f:
                    f.write(audio_file.read())
                # Perform STT
                st.info("Transcribing audio input...")
                query = controller.voice_tool.speech_to_text(temp_path)
                if not query:
                    st.error("Could not transcribe audio. Falling back to text box.")
                    query = user_text
            elif uploaded_audio:
                temp_path = "temp_uploaded.wav"
                with open(temp_path, "wb") as f:
                    f.write(uploaded_audio.read())
                st.info("Transcribing audio file...")
                query = controller.voice_tool.speech_to_text(temp_path)
                if not query:
                    st.error("Could not transcribe audio file.")
                    query = user_text
            else:
                query = user_text
                
            if not query:
                st.error("Please enter text or record audio before submitting.")
            else:
                with st.spinner("Multi-agent system negotiating response..."):
                    result = controller.process_emergency_request(query)
                    st.session_state.result = result
                    st.rerun()

        # Render User Context Memory Info
        st.markdown("### 💾 Active Memory Context")
        profile = controller.user_memory.get_profile()
        st.markdown(f"**Preferred Language:** {profile.get('preferred_language')}")
        st.markdown(f"**Medical Alerts:** `{profile.get('medical_alerts')}`")
        st.markdown(f"**Past Emergencies (Long-term Context):**")
        past_queries = profile.get("past_emergency_summaries", [])
        if past_queries:
            for q in past_queries:
                st.markdown(f"- *{q.get('category')}* (Priority: `{q.get('priority')}`): {q.get('summary')}")
        else:
            st.caption("No past emergencies logged.")

    with col_response:
        res = st.session_state.result
        if not res:
            st.info("Submit an emergency request to view recommendations and agent execution plans.")
        else:
            # 1. Main Response Card
            st.markdown(f"### 📣 Actionable Advice (Language: {res['detected_lang'].upper()})")
            st.markdown(res["response"])
            
            # 2. Speech Playback
            if res.get("audio_path") and os.path.exists(res["audio_path"]):
                st.audio(res["audio_path"])
            
            st.markdown("---")
            
            # 3. Verified Resources
            st.markdown("### 🏥 Verified Emergency Resources")
            resources = res.get("verified_resources", [])
            if resources:
                for idx, r in enumerate(resources):
                    v = r.get("verification", {})
                    score = int(v.get("score", 0.0) * 100)
                    fresh = "badge-ok" if v.get("checks", {}).get("freshness_ok", True) else "badge-warn"
                    phone = "badge-ok" if v.get("checks", {}).get("phone_valid", True) else "badge-fail"
                    status = "badge-ok" if v.get("checks", {}).get("status_ok", True) else "badge-fail"
                    
                    st.markdown(
                        f"**{idx+1}. {r['name']}** (Verification Score: `{score}%`)\n"
                        f"- Address: {r['address']} | Contact: `{r['phone']}`\n"
                        f"- Status: <span class='status-badge {status}'>{r['status']}</span> | "
                        f"Freshness: <span class='status-badge {fresh}'>RECENT</span> | "
                        f"Phone Format: <span class='status-badge {phone}'>VALID</span>",
                        unsafe_allow_html=True
                    )
            else:
                st.info("No resource listings found.")
                
            st.markdown("---")
            
            # 4. Explainable Decision Panel
            st.markdown("### 💡 Decision Explanation (Explainable AI)")
            st.markdown(res["decision_explanation"])

            st.markdown("---")
            
            # 5. Agent Activity Timeline
            st.markdown("### 🕒 Multi-Agent Execution Timeline")
            timeline = controller.session_memory.get_timeline()
            for step in timeline:
                agent = step.get("agent", "System")
                action = step.get("action", "")
                status = step.get("status", "")
                details = step.get("details", "")
                
                color_class = "tag-planner"
                if "worker" in agent.lower(): color_class = "tag-worker"
                elif "evaluator" in agent.lower(): color_class = "tag-evaluator"
                elif "priority" in agent.lower(): color_class = "tag-priority"
                
                details_str = f" | Details: `{details}`" if details else ""
                st.markdown(
                    f"- <span class='agent-tag {color_class}'>{agent}</span> "
                    f"**{action}** ({status}){details_str}",
                    unsafe_allow_html=True
                )

# ==================================================
# TELEMETRY DASHBOARD TAB
# ==================================================
with tab_dashboard:
    dashboard = LogsDashboard()
    dashboard.render()
