from pygments.style import Style
from pygments.token import (
    Comment,
    Keyword,
    Name,
    String,
    Error,
    Generic,
    Number,
    Operator,
    Punctuation,
    Text,
    Literal,
)

class UIConfig:
    DIFF_HEIGHT = 500
    GRAPH_HEIGHT = 500
    TABLE_HEIGHT = 200

    COLOR_BEST_FITNESS = "#C96442"   # terracotta
    COLOR_AVG_FITNESS = "#D4845E"    # warm salmon
    COLOR_DIVERSITY = "#8B7D6B"      # warm umber
    COLOR_VIABILITY = "#A0522D"      # sienna
    COLOR_SELECTED = "#D4A853"       # warm amber

    COLOR_HIGH_FITNESS = "#C96442"   # terracotta
    COLOR_MED_FITNESS = "#D4A853"    # amber
    COLOR_LOW_FITNESS = "#8B8070"    # warm gray
    COLOR_SELECTED_NODE = "#7B3F1A"  # dark sienna (outline/halo)
    COLOR_PATH_HIGHLIGHT = "#D4845E" # warm salmon

    DEFAULT_POLL_RATE = 2

    # Anthropic theme text colors
    LIGHT_TEXT = "#2D2B27"
    DARK_TEXT = "#E8E0D4"

    @staticmethod
    def plot_font_color(session_state) -> str:
        """Auto-detect theme from Streamlit config."""
        try:
            import streamlit as _st
            bg = _st.get_option("theme.backgroundColor") or ""
            # Dark backgrounds have low luminance
            if bg and bg.startswith("#") and len(bg) == 7:
                r, g, b = int(bg[1:3], 16), int(bg[3:5], 16), int(bg[5:7], 16)
                luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
                return UIConfig.DARK_TEXT if luminance < 0.5 else UIConfig.LIGHT_TEXT
        except Exception:
            pass
        return UIConfig.LIGHT_TEXT


class Colors:
    rosewater = "#f5e0dc"
    pink = "#f5c2e7"
    mauve = "#cba6f7"
    red = "#f38ba8"
    maroon = "#eba0ac"
    peach = "#fab387"
    yellow = "#f9e2af"
    green = "#a6e3a1"
    teal = "#94e2d5"
    sky = "#89dceb"
    blue = "#89b4fa"
    text = "#cdd6f4"
    overlay2 = "#9399b2"
    surface1 = "#45475a"
    base = "#1e1e2e"


class CatppuccinMochaStyle(Style):
    """
    Pygments style based on the Catppuccin VS Code theme.

    https://github.com/catppuccin/palette
    """

    name = "catppuccin-mocha"
    aliases = ["Catppuccin Mocha"]

    background_color = Colors.base
    highlight_color = Colors.surface1

    styles = {
        Text: Colors.text,
        Error: Colors.red,
        Comment: Colors.overlay2,
        Comment.Single: "italic",
        Comment.Multiline: "italic",
        Comment.Preproc: Colors.yellow,
        Comment.PreprocFile: Colors.green,
        Keyword: Colors.mauve,
        Keyword.Constant: Colors.blue,
        Operator: Colors.teal,
        Punctuation: Colors.overlay2,
        Punctuation.Marker: Colors.teal,
        Name.Attribute: Colors.yellow,
        Name.Builtin: f"{Colors.peach}",
        Name.Class: Colors.yellow,
        Name.Constant: Colors.blue,
        Name.Decorator: f"{Colors.sky}",
        Name.Function: Colors.blue,
        Name.Function.Magic: Colors.sky,
        Name.Tag: Colors.blue,
        Name.Variable: Colors.text,
        Name.Variable.Instance: Colors.rosewater,
        Literal: Colors.green,
        String: Colors.green,
        String.Backtick: Colors.green,
        String.Escape: Colors.pink,
        String.Regex: Colors.teal,
        String.Interpol: Colors.pink,
        String.Other: Colors.teal,
        Number: Colors.peach,
        Generic.Inserted: Colors.green,
        Generic.Deleted: Colors.red,
        Generic.Error: Colors.red,
        Generic.Traceback: Colors.red,
        Generic.Emph: f"{Colors.red}",
        Generic.Strong: f"bold {Colors.red}",
        Generic.EmphStrong: f"bold {Colors.red}",
        Generic.Heading: Colors.red,
        Generic.Prompt: Colors.teal,
        Generic.Output: Colors.green,
    }
