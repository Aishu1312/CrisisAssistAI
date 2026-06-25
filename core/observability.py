import os
import json
import datetime
from typing import Dict, Any, List

class Observability:
    """
    Tracks telemetry KPIs (durations, scores) and logs them into a local JSONL database.
    """
    def __init__(self, log_dir: str = "data", log_filename: str = "observability_logs.jsonl"):
        self.log_dir = log_dir
        self.log_filepath = os.path.join(self.log_dir, log_filename)
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

    def log_run(
        self,
        trace_id: str,
        query: str,
        language: str,
        priority: str,
        category: str,
        duration_ms: float,
        stages: List[Dict[str, Any]],
        eval_score: float,
        success: bool,
        final_response_status: str = "",
        planner_status: str = "PENDING",
        worker_status: str = "PENDING",
        evaluator_status: str = "PENDING",
        error: str = "",
        planner_latency: float = 0.0,
        worker_latency: float = 0.0,
        evaluator_latency: float = 0.0,
        resources_used: List[str] = None
    ):
        record = {
            "timestamp": datetime.datetime.now().isoformat(),
            "trace_id": trace_id,
            "query": query,
            "language": language,
            "priority": priority,
            "category": category,
            "duration_ms": duration_ms,
            "planner_latency": planner_latency,
            "worker_latency": worker_latency,
            "evaluator_latency": evaluator_latency,
            "resources_used": resources_used or [],
            "latencies": [stage.get("duration_ms", 0) for stage in stages],
            "stages": stages,
            "eval_score": eval_score,
            "success": success,
            "final_response_status": final_response_status,
            "planner_status": planner_status,
            "worker_status": worker_status,
            "evaluator_status": evaluator_status,
            "error": error
        }
        try:
            with open(self.log_filepath, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except Exception as e:
            print(f"Observability logging failed: {e}")

    def read_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        logs = []
        if not os.path.exists(self.log_filepath):
            return logs
            
        try:
            with open(self.log_filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line in reversed(lines):
                    if line.strip():
                        logs.append(json.loads(line))
                        if len(logs) >= limit:
                            break
        except Exception as e:
            print(f"Observability reading failed: {e}")
            
        return logs

    def get_aggregate_stats(self) -> Dict[str, Any]:
        logs = self.read_logs(100)
        if not logs:
            return {
                "total_runs": 0,
                "avg_duration_ms": 0.0,
                "success_rate": 0.0,
                "avg_eval_score": 0.0,
                "category_distribution": {}
            }
            
        total = len(logs)
        durations = []
        scores = []
        successes = 0
        cats = {}
        
        for run in logs:
            durations.append(run.get("duration_ms", 0.0))
            scores.append(run.get("eval_score", 0.0))
            if run.get("success", False):
                successes += 1
            cat = run.get("category", "UNKNOWN")
            cats[cat] = cats.get(cat, 0) + 1
            
        return {
            "total_runs": total,
            "avg_duration_ms": round(sum(durations) / total, 1) if total > 0 else 0.0,
            "success_rate": round((successes / total) * 100, 1) if total > 0 else 0.0,
            "avg_eval_score": round(sum(scores) / total, 2) if total > 0 else 0.0,
            "category_distribution": cats
        }
