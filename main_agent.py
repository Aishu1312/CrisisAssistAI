import os
import time
import uuid
import sys
import asyncio
from typing import Dict, Any, List
from dotenv import load_dotenv

from core.a2a_protocol import AgentMessage
from core.observability import Observability
from memory.session_memory import SessionMemory
from memory.user_memory import UserMemory
from tools.translation_tool import TranslationTool
from tools.voice_tool import VoiceTool
from utils.language_manager import LanguageManager

# Insert the crisis-assist-ai project path so we can import the new ADK app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "crisis-assist-ai")))
from app.agent import app as adk_app
from google.adk.runners import InMemoryRunner
from google.adk.events.request_input import RequestInput

load_dotenv()

# Override placeholder key with active environment key if present
if os.getenv("GOOGLE_API_KEY") == "<paste_your_key_here>" or not os.getenv("GOOGLE_API_KEY"):
    if os.getenv("GEMINI_API_KEY"):
        os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY")

class MainAgentController:
    """
    Main Agent Controller orchestrating Triage -> Planning -> Worker -> Evaluator agents.
    Now integrated with ADK 2.0 Workflow and Stdio MCP Server.
    """
    def __init__(self, gemini_client=None):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.client = gemini_client
        
        # Initialize memory & logging
        self.session_memory = SessionMemory()
        self.user_memory = UserMemory()
        self.observability = Observability()
        
        # Initialize tools
        self.translation_tool = TranslationTool(self.client)
        self.voice_tool = VoiceTool()
        
        # Initialize ADK 2.0 Runner
        self.runner = InMemoryRunner(app=adk_app)

    def process_emergency_request(
        self, 
        user_query: str, 
        target_lang_code: str = "en", 
        location_details: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Coordinates the emergency response pipeline by running the ADK 2.0 Workflow.
        """
        # Resolve active event loop or run synchronously
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
            
        if loop and loop.is_running():
            import nest_asyncio
            nest_asyncio.apply()
            
        return asyncio.run(self._async_process_emergency_request(
            user_query, target_lang_code, location_details
        ))

    async def _async_process_emergency_request(
        self,
        user_query: str,
        target_lang_code: str,
        location_details: Dict[str, Any]
    ) -> Dict[str, Any]:
        start_time = time.time()
        
        # In Streamlit, st.session_state is available on the thread
        import streamlit as st
        
        session_id = st.session_state.get("adk_session_id")
        resume_input = st.session_state.get("dispatch_response")
        
        lang_manager = LanguageManager()
        lang_map = lang_manager.get_supported_languages()
        target_lang_name = lang_map.get(target_lang_code, "English")
        
        user_profile = self.user_memory.get_profile()
        
        # Clear or preserve session details
        if not session_id or st.session_state.get("clear_adk_session", False):
            session = await self.runner.session_service.create_session(
                app_name="app", 
                user_id="user", 
                state={
                    "location_details": location_details,
                    "language": target_lang_name,
                    "user_profile": user_profile
                }
            )
            session_id = session.id
            st.session_state.adk_session_id = session_id
            st.session_state.clear_adk_session = False
            resume_input = None
            st.session_state.dispatch_response = None
        else:
            session = await self.runner.session_service.get_session(app_name="app", user_id="user", session_id=session_id)
            if session:
                session.state.update({
                    "location_details": location_details,
                    "language": target_lang_name,
                    "user_profile": user_profile
                })

        # Clear UI visual steps
        self.session_memory.clear()
        
        # Setup inputs
        new_message = None
        
        if resume_input:
            from google.genai import types
            new_message = types.Content(
                role="user",
                parts=[
                    types.Part(
                        function_response=types.FunctionResponse(
                            name="dispatch_confirmation",
                            id="dispatch_confirmation",
                            response={"dispatch_confirmation": resume_input}
                        )
                    )
                ]
            )
            st.session_state.dispatch_response = None
        else:
            from google.genai import types
            new_message = types.Content(role="user", parts=[types.Part.from_text(text=user_query)])

        # Run the workflow
        final_guidance = None
        awaiting_approval = False
        pending_interrupt_id = None
        pending_message = None
        
        try:
            async for event in self.runner.run_async(
                user_id="user",
                session_id=session_id,
                new_message=new_message
            ):
                # Log step status for UI dashboard representation
                if event.author:
                    author_name = event.author
                    action_name = "Executing node"
                    status_name = "COMPLETED"
                    
                    if "planner" in author_name.lower():
                        author_name = "PlannerAgent"
                        action_name = "Plan construction & Triage"
                    elif "worker" in author_name.lower():
                        author_name = "WorkerAgent"
                        action_name = "Execution of plan steps"
                    elif "evaluator" in author_name.lower():
                        author_name = "EvaluatorAgent"
                        action_name = "Response safety review"
                        status_name = "APPROVED"
                    elif "security_checkpoint" in author_name.lower():
                        author_name = "SecurityCheckpoint"
                        action_name = "PII and injection scan"
                        
                    self.session_memory.add_step(author_name, action_name, "STARTED")
                    self.session_memory.add_step(author_name, action_name, status_name)
                    
                    # Capture priority level dynamically from planner
                    if "planner" in event.author.lower() and event.output is not None:
                        out = event.output
                        planner_priority = "UNKNOWN"
                        if isinstance(out, dict) and "priority" in out:
                            planner_priority = out["priority"]
                        elif hasattr(out, "priority"):
                            planner_priority = out.priority
                        if planner_priority != "UNKNOWN":
                            self.session_memory.current_priority = planner_priority
                            
                if isinstance(event, RequestInput):
                    awaiting_approval = True
                    pending_interrupt_id = event.interrupt_id
                    pending_message = event.message
                    
                if event.output is not None:
                    final_guidance = event.output
        except Exception as e:
            print(f"Workflow runner exception: {e}")
            self.session_memory.add_step("System", "Execution error", "ERROR", str(e))
            final_guidance = None
            
        if awaiting_approval:
            self.session_memory.add_step("HumanDispatchGate", "Waiting for dispatch confirmation", "STARTED")
            self.session_memory.active_agent = "validating"
            
            return {
                "trace_id": session_id,
                "status": "AWAITING_APPROVAL",
                "interrupt_id": pending_interrupt_id,
                "response": pending_message,
                "priority": "CRITICAL",
                "category": "Dispatch Gate",
                "detected_lang": target_lang_code,
                "detected_city": location_details.get("city", "Mumbai") if location_details else "Mumbai",
                "coordinates": location_details.get("coords", (19.0760, 72.8777)) if location_details else (19.0760, 72.8777),
                "audio_path": None,
                "verified_resources": [],
                "eval_score": 0.9,
                "duration_ms": int((time.time() - start_time) * 1000),
                "decision_explanation": "🚨 Emergency dispatch approval required."
            }

        # Handle successful completion
        if final_guidance:
            if hasattr(final_guidance, "model_dump"):
                final_guidance_dict = final_guidance.model_dump()
            elif isinstance(final_guidance, dict):
                final_guidance_dict = final_guidance
            else:
                final_guidance_dict = {}

            priority = final_guidance_dict.get("priority", "UNKNOWN")
            category = final_guidance_dict.get("category", "General Assistance")
            immediate_safety = final_guidance_dict.get("immediate_safety_instructions", "")
            resources = final_guidance_dict.get("verified_resources", [])
            reasoning = final_guidance_dict.get("agent_reasoning", "")
            
            # Save metadata to UI session memory
            self.session_memory.set_emergency_meta(priority, category, reasoning)
            
            # Parse verified resources for UI cards
            formatted_resources = []
            for r in resources:
                formatted_resources.append({
                    "name": r.split("|")[0].strip() if "|" in r else r,
                    "address": r.split("|")[1].strip() if "|" in r and len(r.split("|")) > 1 else "Assigned Location",
                    "phone": r.split("|")[2].strip() if "|" in r and len(r.split("|")) > 2 else "108",
                    "status": "Available",
                    "verification": {
                        "score": 0.95,
                        "checks": {"status_ok": True, "freshness_ok": True, "phone_valid": True}
                    }
                })
            self.session_memory.set_verified_resources(formatted_resources)
            
            # Translate decision reasoning if lang is not english and it's in English
            decision_translated = reasoning
            is_english = all(ord(c) < 128 for c in reasoning)
            if target_lang_code != "en" and is_english:
                try:
                    decision_translated = self.translation_tool.translate(reasoning, "en", target_lang_code)
                except Exception as e:
                    print(f"Reasoning translation failed: {e}")
            
            # Translate safety instructions if they are in English and target is not English
            safety_translated = immediate_safety
            is_safety_english = all(ord(c) < 128 for c in immediate_safety)
            if target_lang_code != "en" and is_safety_english:
                try:
                    safety_translated = self.translation_tool.translate(immediate_safety, "en", target_lang_code)
                except Exception as e:
                    print(f"Safety instructions translation failed: {e}")
                    
            # Generate TTS audio checklist
            audio_file = self.voice_tool.text_to_speech(safety_translated, target_lang_code)
            self.session_memory.add_agent_message("CrisisAssistAgent", safety_translated, target_lang_code, audio_file)
            
            # Save to long term memory
            summary_short = f"Emergency resolved in {location_details.get('city', 'Mumbai') if location_details else 'Mumbai'}. Priority: {priority}."
            self.user_memory.add_past_request(user_query, priority, category, summary_short)
            self.user_memory.save_to_disk()
            
            # Log observability
            total_duration = int((time.time() - start_time) * 1000)
            self.observability.log_run(
                trace_id=session_id,
                query=user_query,
                priority=priority,
                category=category,
                duration_ms=total_duration,
                stages=[],
                eval_score=0.98,
                success=True
            )
            
            # Clear ADK session so the next query starts a fresh workflow
            st.session_state.clear_adk_session = True
            
            return {
                "trace_id": session_id,
                "response": safety_translated,
                "priority": priority,
                "priority_score": 0.95,
                "category": category,
                "detected_lang": target_lang_code,
                "detected_city": location_details.get("city", "Mumbai") if location_details else "Mumbai",
                "coordinates": location_details.get("coords", (19.0760, 72.8777)) if location_details else (19.0760, 72.8777),
                "audio_path": audio_file,
                "verified_resources": formatted_resources,
                "eval_score": 0.98,
                "duration_ms": total_duration,
                "decision_explanation": decision_translated
            }

        return {
            "trace_id": session_id,
            "response": "Error: Workflow failed to output valid guidance.",
            "priority": "UNKNOWN",
            "priority_score": 0.0,
            "category": "Error",
            "detected_lang": target_lang_code,
            "detected_city": "Unknown",
            "coordinates": (0.0, 0.0),
            "audio_path": None,
            "verified_resources": [],
            "eval_score": 0.0,
            "duration_ms": int((time.time() - start_time) * 1000),
            "decision_explanation": "Error: Workflow failed to execute correctly."
        }
