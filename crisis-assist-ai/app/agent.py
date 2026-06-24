import os
import re
import datetime
from typing import List, Optional, Any
from pydantic import BaseModel, Field

from google.adk.agents import Agent
from google.adk.apps import App, ResumabilityConfig
from google.adk.models import Gemini
from google.adk.tools import AgentTool
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from google.adk.workflow import Workflow, START
from google.adk.agents.context import Context
from google.adk.events.event import Event
from google.adk.events.request_input import RequestInput
from google.genai import types
from mcp import StdioServerParameters

from .config import config

# --- 1. Schemas (Pydantic Models) ---

class CrisisAnalysis(BaseModel):
    category: str = Field(description="Emergency category (e.g. medical, fire, natural_disaster, personal_safety, other)")
    priority: str = Field(description="Priority level: LOW, MEDIUM, HIGH, or CRITICAL")
    urgency_reason: str = Field(description="Short reason explaining the priority classification")
    required_services: List[str] = Field(description="Emergency services required (e.g. ambulance, police, fire, rescue)")

class ReliefResources(BaseModel):
    verified_contacts: List[str] = Field(description="Verified contact phone numbers or emergency agency names")
    shelter_options: List[str] = Field(description="Safe locations, shelters, or evacuation centers")
    safety_steps: List[str] = Field(description="Step-by-step immediate safety guidelines for the user")

class CompiledReport(BaseModel):
    priority: str = Field(description="Priority level: LOW, MEDIUM, HIGH, or CRITICAL")
    category: str = Field(description="Emergency category")
    safety_steps: List[str] = Field(description="Step-by-step safety actions")
    verified_contacts: List[str] = Field(description="Emergency contacts")
    shelter_options: List[str] = Field(description="Shelter options")
    reasoning: str = Field(description="Orchestrator compilation reasoning")

class FinalCrisisGuidance(BaseModel):
    priority: str = Field(description="Final priority classification: LOW, MEDIUM, HIGH, or CRITICAL")
    category: str = Field(description="The classified category of the crisis")
    immediate_safety_instructions: str = Field(description="Action-oriented, bold safety instructions for display")
    verified_resources: List[str] = Field(description="Verified emergency resources, contacts, and locations")
    agent_reasoning: str = Field(description="Trace explanation of decisions made during compilation and review")

# --- 2. MCP Server Configuration ---

mcp_toolset = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command="uv",
            args=["run", "python", "-m", "app.mcp_server"],
            cwd=os.path.abspath(os.path.dirname(os.path.dirname(__file__))),
        ),
    )
)

# --- 3. Dynamic Instruction Providers for Agents ---

def get_planner_instruction(ctx: Any) -> str:
    lang = ctx.state.get("language", "English")
    profile = ctx.state.get("user_profile", {})
    return (
        "You are the Crisis Planner Agent. Your job is to analyze the emergency description and categorize it.\n"
        f"The communication language is {lang}. You MUST generate the urgency reason and any explanation in {lang}.\n"
        f"Context: {{'language': '{lang}', 'user_profile': {profile}}}\n"
        "Determine the category, priority (LOW, MEDIUM, HIGH, or CRITICAL), urgency reason, and required services.\n"
        "Triage examples:\n"
        "- 'I need help, I am feeling unsafe and need emergency assistance' -> HIGH\n"
        "- 'I have a medical emergency and need immediate help' -> CRITICAL\n"
        "Use the get_disaster_alerts tool to check for active emergency or disaster hazard alerts for the location mentioned by the user."
    )

def get_worker_instruction(ctx: Any) -> str:
    lang = ctx.state.get("language", "English")
    profile = ctx.state.get("user_profile", {})
    return (
        "You are the Crisis Worker Agent. Your job is to generate immediate, actionable safety steps\n"
        f"and list appropriate emergency contacts and shelter options based on the crisis analysis.\n"
        f"The communication language is {lang}. You MUST generate the safety steps, shelter names, and descriptions in {lang}.\n"
        f"Context: {{'language': '{lang}', 'user_profile': {profile}}}\n"
        "Use the search_shelters tool to find safe shelter options, and the get_emergency_contacts tool\n"
        "to retrieve verified hotline numbers for the location mentioned by the user.\n"
        "Format each contact and shelter option as: 'Name | Address | Phone' in the target language."
    )

