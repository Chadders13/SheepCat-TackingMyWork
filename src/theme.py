"""
SheepCat brand theme constants and ttk style configuration.

Colour tokens and typography match the SheepCat style guide so the desktop
application shares the same visual identity as the website.

Two built-in themes are available:
  "Classic"      – original dark slate/indigo palette
  "Glass Purple" – soft modern purple with rounded, soothing tones
"""
import tkinter as tk
from tkinter import ttk

# ── Built-in theme palettes ───────────────────────────────────────────────────

THEMES = {
    "Classic": {
        "WINDOW_BG":  "#0f172a",
        "SURFACE_BG": "#1e1b4b",
        "INPUT_BG":   "#252250",
        "PRIMARY":    "#818cf8",
        "PRIMARY_D":  "#6366f1",
        "ACCENT":     "#fb923c",
        "GREEN":      "#4ade80",
        "RED":        "#f87171",
        "TEXT":       "#f1f5f9",
        "MUTED":      "#94a3b8",
        "BORDER":     "#2e2b5e",
    },
    "Glass Purple": {
        # Soft deep-purple background with a gentle, soothing feel
        "WINDOW_BG":  "#1a0e30",   # Rich midnight purple
        "SURFACE_BG": "#2d1a52",   # Frosted card surface
        "INPUT_BG":   "#3b2270",   # Slightly lighter input fields
        "PRIMARY":    "#c084fc",   # Soft lavender – buttons & accents
        "PRIMARY_D":  "#a855f7",   # Medium purple – hover / headings
        "ACCENT":     "#f0abfc",   # Pink-lilac – use sparingly
        "GREEN":      "#86efac",   # Mint green – success
        "RED":        "#fca5a5",   # Soft coral – danger
        "TEXT":       "#faf5ff",   # Warm near-white – body text
        "MUTED":      "#d8b4fe",   # Muted lavender – secondary text
        "BORDER":     "#5b21b6",   # Violet border
    },
}

THEME_NAMES = list(THEMES.keys())

# ── Active colour tokens (module-level – updated by apply_theme) ──────────────
WINDOW_BG   = THEMES["Classic"]["WINDOW_BG"]
SURFACE_BG  = THEMES["Classic"]["SURFACE_BG"]
INPUT_BG    = THEMES["Classic"]["INPUT_BG"]
PRIMARY     = THEMES["Classic"]["PRIMARY"]
PRIMARY_D   = THEMES["Classic"]["PRIMARY_D"]
ACCENT      = THEMES["Classic"]["ACCENT"]
GREEN       = THEMES["Classic"]["GREEN"]
RED         = THEMES["Classic"]["RED"]
TEXT        = THEMES["Classic"]["TEXT"]
MUTED       = THEMES["Classic"]["MUTED"]
BORDER      = THEMES["Classic"]["BORDER"]

# ── Typography ────────────────────────────────────────────────────────────────
_FONT = "Segoe UI"

FONT_BODY       = (_FONT, 10)
FONT_BODY_BOLD  = (_FONT, 10, "bold")
FONT_H1         = (_FONT, 18, "bold")
FONT_H2         = (_FONT, 14, "bold")
FONT_H3         = (_FONT, 12, "bold")
FONT_SMALL      = (_FONT, 9)
FONT_MONO       = ("Consolas", 10)


def apply_theme(name: str) -> None:
    """
    Switch the active colour tokens to the named theme.

    Must be called *before* any widgets are created (or before
    ``setup_ttk_styles`` is called) so that every widget picks up the
    correct colours when it is first built.

    Args:
        name: One of the keys in ``THEMES`` (e.g. "Classic", "Glass Purple").
              Falls back to "Classic" if the name is not recognised.
    """
    palette = THEMES.get(name, THEMES["Classic"])
    global WINDOW_BG, SURFACE_BG, INPUT_BG, PRIMARY, PRIMARY_D
    global ACCENT, GREEN, RED, TEXT, MUTED, BORDER
    WINDOW_BG  = palette["WINDOW_BG"]
    SURFACE_BG = palette["SURFACE_BG"]
    INPUT_BG   = palette["INPUT_BG"]
    PRIMARY    = palette["PRIMARY"]
    PRIMARY_D  = palette["PRIMARY_D"]
    ACCENT     = palette["ACCENT"]
    GREEN      = palette["GREEN"]
    RED        = palette["RED"]
    TEXT       = palette["TEXT"]
    MUTED      = palette["MUTED"]
    BORDER     = palette["BORDER"]


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


