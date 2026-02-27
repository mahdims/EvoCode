import streamlit as st

def render_strategies_table(df_strat):
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

    df_display['sort_key'] = df_display['Status'].map(status_order).fillna(5)
    df_display = df_display.sort_values('sort_key').drop('sort_key', axis=1)

    def color_status(val):
        if val == 'Succeeded':
            return 'color: #addb67; font-weight: bold'
        elif val == 'Abandoned':
            return 'color: #ef5350; font-weight: bold'
        elif val == 'Interrupted':
            return 'color: #ecc48d; font-weight: bold'
        elif val == 'Exploring':
            return 'color: #82aaff; font-weight: bold'
        return ''

    st.dataframe(
        df_display.style.map(color_status, subset=['Status']),
        width='stretch',
        hide_index=True,
        column_config={
            "Direction": st.column_config.TextColumn("Direction", width="small"),
            "Idea": st.column_config.TextColumn("Strategy Idea", width="large"),
            "Status": st.column_config.TextColumn("Status", width="small"),
            "Impact": st.column_config.TextColumn("Impact", width="small"),
            # We hide Best_Fit but keep it for potential tooltip/sorting if needed
            "Best_Fit": None
        }
    )

def render_reflection_section(content):
    if not content:
        return

    st.markdown("---")
    st.header("Long-Term Reflections")

    with st.container(border=True):
        st.markdown(content)