def get_orchestrator_instruction(ctx: Any) -> str:
    lang = ctx.state.get("language", "English")
    profile = ctx.state.get("user_profile", {})
    return (
        "You are the Crisis Response Orchestrator. You receive a sanitized crisis situation from the user.\n"
        f"The communication language is {lang}. You MUST compile and generate the report and reasoning in {lang}.\n"
        f"Context: {{'language': '{lang}', 'user_profile': {profile}}}\n"
        "1. Call the planner_agent tool to analyze and prioritize the situation.\n"
        "2. Call the worker_agent tool to compile safety steps and local relief resources.\n"
        "3. Synthesize the findings into a compiled report. Do not make up info; rely solely on the sub-agent responses."
    )

def get_evaluator_instruction(ctx: Any) -> str:
    lang = ctx.state.get("language", "English")
    profile = ctx.state.get("user_profile", {})
    return (
        "You are the Crisis Evaluator Agent. Your job is to review the compiled guidance for safety, accuracy,\n"
        "and completeness. Ensure the recommendations are safe, practical, free of hallucinations, and format\n"
        "the response clearly for the user.\n"
        f"The communication language is {lang}. You MUST generate and format the entire response in {lang}.\n"
        f"Context: {{'language': '{lang}', 'user_profile': {profile}}}\n"
        "Ensure all safety instructions, resource names/descriptions/addresses, and trace reasoning explanation are written completely in the target language. Do not mix languages.\n"
        "Each resource in the verified_resources list MUST be strictly formatted as: 'Name | Address | Phone' in the target language. Do not change this pipe-separated format.\n"
        "Return the final structured guidance containing priority (LOW, MEDIUM, HIGH, or CRITICAL), category, immediate safety instructions, verified resources list, and your trace reasoning explanation."
    )

# --- 4. Specialized LlmAgents ---

