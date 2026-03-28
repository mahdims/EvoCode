import json
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from style import UIConfig

def render_embeddings_plot(snapshot):
    if snapshot is None or not snapshot.get('embeddings_json'):
        st.info("No embedding data available for this generation.")
        return

    try:
        emb_data = json.loads(snapshot['embeddings_json'])
        df_emb = pd.DataFrame(emb_data)

        # Detect real embeddings vs score-based fallback
        has_real_embeddings = "candidate_id" in df_emb.columns

        # Build hover columns (backward compat with old snapshots)
        hover_cols = ["Fitness"]
        if "candidate_id" in df_emb.columns:
            hover_cols.append("candidate_id")
        if "idea" in df_emb.columns:
            hover_cols.append("idea")

        color_options = ["Strategy Cluster"]
        if "Fitness" in df_emb.columns:
            color_options.append("Fitness")

        color_by = st.selectbox("Color by", options=color_options, key="emb_color_by")

        _WARM_CONTINUOUS = ["#F0EBE3", "#D4845E", "#C96442", "#A0522D", "#7B3F1A"]
        _WARM_QUALITATIVE = [
            "#C96442", "#D4A853", "#8B7355", "#A0522D", "#D4845E",
            "#B8860B", "#8B4513", "#CD853F", "#D2691E", "#BC8F5F",
        ]

        if color_by == "Fitness":
            fig = px.scatter(
                df_emb,
                x="x",
                y="y",
                color="Fitness",
                size="Fitness",
                color_continuous_scale=_WARM_CONTINUOUS,
                title="Code Diversity Embedding (by Fitness)" if has_real_embeddings else "Solution Space (by Fitness)",
                hover_data=hover_cols
            )
        else:
            fig = px.scatter(
                df_emb,
                x="x",
                y="y",
                color="Strategy Cluster",
                size="Fitness",
                color_discrete_sequence=_WARM_QUALITATIVE,
                title="Code Diversity Embedding (Semantic Clustering)" if has_real_embeddings else "Solution Space (Strategy Clustering)",
                hover_data=hover_cols
            )

        font_color = UIConfig.plot_font_color(st.session_state)
        x_title = "PCA Component 1" if has_real_embeddings else "Dimension 1"
        y_title = "PCA Component 2" if has_real_embeddings else "Dimension 2"
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color=font_color, size=14),
            title_font_size=18,
            xaxis=dict(showgrid=False, zeroline=False, title=x_title),
            yaxis=dict(showgrid=False, zeroline=False, title=y_title)
        )

        st.plotly_chart(fig, width='stretch')

        with st.expander("Show Exploration Density Heatmap"):
            try:
                _WARM_DENSITY = [
                    [0.0, "#FAF7F2"], [0.3, "#D4A853"],
                    [0.7, "#C96442"], [1.0, "#7B3F1A"]
                ]
                fig_density = go.Figure(go.Histogram2d(
                    x=df_emb['x'],
                    y=df_emb['y'],
                    colorscale=_WARM_DENSITY,
                    showscale=True
                ))

                fig_density.update_layout(
                    title="Search Density (Explored vs Unexplored Regions)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color=font_color, size=14),
                    title_font_size=18,
                    xaxis_title=x_title,
                    yaxis_title=y_title
                )

                st.plotly_chart(fig_density, width='stretch')
            except Exception as e:
                st.warning(f"Could not generate density heatmap: {e}")

    except (json.JSONDecodeError, Exception) as e:
        st.error(f"Failed to parse embedding data: {e}")
