# YouTube Demo Video Script — CrisisAssist AI (5 Minutes)

**Title:** CrisisAssist AI — Trustworthy Multi-Agent Emergency Companion  
**Presenter:** AI Agent Architect  
**Goal:** Showcase how multi-agent collaboration creates high-trust emergency responses.

---

## 🎬 0:00 - 0:30 | The Problem (Why Crisis Info is Broken)
- **Visual:** Split screen showing a person looking panicked in a storm, and a typical AI chatbot screen showing a wall of text with generic warning messages.
- **Audio/Narration:** 
  > "During natural disasters or medical emergencies, every second counts. But if you search the web, you're hit with a wall of text, outdated phone numbers, or flat-out hallucinations from standard chatbots. In a crisis, unverified advice isn't just unhelpful—it's dangerous. We need a system that doesn't just chat, but actively plan, executes, and validates every piece of advice before it reaches a user under stress. Welcome to CrisisAssist AI."

---

## 🏗️ 0:30 - 1:30 | Why Agents & System Architecture
- **Visual:** Show the `assets/architecture.png` diagram showing User → Main Controller → Triage Agent → Planner → Worker → Evaluator loop.
- **Audio/Narration:**
  > "CrisisAssist AI is built as a collaborative multi-agent system using Google ADK concepts. Instead of a single LLM call, we use a Planner-Worker-Evaluator pattern communicating via a standardized Agent-to-Agent protocol. First, the Priority Triage Agent assesses the severity tier from LOW to CRITICAL. Next, the Planner Agent constructs a customized execution checklist. The Worker Agent then runs local database geocoding, queries live disaster telemetry through a Model Context Protocol (MCP) server, and drafts actionable guidelines. Finally, the Evaluator Agent conducts a strict safety and grounding review, initiating a self-correcting refinement loop if safety thresholds are not met."

---

## 🔍 1:30 - 3:00 | Core Technical Innovations
- **Visual:** Show code snippets of the verification scoring algorithm in `tools/verification_tool.py` and the A2A message envelopes in `core/a2a_protocol.py`.
- **Audio/Narration:**
  > "To ensure absolute trustworthiness, we implemented a Resource Verification System. Every helpline, hospital, or shelter is graded on status, database freshness, and format validity. Only verified resources make it through. We also support regional language translation—supporting English, Hindi, and Marathi text or speech inputs. To ensure safety, our Evaluator Agent acts as an automated civil defense checker, filtering out hazardous instructions before final delivery, and logging every trace in our Observability telemetry database."

---

## 💻 3:00 - 4:20 | Live Demo Walkthrough
- **Visual:** Screen recording of the Streamlit interface. 
  1. Show setting up user details (Jane Doe, Type 1 Diabetes, Marathi preferred).
  2. Speak/Type: "Mujhe madad chahiye, rasta block ho gaya hai Pune me." (Or click mic recording).
  3. Show the response populating: Translation to Hindi, synthesized Audio play widget, green verification badges for local shelters, and the explainable decision dashboard.
  4. Switch to the Telemetry tab showing total runs, latencies, and category distribution progress bars.
- **Audio/Narration:**
  > "Let's see it in action. Here is the Streamlit Console. On the sidebar, the user has populated their profile—specifying language preferences and critical medical alerts. I'll enter a mixed Hindi query: 'Mujhe madad chahiye, rasta block ho gaya hai Pune me.' 
  > The system immediately translates the text, triages it as MEDIUM urgency, pulls Pune road blockage and shelter alerts from the MCP server, verifies the contacts, and returns the response in Hindi. I can play the speech aloud. Switching to our Observability Dashboard, we can inspect every sub-agent step duration and validation success rate in real time."

---

## 🌟 4:20 - 5:00 | Real-World Impact & Future Roadmap
- **Visual:** Cinematic footage of community emergency centers, followed by links to the public Kaggle submission and GitHub repository.
- **Audio/Narration:**
  > "CrisisAssist AI is ready for real-world deployment. By ensuring fallback offline heuristic capabilities, it operates even when cellular grids are down. In the future, we plan to integrate directly with civil dispatch systems and offline mesh-networks. CrisisAssist AI shows how multi-agent collaboration can save lives. 
  > All code, documentation, and Kaggle writeups are open-sourced on our GitHub. Check out the link below, and let's build agents for good!"
