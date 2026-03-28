import streamlit as st
import time

from dao import DashboardDAO
from style import UIConfig
from utils import process_metrics_df, initialize_session_state, get_current_generation

from views import metrics, code_diff, geneaology, strategy, history, embedding, cost

DB_PATH = "/data/evolution.db"

st.set_page_config(
    page_title="EvoCode DashBoard",
    layout="wide",
    initial_sidebar_state="expanded"
)

def render_splash_page(connected: bool = False):
    """
    Renders a waiting screen using ONLY native Streamlit elements.
    """
    for _ in range(8):
        st.write("")

    _, col2, _ = st.columns([1, 2, 1])

    with col2:
        st.title("EvoCode Agent")
        st.header("Initializing Evolution...")

        st.write("The system is spinning up the backend and waiting for the first generation of data.")

        st.divider()

        with st.status("Connecting to backend...", expanded=True) as status:
            if not connected:
                st.write("Checking database connection...")
            else:
                st.write("Polling for Generation 1...")
            time.sleep(2)

            status.update(label="Waiting for data...", state="running")

    st.rerun()


def main():
    initialize_session_state()

    # For now, hardcode, but we should get this based on file extension
    project_language = 'java'
    dao = DashboardDAO(DB_PATH)
    try:
        min_gen, max_gen = dao.get_generation_range()
    except Exception:
        min_gen, max_gen = 0, 0

    # Wait for database to initialize
    if max_gen == 0:
        render_splash_page(dao.is_connected)
        return

    raw_df_metrics = dao.get_metrics(max_gen)
    df_metrics, available_metrics = process_metrics_df(raw_df_metrics)

    current_gen = get_current_generation(min_gen, max_gen)

    st.title("EvoCode DashBoard")

    # Run-status strip
    is_live = st.session_state.track_latest
    mode_label = "LIVE" if is_live else "PINNED"
    mode_bg = "#C96442" if is_live else "#8B7D6B"
    strip_best = df_metrics.iloc[-1]['global_best'] if not df_metrics.empty else 0.0
    strip_delta_str = ""
    strip_delta_color = "#8B7D6B"
    if len(df_metrics) > 1:
        strip_delta = float(df_metrics.iloc[-1]['global_best'] - df_metrics.iloc[-2]['global_best'])
        strip_delta_str = f"({strip_delta:+.4f})"
        strip_delta_color = "#A0522D" if strip_delta >= 0 else "#8B8070"
    strip_of = f" of {max_gen}" if current_gen != max_gen else ""
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:24px;padding:10px 20px;
                background:rgba(201,100,66,0.07);border:1px solid rgba(201,100,66,0.2);
                border-radius:8px;margin-bottom:8px;flex-wrap:wrap;">
      <div>
        <span style="font-size:0.72rem;color:#8B7D6B;font-weight:600;text-transform:uppercase;letter-spacing:0.07em;">Generation</span><br>
        <span style="font-size:1.5rem;font-weight:700;line-height:1.2;">{current_gen}</span>
        <span style="font-size:0.9rem;color:#8B7D6B;">{strip_of}</span>
      </div>
      <div style="width:1px;height:40px;background:rgba(201,100,66,0.2);"></div>
      <div>
        <span style="background:{mode_bg};color:#FAF7F2;padding:3px 12px;
                     border-radius:12px;font-size:0.72rem;font-weight:700;letter-spacing:0.08em;">{mode_label}</span>
      </div>
      <div style="width:1px;height:40px;background:rgba(201,100,66,0.2);"></div>
      <div>
        <span style="font-size:0.72rem;color:#8B7D6B;font-weight:600;text-transform:uppercase;letter-spacing:0.07em;">Latest Best Fitness</span><br>
        <span style="font-size:1.3rem;font-weight:700;color:#C96442;">{strip_best:.4f}</span>
        <span style="font-size:0.9rem;color:{strip_delta_color};"> {strip_delta_str}</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Larger tab labels and stronger active highlight
    st.markdown("""
    <style>
    /* Much larger tab text */
    .stTabs [data-baseweb="tab"] {
        padding: 12px 24px !important;
    }
    .stTabs [data-baseweb="tab"] p {
        font-size: 1.5rem;
        font-weight: 700;
        letter-spacing: 0.02em;
    }
    /* Stronger active tab underline */
    .stTabs [aria-selected="true"] {
        border-bottom-width: 4px !important;
    }
    </style>
    """, unsafe_allow_html=True)

    with st.sidebar:
        st.header("Controls")

        # We use a dynamic key to allow programmatic resetting from the main body
        checkbox_key = f"track_latest_{st.session_state.sidebar_refresh_id}"

        # Get the current checkbox state but DON'T update session state yet
        track_latest_widget = st.checkbox(
            "Track Latest Generation",
            value=st.session_state.track_latest,
            key=checkbox_key
        )

        # Only update if the user changed it (not if we set it)
        # This prevents the checkbox from overriding table selections
        if track_latest_widget != st.session_state.track_latest:
            st.session_state.track_latest = track_latest_widget
            if track_latest_widget:
                st.session_state.selected_generation = max_gen
            st.rerun()

        poll_rate = st.slider(
            "Poll Rate (seconds)",
            min_value=1,
            max_value=10,
            value=UIConfig.DEFAULT_POLL_RATE,
            help="How often to check for new data"
        )

    plot_tab, gene_tab, code_tab, dir_tab, emb_tab, cost_tab = st.tabs([
        "Overview",
        "Lineage",
        "Diff",
        "Strategy",
        "Search Space",
        "Cost"
    ])

    with plot_tab:
        st.header("Overview")

        metrics.render_kpi_strip(df_metrics, current_gen)
        metrics.render_alerts(df_metrics)

        selected_metric = st.selectbox("Select Evaluation Metric", options=available_metrics)

        metrics.render_evaluation_plot(df_metrics, current_gen, selected_metric)
        metrics.render_diversity_viability_plots(df_metrics)

    with gene_tab:
        st.header("Evolutionary Lineage")
        snapshot = dao.get_snapshot(current_gen)

        col1, col2 = st.columns([0.6, 0.4])

        active_graph_data = None

        with col1:
            clicked_node, graph_info = geneaology.render_genealogy_graph(snapshot, st.session_state.selected_node_id)

            if clicked_node is not None:
                try:
                    clicked_int = int(clicked_node)
                    if clicked_int != st.session_state.selected_node_id:
                        st.session_state.selected_node_id = clicked_int
                        st.rerun()
                except ValueError:
                    pass

            if graph_info:
                active_graph_data = graph_info

        with col2:
            if active_graph_data:
                G, active_node_id = active_graph_data
                geneaology.render_node_inspector(G, active_node_id, project_language)

                if st.session_state.selected_node_id is not None:
                     if st.button("Clear Selection", use_container_width=True):
                        st.session_state.selected_node_id = None
                        st.rerun()
            else:
                st.info("Loading genealogy...")

        history.render_history_inspector(df_metrics, key_suffix="gene")

    with code_tab:
        st.header("Code Evolution Diff")

        code_diff.render_diff_tab(dao, min_gen, max_gen, project_language)

        history.render_history_inspector(df_metrics, key_suffix="code")

    with dir_tab:
        st.header("Strategy Analysis")

        reflection_text = dao.get_latest_reflection(current_gen)
        strategy.render_learned_insights(reflection_text)

        df_strategies = dao.get_global_strategies()
        strategy.render_strategies_table(df_strategies)

        strategy.render_steering_panel()

    with emb_tab:
        st.header("Search Space")

        snapshot = dao.get_snapshot(current_gen)
        embedding.render_embeddings_plot(snapshot)

    with cost_tab:
        st.header("Cost & Resources")

        df_llm_stats = dao.get_llm_stats(max_gen)
        cost.render_cost_tab(df_llm_stats)

    if st.session_state.track_latest:
        time.sleep(poll_rate)
        st.rerun()

if __name__ == "__main__":
    main()
