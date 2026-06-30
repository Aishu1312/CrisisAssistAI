# Kaggle Capstone Writeup: CrisisAssist AI
### Track: Agents for Good
**Author:** ##Aishwarya Lala
**Workspace ID:** `CrisisAssistAI_Multi_Agent_Capstone_Project`

---

## Abstract
CrisisAssist AI is a trustworthy, multi-agent emergency response companion designed to assist citizens and responders during critical situations (fires, flooding, medical emergencies). By replacing standard unstructured chatbots with a rigid **Planner → Worker → Evaluator** architecture, the system guarantees factual correctness, strict resource verification, and explainable safety guardrails. In addition to text, the platform integrates speech-to-text (STT), text-to-speech (TTS), regional language translation (Hindi and Marathi), and real-time telemetry updates using simulated Model Context Protocol (MCP) server tools. The resulting platform demonstrates how advanced agent collaboration can directly impact and improve human safety.

---

## 1. Introduction: The Crisis Information Challenge
In high-stress situations, minutes save lives. However, current search engines and conversational AI systems present significant vulnerabilities:
1. **Hallucination Risk:** Generative models often hallucinate telephone numbers, medical dosages, or shelter addresses. In an emergency, this is unacceptable.
2. **Cognitive Load:** An user in a panic cannot parse long paragraphs. Text must be structured into immediate action points.
3. **Multilingual Access:** Many residents in developing areas search using mixed vernacular scripts (e.g., Romanized Hindi/Marathi like 'mujhe madad chahiye' or Devanagari script). Standard English-centric interfaces alienate those most in need.

### Why Agents?
Standard chatbots map inputs to responses via a single prompt. If the model makes a mistake, there is no safety net. A multi-agent approach breaks down the solution:
- **Triage** is handled by a specialized classification agent.
- **Planning** maps sequential logic before execution.
- **Worker Execution** interacts with local databases and external servers.
- **Validation** is executed by a separate Evaluator Agent checking safety thresholds.

---

## 2. Multi-Agent System Architecture & Collaboration

CrisisAssist AI utilizes a standardized message envelope protocol (Agent-to-Agent, or A2A) to coordinate communication. Each stage is tracked with a unique `trace_id` for auditing.

### 2.1 The Triage Agent (Priority Class)
The triage agent receives the user request and classifies the priority tier:
- **LOW:** Basic inquiries (e.g., preparation lists, first-aid tips).
- **MEDIUM:** Urgent but non-life-threatening (e.g., power grid status, local clinic addresses).
- **HIGH:** Imminent threats (e.g., storm approaches, nearby brushfire).
- **CRITICAL:** Immediate life-or-death situations (e.g., trapped user, severe injuries, drowning).

It uses a dual-layer approach: a high-speed keyword regex filter followed by semantic classification using the Gemini API.

### 2.2 The Planner Agent (Workflow Sequencing)
Rather than executing code immediately, the Planner Agent categorizes the emergency (Medical, Fire, Disaster, Rescue, or Support) and writes a checklist of tasks. For example, if a user reports a fire, the plan requires geocoding, querying nearby fire stations, verifying burn clinic operating status, and fetching smoke inhalation safety rules.

### 2.3 The Worker Agent (Tool Execution)
The Worker Agent is the executor. It interprets the plan steps and queries the tools:
- **Location Tool:** Parses area names and resolves coordinates.
- **Verification Tool:** Calculates reliability percentages based on database status and data freshness.
- **MCP Server simulation:** Queries live shelter capacity levels and disaster hazard warnings.
- **Summarizer:** Distills instructions into 4 bulleted checklists.

### 2.4 The Evaluator Agent (Safety Validation Loop)
The Evaluator reviews the Worker's recommendations. If the Worker suggests anything unsafe (e.g., advising elevators during a fire) or lists centers with poor verification scores (<75%), the Evaluator rejects the draft, sends detailed design feedback, and prompts the Worker to regenerate the output. The response is only released once the score exceeds `0.85`.

---

## 3. Advanced Features & Technical Implementation

### 3.1 Trustworthy Resource Verification System
To combat hallucinations, all emergency numbers and shelter details pass through a strict verification scoring algorithm:
$$\text{Verification Score} = 1.0 - \text{Status Penalty} - \text{Freshness Penalty} - \text{Phone Format Penalty} - \text{Source Authority Penalty}$$
Only centers scoring $\ge 75\%$ are displayed with verification badges (Green: Recent, Operational, Valid Phone Format).

### 3.2 Explainable AI (XAI)
To establish trust with users and rescuers, every response features a "Decision Explanation Panel" showing:
- Which language and location key was detected.
- The classified priority tier and its score.
- The active plan steps.
- The evaluator validation score.

### 3.3 A2A Message Schema
The core framework includes a robust message schema:
```python
class AgentMessage:
    def __init__(self, sender, receiver, message_type, payload, trace_id):
        self.message_id = str(uuid.uuid4())
        self.trace_id = trace_id
        self.sender = sender
        self.receiver = receiver
        self.message_type = message_type  # REQUEST, RESPONSE, PLAN, EVAL_RESULT
        self.payload = payload
        self.timestamp = datetime.datetime.now().isoformat()
```

---

## 4. Telemetry, Observability, and Performance

The application records run logs to a local JSONL database (`data/observability_logs.jsonl`). An observability class aggregates statistics:
- **Response Latency:** Sub-agent durations are tracked (Triage, Planning, Tool execution, and Evaluation) to identify bottlenecks.
- **Validation Score tracking:** Monitors safety check trends.
- **Category Ratios:** Visualizes high-frequency crisis categories.

---

## 5. Rationale & Innovation Factor

CrisisAssist AI is built on four core innovations:
1. **Fallback Resilience:** Unlike traditional LLM wrappers, the entire pipeline operates on offline rule-based heuristics when API networks fail, ensuring it works even during cellular grid outages.
2. **Evaluator Self-Correction:** The Planner → Worker → Evaluator loop mimics standard human triage operations.
3. **Multilingual Speech pipeline:** Users can speak in Hindi or Marathi, and the system translates, triages, and replies with synthesized regional speech.
4. **MCP Standard Conformity:** Using the Model Context Protocol ensures the agents can seamlessly interface with real municipal databases.

---

## 6. Future Work
1. **Distributed Databases:** Storing verified listings on decentralized nodes to prevent server outages.
2. **Broadband SMS Integration:** Compressing the A2A payloads for SMS protocols.

---

## Conclusion
CrisisAssist AI demonstrates that multi-agent systems are not just for productivity or automation—they are essential for building high-trust, safe, and explainable emergency responses. By prioritizing rigorous resource verification and safety validation over simple chat responses, it showcases the true potential of **Agents for Good**.
