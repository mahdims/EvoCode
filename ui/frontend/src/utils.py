import json
import pandas as pd
import streamlit as st

def process_metrics_df(df: pd.DataFrame):
    """Parses the additional_metrics JSON column and extracts keys"""
    if df.empty:
        return df, ["Fitness"]

    available_metrics = set(["Fitness"])

    if "additional_metrics" not in df.columns:
        return df, list(sorted(available_metrics))

    # Helper to parse and extract
    def extract_extra(row):
        extras = {}
        try:
            if row['additional_metrics']:
                data = json.loads(row['additional_metrics'])
                for metric_name, values in data.items():
                    extras[f"{metric_name}_best"] = values.get('best')
                    extras[f"{metric_name}_avg"] = values.get('avg')
                    available_metrics.add(metric_name)
        except (json.JSONDecodeError, TypeError):
            pass
        return pd.Series(extras)

    # Apply extraction
    extra_df = df.apply(extract_extra, axis=1)
    df_final = pd.concat([df, extra_df], axis=1)

    return df_final, list(sorted(available_metrics))

def initialize_session_state():
    if "track_latest" not in st.session_state:
        st.session_state.track_latest = True

    if "selected_generation" not in st.session_state:
        st.session_state.selected_generation = None

    if "selected_node_id" not in st.session_state:
        st.session_state.selected_node_id = None

    if "sidebar_refresh_id" not in st.session_state:
        st.session_state.sidebar_refresh_id = 0

def get_current_generation(min_gen: int, max_gen: int) -> int:
    """
    Determine the current generation to display.
    Priority: selected_generation (if not tracking latest) > max_gen
    """
    if st.session_state.track_latest:
        return max_gen

    if st.session_state.selected_generation is not None:
        selected = st.session_state.selected_generation
        if min_gen <= selected <= max_gen:
            return selected

    return max_gen