# Planner Agent
planner_agent = Agent(
    name="planner_agent",
    model=Gemini(
        model=config.model,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=get_planner_instruction,
    tools=[mcp_toolset],
    output_schema=CrisisAnalysis,
    description="Analyzes the crisis query and returns structured classification and priority."
)

# Worker Agent
worker_agent = Agent(
    name="worker_agent",
    model=Gemini(
        model=config.model,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=get_worker_instruction,
    tools=[mcp_toolset],
    output_schema=ReliefResources,
    description="Gathers verified resources, shelter options, and immediate safety steps."
)

# Orchestrator Agent (uses AgentTools to delegate)
orchestrator_agent = Agent(
    name="orchestrator_agent",
    model=Gemini(
        model=config.model,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=get_orchestrator_instruction,
    tools=[AgentTool(planner_agent), AgentTool(worker_agent)],
    output_schema=CompiledReport,
    description="Orchestrates planning and execution for crisis requests."
)

# Evaluator Agent (reviews final response)
evaluator_agent = Agent(
    name="evaluator_agent",
    model=Gemini(
        model=config.model,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=get_evaluator_instruction,
    output_schema=FinalCrisisGuidance,
    description="Evaluates the final guidance to ensure safety and accuracy before presentation."
)

# --- 4. Workflow Function Nodes ---

def security_checkpoint(ctx: Context, node_input: types.Content) -> Event:
    """PII Scrubbing and Prompt Injection check."""
    # Resolve input text
    text = ""
    if node_input and node_input.parts:
        text = "".join([part.text for part in node_input.parts if part.text])
        
    # PII scrubbing using regex (emails and phone numbers)
    clean_text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL_REDACTED]', text)
    clean_text = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE_REDACTED]', clean_text)
    
    # Prompt injection check
    injection_keywords = ["ignore previous instructions", "system prompt", "override instructions", "you are now a"]
    is_injection = any(kw in clean_text.lower() for kw in injection_keywords)
    
    # Domain-specific rule: length limit of 1000 characters to prevent overflow/abuse
    if len(clean_text) > 1000:
        clean_text = clean_text[:1000]
        
    severity = "INFO"
    if is_injection:
        severity = "CRITICAL"
    elif "[PHONE_REDACTED]" in clean_text or "[EMAIL_REDACTED]" in clean_text:
        severity = "WARNING"
        
    audit_log = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "severity": severity,
        "pii_detected": severity == "WARNING",
        "injection_detected": is_injection,
        "input_length": len(text)
    }
    print(f"[AUDIT LOG] {audit_log}")
    
    if is_injection:
        return Event(
            output="Security Alert: Suspected prompt injection detected.",
            route="security_alert",
            state={"audit_log": audit_log, "sanitized_query": clean_text}
        )
        
    return Event(
        output=clean_text,
        state={"audit_log": audit_log, "sanitized_query": clean_text}
    )

def security_event(ctx: Context, node_input: str) -> Event:
    """Halts execution and returns a security warning."""
    return Event(
        output={
            "priority": "CRITICAL",
            "category": "Security Violation",
            "immediate_safety_instructions": "⚠ Access Denied: A security policy violation has occurred. Please refrain from using system override keywords.",
            "verified_resources": [],
            "agent_reasoning": "Execution halted at security checkpoint due to suspected prompt injection attempt."
        }
    )

async def human_dispatch_gate(ctx: Context, node_input: Any) -> Event:
    """HITL Approval step for CRITICAL emergencies."""
    # Check if the input is a CompiledReport or dict representing CompiledReport
    report = None
    if isinstance(node_input, CompiledReport):
        report = node_input
    elif isinstance(node_input, dict) and "priority" in node_input:
        try:
            report = CompiledReport(**node_input)
        except Exception:
            pass
            
    if not report:
        yield Event(output=node_input)
        return
        
    priority = report.priority
    
    if priority == "CRITICAL":
        if not ctx.resume_inputs or "dispatch_confirmation" not in ctx.resume_inputs:
            yield RequestInput(
                interrupt_id="dispatch_confirmation",
                message="🚨 EMERGENCY: Critical situation detected. Do you approve emergency dispatch? Type 'approve' to confirm."
            )
            return
        
        user_response = ctx.resume_inputs["dispatch_confirmation"]
        if isinstance(user_response, dict):
            user_response = user_response.get("dispatch_confirmation", next(iter(user_response.values()), ""))
        if not isinstance(user_response, str):
            user_response = str(user_response)
            
        dispatch_approved = (user_response.strip().lower() == "approve")
        # Update orchestrator output reasoning to indicate dispatch status
        report.reasoning += f" | Dispatch Approval Status: {dispatch_approved}"
            
    yield Event(output=report)

def final_output(node_input: Any) -> Event:
    """Nicely formats the result for the ADK Web UI."""
    data = node_input
    if hasattr(node_input, "model_dump"):
        data = node_input.model_dump()
    elif hasattr(node_input, "dict"):
        data = node_input.dict()
        
    if isinstance(data, dict):
        text_output = f"### Crisis Response Guidance ({data.get('priority', 'STANDARD')})\n\n"
        text_output += f"**Immediate Safety Instructions:**\n{data.get('immediate_safety_instructions', 'None')}\n\n"
        text_output += "**Verified Resources:**\n"
        resources = data.get('verified_resources', [])
        if resources:
            for r in resources:
                text_output += f"- {r}\n"
        else:
            text_output += "- No specific resource contacts returned.\n"
        text_output += f"\n**Agent Trace Reasoning:**\n{data.get('agent_reasoning', '')}"
    else:
        text_output = str(node_input)
        
    return Event(
        output=data,
        content=types.Content(role='model', parts=[types.Part.from_text(text=text_output)])
    )

# --- 5. Workflow Definition ---

app_workflow = Workflow(
    name="crisis_assist_workflow",
    edges=[
        (START, security_checkpoint),
        (security_checkpoint, {"security_alert": security_event, "__DEFAULT__": orchestrator_agent}),
        (orchestrator_agent, human_dispatch_gate),
        (human_dispatch_gate, evaluator_agent),
        (security_event, final_output),
        (evaluator_agent, final_output)
    ],
    rerun_on_resume=True
)

app = App(
    name="app",
    root_agent=app_workflow,
    resumability_config=ResumabilityConfig(is_resumable=True)
)
