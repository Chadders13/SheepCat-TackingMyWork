"""
Onboarding dialogs for SheepCat Work Tracker.

Implements three sequential dialogs shown on first launch:

1. EngineConnectionDialog  – tests the Ollama endpoint and lets the user
   configure a custom host/port when the default fails.
2. ModelSelectionDialog    – presents a curated menu of recommended models.
3. ModelPullDialog         – streams the pull progress with a progress bar.
"""

import threading
import tkinter as tk
from tkinter import ttk, messagebox

import theme
from ollama_client import (
    DEFAULT_OLLAMA_BASE_URL,
    RECOMMENDED_MODELS,
    check_connection,
    pull_model,
)


# ──────────────────────────────────────────────────────────────────────────────
# Engine Connection Dialog
# ──────────────────────────────────────────────────────────────────────────────

class EngineConnectionDialog(tk.Toplevel):
    """Modal dialog for establishing a connection to an Ollama engine.

    The dialog tests ``base_url`` immediately on open.  If the test succeeds
    it closes automatically and the ``result`` attribute is set to the working
    URL.  If the test fails the user is prompted to enter a custom host/port
    and retry.

    Attributes:
        result (str | None): The validated base URL on success, or ``None``
            when the user dismissed the dialog without a working connection.
        available_models (list[str]): Model names reported by ``/api/tags``.
    """

    def __init__(self, parent, base_url: str = DEFAULT_OLLAMA_BASE_URL):
        super().__init__(parent)
        self.title("AI Engine Connection")
        self.geometry("480x320")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.configure(bg=theme.WINDOW_BG)

        self.result: str | None = None
        self.available_models: list = []
        self._base_url = base_url

        self._build_ui()
        self._try_connect(base_url)

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.wait_window(self)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        tk.Label(
            self, text="AI Engine Connection",
            font=theme.FONT_H2, bg=theme.WINDOW_BG, fg=theme.TEXT,
        ).pack(pady=(18, 4))

        tk.Label(
            self,
            text=(
                "SheepCat needs to reach an Ollama instance to generate\n"
                "task summaries.  Testing the default endpoint…"
            ),
            font=theme.FONT_BODY, bg=theme.WINDOW_BG, fg=theme.MUTED,
            justify="center",
        ).pack(pady=(0, 10))

        # Status indicator
        self._status_var = tk.StringVar(value="Connecting…")
        tk.Label(
            self, textvariable=self._status_var,
            font=theme.FONT_BODY_BOLD, bg=theme.WINDOW_BG, fg=theme.PRIMARY,
        ).pack(pady=4)

        # Custom host/port row (hidden until needed)
        self._custom_frame = tk.Frame(self, bg=theme.WINDOW_BG)

        tk.Label(
            self._custom_frame, text="Host:",
            font=theme.FONT_BODY, bg=theme.WINDOW_BG, fg=theme.MUTED,
        ).grid(row=0, column=0, padx=(15, 5), pady=6, sticky="e")
        self._host_var = tk.StringVar(value="localhost")
        tk.Entry(
            self._custom_frame, textvariable=self._host_var, width=22,
            bg=theme.INPUT_BG, fg=theme.TEXT, insertbackground=theme.TEXT,
        ).grid(row=0, column=1, padx=5, pady=6, sticky="w")

        tk.Label(
            self._custom_frame, text="Port:",
            font=theme.FONT_BODY, bg=theme.WINDOW_BG, fg=theme.MUTED,
        ).grid(row=0, column=2, padx=(10, 5), pady=6, sticky="e")
        self._port_var = tk.StringVar(value="11434")
        tk.Entry(
            self._custom_frame, textvariable=self._port_var, width=7,
            bg=theme.INPUT_BG, fg=theme.TEXT, insertbackground=theme.TEXT,
        ).grid(row=0, column=3, padx=5, pady=6, sticky="w")

        # Buttons
        btn_frame = tk.Frame(self, bg=theme.WINDOW_BG)
        btn_frame.pack(side="bottom", pady=15)

        self._retry_btn = tk.Button(
            btn_frame, text="Connect", command=self._on_retry,
            bg=theme.PRIMARY_D, fg=theme.TEXT,
            font=theme.FONT_BODY, width=12, relief="flat", cursor="hand2",
        )
        self._retry_btn.pack(side="left", padx=6)
        self._retry_btn.pack_forget()  # hidden initially

        tk.Button(
            btn_frame, text="Cancel", command=self._on_close,
            bg=theme.SURFACE_BG, fg=theme.TEXT,
            font=theme.FONT_BODY, width=10, relief="flat", cursor="hand2",
        ).pack(side="left", padx=6)

    # ------------------------------------------------------------------
    # Connection logic
    # ------------------------------------------------------------------

    def _try_connect(self, base_url: str):
        """Run a connection test in a background thread."""
        self._status_var.set("Connecting…")
        threading.Thread(
            target=self._connect_worker, args=(base_url,), daemon=True,
        ).start()

    def _connect_worker(self, base_url: str):
        success, models = check_connection(base_url)
        self.after(0, self._on_connect_result, success, models, base_url)

    def _on_connect_result(self, success: bool, models: list, base_url: str):
        if success:
            self.result = base_url
            self.available_models = models
            self._status_var.set("✓ Connected successfully!")
            self.after(600, self.destroy)
        else:
            self._status_var.set(
                "✗ Could not connect.  Enter a custom host/port and try again."
            )
            self._custom_frame.pack(pady=6)
            self._retry_btn.pack(side="left", padx=6)

    def _on_retry(self):
        host = self._host_var.get().strip()
        port = self._port_var.get().strip()
        if not host or not port:
            messagebox.showerror(
                "Invalid Input", "Please enter both a host and a port.",
                parent=self,
            )
            return
        base_url = f"http://{host}:{port}"
        self._base_url = base_url
        self._try_connect(base_url)

    def _on_close(self):
        self.result = None
        self.destroy()


