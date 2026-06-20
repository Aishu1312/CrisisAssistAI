import streamlit as st
import datetime
from core.observability import Observability
from utils.translation import TranslationManager

class LogsDashboard:
    """
    Observability Dashboard. Telemetry analysis of latency, safety scores, 
    and multi-agent execution timelines.
    """
    def __init__(self):
        self.observability = Observability()
        self.trans = TranslationManager()

    def render(self, lang_code: str = "en"):
        # Fetch translations
        title = self.trans.get("logs_header", lang_code)
        st.markdown(f"<h2 style='text-align: center; color: #1E3A8A;'>{title}</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #555;'>Analyze live agent latencies, validation scores, and execution timeline history logs.</p>", unsafe_allow_html=True)

        stats = self.observability.get_aggregate_stats()
        logs = self.observability.read_logs(30)

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Executions", stats.get("total_runs", 0))
        with col2:
            st.metric("Avg Response Time", f"{stats.get('avg_duration_ms', 0.0)} ms")
        with col3:
            st.metric("Avg Safety Score", f"{int(stats.get('avg_eval_score', 0.0) * 100)}%")
        with col4:
            st.metric("Success Rate", f"{stats.get('success_rate', 0.0)}%")

        st.markdown("---")

        if not logs:
            st.info("No logs found. Submit emergency queries to populate dashboard metrics.")
            return

        left, right = st.columns([1, 2])
        
        with left:
            st.subheader("Category Distribution")
            cat_dist = stats.get("category_distribution", {})
            if cat_dist:
                for cat, val in cat_dist.items():
                    percentage = int((val / stats.get("total_runs", 1)) * 100)
                    st.write(f"**{cat}** ({val} runs)")
                    st.progress(percentage / 100.0)
            else:
                st.caption("No categories recorded.")

        with right:
            st.subheader("Execution History Timeline")
            for idx, log in enumerate(logs):
                time_str = ""
                try:
                    dt = datetime.datetime.fromisoformat(log.get("timestamp", ""))
                    time_str = dt.strftime("%b %d, %H:%M:%S")
                except:
                    time_str = log.get("timestamp", "")

                success_badge = "✅ PASS" if log.get("success", True) else "⚠️ REJECT"
                title_lbl = f"{time_str} | Priority: **{log.get('priority')}** | Score: {log.get('eval_score')} | {success_badge}"
                
                with st.expander(title_lbl):
                    st.markdown(f"**User Query:** {log.get('query')}")
                    st.markdown(f"**Category:** {log.get('category')} | **Total Time:** {log.get('duration_ms')} ms")
                    
                    st.markdown("**Sub-Agent Execution Plan Latencies:**")
                    stages = log.get("stages", [])
                    for stage in stages:
                        st.markdown(f"- **{stage.get('stage')}:** {stage.get('duration_ms')} ms")
                    
                    if log.get("error"):
                        st.error(f"Error logs: {log.get('error')}")
