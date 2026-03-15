"""
About Us & Sponsors page for SheepCat Work Tracker.

Displays information about the app, recognises sponsors with a
"First to the Flag" 🏁 section, and provides links for new supporters.
"""
import tkinter as tk
import webbrowser

import theme

# ── Sponsor data ──────────────────────────────────────────────────────────────
# Update these entries as new "first to the flag" sponsors are confirmed.

# First Buy Me a Coffee supporter
BMAC_FIRST_SPONSOR = {
    "name":   "Our First Supporter! 🎉",
    "note":   "First to back SheepCat on Buy Me a Coffee",
    "social": "",          # Add social URL when known, e.g. "https://twitter.com/..."
}

# First GitHub Sponsor – set to None until someone sponsors via GitHub
GITHUB_FIRST_SPONSOR = None

# Sponsorship URLs
URL_BMAC    = "https://buymeacoffee.com/chadders13h"
URL_GITHUB  = "https://github.com/sponsors/Chadders13"


class AboutPage(tk.Frame):
    """About Us & Sponsors page."""

    def __init__(self, parent):
        super().__init__(parent, bg=theme.WINDOW_BG)
        self._create_widgets()

    # ── Widget construction ───────────────────────────────────────────────────

    def _create_widgets(self):
        # Scrollable canvas so content fits on any window height
        canvas = tk.Canvas(self, bg=theme.WINDOW_BG, highlightthickness=0)
        scrollbar = tk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        # Inner frame that holds all content
        inner = tk.Frame(canvas, bg=theme.WINDOW_BG)
        inner_id = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _on_frame_configure(_e):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_configure(e):
            canvas.itemconfig(inner_id, width=e.width)

        inner.bind("<Configure>", _on_frame_configure)
        canvas.bind("<Configure>", _on_canvas_configure)

        # Mouse-wheel scrolling (scoped to this canvas only)
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind("<MouseWheel>", _on_mousewheel)
        canvas.bind("<Enter>", lambda _e: canvas.bind_all("<MouseWheel>", _on_mousewheel))
        canvas.bind("<Leave>", lambda _e: canvas.unbind_all("<MouseWheel>"))

        self._build_content(inner)

    def _build_content(self, parent):
        pad = {"padx": 30, "pady": 6}

        # ── Title ─────────────────────────────────────────────────────────────
        tk.Label(
            parent,
            text="🐱 SheepCat — Tracking My Work",
            font=theme.FONT_H1,
            bg=theme.WINDOW_BG, fg=theme.PRIMARY,
        ).pack(pady=(30, 4))

        tk.Label(
            parent,
            text="A gentle, neurodivergent-friendly work-tracker with AI support",
            font=theme.FONT_BODY,
            bg=theme.WINDOW_BG, fg=theme.MUTED,
        ).pack(pady=(0, 20))

        # ── Divider ───────────────────────────────────────────────────────────
        self._divider(parent)

        # ── About Us ──────────────────────────────────────────────────────────
        tk.Label(
            parent,
            text="About Us",
            font=theme.FONT_H2,
            bg=theme.WINDOW_BG, fg=theme.TEXT,
        ).pack(**pad)

        about_text = (
            "SheepCat is built with love for anyone who finds it hard to keep\n"
            "track of what they have done during the day. Whether you are\n"
            "neurodivergent, juggling many tasks, or just want a kinder way to\n"
            "log your work — SheepCat is here to help.\n\n"
            "The app is free and open-source under the AGPLv3 licence.\n"
            "Commercial licences are available — contact us for details."
        )
        tk.Label(
            parent,
            text=about_text,
            font=theme.FONT_BODY,
            bg=theme.WINDOW_BG, fg=theme.TEXT,
            justify="center",
        ).pack(**pad)

        # ── Divider ───────────────────────────────────────────────────────────
        self._divider(parent)

        # ── First to the Flag ─────────────────────────────────────────────────
        tk.Label(
            parent,
            text="🏁  First to the Flag  🏁",
            font=theme.FONT_H2,
            bg=theme.WINDOW_BG, fg=theme.ACCENT,
        ).pack(**pad)

        tk.Label(
            parent,
            text=(
                "These incredible people were the very first to support SheepCat.\n"
                "They are immortalised here in the app forever — thank you! 💜"
            ),
            font=theme.FONT_BODY,
            bg=theme.WINDOW_BG, fg=theme.MUTED,
            justify="center",
        ).pack(**pad)

        # ── Buy Me a Coffee — first sponsor ──────────────────────────────────
        bmac_frame = self._card(parent)

        tk.Label(
            bmac_frame,
            text="☕  Buy Me a Coffee",
            font=theme.FONT_H3,
            bg=theme.SURFACE_BG, fg=theme.PRIMARY,
        ).pack(pady=(12, 4))

        tk.Label(
            bmac_frame,
            text=BMAC_FIRST_SPONSOR["name"],
            font=theme.FONT_H2,
            bg=theme.SURFACE_BG, fg=theme.ACCENT,
        ).pack(pady=2)

        tk.Label(
            bmac_frame,
            text=BMAC_FIRST_SPONSOR["note"],
            font=theme.FONT_BODY,
            bg=theme.SURFACE_BG, fg=theme.TEXT,
        ).pack(pady=(0, 4))

        if BMAC_FIRST_SPONSOR.get("social"):
            theme.RoundedButton(
                bmac_frame,
                text="🔗  Visit their page",
                command=lambda: webbrowser.open(BMAC_FIRST_SPONSOR["social"]),
                bg=theme.PRIMARY_D, fg=theme.TEXT,
                font=theme.FONT_BODY, width=22,
            ).pack(pady=(4, 12))
        else:
            tk.Label(
                bmac_frame,
                text="Social links coming soon 💜",
                font=theme.FONT_SMALL,
                bg=theme.SURFACE_BG, fg=theme.MUTED,
            ).pack(pady=(0, 12))

        # ── GitHub Sponsors — first sponsor ───────────────────────────────────
        gh_frame = self._card(parent)

        tk.Label(
            gh_frame,
            text="🐙  GitHub Sponsors",
            font=theme.FONT_H3,
            bg=theme.SURFACE_BG, fg=theme.PRIMARY,
        ).pack(pady=(12, 4))

        if GITHUB_FIRST_SPONSOR:
            tk.Label(
                gh_frame,
                text=GITHUB_FIRST_SPONSOR["name"],
                font=theme.FONT_H2,
                bg=theme.SURFACE_BG, fg=theme.ACCENT,
            ).pack(pady=2)

            tk.Label(
                gh_frame,
                text=GITHUB_FIRST_SPONSOR["note"],
                font=theme.FONT_BODY,
                bg=theme.SURFACE_BG, fg=theme.TEXT,
            ).pack(pady=(0, 4))

            if GITHUB_FIRST_SPONSOR.get("social"):
                theme.RoundedButton(
                    gh_frame,
                    text="🔗  Visit their page",
                    command=lambda: webbrowser.open(GITHUB_FIRST_SPONSOR["social"]),
                    bg=theme.PRIMARY_D, fg=theme.TEXT,
                    font=theme.FONT_BODY, width=22,
                ).pack(pady=(4, 12))
            else:
                tk.Label(
                    gh_frame,
                    text="Social links coming soon 💜",
                    font=theme.FONT_SMALL,
                    bg=theme.SURFACE_BG, fg=theme.MUTED,
                ).pack(pady=(0, 12))
        else:
            tk.Label(
                gh_frame,
                text="Be the First! 🏁",
                font=theme.FONT_H2,
                bg=theme.SURFACE_BG, fg=theme.GREEN,
            ).pack(pady=2)

            tk.Label(
                gh_frame,
                text=(
                    "No one has sponsored via GitHub yet.\n"
                    "You could be the first — and be immortalised right here!"
                ),
                font=theme.FONT_BODY,
                bg=theme.SURFACE_BG, fg=theme.TEXT,
                justify="center",
            ).pack(pady=(0, 8))

            theme.RoundedButton(
                gh_frame,
                text="⭐  Become the First GitHub Sponsor",
                command=lambda: webbrowser.open(URL_GITHUB),
                bg=theme.PRIMARY_D, fg=theme.TEXT,
                font=theme.FONT_BODY, width=34,
            ).pack(pady=(0, 12))

        # ── Divider ───────────────────────────────────────────────────────────
        self._divider(parent)

        # ── Support Us ────────────────────────────────────────────────────────
        tk.Label(
            parent,
            text="Support Us 💜",
            font=theme.FONT_H2,
            bg=theme.WINDOW_BG, fg=theme.TEXT,
        ).pack(**pad)

        tk.Label(
            parent,
            text=(
                "If SheepCat has helped you, please consider supporting its development.\n"
                "Every coffee and sponsorship helps keep the project alive and growing!"
            ),
            font=theme.FONT_BODY,
            bg=theme.WINDOW_BG, fg=theme.MUTED,
            justify="center",
        ).pack(**pad)

        btn_row = tk.Frame(parent, bg=theme.WINDOW_BG)
        btn_row.pack(pady=10)

        theme.RoundedButton(
            btn_row,
            text="☕  Buy Me a Coffee",
            command=lambda: webbrowser.open(URL_BMAC),
            bg=theme.ACCENT, fg=theme.WINDOW_BG,
            font=theme.FONT_BODY_BOLD, width=22,
        ).pack(side="left", padx=10)

        theme.RoundedButton(
            btn_row,
            text="🐙  GitHub Sponsors",
            command=lambda: webbrowser.open(URL_GITHUB),
            bg=theme.PRIMARY, fg=theme.TEXT,
            font=theme.FONT_BODY_BOLD, width=22,
        ).pack(side="left", padx=10)

        # Bottom padding
        tk.Frame(parent, height=30, bg=theme.WINDOW_BG).pack()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _divider(self, parent):
        """Draw a subtle horizontal divider line."""
        tk.Frame(
            parent,
            height=1,
            bg=theme.BORDER,
        ).pack(fill="x", padx=30, pady=12)

    def _card(self, parent):
        """Return a surface-coloured card frame, centred in the parent."""
        outer = tk.Frame(parent, bg=theme.WINDOW_BG)
        outer.pack(pady=8, padx=60, fill="x")

        card = tk.Frame(outer, bg=theme.SURFACE_BG, bd=0, relief="flat")
        card.pack(fill="x")

        return card