# ── RoundedButton ─────────────────────────────────────────────────────────────

class RoundedButton(tk.Canvas):
    """
    A drop-in replacement for tk.Button with rounded corners and a
    glass-style highlight on the upper half of the button.

    Accepts the same common keyword arguments as tk.Button (``text``,
    ``command``, ``bg``/``background``, ``fg``/``foreground``, ``font``,
    ``width`` in character units, ``state``, ``cursor``, ``padx``,
    ``pady``).  Arguments that are irrelevant to a Canvas widget
    (``relief``, ``activebackground``, ``activeforeground``,
    ``selectcolor``) are silently ignored.
    """

    # Approximate pixel width of one character for sizing
    _CHAR_PX = 7.5
    # Inner text-area height (px) before padding
    _LINE_PX = 18

    def __init__(self, parent, text="", command=None, bg=None, fg=None,
                 font=None, width=None, state=tk.NORMAL, cursor="hand2",
                 padx=8, pady=5, radius=12, **kwargs):
        _bg = bg or PRIMARY
        _fg = fg or TEXT
        _font = font or FONT_BODY

        # Auto-size by text length when no explicit width given (+4 chars breathing room)
        char_w = width if width is not None else (len(text) + 4)
        px_w = max(int(char_w * self._CHAR_PX + 2 * padx + 4), 50)  # +4px border, min 50px
        px_h = self._LINE_PX + 2 * pady
        _radius = min(radius, px_h // 2 - 1, px_w // 2 - 1)  # -1 keeps arc inside canvas edge

        # Canvas background must match the parent so transparency is faked
        try:
            canvas_bg = parent.cget('bg')
        except Exception:
            canvas_bg = WINDOW_BG

        # Strip options that Canvas does not understand
        for _k in ('relief', 'activebackground', 'activeforeground', 'selectcolor'):
            kwargs.pop(_k, None)

        super().__init__(
            parent, width=px_w, height=px_h,
            bg=canvas_bg, highlightthickness=0, bd=0,
            cursor=cursor if state == tk.NORMAL else "arrow",
            **kwargs,
        )

        self._text = text
        self._command = command
        self._bg = _bg
        self._fg = _fg
        self._font = _font
        self._cursor = cursor  # store for state-change restores
        self._radius = _radius
        self._px_w = px_w
        self._px_h = px_h
        self._state = state
        self._hovered = False
        self._pressed = False

        self._draw()

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)

    # ── Public API ────────────────────────────────────────────────────────────

    def config(self, **kwargs):
        """Support the most common tk.Button config attributes."""
        redraw = False
        if 'state' in kwargs:
            self._state = kwargs.pop('state')
            super().config(cursor=self._cursor if self._state == tk.NORMAL else "arrow")
            redraw = True
        if 'text' in kwargs:
            self._text = kwargs.pop('text')
            redraw = True
        for k in ('bg', 'background'):
            if k in kwargs:
                self._bg = kwargs.pop(k)
                redraw = True
        for k in ('fg', 'foreground'):
            if k in kwargs:
                self._fg = kwargs.pop(k)
                redraw = True
        # Silently drop unsupported options
        for k in ('relief', 'activebackground', 'activeforeground'):
            kwargs.pop(k, None)
        if kwargs:
            super().config(**kwargs)
        if redraw:
            self._draw()

    configure = config

    # ── Colour helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _lighten(color, amount):
        r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
        return (f"#{min(255, r + amount):02x}"
                f"{min(255, g + amount):02x}"
                f"{min(255, b + amount):02x}")

    @staticmethod
    def _darken(color, amount):
        r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
        return (f"#{max(0, r - amount):02x}"
                f"{max(0, g - amount):02x}"
                f"{max(0, b - amount):02x}")

    # ── Drawing ───────────────────────────────────────────────────────────────

    def _draw(self):
        self.delete("all")
        w, h, r = self._px_w, self._px_h, self._radius
        is_active = (self._state == tk.NORMAL)

        # Resolve base colour
        base = self._bg if is_active else self._darken(self._bg, 55)
        if is_active:
            if self._pressed:
                base = self._darken(base, 20)
            elif self._hovered:
                base = self._lighten(base, 20)

        # 1 ── Full rounded-rect body
        self._fill_rrect(2, 2, w - 2, h - 2, r, base)

        # 2 ── Glass highlight: lighter band on the top ~44% of height
        if is_active:
            gh = max(r + 2, int(h * 0.44))   # 0.44 = top 44% looks best for glass illusion
            glass = self._lighten(base, 52 if not self._pressed else 15)  # 52=normal glow, 15=pressed glow
            self._fill_top_band(2, 2, w - 2, gh, r, glass)

        # 3 ── Subtle inner-glow border
        border = self._lighten(base, 42) if is_active else self._darken(base, 10)
        self._stroke_rrect(2, 2, w - 2, h - 2, r, border)

        # 4 ── Label
        txt_fg = self._fg if is_active else self._darken(self._fg, 80)
        self.create_text(w // 2, h // 2, text=self._text,
                         fill=txt_fg, font=self._font, anchor="center")

    def _fill_rrect(self, x1, y1, x2, y2, r, color):
        """Fill a rounded rectangle using pieslice arcs + centre rectangles."""
        kw = dict(style='pieslice', fill=color, outline=color)
        self.create_arc(x1,      y1,      x1+2*r, y1+2*r, start=90,  extent=90, **kw)
        self.create_arc(x2-2*r,  y1,      x2,     y1+2*r, start=0,   extent=90, **kw)
        self.create_arc(x1,      y2-2*r,  x1+2*r, y2,     start=180, extent=90, **kw)
        self.create_arc(x2-2*r,  y2-2*r,  x2,     y2,     start=270, extent=90, **kw)
        self.create_rectangle(x1+r, y1,   x2-r, y2,   fill=color, outline="")
        self.create_rectangle(x1,   y1+r, x2,   y2-r, fill=color, outline="")

    def _fill_top_band(self, x1, y1, x2, gh, r, color):
        """Fill only the top glass band (rounded top corners, flat bottom edge)."""
        kw = dict(style='pieslice', fill=color, outline=color)
        self.create_arc(x1,     y1, x1+2*r, y1+2*r, start=90, extent=90, **kw)
        self.create_arc(x2-2*r, y1, x2,     y1+2*r, start=0,  extent=90, **kw)
        # Flat top strip between the two corner arcs
        self.create_rectangle(x1+r, y1, x2-r, min(y1+r, gh), fill=color, outline="")
        # Band body below arc zone
        if gh > y1 + r:
            self.create_rectangle(x1, y1+r, x2, gh, fill=color, outline="")

    def _stroke_rrect(self, x1, y1, x2, y2, r, color):
        """Draw only the outline of a rounded rectangle."""
        kw = dict(style='arc', outline=color)
        self.create_arc(x1,     y1,      x1+2*r, y1+2*r, start=90,  extent=90, **kw)
        self.create_arc(x2-2*r, y1,      x2,     y1+2*r, start=0,   extent=90, **kw)
        self.create_arc(x1,     y2-2*r,  x1+2*r, y2,     start=180, extent=90, **kw)
        self.create_arc(x2-2*r, y2-2*r,  x2,     y2,     start=270, extent=90, **kw)
        self.create_line(x1+r, y1,   x2-r, y1,   fill=color)
        self.create_line(x1+r, y2,   x2-r, y2,   fill=color)
        self.create_line(x1,   y1+r, x1,   y2-r, fill=color)
        self.create_line(x2,   y1+r, x2,   y2-r, fill=color)

    # ── Event handlers ────────────────────────────────────────────────────────

    def _on_enter(self, _e):
        if self._state == tk.NORMAL:
            self._hovered = True
            self._draw()

    def _on_leave(self, _e):
        self._hovered = False
        self._pressed = False
        if self._state == tk.NORMAL:
            self._draw()

    def _on_press(self, _e):
        if self._state == tk.NORMAL:
            self._pressed = True
            self._draw()

    def _on_release(self, _e):
        if self._state == tk.NORMAL:
            was_pressed = self._pressed
            self._pressed = False
            self._hovered = True
            self._draw()
            if was_pressed and self._command:
                self._command()
