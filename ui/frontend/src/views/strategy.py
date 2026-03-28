import re
from datetime import datetime

import streamlit as st


def _parse_reflection_sections(content: str):
    """Parse ## SECTION / bullet markdown into [(title, [bullets])] list."""
    sections = []
    current_title = None
    current_bullets = []

    for line in content.splitlines():
        stripped = line.strip()
        if re.match(r'^##\s+', stripped):
            if current_title is not None:
                sections.append((current_title, current_bullets))
            current_title = re.sub(r'^##\s+', '', stripped).strip()
            current_bullets = []
        elif stripped.startswith(('-', '*')) and current_title is not None:
            bullet = re.sub(r'^[-*]\s*', '', stripped).strip()
            if bullet:
                current_bullets.append(bullet)

    if current_title is not None:
        sections.append((current_title, current_bullets))

    return sections


def render_learned_insights(content: str):
    """Parse and render long-term reflections as collapsible insight cards."""
    st.subheader("Learned Insights")

    if not content or not content.strip():
        st.caption("No insights yet -- reflections accumulate every N generations.")
        return

    sections = _parse_reflection_sections(content)

    if not sections:
        # Fallback: couldn't parse structure, render raw
        with st.expander("Insights", expanded=True):
            st.markdown(content)
        return

    for i, (title, bullets) in enumerate(sections):
        with st.expander(title.title(), expanded=(i == 0)):
            if bullets:
                for bullet in bullets:
                    st.markdown(f"- {bullet}")
            else:
                st.caption("No entries in this section.")


def render_strategies_table(df_strat):
    """Full strategies table: Idea, Direction, Status, Impact, Best Fitness."""
    st.subheader("Tested Strategies")

    if df_strat.empty:
        st.info("No strategy data available yet.")
        return

    status_order = {
        "Succeeded": 0,
        "Exploring": 1,
        "Queued": 2,
        "Interrupted": 3,
        "Abandoned": 4
    }

    df_display = df_strat.copy()

    df_display['_status_key'] = df_display['Status'].map(status_order).fillna(5)
    df_display = df_display.sort_values(
        ['Best_Fit', '_status_key'], ascending=[False, True]
    ).drop('_status_key', axis=1)

    # Summary cards: top 3 strategies before the full table
    top_n = min(3, len(df_display))
    if top_n > 0:
        badge_colors = {
            "Succeeded": "#6B7A4A",
            "Exploring": "#C96442",
            "Queued": "#8B7D6B",
            "Interrupted": "#B8860B",
            "Abandoned": "#A0522D",
        }
        card_cols = st.columns(top_n)
        for col, (_, row) in zip(card_cols, df_display.head(top_n).iterrows()):
            bg = badge_colors.get(row['Status'], "#8B7D6B")
            idea_text = str(row['Idea'])
            idea_short = idea_text[:70] + ("..." if len(idea_text) > 70 else "")
            with col:
                with st.container(border=True):
                    st.markdown(
                        f"<span style='background:{bg};color:#FAF7F2;padding:2px 10px;"
                        f"border-radius:12px;font-size:0.72rem;font-weight:700;"
                        f"letter-spacing:0.05em;'>{row['Status']}</span>",
                        unsafe_allow_html=True,
                    )
                    st.markdown(f"**{idea_short}**")
                    st.caption(f"Best fitness: {row['Best_Fit']:.4f}")
        st.markdown("")

    def color_status(val):
        if val == 'Succeeded':
            return 'color: #6B7A4A; font-weight: bold'
        elif val == 'Abandoned':
            return 'color: #A0522D; font-weight: bold'
        elif val == 'Interrupted':
            return 'color: #B8860B; font-weight: bold'
        elif val == 'Exploring':
            return 'color: #C96442; font-weight: bold'
        return ''

    col_cfg = {
        "Idea": st.column_config.TextColumn("Strategy Idea", width="large"),
        "Status": st.column_config.TextColumn("Status", width="small"),
        "Impact": st.column_config.TextColumn("Impact", width="small"),
        "Best_Fit": st.column_config.NumberColumn("Best Fitness", format="%.4f", width="small"),
    }
    if "Direction" in df_display.columns:
        col_cfg["Direction"] = st.column_config.TextColumn("Direction", width="small")

    st.dataframe(
        df_display.style.map(color_status, subset=['Status']),
        width='stretch',
        hide_index=True,
        column_config=col_cfg
    )


def render_steering_panel():
    """Expert guidance input at the bottom of the Strategy tab."""
    st.subheader("Expert Guidance")

    with st.container(border=True):
        if st.session_state.last_guidance_sent:
            last = st.session_state.last_guidance_sent
            st.info(f"**Last sent** ({last['timestamp']}):\n\n{last['text']}")

        expert_text = st.text_area(
            "Your guidance for the next evolution cycle:",
            placeholder="e.g. Focus on route-aware destroy operators that remove clusters of nearby nodes...",
            height=180,
            key="expert_guidance_input",
        )

        col_send, col_clear = st.columns([0.75, 0.25])
        with col_send:
            send_clicked = st.button(
                "Send to EvoAgent",
                use_container_width=True,
                type="primary",
                key="send_expert_guidance",
            )
        with col_clear:
            clear_clicked = st.button(
                "Clear",
                use_container_width=True,
                key="clear_expert_guidance",
            )

        if send_clicked:
            if expert_text.strip():
                st.session_state.last_guidance_sent = {
                    "text": expert_text.strip(),
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                }
                st.success("Guidance sent to EvoAgent.")
            else:
                st.warning("Please enter some guidance first.")

        if clear_clicked:
            st.session_state.expert_guidance_input = ""
            st.rerun()

        st.caption("Guidance will be applied in the next generation cycle.")
