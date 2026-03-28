import streamlit as st
import time

from dao import DashboardDAO
from style import UIConfig
from utils import process_metrics_df, initialize_session_state, get_current_generation

from views import metrics, code_diff, geneaology, strategy, history, embedding

DB_PATH = "/data/evolution.db"

st.set_page_config(
    page_title="EvoCode Agent Dashboard",
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

    st.title("EvoCode Agent Dashboard")

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

        current_gen = get_current_generation(min_gen, max_gen)

        st.markdown("---")
        st.header("Snapshot Stats")

        if not df_metrics.empty:
            st.markdown("### Selected Generation")
            curr_row = df_metrics[df_metrics['generation'] == current_gen]

            if not curr_row.empty:
                st.metric("Generation", f"{current_gen}")
                st.metric("Best Fitness", f"{curr_row.iloc[0]['global_best']:.4f}")
                st.metric("Avg Fitness", f"{curr_row.iloc[0]['avg_fitness']:.4f}")
                st.metric("Diversity", f"{curr_row.iloc[0]['diversity']:.4f}")
            else:
                st.warning("No data for selected generation")

            st.markdown("---")

            st.markdown("### Latest")
            latest_row = df_metrics.iloc[-1]
            st.metric("Generation", f"{max_gen}")
            st.metric("Best Fitness", f"{latest_row['global_best']:.4f}")

            if len(df_metrics) > 1:
                prev_row = df_metrics.iloc[-2]
                delta = latest_row['global_best'] - prev_row['global_best']
                st.metric(
                    "Improvement",
                    f"{delta:+.4f}",
                    delta=delta
                )

    plot_tab, gene_tab, code_tab, dir_tab, emb_tab = st.tabs([
        "Plots",
        "Genealogy",
        "Code Diff",
        "Strategies",
        "Embeddings"
    ])

    with plot_tab:
        st.header("Performance Metrics")

        selected_metric = st.selectbox("Select Evaluation Metric", options=available_metrics)

        metrics.render_evaluation_plot(df_metrics, current_gen, selected_metric)
        metrics.render_diversity_viability_plots(df_metrics)
        history.render_history_inspector(df_metrics, key_suffix="plot")

    with gene_tab:
        st.header("Evolutionary Genealogy Tree")
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

        baseline_gen = st.number_input(
            "Compare against Baseline Generation:",
            min_value=1,
            max_value=current_gen,
            value=1,
            step=1
        )

        target_snapshot = dao.get_snapshot(current_gen)
        baseline_snapshot = dao.get_snapshot(int(baseline_gen))

        if target_snapshot is not None and baseline_snapshot is not None:
            baseline_code = baseline_snapshot.get('best_code_snippet', '')
            target_code = target_snapshot.get('best_code_snippet', '')

            code_diff.render_diff_view(
                baseline_code,
                target_code,
                left_title=f"Gen {baseline_gen} (Baseline)",
                right_title=f"Gen {current_gen} (Selected)",
                language=project_language
            )

        elif baseline_snapshot is None:
             st.warning(f"No data available for Baseline Generation {baseline_gen}")
        else:
             st.warning(f"No data available for Generation {current_gen}")

        history.render_history_inspector(df_metrics, key_suffix="code")

    with dir_tab:
        st.header("Strategy Analysis")

        strategy.render_expert_input()

        df_strategies = dao.get_global_strategies()
        strategy.render_strategies_table(df_strategies)

        reflection_text = dao.get_latest_reflection(current_gen)
        strategy.render_reflection_section(reflection_text)

    with emb_tab:
        st.header("Solution Space Embeddings")

        snapshot = dao.get_snapshot(current_gen)
        embedding.render_embeddings_plot(snapshot)

    if st.session_state.track_latest:
        time.sleep(poll_rate)
        st.rerun()

if __name__ == "__main__":
    main()
