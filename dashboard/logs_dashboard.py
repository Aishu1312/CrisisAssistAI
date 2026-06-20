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
        subtitle = self.trans.get("dash_subtitle", lang_code)
        st.markdown(f"<h2 style='text-align: center; color: #1E3A8A;'>{title}</h2>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align: center; color: #555;'>{subtitle}</p>", unsafe_allow_html=True)

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
                    
                    st.markdown(f"**{self.trans.get('dash_latencies', lang_code)}**")
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
                    
                    if log.get("error"):
                        st.error(f"{self.trans.get('dash_error_logs', lang_code)} {log.get('error')}")

