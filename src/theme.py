"""
SheepCat brand theme constants and ttk style configuration.

Colour tokens and typography match the SheepCat style guide so the desktop
application shares the same visual identity as the website.
"""
from tkinter import ttk

# ── Colours ───────────────────────────────────────────────────────────────────
# Background gradient stops (used as solid equivalents in a desktop context)
WINDOW_BG   = "#0f172a"   # Slate Dark – root window / outer frames
SURFACE_BG  = "#1e1b4b"   # Deep Indigo Night – inner frames / cards
INPUT_BG    = "#252250"   # Slightly lighter – entry / text widgets

# Brand & UI colours
PRIMARY     = "#818cf8"   # Indigo primary – buttons, accents, step numbers
PRIMARY_D   = "#6366f1"   # Deeper indigo – hover / treeview headings
ACCENT      = "#fb923c"   # Warm orange – use sparingly
GREEN       = "#4ade80"   # Success states
RED         = "#f87171"   # Danger / stop

# Text colours
TEXT        = "#f1f5f9"   # Primary body copy and headings  (≈ 15:1 contrast AAA)
MUTED       = "#94a3b8"   # Secondary / descriptive copy    (≈ 5:1  contrast AA)

# Surface border (visible divider on the dark background)
BORDER      = "#2e2b5e"

# ── Typography ────────────────────────────────────────────────────────────────
_FONT = "Segoe UI"

FONT_BODY       = (_FONT, 10)
FONT_BODY_BOLD  = (_FONT, 10, "bold")
FONT_H1         = (_FONT, 18, "bold")
FONT_H2         = (_FONT, 14, "bold")
FONT_H3         = (_FONT, 12, "bold")
FONT_SMALL      = (_FONT, 9)
FONT_MONO       = ("Consolas", 10)


# ── ttk style setup ───────────────────────────────────────────────────────────

def setup_ttk_styles(root):
    """
    Configure ttk widget styles to match the SheepCat brand theme.

    Call once from the application root window before creating any pages.
    """
    style = ttk.Style(root)
    style.theme_use("clam")   # clam allows the most colour customisation

    # Frames & labels
    style.configure("TFrame", background=WINDOW_BG)
    style.configure("TLabel", background=WINDOW_BG, foreground=TEXT, font=FONT_BODY)

    # Scrollbar
    style.configure(
        "TScrollbar",
        background=SURFACE_BG,
        troughcolor=WINDOW_BG,
        arrowcolor=MUTED,
        bordercolor=WINDOW_BG,
        relief="flat",
    )
    style.map("TScrollbar", background=[("active", PRIMARY_D)])

    # Combobox
    style.configure(
        "TCombobox",
        fieldbackground=INPUT_BG,
        background=SURFACE_BG,
        foreground=TEXT,
        selectbackground=PRIMARY_D,
        selectforeground=TEXT,
        arrowcolor=TEXT,
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", INPUT_BG)],
        foreground=[("readonly", TEXT)],
        selectbackground=[("readonly", PRIMARY_D)],
    )

    # Treeview
    style.configure(
        "Treeview",
        background=SURFACE_BG,
        foreground=TEXT,
        rowheight=26,
        fieldbackground=SURFACE_BG,
        font=FONT_BODY,
        borderwidth=0,
    )
    style.configure(
        "Treeview.Heading",
        background=PRIMARY_D,
        foreground=TEXT,
        font=FONT_BODY_BOLD,
        relief="flat",
    )
    style.map(
        "Treeview",
        background=[("selected", PRIMARY_D)],
        foreground=[("selected", TEXT)],
    )
    style.map(
        "Treeview.Heading",
        background=[("active", PRIMARY)],
    )
