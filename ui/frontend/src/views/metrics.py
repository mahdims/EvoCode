import streamlit as st
import pandas as pd
import plotly.express as px

from style import UIConfig

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

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="white",
        hovermode="x unified"
    )

    st.plotly_chart(fig, width='stretch')

def render_diversity_viability_plots(df_metrics: pd.DataFrame):
    if df_metrics.empty:
        return

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
            font_color="white"
        )
        st.plotly_chart(fig_div, width='stretch')

    with col2:
        fig_via = px.bar(
            df_metrics,
            x="generation",
            y="viability_rate",
            title="Viability Rate (Compilation Success)",
            range_y=[0, 1],
            color_discrete_sequence=[UIConfig.COLOR_VIABILITY]
        )
        fig_via.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="white"
        )
        st.plotly_chart(fig_via, width='stretch')
