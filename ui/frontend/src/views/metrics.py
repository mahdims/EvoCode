import streamlit as st
import pandas as pd
import plotly.express as px

from style import UIConfig


def _compute_stagnation(df_metrics: pd.DataFrame) -> int:
    """Count consecutive generations (from latest) with no improvement in global_best."""
    if len(df_metrics) < 2:
        return 0
    bests = df_metrics['global_best'].values
    count = 0
    for i in range(len(bests) - 1, 0, -1):
        if bests[i] <= bests[i - 1]:
            count += 1
        else:
            break
    return count


def render_kpi_strip(df_metrics: pd.DataFrame, current_gen: int):
    """Render top-level KPI cards for at-a-glance run status."""
    if df_metrics.empty:
        return

    latest = df_metrics.iloc[-1]
    best_fitness = latest['global_best']
    avg_fitness = latest['avg_fitness']
    diversity = latest['diversity']
    viability = latest['viability_rate']

    # Clean bordered KPI cards (scoped to main content, not sidebar)
    st.markdown("""
    <style>
    section.main div[data-testid="stMetric"] {
        background-color: transparent !important;
        border: 1px solid rgba(201, 100, 66, 0.25) !important;
        border-radius: 8px;
        padding: 12px 16px;
    }
    section.main div[data-testid="stMetric"] label {
        font-size: 0.95rem !important;
    }
    section.main div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        font-size: 1.6rem !important;
    }
    </style>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        delta_best = None
        if len(df_metrics) > 1:
            delta_best = float(best_fitness - df_metrics.iloc[-2]['global_best'])
        st.metric("Best Fitness", f"{best_fitness:.4f}", delta=delta_best)
    with c2:
        delta_avg = None
        if len(df_metrics) > 1:
            delta_avg = float(avg_fitness - df_metrics.iloc[-2]['avg_fitness'])
        st.metric("Avg Fitness", f"{avg_fitness:.4f}", delta=delta_avg)
    with c3:
        st.metric("Diversity", f"{diversity:.4f}")
    with c4:
        st.metric("Completion", f"{viability:.1%}")


def render_alerts(df_metrics: pd.DataFrame):
    """Show contextual alert badges when the run needs attention."""
    if df_metrics.empty or len(df_metrics) < 2:
        return

    alerts = []

    # Stagnation alert
    stagnation = _compute_stagnation(df_metrics)
    if stagnation >= 5:
        alerts.append(("error", f"Stalled: no improvement for {stagnation} consecutive generations"))
    elif stagnation >= 3:
        alerts.append(("warning", f"Slowing down: no improvement for {stagnation} consecutive generations"))

    # Low diversity
    latest_diversity = df_metrics.iloc[-1]['diversity']
    if latest_diversity < 0.001:
        alerts.append(("error", "Very low diversity -- population may have converged"))
    elif latest_diversity < 0.01:
        alerts.append(("warning", "Diversity is declining -- consider more exploration"))

    # Viability drop
    peak_viability = df_metrics['viability_rate'].max()
    current_viability = df_metrics.iloc[-1]['viability_rate']
    if peak_viability > 0 and current_viability < peak_viability * 0.6:
        alerts.append(("warning", f"Completion dropped to {current_viability:.0%} (peak was {peak_viability:.0%})"))

    # Suspicious fitness spike
    if len(df_metrics) >= 3:
        recent = df_metrics['global_best'].iloc[-3:]
        jump = recent.iloc[-1] - recent.iloc[-2]
        avg_delta = abs(recent.diff().dropna()).mean()
        if avg_delta > 0 and jump > avg_delta * 5:
            alerts.append(("warning", "Suspicious fitness spike — verify latest candidate"))

    for level, msg in alerts:
        if level == "error":
            st.error(msg)
        else:
            st.warning(msg)


def render_evaluation_plot(df_metrics: pd.DataFrame, current_gen: int, metric_name: str):
    if df_metrics.empty:
        st.info("No data available yet.")
        return

    if metric_name == "Fitness":
        y_cols = ["global_best", "avg_fitness"]
        title = "Fitness Evolution Over Time"
        colors = [UIConfig.COLOR_BEST_FITNESS, UIConfig.COLOR_AVG_FITNESS]
    else:
        best_col = f"{metric_name}_best"
        avg_col = f"{metric_name}_avg"

        if best_col not in df_metrics.columns or avg_col not in df_metrics.columns:
            st.warning(f"Data for {metric_name} is incomplete or missing.")
            return

        y_cols = [best_col, avg_col]
        title = f"{metric_name} Evolution Over Time"
        colors = [UIConfig.COLOR_BEST_FITNESS, UIConfig.COLOR_AVG_FITNESS]

    fig = px.line(
        df_metrics,
        x="generation",
        y=y_cols,
        labels={
            "value": metric_name,
            "variable": "Metric Type",
            "generation": "Generation"
        },
        title=title
    )

    for i, trace in enumerate(fig.data):
        trace.line.color = colors[i % len(colors)]
        if "best" in trace.name or "global" in trace.name:
            trace.name = f"Best {metric_name}"
        elif "avg" in trace.name:
            trace.name = f"Avg {metric_name}"

    fig.add_vline(
        x=current_gen,
        line_dash="dash",
        line_color=UIConfig.COLOR_SELECTED,
        annotation_text=f"Gen {current_gen}",
        annotation_position="top"
    )

    font_color = UIConfig.plot_font_color(st.session_state)
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=font_color, size=14),
        title_font_size=18,
        hovermode="x unified"
    )

    with st.container(border=True):
        st.plotly_chart(fig, width='stretch')

def render_diversity_viability_plots(df_metrics: pd.DataFrame):
    if df_metrics.empty:
        return

    font_color = UIConfig.plot_font_color(st.session_state)

    col1, col2 = st.columns(2)

    with col1:
        fig_div = px.area(
            df_metrics,
            x="generation",
            y="diversity",
            title="Diversity Index (Population Variance)",
            color_discrete_sequence=[UIConfig.COLOR_DIVERSITY]
        )
        fig_div.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color=font_color, size=14),
            title_font_size=18,
        )
        with st.container(border=True):
            st.plotly_chart(fig_div, width='stretch')

    with col2:
        fig_via = px.bar(
            df_metrics,
            x="generation",
            y="viability_rate",
            title="Completion Rate",
            range_y=[0, 1],
            color_discrete_sequence=[UIConfig.COLOR_VIABILITY]
        )
        fig_via.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color=font_color, size=14),
            title_font_size=18,
        )
        with st.container(border=True):
            st.plotly_chart(fig_via, width='stretch')
