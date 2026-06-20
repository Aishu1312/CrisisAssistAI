# CrisisAssist AI

## Problem Statement

During emergency situations (natural disasters, medical crises, fires, or rescue needs), citizens and responders face critical challenges:
- **Intelligent Reasoning:** Inability to dynamically triage situations and customize step-by-step guidance based on user needs.
- **Personalization:** Neglecting critical user medical history (e.g. insulin reliance, asthma, allergies, or mobility restrictions) and default home location coordinates.
- **Adaptive Assistance:** Lack of support for regional dialects, voice queries, or low-bandwidth offline environments.
- **Explainability:** Delivering outputs without validating resource freshness or explaining why a decision was reached, causing trust deficits.

## Solution Overview

CrisisAssist AI is an intelligent, high-trust emergency response companion powered by collaborative multi-agent workflows, strict resource verification, explainable triage logic, and regional language speech pipelines to deliver reliable, actionable guidance during critical situations.

Unlike static search engines or simple chatbots, CrisisAssist AI processes queries in structured phases to prioritize situations, verify physical locations and numbers, and generate highly summarized, life-saving advice.

## Key Features

- **Complete 28-Language UI Localization:** The entire application interface (headers, forms, buttons, timeline activity, and observability stats) immediately switches into any of the 28 supported languages upon selection.
- **Language-Aware AI Response Generation:** Sub-agents recognize the communication language and output all guidelines and decision explanations in that target language.
- **Integrated Voice Input & Synthesized Playback:** Supports speech-to-text voice uploads and synthesizes text-to-speech audio outputs for hands-free listening.
- **Long-Term User Memory Profile:** Persists name, default coordinates, and critical medical alerts (allergies, diabetes, mobility restrictions) in a local user database to automatically customize guidance.
- **Consolidated Resource Tool:** Resolves coordinates, filters municipal contacts for major Indian cities, and validates contact numbers and freshness.
- **Observability Telemetry Dashboard:** Full telemetry logging (latencies, token counts, and validation scores) displayed on an interactive dashboard.

## Multi-Agent System

CrisisAssist AI orchestrates a collaborative pipeline of specialized sub-agents communicating via standard JSON message envelopes (Agent-to-Agent, or A2A):
1. **Priority & Triage Agent:** Classifies user query urgency levels (LOW, MEDIUM, HIGH, CRITICAL) using high-speed keyword checks and semantic categorization.
2. **Planner Agent:** Formulates a step-by-step action plan depending on the crisis type (Medical, Fire, Natural Disaster, Search & Rescue, General Support).
3. **Worker Agent:** Performs resource database querying, simulated Model Context Protocol (MCP) server lookup, and compiles the safety guidelines draft.
4. **Evaluator Agent:** Performs safety checks (e.g. confirming elevator warnings during fires) and rates the draft. If the safety score is under 85%, it rejects the response and requests refinements.

## Technologies Used

- **Frontend & App Interface:** Streamlit (Custom HSL/CSS premium layout, dark mode, glassmorphism card designs)
- **Agent Engine:** Google Gemini Developer APIs (gemini-2.5-flash model)
- **Audio & Voice:** gTTS (Google Text-to-Speech)
- **Data & Logs:** JSON & JSONL local file-based database for user profiles and telemetry tracking.
- **Source Control:** Git & GitHub

## Future Scope

- **Offline Sync & Mesh Networks:** Implement local peer-to-peer data syncing for complete network blackouts.
- **Real-Time Municipal Integration:** Connect directly to active police, fire department, and hospital dispatch systems via secure APIs.
- **Advanced Diagnostic Input:** Attach images of injuries or damage for automated visual triage using Gemini Multimodal capabilities.
- **Automated Alert Broadcasts:** Geo-fenced push notifications to alert residents in high-risk areas.
