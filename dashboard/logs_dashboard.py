import streamlit as st
import datetime
from core.observability import Observability
from utils.language_manager import LanguageManager

class LogsDashboard:
    """
    Observability Dashboard. Telemetry analysis of latency, safety scores, 
    and multi-agent execution timelines.
    """
    def __init__(self):
        self.observability = Observability()
        self.trans = LanguageManager()

    def render(self, lang_code: str = "en"):
        # Fetch translations
        title = self.trans.get("logs_header", lang_code)
        subtitle = self.trans.get("dash_subtitle", lang_code)
        st.title(title)
        if subtitle:
            st.write(subtitle)

        stats = self.observability.get_aggregate_stats()
        logs = self.observability.read_logs(30)

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(self.trans.get("dash_total_executions", lang_code), stats.get("total_runs", 0))
        with col2:
            st.metric(self.trans.get("dash_avg_response_time", lang_code), f"{stats.get('avg_duration_ms', 0.0)} ms")
        with col3:
            st.metric(self.trans.get("dash_avg_safety_score", lang_code), f"{int(stats.get('avg_eval_score', 0.0) * 100)}%")
        with col4:
            st.metric(self.trans.get("dash_success_rate", lang_code), f"{stats.get('success_rate', 0.0)}%")

        st.markdown("---")

        if not logs:
            st.info(self.trans.get("dash_no_logs", lang_code))
            return

        left, right = st.columns([1, 2])
        
        with left:
            st.subheader(self.trans.get("dash_cat_dist", lang_code))
            cat_dist = stats.get("category_distribution", {})
            if cat_dist:
                for cat, val in cat_dist.items():
                    percentage = int((val / stats.get("total_runs", 1)) * 100)
                    cat_key = "category_" + cat.lower().replace(" & ", "_").replace(" ", "_")
                    cat_translated = self.trans.get(cat_key, lang_code)
                    st.write(f"**{cat_translated}** ({val})")
                    st.progress(percentage / 100.0)
            else:
                st.caption(self.trans.get("dash_no_cats", lang_code))

        with right:
            st.subheader(self.trans.get("dash_history", lang_code))
            for idx, log in enumerate(logs):
                time_str = ""
                try:
                    dt = datetime.datetime.fromisoformat(log.get("timestamp", ""))
                    time_str = dt.strftime("%b %d, %H:%M:%S")
                except:
                    time_str = log.get("timestamp", "")

                success_badge = "✅ PASS" if log.get("success", True) else "⚠️ REJECT"
                p_tier = log.get('priority', 'LOW')
                title_lbl = f"{time_str} | Priority: **{p_tier}** | Score: {log.get('eval_score')} | {success_badge}"
                
                with st.expander(title_lbl):
                    st.markdown(f"**{self.trans.get('dash_user_query', lang_code)}** {log.get('query')}")
                    
                    cat_raw = log.get('category', 'General Support')
                    cat_key = "category_" + cat_raw.lower().replace(" & ", "_").replace(" ", "_")
                    cat_translated = self.trans.get(cat_key, lang_code)
                    
                    st.markdown(f"**{self.trans.get('dash_category', lang_code)}** {cat_translated} | **{self.trans.get('dash_total_time', lang_code)}** {log.get('duration_ms')} ms")
                    
                    # Structured Execution Log
                    st.markdown("### 📋 Execution Log")
                    
                    log_time_str = ""
                    try:
                        dt_time = datetime.datetime.fromisoformat(log.get("timestamp", ""))
                        log_time_str = dt_time.strftime("%I:%M %p")
                    except:
                        log_time_str = log.get("timestamp", "")
                        
                    lang_map = self.trans.get_supported_languages()
                    lang_code_val = log.get("language", "en")
                    lang_name_translated = lang_map.get(lang_code_val, lang_code_val).capitalize()
                    
                    p_val = log.get("priority", "MEDIUM").strip().upper()
                    
                    pl_status = log.get("planner_status", "Completed")
                    wk_status = log.get("worker_status", "Completed")
                    ev_status = log.get("evaluator_status", "Completed")
                    if pl_status in ["COMPLETED", "APPROVED"]: pl_status = "Completed"
                    if wk_status in ["COMPLETED", "APPROVED"]: wk_status = "Completed"
                    if ev_status in ["COMPLETED", "APPROVED"]: ev_status = "Completed"
                    
                    val_score = f"{int(log.get('eval_score', 0.98) * 100)}%"
                    
                    final_status_raw = log.get("final_response_status", "SUCCESS")
                    final_status = "Delivered" if final_status_raw in ["SUCCESS", "HEURISTIC_FALLBACK"] else "Failed"
                    
                    location_val = log.get("location", "N/A")
                    fallback_used_val = "Yes" if log.get("fallback_used", False) else "No"
                    
                    st.markdown(f"""
                    **Time:**
                    {log_time_str}
                    
                    **Language:**
                    {lang_name_translated}
                    
                    **Location:**
                    {location_val}
                    
                    **Priority:**
                    {p_val}
                    
                    **Planner:**
                    {pl_status}
                    
                    **Worker:**
                    {wk_status}
                    
                    **Evaluator:**
                    {ev_status}
                    
                    **Validation:**
                    {val_score}
                    
                    **Fallback Used:**
                    {fallback_used_val}
                    
                    **Response:**
                    {final_status}
                    """)
                    
                    st.markdown(f"**{self.trans.get('dash_latencies', lang_code)}**")
                    if "planner_latency" in log or "worker_latency" in log or "evaluator_latency" in log:
                        st.markdown(f"- **Planner Latency:** {log.get('planner_latency', 0.0)} ms")
                        st.markdown(f"- **Worker Latency:** {log.get('worker_latency', 0.0)} ms")
                        st.markdown(f"- **Evaluator Latency:** {log.get('evaluator_latency', 0.0)} ms")
                    else:
                        stages = log.get("stages", [])
                        stage_map = {
                            "Language Detection": "stage_lang_detect",
                            "Input Translation": "stage_input_trans",
                            "Priority Detection": "stage_priority",
                            "Planning": "stage_planning",
                            "Worker Execution": "stage_worker",
                            "Safety Review": "stage_safety",
                            "Output Synthesis": "stage_output"
                        }
                        for stage in stages:
                            s_raw = stage.get('stage', '')
                            s_key = stage_map.get(s_raw, "")
                            s_trans = self.trans.get(s_key, lang_code) if s_key else s_raw
                            st.markdown(f"- **{s_trans}:** {stage.get('duration_ms')} ms")
                            
                    res_used = log.get("resources_used", [])
                    if res_used:
                        st.markdown(f"**Resources Used:** {', '.join(res_used)}")
                    
                    if log.get("error"):
                        st.error(f"{self.trans.get('dash_error_logs', lang_code)} {log.get('error')}")

