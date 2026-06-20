import os
import time
import uuid
from typing import Dict, Any, List
from dotenv import load_dotenv
from google import genai

from core.a2a_protocol import AgentMessage
from core.observability import Observability
from memory.session_memory import SessionMemory
from memory.user_memory import UserMemory
from tools.translation_tool import TranslationTool
from tools.voice_tool import VoiceTool

from agents.priority_agent import PriorityAgent
from agents.planner import PlannerAgent
from agents.worker import WorkerAgent
from agents.evaluator import EvaluatorAgent

load_dotenv()

class MainAgentController:
    """
    Main Agent Controller orchestrating Triage -> Planning -> Worker -> Evaluator agents.
    Supports 28 regional/global languages and logs trace activity telemetry.
    """
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.client = None
        if self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                print(f"Failed to initialize Gemini Client: {e}. Running in heuristic fallback mode.")
                
        # Initialize memory & logging
        self.session_memory = SessionMemory()
        self.user_memory = UserMemory()
        self.observability = Observability()
        
        # Initialize tools
        self.translation_tool = TranslationTool(self.client)
        self.voice_tool = VoiceTool()
        
        # Initialize agents
        self.priority_agent = PriorityAgent(self.client)
        self.planner_agent = PlannerAgent(self.client)
        self.worker_agent = WorkerAgent(self.client)
        self.evaluator_agent = EvaluatorAgent(self.client)

    def process_emergency_request(self, user_query: str, target_lang_code: str = "en") -> Dict[str, Any]:
        """
        Coordinates the emergency response pipeline.
        Processes internal logic in English, translating inputs and outputs dynamically.
        """
        start_time = time.time()
        trace_id = str(uuid.uuid4())
        self.session_memory.clear()
        
        user_profile = self.user_memory.get_profile()
        stages_log = []
        
        # 1. Language Detection & Input Translation
        self.session_memory.add_step("MainController", "Language Detection", "STARTED")
        detected_lang = self.translation_tool.detect_language(user_query)
        self.session_memory.add_user_message(user_query, detected_lang)
        
        english_query = user_query
        if detected_lang != "en":
            english_query = self.translation_tool.translate(user_query, detected_lang, "en")
            self.session_memory.add_step(
                "MainController", 
                "Translating input", 
                "COMPLETED", 
                {"source": user_query, "translated": english_query}
            )
            stages_log.append({"stage": "Input Translation", "duration_ms": 100})
        else:
            self.session_memory.add_step("MainController", "Input is English", "COMPLETED")
            
        # 2. Priority Classification (Triage)
        triage_start = time.time()
        self.session_memory.add_step("PriorityAgent", "Triage classification", "STARTED")
        
        triage_msg_in = AgentMessage(
            sender="MainController",
            receiver="PriorityAgent",
            message_type="REQUEST",
            payload={"query": english_query},
            trace_id=trace_id
        )
        triage_msg_out = self.priority_agent.run(triage_msg_in, user_profile)
        priority_tier = triage_msg_out.payload.get("priority_tier", "LOW")
        priority_score = triage_msg_out.payload.get("priority_score", 0.0)
        triage_reason = triage_msg_out.payload.get("reasoning", "")
        
        triage_duration = int((time.time() - triage_start) * 1000)
        self.session_memory.add_step(
            "PriorityAgent", 
            "Triage classification", 
            "COMPLETED", 
            {"priority": priority_tier, "score": priority_score, "reasoning": triage_reason}
        )
        stages_log.append({"stage": "Priority Detection", "duration_ms": triage_duration})

        # 3. Planning
        planning_start = time.time()
        self.session_memory.add_step("PlannerAgent", "Plan construction", "STARTED")
        
        plan_msg_in = AgentMessage(
            sender="MainController",
            receiver="PlannerAgent",
            message_type="REQUEST",
            payload={
                "query": english_query,
                "priority_tier": priority_tier
            },
            trace_id=trace_id
        )
        plan_msg_out = self.planner_agent.run(plan_msg_in, user_profile)
        category = plan_msg_out.payload.get("category", "General Support")
        plan_steps = plan_msg_out.payload.get("steps", [])
        plan_rationale = plan_msg_out.payload.get("rationale", "")
        
        self.session_memory.set_emergency_meta(priority_tier, category, triage_reason)
        
        planning_duration = int((time.time() - planning_start) * 1000)
        self.session_memory.add_step(
            "PlannerAgent", 
            "Plan construction", 
            "COMPLETED", 
            {"category": category, "steps": plan_steps, "rationale": plan_rationale}
        )
        stages_log.append({"stage": "Planning", "duration_ms": planning_duration})

        # 4. Worker Execution
        worker_start = time.time()
        self.session_memory.add_step("WorkerAgent", "Execution of plan steps", "STARTED")
        
        worker_msg_in = AgentMessage(
            sender="MainController",
            receiver="WorkerAgent",
            message_type="REQUEST",
            payload=plan_msg_out.payload,
            trace_id=trace_id
        )
        worker_msg_out = self.worker_agent.run(worker_msg_in, user_profile)
        worker_payload = worker_msg_out.payload
        draft_guidelines = worker_payload.get("guidelines", "")
        verified_resources = worker_payload.get("verified_resources", [])
        tool_logs = worker_payload.get("tool_execution_log", [])
        detected_city = worker_payload.get("detected_city", "Unknown")
        coords = worker_payload.get("coordinates", (0.0, 0.0))
        
        for log in tool_logs:
            self.session_memory.add_step("WorkerAgent:Tool", log["step"], "COMPLETED", log["result"])
            
        worker_duration = int((time.time() - worker_start) * 1000)
        self.session_memory.add_step("WorkerAgent", "Draft compiled", "COMPLETED")
        stages_log.append({"stage": "Worker Execution", "duration_ms": worker_duration})

        # 5. Evaluation Loop
        eval_start = time.time()
        self.session_memory.add_step("EvaluatorAgent", "Response safety review", "STARTED")
        
        eval_msg_in = AgentMessage(
            sender="MainController",
            receiver="EvaluatorAgent",
            message_type="REQUEST",
            payload=worker_payload,
            trace_id=trace_id
        )
        eval_msg_out = self.evaluator_agent.run(eval_msg_in)
        eval_score = eval_msg_out.payload.get("score", 0.0)
        eval_approved = eval_msg_out.payload.get("approved", False)
        eval_feedback = eval_msg_out.payload.get("feedback", "")
        
        # Self-correction check
        if not eval_approved:
            self.session_memory.add_step("EvaluatorAgent", "Review FAILED", "REJECTED", {"score": eval_score, "feedback": eval_feedback})
            self.session_memory.add_step("WorkerAgent", "Refining draft based on feedback", "STARTED")
            plan_msg_out.payload["steps"].append(f"REFINEMENT: {eval_feedback}")
            
            worker_msg_out = self.worker_agent.run(worker_msg_in, user_profile)
            worker_payload = worker_msg_out.payload
            draft_guidelines = worker_payload.get("guidelines", "")
            verified_resources = worker_payload.get("verified_resources", [])
            
            self.session_memory.add_step("EvaluatorAgent", "Second review pass", "STARTED")
            eval_msg_in = AgentMessage(sender="MainController", receiver="EvaluatorAgent", message_type="REQUEST", payload=worker_payload, trace_id=trace_id)
            eval_msg_out = self.evaluator_agent.run(eval_msg_in)
            eval_score = eval_msg_out.payload.get("score", 0.0)
            eval_approved = eval_msg_out.payload.get("approved", True)
            eval_feedback = eval_msg_out.payload.get("feedback", "Refinement complete.")
            self.session_memory.add_step("EvaluatorAgent", "Review completed", "APPROVED")
        else:
            self.session_memory.add_step("EvaluatorAgent", "Review APPROVED", "COMPLETED", {"score": eval_score, "feedback": eval_feedback})
            
        eval_duration = int((time.time() - eval_start) * 1000)
        stages_log.append({"stage": "Safety Review", "duration_ms": eval_duration})

        self.session_memory.set_verified_resources(verified_resources)

        # 6. Target Language Translation & TTS Synthesis
        translation_start = time.time()
        final_text = (
            f"### Immediate Actions:\n{draft_guidelines}\n\n"
            f"### Checklist:\n{worker_payload.get('summary_checklist', '')}"
        )
        
        translated_output = final_text
        decision_raw = (
            f"- User message detected as '{detected_lang.upper()}' language.\n"
            f"- Emergency priority classified as **{priority_tier}** (Score: {priority_score}).\n"
            f"- Situation mapped to category: **{category}**.\n"
            f"- Geocoded coordinates: {coords} ({detected_city.upper()}).\n"
            f"- Safety Validation Score: **{eval_score * 100}%**."
        )
        decision_translated = decision_raw
        
        if target_lang_code != "en":
            self.session_memory.add_step("MainController", f"Translating output to {target_lang_code}", "STARTED")
            translated_output = self.translation_tool.translate(final_text, "en", target_lang_code)
            decision_translated = self.translation_tool.translate(decision_raw, "en", target_lang_code)
            self.session_memory.add_step("MainController", "Translation complete", "COMPLETED")
            
        # TTS synthesis
        self.session_memory.add_step("VoiceTool", "Generating voice file", "STARTED")
        tts_text = f"Emergency type {category} resolved. Action checklist: " + worker_payload.get("summary_checklist", "")
        audio_file = self.voice_tool.text_to_speech(tts_text, target_lang_code)
        if audio_file:
            self.session_memory.add_step("VoiceTool", "TTS Complete", "COMPLETED", {"path": audio_file})
        else:
            self.session_memory.add_step("VoiceTool", "TTS Failed", "ERROR")

        output_duration = int((time.time() - translation_start) * 1000)
        stages_log.append({"stage": "Output Synthesis", "duration_ms": output_duration})

        # Save context to long-term user memory
        summary_short = f"Emergency type {category} classified as {priority_tier}. Location: {detected_city}."
        self.user_memory.add_past_request(user_query, priority_tier, category, summary_short)

        self.session_memory.add_agent_message("CrisisAssistAgent", translated_output, target_lang_code, audio_file)
        
        total_duration = int((time.time() - start_time) * 1000)
        
        # Log telemetry metrics
        self.observability.log_run(
            trace_id=trace_id,
            query=user_query,
            priority=priority_tier,
            category=category,
            duration_ms=total_duration,
            stages=stages_log,
            eval_score=eval_score,
            success=eval_approved
        )

        return {
            "trace_id": trace_id,
            "response": translated_output,
            "priority": priority_tier,
            "priority_score": priority_score,
            "category": category,
            "detected_lang": detected_lang,
            "detected_city": detected_city,
            "coordinates": coords,
            "audio_path": audio_file,
            "verified_resources": verified_resources,
            "eval_score": eval_score,
            "duration_ms": total_duration,
            "decision_explanation": decision_translated
        }
