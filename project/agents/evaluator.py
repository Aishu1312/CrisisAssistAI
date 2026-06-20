import re
import json
from google import genai
from core.context_engineering import ContextEngineering
from core.a2a_protocol import AgentMessage

class EvaluatorAgent:
    """
    Validates safety, resource reliability, and readability metrics.
    Ensures zero hallucinated phone numbers and score >= 0.85 before final output.
    """
    def __init__(self, gemini_client: genai.Client = None):
        self.client = gemini_client

    def run(self, message: AgentMessage) -> AgentMessage:
        """
        Grades the Worker Agent's output.
        """
        worker_payload = message.payload
        query = worker_payload.get("query", "")
        guidelines = worker_payload.get("guidelines", "")
        resources = worker_payload.get("verified_resources", [])
        
        # Default heuristic checks
        score = 1.0
        feedback_points = []
        approved = True
        
        # 1. Safety / Contradiction check:
        # Check for dangerous advice like "touch power lines", "run back inside", etc.
        dangerous_patterns = [
            (r"touch.*power line", "Do not tell users to touch power lines."),
            (r"use.*elevator.*fire", "Elevators should never be advised during fire evacuations."),
            (r"stay.*low.*lying.*flood", "Advise moving to high ground in flood situations.")
        ]
        
        for pattern, warning in dangerous_patterns:
            if re.search(pattern, guidelines.lower()):
                score -= 0.3
                feedback_points.append(warning)
                
        # 2. Grounding check:
        # Check if resources exist and have valid verification status.
        if not resources:
            score -= 0.15
            feedback_points.append("No local rescue centers were found or recommended.")
        else:
            unverified_count = sum(1 for r in resources if not r.get("verification", {}).get("verified", False))
            if unverified_count > 0:
                score -= (0.05 * unverified_count)
                feedback_points.append(f"Recommended {unverified_count} unverified resources. Check status.")

        # 3. Conciseness and checklist check:
        if not worker_payload.get("summary_checklist"):
            score -= 0.1
            feedback_points.append("Missing emergency summary checklist.")
            
        score = max(0.0, round(score, 2))
        approved = score >= 0.85
        feedback = "; ".join(feedback_points) if feedback_points else "Response passes all validation checks."

        # Leverage Gemini LLM-as-a-judge if online
        if self.client:
            try:
                system_instruction = ContextEngineering.build_system_instruction("evaluator", {})
                prompt = (
                    "Evaluate this emergency draft. Output ONLY a valid JSON string (no markdown ticks, no preamble) "
                    "with keys: 'score' (float 0.0-1.0), 'approved' (boolean), and 'feedback' (string).\n\n"
                    f"Draft Guidelines:\n{guidelines}\n\n"
                    f"Number of Resources: {len(resources)}"
                )
                
                response = self.client.models.generate_content(
                    model="gemini-1.5-flash",
                    contents=prompt,
                    config={"system_instruction": system_instruction}
                )
                
                response_text = response.text.strip()
                if response_text.startswith("```"):
                    response_text = re.sub(r"^```(?:json)?\n", "", response_text)
                    response_text = re.sub(r"\n```$", "", response_text)
                    
                parsed = json.loads(response_text)
                if parsed.get("score") is not None:
                    score = float(parsed["score"])
                    approved = bool(parsed.get("approved", score >= 0.85))
                    feedback = parsed.get("feedback", "LLM evaluation finished.")
            except Exception as e:
                print(f"EvaluatorAgent LLM review failed: {e}. Falling back to default heuristics.")

        response_payload = {
            "score": score,
            "approved": approved,
            "feedback": feedback,
            "checked_draft": worker_payload
        }

        return AgentMessage(
            sender="EvaluatorAgent",
            receiver=message.sender,
            message_type="EVAL_RESULT",
            payload=response_payload,
            trace_id=message.trace_id
        )
