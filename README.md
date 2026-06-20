# 🚨 CrisisAssist AI — Trustworthy Multi-Agent Emergency Response Companion

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Streamlit App](https://static.streamlit.io/badge-streamlit.svg)](app.py)

**CrisisAssist AI** is a multi-agent emergency response companion designed to deliver fast, localized, and strictly verified crisis instructions to citizens and first responders. Built for the **Kaggle "5-Day AI Agents" Capstone Project (Track: Agents for Good)**, the system targets a Top 12 placement by combining advanced AI orchestration, safety validation, real-time Model Context Protocol (MCP) telemetry, and multi-language/speech processing.

---

## 📖 Problem Statement & Why It Matters

During natural disasters, fires, or medical crises, access to information is a double-edged sword. While search engines provide millions of results, users face:
- **Information Overload:** Dense text is impossible to digest under panic or high stress.
- **Hallucinated / Stale Data:** Outdated phone numbers or closed shelters can cost lives.
- **Language Barriers:** In multilingual societies (such as India), crucial alerts are often unavailable in regional dialects (e.g. Hindi or Marathi).

**CrisisAssist AI solves this** by utilizing a collaborative multi-agent architecture. It acts as an explainable, reliable assistant that parses voice or text requests, geolocates search fields, checks resource validity on municipal schemas, translates answers, and reads guidelines aloud, all while maintaining trace logs and safety check validations.

---

## 🎨 Premium Visual Interface

The interface features a dual-layout design:
1. **🎮 Emergency Console:** Voice recording, custom home profiles, priority classifications, step timeline logs, and maps coordinates listing verified resources with status indicators.
2. **📊 Telemetry Dashboard:** Performance analysis of system duration latency, safety validation stats, log records, and category distribution ratios.

---

## 🏗️ Multi-Agent System Architecture

CrisisAssist AI is built around a **Planner → Worker → Evaluator** design pattern utilizing structured Agent-to-Agent (A2A) protocol communication.

```
       User Voice / Text Input
                 │
                 ▼
        [Main Controller]
                 │
       ┌─────────┴─────────┐
       ▼                   ▼
[Priority Agent]    [Planner Agent]
 (Triage Level)     (Action Sequence)
       │                   │
       └─────────┬─────────┘
                 ▼
          [Worker Agent] ◄──────┐ (Re-execution feedback loop)
        (Executes Tools/MCP)    │
                 │              │
                 ▼              │
        [Evaluator Agent] ──────┘
      (Safety & Grounding Check)
                 │
                 ▼ (Approved)
       Output translation & TTS
```

### 🤖 Collaborating Agents
- **Priority Triage Agent:** Classifies incoming emergencies into `LOW`, `MEDIUM`, `HIGH`, or `CRITICAL` severity tiers.
- **Planner Agent:** Identifies the emergency category (Medical, Fire, Disaster, Rescue) and generates sequential plan steps.
- **Worker Agent:** Fulfills the plan by calling location, verification, and summarizer tools, as well as checking telemetry from the MCP server.
- **Evaluator Agent:** Validates the compiled draft, checking formatting and verifying safety. Rejects output and triggers a refinement loop if score is `< 0.85`.

---

## 🔌 Model Context Protocol (MCP) Implementation

The system integrates a simulated **Model Context Protocol (MCP) Server** (`mcp_server/server.py`) which acts as an external data interface. The Worker Agent uses this MCP connection to query:
1. `get_disaster_alerts`: Retrieves live meteorological or hazard warnings.
2. `search_shelters`: Queries available capacities and occupancy ratios from local relief centers in real time.

---

## 🛠️ Installation & Local Usage

Ensure you have **Python 3.9+** installed.

### 1. Clone & Setup
```bash
git clone https://github.com/your-username/CrisisAssistAI.git
cd CrisisAssistAI
```

### 2. Install Dependencies
We recommend using `uv` or `pip`:
```bash
pip install -r requirements.txt
```

### 3. Configure Environment
Create a `.env` file from the template:
```bash
copy .env.example .env
```
*(Optional)* Add your `GEMINI_API_KEY` to enable Gemini LLM-based reasoning. If left empty, the system runs on local heuristics.

### 4. Run the Streamlit Application
```bash
streamlit run app.py
```

### 5. Run the CLI Demo Walkthrough
```bash
python run_demo.py
```

---

## 🔒 Security Practices

- **Zero API Keys in Repository:** API key is strictly loaded via `.env`.
- **Validation Guardrails:** Input sanitization prevents prompt injections. The Evaluator Agent checks responses for hazardous instructions before they are displayed.
- **Privacy-Friendly Memory:** Long-term memory profile data is saved locally on the user's hard drive (`user_profile.json`) rather than shared on external clouds.

---

## 🚀 Future Scope

1. **Direct CAD Integration:** Connect with Computer-Aided Dispatch systems for automatic emergency services dispatch.
2. **Offline Mesh-Network Broadcast:** Compress guidelines for local broadcast via radio waves or bluetooth mesh-nets when cell service goes down.
3. **Advanced RAG integration:** Incorporate real civil defense manuals for semantic queries.

---

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
