import json
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from style import UIConfig

_CALL_TYPE_LABELS = {
    "mutation":          "Mutation",
    "crossover":         "Crossover",
    "reflection_short":  "Short Reflection",
    "reflection_long":   "Long Reflection",
    "reflection":        "Reflection",
    "insight":           "User Insight",
    "strategy_analysis": "Strategy Analysis",
    "unknown":           "Other",
}

_CALL_COLORS = [
    "#C96442", "#D4A853", "#8B7D6B", "#A0522D",
    "#D4845E", "#B8860B", "#8B4513", "#CD853F",
]


def _parse_breakdown(df: pd.DataFrame) -> pd.DataFrame:
    """Expand call_breakdown JSON into per-type per-generation rows."""
    rows = []
    for _, r in df.iterrows():
        gen = r["generation"]
        try:
            breakdown = json.loads(r.get("call_breakdown") or "{}")
        except (json.JSONDecodeError, TypeError):
            breakdown = {}
        for call_type, stats in breakdown.items():
            rows.append({
                "generation":    gen,
                "call_type":     _CALL_TYPE_LABELS.get(call_type, call_type),
                "calls":         stats.get("calls", 0),
                "input_tokens":  stats.get("input_tokens", 0),
                "output_tokens": stats.get("output_tokens", 0),
            })
    return pd.DataFrame(rows) if rows else pd.DataFrame(
        columns=["generation", "call_type", "calls", "input_tokens", "output_tokens"]
    )


def render_cost_tab(df: pd.DataFrame):
    if df.empty:
        st.info("No cost data yet — LLM stats are recorded from the second generation onward.")
        return

    font_color = UIConfig.plot_font_color(st.session_state)

    # ── KPI strip ────────────────────────────────────────────────────────────
    total_calls   = int(df["total_calls"].sum())
    total_in      = int(df["input_tokens"].sum())
    total_out     = int(df["output_tokens"].sum())
    total_tokens  = total_in + total_out
    avg_wall      = df["wall_time_sec"].mean()
    avg_cpu       = df["process_cpu_pct"].mean()
    peak_mem      = df["process_mem_mb"].max()

    cols = st.columns(6)
    kpi_data = [
        ("LLM Calls",      f"{total_calls:,}",       None),
        ("Input Tokens",   f"{total_in/1000:.1f}k",   None),
        ("Output Tokens",  f"{total_out/1000:.1f}k",  None),
        ("Total Tokens",   f"{total_tokens/1000:.1f}k", None),
        ("Avg Gen Time",   f"{avg_wall:.1f}s",         None),
        ("Peak Mem",       f"{peak_mem:.0f} MB",       None),
    ]
    for col, (label, value, delta) in zip(cols, kpi_data):
        with col:
            st.metric(label, value, delta)

    st.divider()

    # ── Token usage over generations ─────────────────────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        fig_tok = go.Figure()
        fig_tok.add_trace(go.Bar(
            x=df["generation"], y=df["input_tokens"],
            name="Input", marker_color="#C96442"
        ))
        fig_tok.add_trace(go.Bar(
            x=df["generation"], y=df["output_tokens"],
            name="Output", marker_color="#D4A853"
        ))
        fig_tok.update_layout(
            barmode="stack",
            title="Token Usage per Generation",
            xaxis_title="Generation",
            yaxis_title="Tokens",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color=font_color, size=13),
            title_font_size=16,
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        with st.container(border=True):
            st.plotly_chart(fig_tok, use_container_width=True)

    with col2:
        fig_calls = px.line(
            df, x="generation", y="total_calls",
            title="LLM Calls per Generation",
            markers=True,
            color_discrete_sequence=["#C96442"],
        )
        fig_calls.update_layout(
            xaxis_title="Generation",
            yaxis_title="Calls",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color=font_color, size=13),
            title_font_size=16,
        )
        with st.container(border=True):
            st.plotly_chart(fig_calls, use_container_width=True)

    # ── Call-type breakdown ───────────────────────────────────────────────────
    df_breakdown = _parse_breakdown(df)
    if not df_breakdown.empty:
        col3, col4 = st.columns(2)

        with col3:
            # Stacked bar: tokens by call type over generations
            pivot = df_breakdown.pivot_table(
                index="generation", columns="call_type",
                values="input_tokens", aggfunc="sum", fill_value=0
            ).reset_index()

            fig_type = go.Figure()
            for i, ct in enumerate(pivot.columns[1:]):
                fig_type.add_trace(go.Bar(
                    x=pivot["generation"], y=pivot[ct],
                    name=ct, marker_color=_CALL_COLORS[i % len(_CALL_COLORS)]
                ))
            fig_type.update_layout(
                barmode="stack",
                title="Input Tokens by Call Type",
                xaxis_title="Generation",
                yaxis_title="Input Tokens",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color=font_color, size=13),
                title_font_size=16,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, font_size=11),
            )
            with st.container(border=True):
                st.plotly_chart(fig_type, use_container_width=True)

        with col4:
            # Pie: total calls by type
            agg = df_breakdown.groupby("call_type")["calls"].sum().reset_index()
            fig_pie = px.pie(
                agg, names="call_type", values="calls",
                title="Call Distribution",
                color_discrete_sequence=_CALL_COLORS,
                hole=0.4,
            )
            fig_pie.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color=font_color, size=13),
                title_font_size=16,
            )
            with st.container(border=True):
                st.plotly_chart(fig_pie, use_container_width=True)

    # ── Resource usage ────────────────────────────────────────────────────────
    st.subheader("Local Resource Usage")
    col5, col6 = st.columns(2)

    with col5:
        fig_cpu = px.area(
            df, x="generation", y="process_cpu_pct",
            title="Process CPU % (sampled per generation)",
            color_discrete_sequence=["#8B7D6B"],
        )
        fig_cpu.update_layout(
            xaxis_title="Generation",
            yaxis_title="CPU %",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color=font_color, size=13),
            title_font_size=16,
        )
        with st.container(border=True):
            st.plotly_chart(fig_cpu, use_container_width=True)

    with col6:
        fig_mem = px.area(
            df, x="generation", y="process_mem_mb",
            title="Process Memory (RSS MB)",
            color_discrete_sequence=["#A0522D"],
        )
        fig_mem.update_layout(
            xaxis_title="Generation",
            yaxis_title="MB",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color=font_color, size=13),
            title_font_size=16,
        )
        with st.container(border=True):
            st.plotly_chart(fig_mem, use_container_width=True)

    # ── Per-generation table ──────────────────────────────────────────────────
    with st.expander("Per-Generation Detail Table"):
        display_cols = ["generation", "total_calls", "input_tokens",
                        "output_tokens", "wall_time_sec", "process_cpu_pct", "process_mem_mb"]
        present = [c for c in display_cols if c in df.columns]
        st.dataframe(
            df[present].sort_values("generation", ascending=False),
            hide_index=True,
            column_config={
                "generation":      st.column_config.NumberColumn("Gen", width="small"),
                "total_calls":     st.column_config.NumberColumn("Calls", width="small"),
                "input_tokens":    st.column_config.NumberColumn("In Tokens"),
                "output_tokens":   st.column_config.NumberColumn("Out Tokens"),
                "wall_time_sec":   st.column_config.NumberColumn("Wall Time (s)", format="%.1f"),
                "process_cpu_pct": st.column_config.NumberColumn("CPU %", format="%.1f"),
                "process_mem_mb":  st.column_config.NumberColumn("Mem (MB)", format="%.0f"),
            },
            use_container_width=True,
        )