# ──────────────────────────────────────────────────────────────────────────────
# Model Selection Dialog
# ──────────────────────────────────────────────────────────────────────────────

class ModelSelectionDialog(tk.Toplevel):
    """Presents a curated list of recommended models for the user to choose.

    Attributes:
        result (str | None): The selected model name, or ``None`` when
            dismissed without a selection.
        model_already_present (bool): ``True`` when the chosen model is already
            available on the Ollama instance (no pull required).
    """

    def __init__(self, parent, available_models: list):
        super().__init__(parent)
        self.title("Select AI Model")
        self.geometry("560x420")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.configure(bg=theme.WINDOW_BG)

        self.result: str | None = None
        self.model_already_present: bool = False
        self._available_models = available_models

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.wait_window(self)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        tk.Label(
            self, text="Choose Your AI Model",
            font=theme.FONT_H2, bg=theme.WINDOW_BG, fg=theme.TEXT,
        ).pack(pady=(18, 4))

        tk.Label(
            self,
            text=(
                "Select a model for generating task summaries.\n"
                "Missing models will be downloaded automatically."
            ),
            font=theme.FONT_BODY, bg=theme.WINDOW_BG, fg=theme.MUTED,
            justify="center",
        ).pack(pady=(0, 12))

        self._selected_var = tk.StringVar(value=RECOMMENDED_MODELS[0]["name"])

        for model in RECOMMENDED_MODELS:
            self._build_model_row(model)

        # Separator
        tk.Frame(self, height=1, bg=theme.BORDER).pack(fill="x", padx=20, pady=10)

        # Confirm button
        tk.Button(
            self, text="Use Selected Model", command=self._on_confirm,
            bg=theme.GREEN, fg=theme.WINDOW_BG,
            font=theme.FONT_BODY_BOLD, width=20, relief="flat", cursor="hand2",
        ).pack(pady=10)

    def _build_model_row(self, model: dict):
        frame = tk.Frame(
            self, bg=theme.SURFACE_BG,
            highlightbackground=theme.BORDER,
            highlightthickness=1,
        )
        frame.pack(fill="x", padx=20, pady=4)

        rb = tk.Radiobutton(
            frame, variable=self._selected_var, value=model["name"],
            bg=theme.SURFACE_BG, activebackground=theme.SURFACE_BG,
            selectcolor=theme.INPUT_BG, cursor="hand2",
        )
        rb.grid(row=0, column=0, rowspan=2, padx=8, pady=8)

        is_present = any(
            model["name"] in m for m in self._available_models
        )
        badge = " ✓ installed" if is_present else ""

        tk.Label(
            frame, text=model["label"] + badge,
            font=theme.FONT_BODY_BOLD, bg=theme.SURFACE_BG,
            fg=theme.GREEN if is_present else theme.TEXT,
        ).grid(row=0, column=1, sticky="w", padx=(0, 10), pady=(8, 2))

        tk.Label(
            frame, text=model["description"],
            font=theme.FONT_SMALL, bg=theme.SURFACE_BG, fg=theme.MUTED,
        ).grid(row=1, column=1, sticky="w", padx=(0, 10), pady=(0, 8))

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_confirm(self):
        selected = self._selected_var.get()
        self.result = selected
        self.model_already_present = any(
            selected in m for m in self._available_models
        )
        self.destroy()

    def _on_close(self):
        self.result = None
        self.destroy()


