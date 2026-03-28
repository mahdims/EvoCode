import re
import difflib
import streamlit as st

from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter

from style import Colors, CatppuccinMochaStyle, UIConfig

# Diff highlight colors
_BG_REMOVED  = "rgba(220, 50, 40, 0.22)"
_BG_ADDED    = "rgba(40, 180, 80, 0.22)"
_BG_EMPTY    = "rgba(0,0,0,0.04)"

# Gutter symbols
_SYM_REMOVED = "−"
_SYM_ADDED   = "+"
_SYM_EMPTY   = " "
_SYM_EQUAL   = " "

# Patterns for extracting method/function signatures
_METHOD_PATTERNS = [
    re.compile(r'(?:public|private|protected|static|\s)+[\w<>\[\]]+\s+(\w+)\s*\('),  # Java
    re.compile(r'def\s+(\w+)\s*\('),  # Python
    re.compile(r'function\s+(\w+)\s*\('),  # JS
]

def _extract_methods(lines):
    methods = set()
    for line in lines:
        for pattern in _METHOD_PATTERNS:
            match = pattern.search(line)
            if match:
                methods.add(match.group(1))
    return methods


def render_diff_summary(old_code: str, new_code: str):
    """Render a compact summary of what changed between two code versions."""
    old_lines = old_code.splitlines() if old_code else []
    new_lines = new_code.splitlines() if new_code else []

    matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
    added = removed = changed = 0
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'insert':
            added += j2 - j1
        elif tag == 'delete':
            removed += i2 - i1
        elif tag == 'replace':
            changed += max(i2 - i1, j2 - j1)

    old_methods = _extract_methods(old_lines)
    new_methods = _extract_methods(new_lines)
    added_methods = new_methods - old_methods
    removed_methods = old_methods - new_methods

    parts = []
    if added:
        parts.append(f"**+{added}** added")
    if removed:
        parts.append(f"**-{removed}** removed")
    if changed:
        parts.append(f"**~{changed}** changed")
    if not parts:
        parts.append("No changes")

    summary = f"Lines: {' / '.join(parts)}"

    method_notes = []
    if added_methods:
        method_notes.append(f"New: `{'`, `'.join(sorted(added_methods))}`")
    if removed_methods:
        method_notes.append(f"Removed: `{'`, `'.join(sorted(removed_methods))}`")

    if method_notes:
        summary += "  |  Methods: " + " / ".join(method_notes)

    st.caption(summary)


def render_diff_view(old_code: str, new_code: str, left_title: str = "Baseline", right_title: str = "Target", language: str = "java"):
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

    # Each entry: (html_text, background_color, gutter_symbol)
    left_output = []
    right_output = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            for k in range(i1, i2):
                text = old_html[k] if k < len(old_html) else old_lines[k]
                left_output.append((text, "transparent", _SYM_EQUAL))
                right_output.append((text, "transparent", _SYM_EQUAL))

        elif tag == 'replace':
            max_len = max(i2 - i1, j2 - j1)
            left_chunk  = [old_html[k] if k < len(old_html) else old_lines[k] for k in range(i1, i2)]
            right_chunk = [new_html[k] if k < len(new_html) else new_lines[k] for k in range(j1, j2)]
            # Pad shorter side with blank lines
            while len(left_chunk) < max_len:
                left_chunk.append("&nbsp;")
            while len(right_chunk) < max_len:
                right_chunk.append("&nbsp;")
            for text in left_chunk:
                left_output.append((text, _BG_REMOVED, _SYM_REMOVED))
            for text in right_chunk:
                right_output.append((text, _BG_ADDED, _SYM_ADDED))

        elif tag == 'delete':
            for k in range(i1, i2):
                text = old_html[k] if k < len(old_html) else old_lines[k]
                left_output.append((text, _BG_REMOVED, _SYM_REMOVED))
                right_output.append(("&nbsp;", _BG_EMPTY, _SYM_EMPTY))

        elif tag == 'insert':
            for k in range(j1, j2):
                text = new_html[k] if k < len(new_html) else new_lines[k]
                left_output.append(("&nbsp;", _BG_EMPTY, _SYM_EMPTY))
                right_output.append((text, _BG_ADDED, _SYM_ADDED))

    def build_html(lines, title):
        toolbar = (
            f'<div style="background:rgba(20,20,36,0.97);padding:7px 12px;'
            f'border-bottom:1px solid rgba(139,125,107,0.2);display:flex;'
            f'align-items:center;">'
            f'<span style="font-size:0.85rem;font-weight:600;color:#E8E0D4;">{title}</span>'
            f'</div>'
        )
        rows = []
        for i, (text, bg, sym) in enumerate(lines, 1):
            sym_color = "#e05550" if sym == _SYM_REMOVED else ("#3db868" if sym == _SYM_ADDED else "transparent")
            gutter = (
                f'<div style="color:#6B5D52;user-select:none;padding:0 6px;'
                f'min-width:36px;text-align:right;flex-shrink:0;display:flex;'
                f'align-items:center;justify-content:flex-end;gap:4px;'
                f'border-right:1px solid rgba(139,125,107,0.15);">'
                f'<span style="color:{sym_color};font-weight:700;width:10px;text-align:center;">{sym}</span>'
                f'<span>{i}</span>'
                f'</div>'
            )
            content = f'<div style="flex:1;background-color:{bg};white-space:pre;padding:0 8px;">{text}</div>'
            rows.append(f'<div style="display:flex;">{gutter}{content}</div>')
        return (
            f'<div style="font-family:monospace;font-size:12px;'
            f'background-color:{CatppuccinMochaStyle.background_color};'
            f'color:{Colors.text};border-radius:8px;overflow:hidden;'
            f'border:1px solid rgba(139,125,107,0.25);">'
            f'{toolbar}'
            f'<div style="overflow-x:auto;height:{UIConfig.DIFF_HEIGHT}px;overflow-y:auto;">'
            + "".join(rows)
            + f'</div></div>'
        )

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(build_html(left_output, left_title), unsafe_allow_html=True)
    with col2:
        st.markdown(build_html(right_output, right_title), unsafe_allow_html=True)


def render_diff_tab(dao, min_gen: int, max_gen: int, language: str = "java"):
    """Full diff tab: generation dropdowns above each panel, then colored diff."""
    gen_options = list(range(min_gen, max_gen + 1))

    col_left_sel, col_right_sel = st.columns(2)
    with col_left_sel:
        left_gen = st.selectbox(
            "Left generation",
            options=gen_options,
            index=0,
            key="diff_left_gen",
        )
    with col_right_sel:
        right_gen = st.selectbox(
            "Right generation",
            options=gen_options,
            index=len(gen_options) - 1,
            key="diff_right_gen",
        )

    left_snapshot  = dao.get_snapshot(int(left_gen))
    right_snapshot = dao.get_snapshot(int(right_gen))

    if left_snapshot is None:
        st.warning(f"No data available for Generation {left_gen}")
        return
    if right_snapshot is None:
        st.warning(f"No data available for Generation {right_gen}")
        return

    left_code  = left_snapshot.get('best_code_snippet', '') or ''
    right_code = right_snapshot.get('best_code_snippet', '') or ''

    render_diff_summary(left_code, right_code)
    render_diff_view(left_code, right_code, f"Gen {left_gen}", f"Gen {right_gen}", language)
