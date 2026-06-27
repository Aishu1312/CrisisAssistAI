# CrisisAssist AI

![CrisisAssist AI](https://img.shields.io/badge/Google-Kaggle%20Capstone-blue) ![Agents For Good](https://img.shields.io/badge/Track-Agents%20For%20Good-success) ![Python](https://img.shields.io/badge/Python-3.9+-blue.svg) ![Streamlit](https://img.shields.io/badge/UI-Streamlit-red.svg)

CrisisAssist AI is a trustworthy, multi-agent emergency support companion built for the **Google x Kaggle 5-Day AI Agents Intensive Capstone (Agents for Good Track)**. It intelligently triages crisis situations, provides actionable localized safety guidelines, verifies real-world emergency resources, and operates seamlessly across 28 global languages via both text and voice.

## 🎯 Problem Statement

During an emergency (e.g., natural disasters, medical crises, personal safety threats), individuals often face:
1. **Information Overload:** Struggling to find exact, life-saving steps in the heat of the moment.
2. **Language Barriers:** First responders or default AI agents may not speak the user's native language.
3. **Resource Uncertainty:** Difficulty locating *verified* and *operational* emergency contacts (hospitals, police stations, shelters).
4. **Accessibility Constraints:** Inability to type due to injury or panic.

## 💡 Solution Overview

CrisisAssist AI solves these challenges through an orchestrated **Multi-Agent Architecture** powered by Google Gemini 2.5 Flash:
- **Intelligent Triage:** Instantly categorizes emergencies (e.g., "Personal Safety / Harassment", "Fire Hazard", "Medical Emergency") and assigns dynamic priority levels (CRITICAL, HIGH, MEDIUM).
- **Localized Actionable Advice:** Generates step-by-step safety checklists explicitly in the user's selected language.
- **Verified Resource Mapping:** Geocodes the user's location to fetch real-world hospitals, fire stations, and police contacts, complete with an algorithmic "Verification Score" measuring the freshness and validity of the contact.
- **Voice-First Accessibility:** Full support for multilingual Speech-to-Text and Text-to-Speech (via Google TTS).
- **Explainable AI (XAI):** A transparent UI panel detailing exactly *why* a specific priority and category were assigned.

---

## 🏗️ Multi-Agent Architecture

The system utilizes an A2A (Agent-to-Agent) communication protocol, orchestrating three specialized agents:

1. **Planner Agent 📝**
   - **Role:** The first line of defense.
   - **Responsibility:** Parses user input, detects the emergency category, evaluates severity (via regex heuristics and LLM inference), and formulates a strategic execution plan.

2. **Worker Agent ⚙️**
   - **Role:** The execution engine.
   - **Responsibility:** Carries out the Planner's steps. It interacts with the `LocationTool` to fetch geo-coordinated resources, calls the `VoiceTool` for audio synthesis, and strictly enforces translation constraints to ensure the output is exclusively in the target language.

3. **Evaluator Agent 🛡️**
   - **Role:** The safety mechanism.
   - **Responsibility:** Validates the Worker's response against AI Safety guardrails to ensure no harmful, misleading, or hallucinatory advice is dispatched to a vulnerable user.

---

## 🧠 Memory System

CrisisAssist AI implements a dual-layer memory system:
- **User Memory (Persistent):** Stores critical static profile information such as Medical Conditions, Allergies, default Locations, and Emergency Contact details.
- **Session Memory (Dynamic):** Tracks the active state of the current emergency pipeline, preserving the chat history (Past Request Memory Context) to ensure continuity during an ongoing crisis event.

---

## 🛠️ Tools & Integrations

- **LocationTool:** Resolves geographic coordinates and maps them to a curated database of verified resources (Hospitals, Police, Fire, Shelters). It implements a robust fallback heuristic (e.g., 1091 for Women's Safety, 112 for Police).
- **MapsTool:** Generates direct Google Maps deep-links for instant navigation to verified facilities.
- **VoiceTool:** Integrates `speech_recognition` and `gTTS` to handle 28 diverse languages, providing vital accessibility for injured or visually impaired users.
- **TranslationTool:** Ensures strict, real-time contextual translation of complex safety protocols without English leakage.
- **Agent Analytics Dashboard:** Built-in observability tracing LLM execution times, confidence scores, XAI rationales, and fallback triggers.

---

## 🚀 Deployment Instructions

CrisisAssist AI is built using **Streamlit** and the **Google GenAI SDK**.

### Prerequisites
- Python 3.9+
- A valid Google Gemini API Key

### Local Installation
```bash
# 1. Clone the repository
git clone https://github.com/Aishu1312/CrisisAssistAI.git
cd CrisisAssistAI

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment variables
# Create a .env file and add your key:
GEMINI_API_KEY="your_api_key_here"

# 4. Run the Streamlit Application
streamlit run app.py
```

---

## 🔒 Security & AI Safety Features

- **Offline Rule Fallbacks:** If API rate limits (429 RESOURCE_EXHAUSTED) occur, the system gracefully falls back to deterministic rule-based advice and hardcoded national emergency numbers.
- **Explainability Panel:** Every decision is traced and displayed in the UI, ensuring end-users understand the agent's logic.
- **Evaluator Guardrails:** The dedicated Evaluator Agent explicitly blocks advice that could exacerbate injuries (e.g., suggesting incorrect medical procedures).

---

*Developed for the Google x Kaggle Agents For Good Capstone. Let's build AI that saves lives.*