# ──────────────────────────────────────────────────────────────────────────────
# Model Pull Dialog
# ──────────────────────────────────────────────────────────────────────────────

class ModelPullDialog(tk.Toplevel):
    """Streams the Ollama pull progress for a model with a visual progress bar.

    The pull runs in a background thread.  The UI is updated via
    ``after()`` calls so the main thread stays responsive.

    Attributes:
        success (bool): ``True`` when the pull completed without errors.
    """

    def __init__(self, parent, base_url: str, model_name: str):
        super().__init__(parent)
        self.title("Downloading Model")
        self.geometry("500x220")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.configure(bg=theme.WINDOW_BG)

        self.success: bool = False
        self._base_url = base_url
        self._model_name = model_name

        self._build_ui()
        self._start_pull()
        self.protocol("WM_DELETE_WINDOW", lambda: None)  # prevent closing mid-pull
        self.wait_window(self)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        tk.Label(
            self, text=f"Downloading  {self._model_name}",
            font=theme.FONT_H2, bg=theme.WINDOW_BG, fg=theme.TEXT,
        ).pack(pady=(18, 4))

        self._status_var = tk.StringVar(value="Starting download…")
        tk.Label(
            self, textvariable=self._status_var,
            font=theme.FONT_BODY, bg=theme.WINDOW_BG, fg=theme.MUTED,
            wraplength=460,
        ).pack(pady=4)

        # Progress bar
        bar_frame = tk.Frame(self, bg=theme.WINDOW_BG)
        bar_frame.pack(fill="x", padx=30, pady=8)

        self._progress_var = tk.DoubleVar(value=0.0)
        self._progress_bar = ttk.Progressbar(
            bar_frame, variable=self._progress_var,
            maximum=100, length=440,
        )
        self._progress_bar.pack()

        self._pct_var = tk.StringVar(value="0 %")
        tk.Label(
            self, textvariable=self._pct_var,
            font=theme.FONT_SMALL, bg=theme.WINDOW_BG, fg=theme.PRIMARY,
        ).pack(pady=2)

    # ------------------------------------------------------------------
    # Pull logic
    # ------------------------------------------------------------------

    def _start_pull(self):
        threading.Thread(target=self._pull_worker, daemon=True).start()

    def _pull_worker(self):
        success = pull_model(
            self._base_url,
            self._model_name,
            progress_callback=self._on_progress,
        )
        self.after(0, self._on_pull_complete, success)

    def _on_progress(self, status: str, completed: int, total: int):
        """Called from the background thread; schedules a UI update."""
        self.after(0, self._update_ui, status, completed, total)

    def _update_ui(self, status: str, completed: int, total: int):
        self._status_var.set(status)
        if total > 0:
            pct = min(100.0, (completed / total) * 100)
            self._progress_var.set(pct)
            self._pct_var.set(f"{pct:.1f}%  ({_fmt_bytes(completed)} / {_fmt_bytes(total)})")
        else:
            # Indeterminate — pulse the bar
            self._progress_bar.config(mode="indeterminate")
            self._progress_bar.start(15)

    def _on_pull_complete(self, success: bool):
        self.success = success
        if success:
            self._status_var.set("✓ Download complete!")
            self._progress_var.set(100)
            self._pct_var.set("100%")
            self._progress_bar.config(mode="determinate")
            self._progress_bar.stop()
            self.after(800, self.destroy)
        else:
            self._status_var.set("✗ Download failed.  Check your connection and try again.")
            self.protocol("WM_DELETE_WINDOW", self.destroy)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _fmt_bytes(n: int) -> str:
    """Return a human-readable byte size string."""
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


