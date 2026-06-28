# CrisisAssist AI — Trustworthy Multi-Agent Emergency Support Companion

CrisisAssist AI is an advanced, multi-agent AI system designed to act as a trustworthy and instantaneous emergency support companion. Built for the **Google 5-Day AI Agents Intensive Vibe Coding Course (Agents for Good track)**, this project leverages autonomous agents to intelligently process, route, and respond to critical situations, offering a lifeline when it's needed most.

---

## 1. Problem Statement

During emergencies, every second counts. Traditional emergency response systems often struggle with language barriers, imprecise location tracking, and high call volumes, leading to delayed assistance. Additionally, users under stress need immediate actionable guidance alongside verified contacts, which standard search engines or singular AI chatbots fail to provide safely and reliably.

## 2. Solution Overview

CrisisAssist AI solves this problem by using a robust **Multi-Agent Architecture**. It listens to emergency requests (via text or audio), instantly assesses priority, factors in user memory (like medical conditions and exact location), and outputs clear, actionable safety instructions alongside verified, hyper-local emergency resources. With built-in fallback mechanisms and translation support for 28 languages, it ensures immediate, inclusive, and fail-safe assistance.

![Home Page Screenshot](./assets/home_page_placeholder.png)

## 3. Multi-Agent Architecture

The system utilizes an Agent-to-Agent (A2A) protocol where specialized agents communicate to complete the emergency response lifecycle. The architecture prevents hallucinations in critical scenarios by using a tripartite review system.

![Agent Pipeline Screenshot](./assets/agent_pipeline_placeholder.png)

## 4. Planner Agent

The **Planner Agent** acts as the system's brain and first responder. 
- **Triage & Analysis:** Analyzes the incoming emergency request.
- **Categorization:** Classifies the situation (e.g., Fire Hazard, Medical Emergency, Personal Safety).
- **Prioritization:** Assigns a priority level (LOW, MEDIUM, HIGH, CRITICAL).
- **Execution Plan:** Formulates a step-by-step plan for the Worker Agent.

## 5. Worker Agent

The **Worker Agent** executes the plan constructed by the Planner.
- **Resource Fetching:** Uses tools to fetch verified local emergency resources based on coordinates.
- **Guidance Generation:** Generates actionable safety advice tailored to the specific emergency type.
- **Context Injection:** Integrates the user's specific medical memory and profile data to ensure instructions are safe for their conditions.

![Emergency Response Screenshot](./assets/emergency_response_placeholder.png)

## 6. Evaluator Agent

The **Evaluator Agent** provides a critical safety layer, preventing dangerous AI hallucinations.
- **Safety Review:** Reviews the output from the Worker Agent against safety guidelines.
- **Verification Score:** Grades the response to ensure accuracy.
- **Approval Flow:** If a response falls below a safety threshold, it halts the workflow and asks the user for explicit approval, or forces a safe fallback response.

## 7. Memory System

CrisisAssist AI maintains both short-term and long-term memory:
- **Current User Memory:** A persistent profile storing the user's name, default location, medical alerts/allergies, medical conditions, and emergency contacts.
- **Past Request Memory Context:** Session-based history that logs resolved emergencies for context in ongoing situations.

## 8. Context Engineering

The system uses advanced context engineering to ensure agents have precisely the right information at the right time. By injecting real-time location data (Browser API / IP fallback), language preferences, and historical memory directly into the prompt context, agents make highly contextualized, rapid decisions without requiring the user to restate crucial details.

## 9. Tools Used

- **Google Gemini API (Gemini 3.1 Pro):** Powers the core intelligence of the agents.
- **Streamlit:** Provides the interactive, highly responsive, and accessible UI.
- **Streamlit-JS-Eval:** Fetches precise browser geolocation.
- **Voice Tool (STT):** Transcribes audio emergency inputs.
- **Maps Tool / Location Tool:** Resolves coordinates to verified emergency services.
- **Translation Tool:** Provides dynamic support across 28 local languages.

![Verified Resources Screenshot](./assets/verified_resources_placeholder.png)

## 10. A2A Communication

Agents pass structured `AgentMessage` objects back and forth. The main controller orchestrates the state machine (Planning ➡️ Executing ➡️ Validating), ensuring strict adherence to the response pipeline. The history of this communication is fully auditable.

## 11. Security Features

- **No API Key Exposure:** All secrets are securely managed in `.env` and Streamlit secrets.
- **Hallucination Prevention:** The Evaluator Agent guarantees safety-critical advice is grounded.
- **Explainable AI:** Provides clear "Response Reasoning" to the user, explaining exactly how a priority was assessed and resources verified.
- **Agent Observability:** Detailed telemetry logs track latency, validation scores, and failure rates (safely tucked away in an expander for admin use).

![Observability Screenshot](./assets/observability_placeholder.png)

## 12. Deployment Instructions

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Aishu1312/CrisisAssistAI.git
   cd CrisisAssistAI
   ```
2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Configure Secrets:**
   Create a `.streamlit/secrets.toml` or `.env` file and add:
   ```env
   GEMINI_API_KEY="your_google_api_key_here"
   ```
4. **Run the App Locally:**
   ```bash
   streamlit run app.py
   ```
5. **Live Deployment:**
   The app is currently deployed via Streamlit Community Cloud: [CrisisAssist AI Live](https://jb9pe4aoyd9ssqpy3v6thk.streamlit.app/)

## 13. Future Scope

- **Integration with Physical IoT:** Automatically triggering local sirens or unlocking smart doors during detected fires.
- **Direct Dispatch:** Programmatic integration with real-world PSAP (Public Safety Answering Point) APIs.
- **Offline Mode:** Local SLMs (Small Language Models) for edge execution when internet connectivity drops.

---
*Built with ❤️ for the Agents for Good track.*
