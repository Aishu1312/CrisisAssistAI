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

from agents.planner import PlannerAgent
from agents.worker import WorkerAgent
from agents.evaluator import EvaluatorAgent

load_dotenv()

class MainAgentController:
    """
    Main Agent Controller orchestrating Triage -> Planning -> Worker -> Evaluator agents.
    Now integrates persistent UserMemory and ContextEngineering for personalized response context.
    """
    def __init__(self, gemini_client=None):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.client = gemini_client
        if not self.client and self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                print(f"Failed to initialize Gemini Client in controller: {e}")
                
        # Initialize memory & logging
        self.session_memory = SessionMemory()
        self.user_memory = UserMemory()
        self.observability = Observability()
        
        # Initialize tools
        self.translation_tool = TranslationTool(self.client)
        self.voice_tool = VoiceTool()
        
        # Initialize agents passing client
        self.planner_agent = PlannerAgent(self.client)
        self.worker_agent = WorkerAgent(self.client)
        self.evaluator_agent = EvaluatorAgent(self.client)

    def process_emergency_request(
        self, 
        user_query: str, 
        target_lang_code: str = "en", 
        location_details: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Coordinates the emergency response pipeline.
        Always loads the latest user memory before processing requests.
        """
        start_time = time.time()
        trace_id = str(uuid.uuid4())
        self.session_memory.clear()
        
        # Proactively load the latest user memory from disk
        self.user_memory.load_from_disk()
        user_profile = self.user_memory.get_profile()
        stages_log = []
        
        # Map location coordinates
        detected_city = location_details.get("city", "Mumbai") if location_details else "Mumbai"
        coords = location_details.get("coords", (19.0760, 72.8777)) if location_details else (19.0760, 72.8777)
        
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
            
        # 2. Planning & Triage
        planning_start = time.time()
        self.session_memory.add_step("PlannerAgent", "Plan construction & Triage", "STARTED")
        
        plan_msg_in = AgentMessage(
            sender="MainController",
            receiver="PlannerAgent",
            message_type="REQUEST",
            payload={
                "query": english_query,
                "language": target_lang_code
            },
            trace_id=trace_id
        )
        plan_msg_out = self.planner_agent.run(plan_msg_in, user_profile)
        category = plan_msg_out.payload.get("category", "General Support")
        plan_steps = plan_msg_out.payload.get("steps", [])
        plan_rationale = plan_msg_out.payload.get("rationale", "")
        priority_tier = plan_msg_out.payload.get("priority", "LOW")
        priority_score = plan_msg_out.payload.get("priority_score", 0.0)
        triage_reason = plan_msg_out.payload.get("triage_reason", "")
        
        self.session_memory.set_emergency_meta(priority_tier, category, triage_reason)
        
        planning_duration = int((time.time() - planning_start) * 1000)
        self.session_memory.add_step(
            "PlannerAgent", 
            "Plan construction & Triage", 
            "COMPLETED", 
            {"category": category, "steps": plan_steps, "rationale": plan_rationale}
        )
        stages_log.append({"stage": "Planning", "duration_ms": planning_duration})

        # 3. Worker Execution
        worker_start = time.time()
        self.session_memory.add_step("WorkerAgent", "Execution of plan steps", "STARTED")
        
        worker_payload_in = plan_msg_out.payload.copy()
        worker_payload_in["detected_city"] = detected_city
        worker_payload_in["coordinates"] = coords
        
        worker_msg_in = AgentMessage(
            sender="MainController",
            receiver="WorkerAgent",
            message_type="REQUEST",
            payload=worker_payload_in,
            trace_id=trace_id
        )
        worker_msg_out = self.worker_agent.run(worker_msg_in, user_profile)
        worker_payload = worker_msg_out.payload
        draft_guidelines = worker_payload.get("guidelines", "")
        verified_resources = worker_payload.get("verified_resources", [])
        tool_logs = worker_payload.get("tool_execution_log", [])
        
        for log in tool_logs:
            self.session_memory.add_step("WorkerAgent:Tool", log["step"], "COMPLETED", log["result"])
            
        worker_duration = int((time.time() - worker_start) * 1000)
        self.session_memory.add_step("WorkerAgent", "Draft compiled", "COMPLETED")
        stages_log.append({"stage": "Worker Execution", "duration_ms": worker_duration})

        # 4. Evaluation Loop
        eval_start = time.time()
        self.session_memory.add_step("EvaluatorAgent", "Response safety review", "STARTED")
        
        eval_msg_in = AgentMessage(
            sender="MainController",
            receiver="EvaluatorAgent",
            message_type="REQUEST",
            payload=worker_payload,
            trace_id=trace_id
        )
        eval_msg_out = self.evaluator_agent.run(eval_msg_in, user_profile)
        eval_score = eval_msg_out.payload.get("score", 0.0)
        eval_approved = eval_msg_out.payload.get("approved", False)
        eval_feedback = eval_msg_out.payload.get("feedback", "")
        
        # Self-correction check
        if not eval_approved:
            self.session_memory.add_step("EvaluatorAgent", "Review FAILED", "REJECTED", {"score": eval_score, "feedback": eval_feedback})
            self.session_memory.add_step("WorkerAgent", "Refining draft based on feedback", "STARTED")
            
            worker_msg_in.payload["steps"].append(f"REFINEMENT: {eval_feedback}")
            worker_msg_out = self.worker_agent.run(worker_msg_in, user_profile)
            worker_payload = worker_msg_out.payload
            draft_guidelines = worker_payload.get("guidelines", "")
            verified_resources = worker_payload.get("verified_resources", [])
            
            self.session_memory.add_step("EvaluatorAgent", "Second review pass", "STARTED")
            eval_msg_in = AgentMessage(sender="MainController", receiver="EvaluatorAgent", message_type="REQUEST", payload=worker_payload, trace_id=trace_id)
            eval_msg_out = self.evaluator_agent.run(eval_msg_in, user_profile)
            eval_score = eval_msg_out.payload.get("score", 0.0)
            eval_approved = eval_msg_out.payload.get("approved", True)
            eval_feedback = eval_msg_out.payload.get("feedback", "Refinement complete.")
            self.session_memory.add_step("EvaluatorAgent", "Review completed", "APPROVED")
        else:
            self.session_memory.add_step("EvaluatorAgent", "Review APPROVED", "COMPLETED", {"score": eval_score, "feedback": eval_feedback})
            
        eval_duration = int((time.time() - eval_start) * 1000)
        stages_log.append({"stage": "Safety Review", "duration_ms": eval_duration})

        self.session_memory.set_verified_resources(verified_resources)

        # 5. Localized Output Construction & TTS
        translation_start = time.time()
        final_text = (
            f"### Immediate Actions:\n{draft_guidelines}\n\n"
            f"### Checklist:\n{worker_payload.get('summary_checklist', '')}"
        )
        
        decision_raw = (
            f"- User message detected as '{detected_lang.upper()}' language.\n"
            f"- Emergency priority classified as **{priority_tier}** (Score: {priority_score}).\n"
            f"- Situation mapped to category: **{category}**.\n"
            f"- Geocoded coordinates: {coords} ({detected_city.upper()}).\n"
            f"- Safety Validation Score: **{eval_score * 100}%**."
        )
        
        decision_translated = decision_raw
        if target_lang_code != "en":
            try:
                decision_translated = self.translation_tool.translate(decision_raw, "en", target_lang_code)
            except Exception as e:
                print(f"Decision explanation translation failed: {e}")
            
        # TTS synthesis
        self.session_memory.add_step("VoiceTool", "Generating voice file", "STARTED")
        prefix_en = f"Emergency category {category} resolved. Here is your action checklist:"
        
        prefix_translated = prefix_en
        if target_lang_code != "en":
            try:
                prefix_translated = self.translation_tool.translate(prefix_en, "en", target_lang_code)
            except Exception as e:
                print(f"TTS prefix translation failed: {e}")
                
        tts_text = f"{prefix_translated}\n{worker_payload.get('summary_checklist', '')}"
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

        self.session_memory.add_agent_message("CrisisAssistAgent", final_text, target_lang_code, audio_file)
        
        total_duration = int((time.time() - start_time) * 1000)
        
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
            "response": final_text,
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
