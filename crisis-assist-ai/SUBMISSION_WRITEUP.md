# CrisisAssist AI — Submission Write-Up

## Problem Statement
During severe crises and natural disasters (such as flash floods, landslides, or extreme heatwaves), individuals struggle to find reliable emergency information, understand critical safety steps, and access open shelter spaces. Traditional disaster applications provide only static checklists or contact forms and lack intelligent triage, safety validation, multilingual availability, and real-time shelter/telemetry integration. CrisisAssist AI fills this gap by utilizing a secure, cooperative multi-agent architecture to deliver trusted, real-time emergency guidance.

## Solution Architecture
```
    START [User Request]
             │
             ▼
     [Security Checkpoint] ─── (Suspected Injection) ───► [Security Event Block]
             │                                                     │
             ▼ (__DEFAULT__)                                        │
    [Orchestrator Agent]                                            │
       ├───► [Planner Agent] ───► MCP Server (Alerts)               │
       └───► [Worker Agent]  ───► MCP Server (Shelters/Contacts)    │
             │                                                     │
             ▼                                                     │
    [Human Dispatch Gate] ─── (Priority=CRITICAL) ──► [HITL Dialog] │
             │                                          │          │
             ▼ (__DEFAULT__)                            ▼          │
     [Evaluator Agent] ◄────────────────────────────────┘          │
             │                                                     │
             ▼                                                     │
    [Final Output Formatter] ◄─────────────────────────────────────┘
             │
             ▼
     [Formatted Guidance]
```

## Concepts Used

1. **ADK 2.0 Workflows:** The system is built around a graph-based state machine containing function nodes and directed routes defined in [agent.py](file:///c:/Users/Aishwarya%20Lala/Downloads/adk-workspace/crisis-assist-ai/app/agent.py#L236-L248).
2. **LlmAgents:** Four distinct specialized agents cooperate to analyze, gather resources, and evaluate the crisis guidance: `planner_agent`, `worker_agent`, `orchestrator_agent`, and `evaluator_agent` defined in [agent.py](file:///c:/Users/Aishwarya%20Lala/Downloads/adk-workspace/crisis-assist-ai/app/agent.py#L40-L113).
3. **AgentTool:** The `orchestrator_agent` delegates analysis and execution using `AgentTool(planner_agent)` and `AgentTool(worker_agent)` to manage multi-agent collaboration seamlessly.
4. **MCP Server:** A stdio-based Model Context Protocol server implemented in [mcp_server.py](file:///c:/Users/Aishwarya%20Lala/Downloads/adk-workspace/crisis-assist-ai/app/mcp_server.py) exposes live database tools: `get_disaster_alerts`, `search_shelters`, and `get_emergency_contacts`.
5. **Security Checkpoint:** The first gate in the workflow ([agent.py:L117-L177](file:///c:/Users/Aishwarya%20Lala/Downloads/adk-workspace/crisis-assist-ai/app/agent.py#L117-L177)) scrubs email and phone PII, blocks prompt injections, writes a structured JSON audit log to stdout, and restricts input length.
6. **Agents CLI:** Scaffolding, dependency syncing, and environment configurations are fully managed using the `agents-cli` tool.

## Security Design
* **PII Scrubbing:** Employs regex filters to redact phone numbers and email addresses to protect user privacy before queries reach LLM endpoints.
* **Injection Block:** Detects prompt override keywords (e.g., "ignore previous instructions") to route users directly to a static `security_event` block, preventing jailbreaking.
* **JSON Audit Log:** Structured telemetry data is printed on every invocation, tracking severity levels (INFO/WARNING/CRITICAL) for security audits.
* **Length Constraints:** Truncates inputs to 1000 characters to prevent buffer overflow attacks and abuse.

## MCP Server Design
* **`get_disaster_alerts`:** Queries live active warnings (e.g., Mumbai waterlogging) to determine danger levels.
* **`search_shelters`:** Checks shelter locations, capacity, occupancy, and coordinates.
* **`get_emergency_contacts`:** Retrieves verified emergency service hotlines for dispatch.

## HITL Flow (Human-in-the-Loop)
Emergency dispatch is a high-stakes, real-world action. If `planner_agent` classifies an incident priority as `CRITICAL`, the execution halts at `human_dispatch_gate` and yields a `RequestInput` block. The system resumes execution only when a human user explicitly confirms the dispatch by typing `approve`.

## Demo Walkthrough
1. **Critical Flood Input:** Send flood details for Mumbai. The system triggers the approval gate. Submit `approve` to receive emergency guidelines.
2. **Heatwave Triage:** Send weather inquiry for Delhi. The system automatically fetches shelters and warnings and presents guidelines without halting.
3. **Prompt Injection Attempt:** Test injection. The system blocks it instantly and denies access.

## Impact / Value Statement
CrisisAssist AI demonstrates how secure multi-agent systems can orchestrate emergency dispatching, gather real-time disaster information, and format actionable guidelines safely. It reduces emergency response latency while protecting user privacy and ensuring safe human oversight.
