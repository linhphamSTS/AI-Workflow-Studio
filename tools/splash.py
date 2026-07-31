#!/usr/bin/env python3
"""A small progress window for the windowless launch.

Clicking the Desktop icon starts a process with no console, so every message the launcher
prints goes to a log file nobody is watching. Between the update check, a possible 65 MB
download and the server coming up, that can be a minute or more of a machine doing nothing
visible, which reads as "the icon is broken" and gets clicked again.

So: a borderless window appears immediately, says what is happening, and closes itself once
the app is actually serving. It owns the main thread because that is tkinter's rule; the real
work runs on a worker thread and posts status lines back through a queue.

If tkinter is unavailable for any reason the caller falls back to running silently. A missing
progress window must never be the thing that stops the app from starting.
"""
from __future__ import annotations

import queue
import threading
from pathlib import Path

BRAND = "#6366f1"
INK = "#0e1420"
MUTED = "#6b7688"
SURFACE = "#ffffff"


class Splash:
    """Usage:

        s = Splash(icon_path)
        s.run(worker)      # worker(post) runs on a thread; call post("text") to update,
                           # and return when finished. run() returns the worker's result.
    """

    def __init__(self, icon: Path | None = None, title: str = "AI Workflow Studio"):
        self.icon = icon
        self.title = title
        self._q: queue.Queue[tuple[str, object]] = queue.Queue()
        self._result: object = None
        self._error: BaseException | None = None

    # ---------------------------------------------------------------- public
    def run(self, worker) -> object:
        try:
            import tkinter as tk
            from tkinter import ttk
        except Exception:                      # noqa: BLE001 - headless or trimmed Python
            return worker(lambda _msg: None)   # no window, same work

        root = tk.Tk()
        root.title(self.title)
        root.overrideredirect(True)            # no title bar: this is a splash, not a window
        root.attributes("-topmost", True)
        root.configure(bg=BRAND)

        # 1px brand border, drawn by inset rather than a real border so it works everywhere
        frame = tk.Frame(root, bg=SURFACE)
        frame.pack(fill="both", expand=True, padx=1, pady=1)

        head = tk.Frame(frame, bg=SURFACE)
        head.pack(fill="x", padx=18, pady=(16, 0))

        self._img = None
        if self.icon and self.icon.exists():
            try:
                img = tk.PhotoImage(file=str(self.icon))
                # The source is 256px for the desktop; subsample down rather than ship a second
                # file. Integer factors only, so pick the one that lands nearest 48px.
                factor = max(1, round(img.width() / 48))
                self._img = img.subsample(factor, factor)
                tk.Label(head, image=self._img, bg=SURFACE).pack(side="left", padx=(0, 12))
            except Exception:                  # noqa: BLE001 - PNG only; skip if it will not load
                self._img = None

        text = tk.Frame(head, bg=SURFACE)
        text.pack(side="left", fill="x", expand=True)
        tk.Label(text, text=self.title, bg=SURFACE, fg=INK,
                 font=("Segoe UI", 11, "bold"), anchor="w").pack(fill="x")
        status = tk.Label(text, text="Starting ...", bg=SURFACE, fg=MUTED,
                          font=("Segoe UI", 9), anchor="w", justify="left", wraplength=300)
        status.pack(fill="x", pady=(2, 0))

        bar = ttk.Progressbar(frame, mode="indeterminate", length=340)
        bar.pack(padx=18, pady=(14, 16))
        bar.start(12)

        root.update_idletasks()
        w, h = max(root.winfo_reqwidth(), 380), root.winfo_reqheight()
        x = (root.winfo_screenwidth() - w) // 2
        y = (root.winfo_screenheight() - h) // 3      # a third down reads better than centred
        root.geometry(f"{w}x{h}+{x}+{y}")

        def post(msg: str) -> None:
            self._q.put(("status", msg))

        def body() -> None:
            try:
                self._result = worker(post)
            except BaseException as e:          # noqa: BLE001 - surfaced by run(), not swallowed
                self._error = e
            finally:
                self._q.put(("done", None))

        threading.Thread(target=body, daemon=True).start()

        def pump() -> None:
            try:
                while True:
                    kind, payload = self._q.get_nowait()
                    if kind == "status":
                        status.config(text=str(payload))
                    elif kind == "done":
                        root.destroy()
                        return
            except queue.Empty:
                pass
            root.after(80, pump)

        root.after(80, pump)
        root.mainloop()

        if self._error is not None:
            raise self._error
        return self._result
