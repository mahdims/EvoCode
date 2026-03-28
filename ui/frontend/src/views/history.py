import streamlit as st

def render_history_inspector(df_metrics, key_suffix):
    st.markdown("---")

    # Initialize the reset counter if it doesn't exist
    if 'table_reset_id' not in st.session_state:
        st.session_state.table_reset_id = 0

    with st.expander("Generation History Inspector", expanded=True):
        if not df_metrics.empty:
            df_display = df_metrics.sort_values(by="generation", ascending=False).copy()

            def highlight_active_row(row):
                if row['generation'] == st.session_state.get('selected_generation'):
                    return ['background-color: rgba(255, 215, 0, 0.2); color: white'] * len(row)
                return [''] * len(row)

            styled_df = (
                df_display[[
                    'generation', 'global_best', 'avg_fitness', 'viability_rate', 'diversity'
                ]]
                .style
                .apply(highlight_active_row, axis=1)
                .format({
                    'generation': '{:.0f}', 'global_best': '{:.4f}',
                    'avg_fitness': '{:.4f}', 'viability_rate': '{:.3f}',
                    'diversity': '{:.3f}'
                })
            )

            column_config = {
                "generation": st.column_config.NumberColumn("Gen", width="small"),
                "global_best": st.column_config.NumberColumn("Best Fitness"),
                "avg_fitness": st.column_config.NumberColumn("Avg Fitness"),
                "viability_rate": st.column_config.NumberColumn("Completion"),
                "diversity": st.column_config.NumberColumn("Diversity"),
            }

            table_key = f"history_table_{st.session_state.table_reset_id}_{key_suffix}"

            event = st.dataframe(
                styled_df,
                width='stretch',
                hide_index=True,
                column_config=column_config,
                selection_mode="single-row",
                on_select="rerun",
                height=300,
                key=table_key
            )

            if len(event.selection.rows) > 0:
                clicked_row_index = event.selection.rows[0]

                previous_view_ids = st.session_state.get('table_snapshot_ids', [])
                if previous_view_ids and clicked_row_index < len(previous_view_ids):
                    target_gen = previous_view_ids[clicked_row_index]
                else:
                    # Fallback if IDs aren't cached correctly
                    target_gen = int(df_display.iloc[clicked_row_index]['generation'])

                if target_gen != st.session_state.get('selected_generation'):
                    st.session_state.selected_generation = target_gen

                    st.session_state.track_latest = False
                    if "sidebar_refresh_id" in st.session_state:
                        st.session_state.sidebar_refresh_id += 1

                    st.session_state.table_reset_id += 1

                    st.rerun()

            # Cache the IDs so we can map indices accurately on the next run
            st.session_state['table_snapshot_ids'] = df_display['generation'].tolist()

        else:
            st.info("No history data available yet.")
