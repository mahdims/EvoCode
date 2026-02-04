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

    COLOR_BEST_FITNESS = "#82aaff"
    COLOR_AVG_FITNESS = "#c792ea"
    COLOR_DIVERSITY = "#addb67"
    COLOR_VIABILITY = "#ef5350"
    COLOR_SELECTED = "#FFD700"

    COLOR_HIGH_FITNESS = "#00FF00"
    COLOR_MED_FITNESS = "#FFFF00"
    COLOR_LOW_FITNESS = "#808080"
    COLOR_SELECTED_NODE = "#FF0055"
    COLOR_PATH_HIGHLIGHT = "#00FFFF"

    DEFAULT_POLL_RATE = 2


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
