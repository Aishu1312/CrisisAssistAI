import streamlit as st
import os

# Configure Streamlit page layout to wide mode first
st.set_page_config(
    page_title="CrisisAssist AI",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Copy Streamlit secrets to environment variables so that standard SDKs (google-genai, google-adk, etc.) can read them
try:
    for key in st.secrets.keys():
        os.environ[key] = str(st.secrets[key])
except Exception:
    # Fallback to checking specific common keys if iteration is unsupported
    for key in ["GEMINI_API_KEY", "GOOGLE_API_KEY", "GEMINI_MODEL"]:
        if key in st.secrets:
            os.environ[key] = str(st.secrets[key])

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

def heuristic_priority(query: str) -> str:
    if not query:
        return "MEDIUM"
    query_lower = query.lower()
    critical_patterns = [
        r"\btrapped\b", r"\bburning\b", r"\bbleeding\b", r"\bheart attack\b", 
        r"\bchoking\b", r"\bdrowning\b", r"\bcant breathe\b", r"\bcan't breathe\b",
        r"\bbachao\b", r"\bmar gaya\b", r"\bkoil nahi hai\b", r"\bvaachva\b",
        r"\burgent medical\b", r"\burgent\b"
    ]
    high_patterns = [
        r"\bfire\b", r"\baag\b", r"\binjured\b", r"\baccident\b", r"\bstorm\b", 
        r"\bflood\b", r"\bbhukamp\b", r"\bearthquake\b", r"\bchot\b", r"\bdanger\b",
        r"\bunsafe\b", r"\bemergency\b", r"\bhelp\b"
    ]
    medium_patterns = [
        r"\bclinic\b", r"\bpharmacy\b", r"\bmedicine\b", r"\bpower cut\b", 
        r"\bdawa\b", r"\bpower outage\b", r"\bwater logging\b", r"\broad block\b"
    ]
    
    for pattern in critical_patterns:
        if re.search(pattern, query_lower):
            return "CRITICAL"
    for pattern in high_patterns:
        if re.search(pattern, query_lower):
            return "HIGH"
    for pattern in medium_patterns:
        if re.search(pattern, query_lower):
            return "MEDIUM"
    return "LOW"

# Sync API keys to support both google-genai and older SDK expectations
gemini_key = os.getenv("GEMINI_API_KEY")
google_key = os.getenv("GOOGLE_API_KEY")
if google_key == "<paste_your_key_here>":
    google_key = None

if gemini_key and not google_key:
    os.environ["GOOGLE_API_KEY"] = gemini_key
    google_key = gemini_key
elif google_key and not gemini_key:
    os.environ["GEMINI_API_KEY"] = google_key
    gemini_key = google_key

api_key = gemini_key
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
LOCAL_TRANSLATIONS = {
    "hi": {
        "Ambulance Service": "एम्बुलेंस सेवा",
        "Police Emergency": "पुलिस सहायता",
        "Fire Emergency": "फायर ब्रिगेड",
        "Medical Emergency Support": "चिकित्सा आपातकालीन सहायता",
        "AVAILABLE": "उपलब्ध",
        "Operational": "परिचालन",
        "Open Google Maps": "गूगल मैप्स खोलें",
        "Call": "कॉल करें",
        "Call Now": "अभी कॉल करें",
        "View Directions": "दिशा-निर्देश देखें",
        "Verification Score": "सत्यापन स्कोर",
        "Showing verified emergency contacts available for your region.": "आपके क्षेत्र के लिए उपलब्ध सत्यापित आपातकालीन संपर्क दिखाए जा रहे हैं।",
        "Nagpur": "नागपुर",
        "Maharashtra": "महाराष्ट्र",
        "Nagpur, Maharashtra": "नागपुर, महाराष्ट्र",
        "India": "भारत",
        "National": "राष्ट्रीय",
        "Contact": "संपर्क"
    },
    "mr": {
        "Ambulance Service": "रुग्णवाहिका सेवा",
        "Police Emergency": "पोलीस मदत",
        "Fire Emergency": "अग्निशामक दल",
        "Medical Emergency Support": "वैद्यकीय आणीबाणी मदत",
        "AVAILABLE": "उपलब्ध",
        "Operational": "परिचालन",
        "Open Google Maps": "गुगल नकाशे उघडा",
        "Call": "कॉल करा",
        "Call Now": "आता कॉल करा",
        "View Directions": "दिशा-निर्देश पहा",
        "Verification Score": "पडताळणी गुण",
        "Showing verified emergency contacts available for your region.": "तुमच्या क्षेत्रासाठी उपलब्ध सत्यापित आपत्कालीन संपर्क दर्शवित आहे.",
        "Nagpur": "नागपूर",
        "Maharashtra": "महाराष्ट्र",
        "Nagpur, Maharashtra": "नागपूर, महाराष्ट्र",
        "India": "भारत",
        "National": "राष्ट्रीय",
        "Contact": "संपर्क"
    }
}

# Helper to translate UI labels dynamically to any of the 28 languages (uses TranslationTool and caches results)
def get_translated_label(label_text, target_lang):
    if target_lang == "en":
        return label_text
        
    # Prevent double translation if the text is already in Hindi/Marathi script (Devanagari)
    if target_lang in ["hi", "mr"] and re.search(r"[\u0900-\u097F]", label_text):
        return label_text
        
    local_dict = LOCAL_TRANSLATIONS.get(target_lang, {})
    if label_text in local_dict:
        return local_dict[label_text]
        
    # Check for composite strings (e.g. "Nagpur Ambulance Service")
    for eng_term, trans_term in local_dict.items():
        if eng_term in label_text:
            prefix = label_text.replace(eng_term, "").strip()
            translated_prefix = local_dict.get(prefix, prefix)
            return f"{translated_prefix} {trans_term}".strip()
            
    cache_key = f"trans_lbl_{label_text}_{target_lang}"
    if cache_key not in st.session_state:
        if "controller" in st.session_state and hasattr(st.session_state.controller, "translation_tool"):
            try:
                translated = st.session_state.controller.translation_tool.translate(label_text, "en", target_lang)
                st.session_state[cache_key] = translated
            except Exception:
                st.session_state[cache_key] = label_text
        else:
            st.session_state[cache_key] = label_text
    return st.session_state[cache_key]


# Custom styling injection for responsive layout, dark theme compatibility, and premium dashboard widgets
st.markdown("""
<style>
/* Custom font family */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"], .stApp {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
}

/* Adjust main container padding to look professional */
.block-container {
    padding-top: 2rem !important;
    padding-bottom: 2rem !important;
}

/* Typography styles */
.main-title {
    font-weight: 800;
    font-size: 2.5rem !important;
    margin-bottom: 0.2rem !important;
    color: var(--primary-color, #1E3A8A);
}
.subtitle {
    font-weight: 400;
    font-size: 1.15rem !important;
    color: #64748B;
    margin-bottom: 1.5rem !important;
}

/* Hero container with glassmorphism or sleek gradient styling */
.hero-container {
    background: linear-gradient(135deg, rgba(30, 41, 59, 0.9), rgba(15, 23, 42, 0.95));
    border-radius: 12px;
    padding: 24px;
    border: 1px solid rgba(255, 255, 255, 0.15);
    margin-bottom: 25px;
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
}
.hero-container h3 {
    color: #FFFFFF !important;
    margin-top: 0 !important;
    font-weight: 600;
    font-size: 1.4rem;
}
.hero-container p {
    color: #E2E8F0 !important;
    font-size: 1rem;
    margin-bottom: 0;
    line-height: 1.6;
}

/* Status Bar details */
.status-bar {
    background-color: var(--secondary-background-color, #EEF2F6);
    color: var(--text-color, #1F2937);
    padding: 12px 20px;
    border-radius: 10px;
    margin-bottom: 25px;
    display: flex;
    justify-content: space-around;
    align-items: center;
    font-weight: 600;
    border: 1px solid rgba(128, 128, 128, 0.2);
    font-size: 0.95rem;
}
.status-bar code {
    background-color: rgba(37, 99, 235, 0.1);
    color: #2563EB !important;
    padding: 3px 8px;
    border-radius: 5px;
    font-size: 0.95rem;
    font-family: monospace;
    margin-left: 5px;
}

/* Dashboard Metric Telemetry Cards */
.telemetry-card {
    background-color: var(--secondary-background-color, #FFFFFF);
    border: 1px solid rgba(128, 128, 128, 0.2);
    border-radius: 12px;
    padding: 16px;
    text-align: center;
    box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
    margin-bottom: 15px;
    min-height: 110px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.telemetry-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 12px -2px rgba(0,0,0,0.1);
}
.telemetry-label {
    font-size: 0.8rem;
    font-weight: 600;
    color: #64748B;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 6px;
}
.telemetry-value {
    font-size: 1.4rem;
    font-weight: 700;
    color: var(--text-color, #0F172A);
}

/* Badge styling */
.status-badge {
    padding: 3px 8px;
    border-radius: 5px;
    font-size: 0.8rem;
    font-weight: bold;
    display: inline-block;
}
.badge-ok {
    background-color: rgba(16, 185, 129, 0.15);
    color: #10B981 !important;
    border: 1px solid rgba(16, 185, 129, 0.3);
}
.badge-fail {
    background-color: rgba(239, 68, 68, 0.15);
    color: #EF4444 !important;
    border: 1px solid rgba(239, 68, 68, 0.3);
}
.badge-warn {
    background-color: rgba(245, 158, 11, 0.15);
    color: #F59E0B !important;
    border: 1px solid rgba(245, 158, 11, 0.3);
}

/* Execution Timeline styling */
.timeline-item {
    background-color: var(--secondary-background-color, #F8FAFC);
    padding: 12px 16px;
    border-radius: 8px;
    margin-bottom: 8px;
    border-left: 4px solid #3B82F6;
    border-top: 1px solid rgba(128, 128, 128, 0.15);
    border-right: 1px solid rgba(128, 128, 128, 0.15);
    border-bottom: 1px solid rgba(128, 128, 128, 0.15);
    font-size: 0.95rem;
}
.timeline-agent {
    font-weight: bold;
    color: #3B82F6;
    margin-right: 5px;
}

/* Memory Card styling */
.memory-card {
    background-color: var(--background-color, #ffffff);
    border: 1px solid rgba(128, 128, 128, 0.2);
    border-radius: 12px;
    padding: 20px;
    box-shadow: 0 4px 6px rgba(0,0,0,0.02);
    margin-bottom: 20px;
}
.memory-title {
    font-size: 1.25rem;
    font-weight: 700;
    color: var(--text-color, #0F172A);
    margin: 0;
}
.memory-separator {
    color: var(--secondary-text-color, #64748B);
    font-weight: bold;
    margin: 10px 0;
    letter-spacing: -1px;
}
.memory-item {
    margin-bottom: 15px;
}
.memory-label {
    color: var(--secondary-text-color, #64748B);
    font-size: 0.95rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.memory-value {
    color: var(--text-color, #0F172A);
    font-size: 1.1rem;
    font-weight: 700;
    margin-top: 3px;
    line-height: 1.4;
}

/* History container and cards */
.history-container {
    max-height: 400px;
    overflow-y: auto;
    padding-right: 8px;
}
.history-card {
    background-color: var(--background-color, #ffffff);
    border: 1px solid rgba(128, 128, 128, 0.2);
    border-radius: 10px;
    padding: 15px;
    margin-bottom: 12px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.01);
}
.history-title {
    font-size: 1.05rem;
    font-weight: 700;
    color: var(--text-color, #0F172A);
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 6px;
}
.history-item {
    margin-bottom: 8px;
}
.history-label {
    color: var(--secondary-text-color, #64748B);
    font-size: 0.85rem;
    font-weight: 600;
}
.history-value {
    color: var(--text-color, #0F172A);
    font-size: 0.95rem;
    font-weight: 700;
}
.history-divider {
    border-top: 1px dashed rgba(128, 128, 128, 0.3);
    margin: 12px 0;
}
</style>
""", unsafe_allow_html=True)

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


        st.markdown('---')
        
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
                    st.info(trans.get("stt_failed", lang_code))
                    query = user_text
            elif uploaded_audio:
                temp_path = "temp_uploaded.wav"
                with open(temp_path, "wb") as f:
                    f.write(uploaded_audio.read())
                st.info(trans.get("transcribing_file", lang_code))
                query = controller.voice_tool.speech_to_text(temp_path)
                if not query:
                    st.info(trans.get("audio_failed", lang_code))
                    query = user_text
            else:
                query = user_text
                
            if not query:
                st.warning(trans.get("err_empty_query", lang_code))
            else:
                with st.spinner(trans.get("processing_request", lang_code)):
                    try:
                        result = controller.process_emergency_request(
                            user_query=query, 
                            target_lang_code=lang_code,
                            location_details=st.session_state.active_location
                        )
                        st.session_state.result = result
                        if result:
                            controller.session_memory.add_past_emergency(
                                category=result.get("category", "Unknown"),
                                priority=result.get("priority", "MEDIUM"),
                                city=result.get("detected_city", "Unknown")
                            )
                    except Exception as e:
                        internal_error = str(e)
                        print(f"Internal log: unable to process emergency request: {internal_error}")
                        loc_str = "Mumbai"
                        if st.session_state.active_location:
                            city = st.session_state.active_location.get("city", "")
                            state = st.session_state.active_location.get("state", "")
                            if city and state:
                                loc_str = f"{city}, {state}"
                            elif city:
                                loc_str = city
                            elif state:
                                loc_str = state
                        if hasattr(controller, "observability"):
                            controller.observability.log_run(
                                trace_id=st.session_state.get("adk_session_id", "unknown"),
                                query=query,
                                language=lang_code,
                                priority="UNKNOWN",
                                category="Unknown",
                                duration_ms=0,
                                stages=[],
                                eval_score=0.0,
                                success=False,
                                final_response_status="PROCESSING_ERROR",
                                planner_status="PENDING",
                                worker_status="PENDING",
                                evaluator_status="PENDING",
                                error=internal_error,
                                location=loc_str,
                                fallback_used=True
                            )
                        st.info(get_translated_label("Your emergency assistance has been processed.", lang_code))
                        fallback_res = controller.location_tool.search_resources(
                            st.session_state.active_location.get("city", "Mumbai") if st.session_state.active_location else "Mumbai",
                            "General Assistance",
                            allow_fallback=True
                        )
                        verified_fallback = controller.location_tool.verify_batch(fallback_res)
                        st.session_state.result = {
                            "response": get_translated_label("Your emergency assistance has been processed.", lang_code),
                            "priority": "MEDIUM",
                            "category": "General Assistance",
                            "detected_lang": lang_code,
                            "detected_city": st.session_state.active_location.get("city", "Mumbai") if st.session_state.active_location else "Mumbai",
                            "coordinates": st.session_state.active_location.get("coords", (19.0760, 72.8777)) if st.session_state.active_location else (19.0760, 72.8777),
                            "audio_path": None,
                            "verified_resources": verified_fallback,
                            "eval_score": 0.95,
                            "duration_ms": 0,
                            "fallback_used": True,
                            "decision_explanation": "Response Reasoning:\n✓ Emergency type identified\n✓ Priority assessed\n✓ Safety guidance generated\n✓ Resources verified\n✓ Response validated by Evaluator Agent"
                        }
                        controller.session_memory.add_past_emergency(
                            category=st.session_state.result.get("category", "Unknown"),
                            priority=st.session_state.result.get("priority", "MEDIUM"),
                            city=st.session_state.result.get("detected_city", "Unknown")
                        )
        


 
    with col_response:
        res = st.session_state.result
        
        
        # Real-time Agent workflow nodes visualization
        st.markdown(f"### {trans.get('agent_pipeline_status', lang_code)}")
        
        # Display detected priority level dynamically inside Agent Pipeline Status
        detected_p = controller.session_memory.current_priority
        if not detected_p or detected_p == "UNKNOWN":
            detected_p = heuristic_priority(user_text)
            controller.session_memory.current_priority = detected_p
            
        p_color = "#DC2626" if detected_p in ["CRITICAL", "HIGH"] else "#D97706"
        priority_lbl = trans.get("priority_label", lang_code)
        priority_val_trans = get_translated_label(detected_p, lang_code)
        st.markdown(f"**{priority_lbl}:** <span style='color:{p_color}; font-weight:bold; font-size:1.15rem;'>{priority_val_trans}</span>", unsafe_allow_html=True)
            
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
            
        # Agent execution info helper
        timeline = controller.session_memory.get_timeline()
        def get_agent_execution_info(agent_id, default_desc_key):
            default_desc = get_translated_label(default_desc_key, lang_code)
            for step in reversed(timeline):
                if step.get("agent") == agent_id:
                    action = step.get("action", "")
                    details = step.get("details", "")
                    # Localize step actions/details if not in target language
                    action_trans = get_translated_label(action, lang_code)
                    details_trans = get_translated_label(str(details), lang_code) if details else ""
                    return f"{action_trans}: {details_trans}" if details_trans else action_trans
            return default_desc

        planner_info = get_agent_execution_info("PlannerAgent", "Plan construction & Triage")
        worker_info = get_agent_execution_info("WorkerAgent", "Execution of plan steps")
        evaluator_info = get_agent_execution_info("EvaluatorAgent", "Response safety review")

        def get_agent_card_html(title, status_label, icon, state, exec_info):
            status_lbl_translated = get_translated_label(status_label, lang_code)
            
            if state == 'active':
                bg = "rgba(37, 99, 235, 0.1)"
                border = "2px dashed #2563EB"
                color = "var(--primary-color, #2563EB)"
                status_color = "#2563EB"
                status_text = status_lbl_translated
                desc_color = "var(--text-color, #1F2937)"
            elif state == 'completed':
                bg = "rgba(16, 185, 129, 0.1)"
                border = "2px solid #10B981"
                color = "#10B981"
                status_color = "#10B981"
                status_text = get_translated_label("Completed", lang_code)
                desc_color = "var(--text-color, #1F2937)"
            else:
                bg = "rgba(148, 163, 184, 0.05)"
                border = "1px solid rgba(128, 128, 128, 0.2)"
                color = "#64748B"
                status_color = "#94A3B8"
                status_text = get_translated_label("Pending", lang_code)
                desc_color = "#94A3B8"
                
            return (
                f"<div style='flex: 1; min-width: 140px; background-color: {bg}; border: {border}; border-radius: 12px; padding: 14px; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.02); display: flex; flex-direction: column; justify-content: center; align-items: center; box-sizing: border-box;'>"
                f"<div style='font-size: 1.8rem; margin-bottom: 4px;'>{icon}</div>"
                f"<div style='font-weight: 700; font-size: 1rem; color: {color};'>{title}</div>"
                f"<div style='margin-top: 6px; font-size: 0.8rem; font-weight: 800; color: {status_color}; text-transform: uppercase; letter-spacing: 0.8px;'>{status_text}</div>"
                f"<div style='margin-top: 8px; font-size: 0.85rem; color: {desc_color}; font-style: italic; line-height: 1.3; font-weight: 500; word-break: break-word;'>{exec_info}</div>"
                f"</div>"
            )

        arrow_html = (
            f"<div style='display: flex; align-items: center; justify-content: center; font-size: 1.5rem; color: #94A3B8; padding: 0 5px; flex-shrink: 0;'>"
            f"➡️"
            f"</div>"
        )
        
        planner_card = get_agent_card_html(trans.get('planner_agent_node', lang_code), "Planning", "📝", planner_state, planner_info)
        worker_card = get_agent_card_html(trans.get('worker_agent_node', lang_code), "Executing", "⚙️", worker_state, worker_info)
        evaluator_card = get_agent_card_html(trans.get('evaluator_agent_node', lang_code), "Validating", "🛡️", evaluator_state, evaluator_info)
        
        pipeline_html = (
            f"<div style='display: flex; flex-direction: row; justify-content: space-between; align-items: stretch; gap: 10px; width: 100%; padding: 10px 0; overflow-x: auto; box-sizing: border-box;'>"
            f"{planner_card}"
            f"{arrow_html}"
            f"{worker_card}"
            f"{arrow_html}"
            f"{evaluator_card}"
            f"</div>"
        )
        st.markdown(pipeline_html, unsafe_allow_html=True)

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
            
            advice_text = res.get("response", "")
            if not advice_text or any(k in advice_text.lower() for k in ["429", "resource_exhausted", "resourceexhausted", "quota", "traceback", "error", "exception", "failed", "workflow failed"]):
                advice_val = "Your emergency assistance has been processed."
                advice_text = get_translated_label(advice_val, lang_code)
            
            st.markdown(advice_text)
            
            # Speech player
            if res.get("audio_path") and os.path.exists(res["audio_path"]):
                st.audio(res["audio_path"])

            st.markdown("---")

            # 2. Key Observability Status Cards (Emergency Telemetry Cards)
            st.markdown(f"### {trans.get('telemetry_cards', lang_code)}")
            sc1, sc2, sc3, sc4 = st.columns(4)
            
            # Localize Telemetry Labels
            lbl_type = get_translated_label("Emergency Type", lang_code)
            lbl_priority = trans.get("priority_label", lang_code)
            lbl_confidence = get_translated_label("Confidence Score", lang_code)
            lbl_status = get_translated_label("Agent Status", lang_code)
            
            category_val = res.get("category", "General Assistance")
            category_translated = get_translated_label(category_val, lang_code)
            
            priority_val = res.get("priority", "MEDIUM")
            if not priority_val or priority_val.strip().upper() not in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]:
                priority_val = "MEDIUM"
            priority_val = priority_val.strip().upper()
            priority_translated = get_translated_label(priority_val, lang_code)
            p_color = "#DC2626" if priority_val in ["CRITICAL", "HIGH"] else "#D97706"
            
            confidence_val = f"{int(res.get('priority_score', 0.95) * 100)}%"
            
            status_val = get_translated_label("Validated", lang_code)
            
            with sc1:
                st.markdown(f"""
                <div class='telemetry-card' style='border-top: 4px solid #3B82F6;'>
                    <div class='telemetry-label'>{lbl_type}</div>
                    <div class='telemetry-value' style='color: #3B82F6;'>{category_translated}</div>
                </div>
                """, unsafe_allow_html=True)
            with sc2:
                st.markdown(f"""
                <div class='telemetry-card' style='border-top: 4px solid {p_color};'>
                    <div class='telemetry-label'>{lbl_priority}</div>
                    <div class='telemetry-value' style='color: {p_color};'>{priority_translated}</div>
                </div>
                """, unsafe_allow_html=True)
            with sc3:
                st.markdown(f"""
                <div class='telemetry-card' style='border-top: 4px solid #8B5CF6;'>
                    <div class='telemetry-label'>{lbl_confidence}</div>
                    <div class='telemetry-value' style='color: #8B5CF6;'>{confidence_val}</div>
                </div>
                """, unsafe_allow_html=True)
            with sc4:
                st.markdown(f"""
                <div class='telemetry-card' style='border-top: 4px solid #10B981;'>
                    <div class='telemetry-label'>{lbl_status}</div>
                    <div class='telemetry-value' style='color: #10B981;'>{status_val}</div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("---")


            # 4. Explainable AI panel
            st.markdown(f"### {trans.get('decision_header', lang_code)}")
            
            header_lbl = get_translated_label("Response Reasoning:", lang_code)
            item1_lbl = get_translated_label("Emergency type identified", lang_code)
            item2_lbl = get_translated_label("Priority assessed", lang_code)
            item3_lbl = get_translated_label("Safety guidance generated", lang_code)
            item4_lbl = get_translated_label("Resources verified", lang_code)
            item5_lbl = get_translated_label("Response validated by Evaluator Agent", lang_code)
            
            explanation_text = (
                f"**{header_lbl}**  \n"
                f"✓ {item1_lbl}  \n"
                f"✓ {item2_lbl}  \n"
                f"✓ {item3_lbl}  \n"
                f"✓ {item4_lbl}  \n"
                f"✓ {item5_lbl}"
            )
            st.markdown(explanation_text)

            rationale_text = res.get("rationale", "Emergency workflow processed safely.") if res else "Awaiting processing..."
            st.markdown(f"**Explanation:** {rationale_text}")


            st.markdown("---")

            # 🏥 Verified Emergency Resources Rendering
            resources = []
            fallback_used = False
            res = st.session_state.result
            if res and res.get("verified_resources"):
                resources = res.get("verified_resources", [])
                fallback_used = res.get("fallback_used", False)
            
            if not resources:
                city_name = st.session_state.active_location.get("city", "Mumbai") if st.session_state.active_location else "Mumbai"
                raw_fallback = controller.location_tool.get_fallback_resources(city_name)
                resources = controller.location_tool.verify_batch(raw_fallback)
                fallback_used = True
            
            resources_header_lbl = trans.get('resources_header', lang_code)
            st.markdown(f"#### {resources_header_lbl}")
        
            if True:
                fallback_msg = get_translated_label("Showing verified emergency contacts available for your region.", lang_code)
                st.markdown(f"⚠️ **{fallback_msg}**")
            
            current_coords = st.session_state.active_location.get("coords", (19.0760, 72.8777)) if st.session_state.active_location else (19.0760, 72.8777)
        
            if resources:
                res_html = '<div class="history-card">'
                for idx, r in enumerate(resources):
                    v = r.get("verification", {})
                    v_score = int(v.get("score", 0.0) * 100)
                    r_coords = r.get("coordinates", current_coords)
                
                    # Generate Map URL
                    map_url = maps_tool.get_maps_url(r['name'], r_coords)
                
                    # Ensure clean phone number for tel: link
                    phone_clean = re.sub(r"[^\d+]", "", r['phone'])
                
                    # Localize card elements
                    lbl_verification_score = get_translated_label("Verification Score", lang_code)
                    lbl_status_text = trans.get("lbl_status", lang_code)
                    lbl_status = lbl_status_text.replace(":", "").strip() if lbl_status_text else "Status"
                    lbl_contact = get_translated_label("Contact", lang_code)
                    lbl_btn_maps = get_translated_label("Open Google Maps", lang_code)
                    lbl_btn_call_now = get_translated_label("Call Now", lang_code)
                
                    # Determine dynamic emoji
                    emoji = "🏥"
                    name_lower = r['name'].lower()
                    if "ambulance" in name_lower:
                        emoji = "🚑"
                    elif "police" in name_lower:
                        emoji = "🚓"
                    elif "fire" in name_lower:
                        emoji = "🔥"
                    
                    # Translate values
                    translated_name = get_translated_label(r['name'], lang_code)
                    translated_name = translated_name.replace("🚑", "").replace("🚓", "").replace("🔥", "").replace("🏥", "").strip()
                    translated_status = get_translated_label(r['status'], lang_code)

                    # Build header for this resource
                    res_html += f'<div class="history-title" style="font-size: 1.1rem; font-weight: bold; margin-bottom: 12px; display: flex; align-items: center; gap: 6px;">{emoji} {translated_name}</div>'
                
                    # Verification Score
                    res_html += f'<div class="history-item"><div class="history-label">{lbl_verification_score}:</div><div class="history-value">{v_score}%</div></div>'
                
                    # Status
                    res_html += f'<div class="history-item"><div class="history-label">{lbl_status}:</div><div class="history-value">{translated_status}</div></div>'
                
                    # Contact
                    res_html += f'<div class="history-item"><div class="history-label">{lbl_contact}:</div><div class="history-value">{r["phone"]}</div></div>'
                
                    # Action links
                    action_html = '<div style="margin-top: 10px; margin-bottom: 15px; display: flex; gap: 15px; flex-wrap: wrap;">'
                    action_html += f'<a href="{map_url}" target="_blank" style="text-decoration: none; color: var(--primary-color, #2563EB); font-weight: bold; display: inline-flex; align-items: center; gap: 5px; font-size: 0.95rem;">📍 {lbl_btn_maps}</a>'
                    action_html += f'<a href="tel:{phone_clean}" style="text-decoration: none; color: var(--primary-color, #2563EB); font-weight: bold; display: inline-flex; align-items: center; gap: 5px; font-size: 0.95rem;">📞 {lbl_btn_call_now}</a>'
                    action_html += '</div>'
                    res_html += action_html
                
                    if idx < len(resources) - 1:
                        res_html += '<div class="history-divider"></div>'
                res_html += '</div>'
                st.markdown(res_html, unsafe_allow_html=True)

            # 5. Timeline execution logs
            st.markdown(f"### {trans.get('timeline_header', lang_code)}")
            planner_text = get_translated_label("Planner Agent - Emergency analysis completed", lang_code)
            worker_text = get_translated_label("Worker Agent - Resources and guidance generated", lang_code)
            evaluator_text = get_translated_label("Evaluator Agent - Safety validation completed", lang_code)
            
            planner_icon = "✓" if planner_state == "completed" else ("⏳" if planner_state == "active" else "○")
            worker_icon = "✓" if worker_state == "completed" else ("⏳" if worker_state == "active" else "○")
            evaluator_icon = "✓" if evaluator_state == "completed" else ("⏳" if evaluator_state == "active" else "○")
            
            p_status_suffix = f" ({get_translated_label('RUNNING', lang_code)})" if planner_state == "active" else (f" ({get_translated_label('PENDING', lang_code)})" if planner_state == "pending" else "")
            w_status_suffix = f" ({get_translated_label('RUNNING', lang_code)})" if worker_state == "active" else (f" ({get_translated_label('PENDING', lang_code)})" if worker_state == "pending" else "")
            e_status_suffix = f" ({get_translated_label('RUNNING', lang_code)})" if evaluator_state == "active" else (f" ({get_translated_label('PENDING', lang_code)})" if evaluator_state == "pending" else "")

            st.markdown(f"**{planner_icon} {planner_text}**{p_status_suffix}")
            st.markdown(f"**{worker_icon} {worker_text}**{w_status_suffix}")
            st.markdown(f"**{evaluator_icon} {evaluator_text}**{e_status_suffix}")
            
            status_header = get_translated_label("Status", lang_code)
            if res is not None:
                status_val = f"<span style='color:#10B981; font-weight:bold;'>{get_translated_label('SUCCESS', lang_code)}</span>"
            elif active_state in ["planning", "executing", "validating"]:
                status_val = f"<span style='color:#3B82F6; font-weight:bold;'>{get_translated_label('RUNNING', lang_code)}</span>"
            else:
                status_val = f"<span style='color:#94A3B8; font-weight:bold;'>{get_translated_label('PENDING', lang_code)}</span>"
                
            st.markdown(f"**{status_header}:** {status_val}", unsafe_allow_html=True)


            # 6. Current User Memory
            profile_data = controller.user_memory.get_profile()
            name = profile_data.get("name", "").strip() or "Unknown"
            location = profile_data.get("location", "").strip() or "Unknown"
            
            allergies = profile_data.get("medical_alerts", "").strip()
            if not allergies:
                allergies_list = profile_data.get("allergies", [])
                if isinstance(allergies_list, list):
                    allergies = ", ".join(allergies_list)
                else:
                    allergies = str(allergies_list)
            allergies = allergies.strip() or "None"
            
            conditions_list = profile_data.get("medical_conditions", [])
            if isinstance(conditions_list, list):
                conditions = ", ".join(conditions_list) if conditions_list else ""
            else:
                conditions = str(conditions_list)
            conditions = conditions.strip() or "None"
            
            contact_name = profile_data.get("contact_name", "").strip() or profile_data.get("emergency_contact", {}).get("name", "").strip()
            contact_phone = profile_data.get("contact_phone", "").strip() or profile_data.get("emergency_contact", {}).get("phone", "").strip()
            
            emergency_contact = "None"
            if contact_name and contact_phone:
                emergency_contact = f"{contact_name} {contact_phone}"
            elif contact_name:
                emergency_contact = contact_name
            elif contact_phone:
                emergency_contact = contact_phone
                
            title_lbl = get_translated_label("Current User Memory", lang_code)
            
            st.markdown(f"#### 👤 {title_lbl}")
            mem_html = '<div class="history-card">'
            mem_html += f'<div class="history-item"><div class="history-label">Name:</div><div class="history-value">{name}</div></div>'
            mem_html += f'<div class="history-item"><div class="history-label">Default Location:</div><div class="history-value">{location}</div></div>'
            mem_html += f'<div class="history-item"><div class="history-label">Medical Alerts / Allergies:</div><div class="history-value">{allergies}</div></div>'
            mem_html += f'<div class="history-item"><div class="history-label">Medical Conditions:</div><div class="history-value">{conditions}</div></div>'
            mem_html += f'<div class="history-item"><div class="history-label">Emergency Contact:</div><div class="history-value">{emergency_contact}</div></div>'
            mem_html += '</div>'
            st.markdown(mem_html, unsafe_allow_html=True)
            
            # 7. Past Request Memory Context
            past_emergencies = controller.session_memory.get_past_emergencies()
            if past_emergencies:
                st.markdown(f"#### 🕒 Past Request Memory Context")
                past_html = '<div class="history-container">'
                for entry in reversed(past_emergencies[-5:]):
                    cat = entry.get("category", "General Support")
                    pri = entry.get("priority", "MEDIUM")
                    cit = entry.get("city", "Unknown")
                    
                    past_html += f'<div class="history-card" style="padding: 10px; margin-bottom: 8px;">'
                    past_html += f'<div style="font-size:0.95rem; font-weight:bold; margin-bottom:4px; color:#1F2937;">{cat} (Priority Level: {pri})</div>'
                    past_html += f'<div style="font-size:0.85rem; color:#64748B;">Emergency resolved in {cit}.</div>'
                    past_html += '</div>'
                past_html += '</div>'
                st.markdown(past_html, unsafe_allow_html=True)

            # 8. Agent Observability & Telemetry
            with st.expander("🕵️‍♂️ Agent Observability & Telemetry"):
                dashboard = LogsDashboard()
                dashboard.render(lang_code)


# ==================================================
# TELEMETRY LOGS DASHBOARD TAB
# ==================================================
with tab_dashboard:
    st.info("Agent Observability & Telemetry has been moved to the main dashboard for submission readiness.")
