import json
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

def render_embeddings_plot(snapshot):
    if snapshot is None or not snapshot.get('embeddings_json'):
        st.info("No embedding data available for this generation.")
        return

    try:
        emb_data = json.loads(snapshot['embeddings_json'])
        df_emb = pd.DataFrame(emb_data)

        fig = px.scatter(
            df_emb,
            x="x",
            y="y",
            color="Strategy Cluster",
            size="Fitness",
            color_discrete_sequence=px.colors.qualitative.Pastel,
            title="Solution Space Embedding (Semantic Clustering)",
            hover_data=["Fitness"]
        )

        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="white",
            xaxis=dict(showgrid=False, zeroline=False, title="Dimension 1"),
            yaxis=dict(showgrid=False, zeroline=False, title="Dimension 2")
        )

        st.plotly_chart(fig, width='stretch')

        with st.expander("Show Exploration Density Heatmap"):
            try:
                fig_density = go.Figure(go.Histogram2d(
                    x=df_emb['x'],
                    y=df_emb['y'],
                    colorscale='Hot',
                    showscale=True
                ))

                fig_density.update_layout(
                    title="Search Density (Explored vs Unexplored Regions)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font_color="white",
                    xaxis_title="Dimension 1",
                    yaxis_title="Dimension 2"
                )

                st.plotly_chart(fig_density, width='stretch')
            except Exception as e:
                st.warning(f"Could not generate density heatmap: {e}")

    except (json.JSONDecodeError, Exception) as e:
        st.error(f"Failed to parse embedding data: {e}")
