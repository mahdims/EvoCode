import difflib
import streamlit as st

from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter

from style import Colors, CatppuccinMochaStyle, UIConfig

def render_diff_view(old_code: str, new_code: str, left_title: str = "Baseline Code", right_title: str = "Current Code", language: str = "java"):
    if not old_code:
        old_code = ""
    if not new_code:
        new_code = ""

    old_lines = old_code.splitlines()
    new_lines = new_code.splitlines()

    formatter = HtmlFormatter(style=CatppuccinMochaStyle, nowrap=True, noclasses=True)

    try:
        lexer = get_lexer_by_name(language)
        old_html = highlight(old_code, lexer, formatter).splitlines()
        new_html = highlight(new_code, lexer, formatter).splitlines()
    except Exception:
        old_html = old_lines
        new_html = new_lines

    if not old_html and old_lines:
        old_html = [""] * len(old_lines)
    if not new_html and new_lines:
        new_html = [""] * len(new_lines)

    matcher = difflib.SequenceMatcher(None, old_lines, new_lines)

    col1, col2 = st.columns(2)
    with col1:
        st.caption(left_title)
    with col2:
        st.caption(right_title)

    left_output = []
    right_output = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            for k in range(i1, i2):
                text = old_html[k] if k < len(old_html) else old_lines[k]
                left_output.append((text, "transparent"))
                right_output.append((text, "transparent"))

        elif tag == 'replace':
            for k in range(i1, i2):
                text = old_html[k] if k < len(old_html) else old_lines[k]
                left_output.append((text, "rgba(255, 0, 0, 0.25)"))
            for k in range(j1, j2):
                text = new_html[k] if k < len(new_html) else new_lines[k]
                right_output.append((text, "rgba(0, 255, 0, 0.25)"))

        elif tag == 'delete':
            for k in range(i1, i2):
                text = old_html[k] if k < len(old_html) else old_lines[k]
                left_output.append((text, "rgba(255, 0, 0, 0.25)"))
                right_output.append(("&nbsp;", "transparent"))

        elif tag == 'insert':
            for k in range(j1, j2):
                left_output.append(("&nbsp;", "transparent"))
                text = new_html[k] if k < len(new_html) else new_lines[k]
                right_output.append((text, "rgba(0, 255, 0, 0.25)"))

    def build_html(lines):
        html = f'<div style="font-family: monospace; font-size: 12px; background-color: {CatppuccinMochaStyle.background_color}; color: {Colors.text}; padding: 10px; border-radius: 5px; overflow-x: auto; height: {UIConfig.DIFF_HEIGHT}px; overflow-y: auto;">'
        for text, bg in lines:
            html += f'<div style="background-color: {bg}; white-space: pre;">{text}</div>'
        html += '</div>'
        return html

    with col1:
        st.markdown(build_html(left_output), unsafe_allow_html=True)
    with col2:
        st.markdown(build_html(right_output), unsafe_allow_html=True)