# ──────────────────────────────────────────────────────────────────────────────
# Convenience orchestrator
# ──────────────────────────────────────────────────────────────────────────────

def run_onboarding(parent, settings_manager) -> bool:
    """Run the full onboarding sequence and persist the resulting settings.

    Sequence:
      1. Engine connection dialog.
      2. Model selection dialog.
      3. Model pull dialog (skipped when model is already present).

    Args:
        parent: Root tkinter window.
        settings_manager: Application ``SettingsManager`` instance.

    Returns:
        ``True`` when onboarding completed successfully and the app may proceed
        to the main task-tracking view.  ``False`` when the user cancelled.
    """
    # ── Step 1: Engine handshake ──────────────────────────────────────
    saved_url = settings_manager.get("ai_api_url", "")
    # Derive base URL from the stored generate endpoint, or fall back to default
    base_url = _base_url_from_api_url(saved_url)

    conn_dialog = EngineConnectionDialog(parent, base_url)
    if conn_dialog.result is None:
        return False  # user cancelled

    base_url = conn_dialog.result
    available_models = conn_dialog.available_models

    # Persist the (potentially updated) base URL back into the settings
    _update_api_url(settings_manager, base_url)

    # ── Step 2: Model selection ───────────────────────────────────────
    model_dialog = ModelSelectionDialog(parent, available_models)
    if model_dialog.result is None:
        return False  # user cancelled

    chosen_model = model_dialog.result
    settings_manager.set("ai_model", chosen_model)
    settings_manager.save()

    # ── Step 3: Pull model if needed ──────────────────────────────────
    if not model_dialog.model_already_present:
        pull_dialog = ModelPullDialog(parent, base_url, chosen_model)
        if not pull_dialog.success:
            messagebox.showerror(
                "Download Failed",
                f"Could not download '{chosen_model}'.  "
                "You can try pulling the model manually via the Ollama CLI.",
                parent=parent,
            )
            return False

    return True


# ──────────────────────────────────────────────────────────────────────────────
# Private URL helpers
# ──────────────────────────────────────────────────────────────────────────────

def _base_url_from_api_url(api_url: str) -> str:
    """Strip the ``/api/generate`` path (or similar) from a full API URL."""
    from urllib.parse import urlparse
    parsed = urlparse(api_url)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}"
    return DEFAULT_OLLAMA_BASE_URL


def _update_api_url(settings_manager, base_url: str):
    """Store the Ollama generate endpoint derived from *base_url*."""
    generate_url = base_url.rstrip("/") + "/api/generate"
    settings_manager.set("ai_api_url", generate_url)
    settings_manager.save()
