#!/usr/bin/env python3
"""Layer-shell overlay para voice-claude.

Punto pequeno arriba-derecha que cambia de color segun el estado.
Estado se lee de ~/.local/share/voice-claude/state (un solo token).
Compatible con fullscreen porque usa la capa OVERLAY.

Valores de estado: idle (oculto) | listening | thinking | speaking | error

Lectura: Gio.FileMonitor (inotify) sin polling. Si el archivo no existe,
toma "idle". El error vuelve a idle tras 2s para evitar quedarse rojo.

Dependencias del sistema: gtk4 + gtk4-layer-shell + python-gobject.
"""
import os
import sys
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gtk4LayerShell", "1.0")
from gi.repository import Gio, GLib, Gtk, Gtk4LayerShell  # noqa: E402

STATE_DIR = Path(os.environ.get(
    "VOICE_CLAUDE_STATE_DIR", Path.home() / ".local/share/voice-claude"
))
STATE_FILE = STATE_DIR / "state"

SIZE_PX = int(os.environ.get("VOICE_CLAUDE_OVERLAY_SIZE", "18"))
MARGIN_TOP = int(os.environ.get("VOICE_CLAUDE_OVERLAY_MARGIN_TOP", "8"))
MARGIN_RIGHT = int(os.environ.get("VOICE_CLAUDE_OVERLAY_MARGIN_RIGHT", "12"))
ERROR_RESET_MS = int(os.environ.get("VOICE_CLAUDE_OVERLAY_ERROR_MS", "2500"))

# (color CSS, glow opcional)
STATE_STYLE = {
    "idle":      ("transparent", "rgba(0,0,0,0)"),
    "listening": ("#22c55e",     "rgba(34,197,94,0.55)"),   # verde
    "thinking":  ("#f59e0b",     "rgba(245,158,11,0.55)"),  # ambar
    "speaking":  ("#3b82f6",     "rgba(59,130,246,0.55)"),  # azul
    "error":     ("#ef4444",     "rgba(239,68,68,0.55)"),   # rojo
}


def build_css(state: str) -> str:
    fill, glow = STATE_STYLE.get(state, STATE_STYLE["idle"])
    if state == "idle":
        # Box invisible (la ventana se ocultara via set_visible(False)).
        return ".dot { background: transparent; border: none; }"
    return f"""
    .dot {{
        background: {fill};
        border-radius: {SIZE_PX // 2}px;
        border: 1px solid rgba(0, 0, 0, 0.35);
        box-shadow: 0 0 8px 1px {glow};
    }}
    """


class Overlay(Gtk.Application):
    def __init__(self) -> None:
        super().__init__(
            application_id="org.voice-claude.overlay",
            flags=Gio.ApplicationFlags.FLAGS_NONE,
        )
        self.win: Gtk.ApplicationWindow | None = None
        self.dot: Gtk.Box | None = None
        self.css_provider: Gtk.CssProvider | None = None
        self.monitor: Gio.FileMonitor | None = None
        self.reset_timer: int | None = None

    def do_activate(self) -> None:  # noqa: N802
        self.win = Gtk.ApplicationWindow(application=self)
        self.win.set_decorated(False)
        self.win.set_resizable(False)
        self.win.set_default_size(SIZE_PX, SIZE_PX)

        Gtk4LayerShell.init_for_window(self.win)
        Gtk4LayerShell.set_layer(self.win, Gtk4LayerShell.Layer.OVERLAY)
        Gtk4LayerShell.set_anchor(self.win, Gtk4LayerShell.Edge.TOP, True)
        Gtk4LayerShell.set_anchor(self.win, Gtk4LayerShell.Edge.RIGHT, True)
        Gtk4LayerShell.set_margin(self.win, Gtk4LayerShell.Edge.TOP, MARGIN_TOP)
        Gtk4LayerShell.set_margin(self.win, Gtk4LayerShell.Edge.RIGHT, MARGIN_RIGHT)
        Gtk4LayerShell.set_keyboard_mode(self.win, Gtk4LayerShell.KeyboardMode.NONE)
        Gtk4LayerShell.set_exclusive_zone(self.win, 0)  # no roba espacio

        self.dot = Gtk.Box()
        self.dot.set_size_request(SIZE_PX, SIZE_PX)
        self.dot.add_css_class("dot")
        self.win.set_child(self.dot)

        self.css_provider = Gtk.CssProvider()
        Gtk.StyleContext.add_provider_for_display(
            self.win.get_display(),
            self.css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

        # Cargar estado inicial + monitorear archivo.
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        gio_file = Gio.File.new_for_path(str(STATE_FILE))
        self.monitor = gio_file.monitor_file(Gio.FileMonitorFlags.NONE, None)
        self.monitor.connect("changed", self._on_state_changed)

        self._apply(self._read_state())
        self.win.present()
        # Para Hyprland: dejar ventana sin foco. Ya cubierto por LayerShell +
        # keyboard_mode=NONE, pero por si acaso.
        self.win.set_can_focus(False)

    def _read_state(self) -> str:
        try:
            s = STATE_FILE.read_text().strip().lower()
        except OSError:
            return "idle"
        return s if s in STATE_STYLE else "idle"

    def _on_state_changed(self, *_args) -> None:
        # Debouncing minimo: leer estado actual (puede haber multiples evts
        # por escritura — solo procesamos el ultimo valor leido).
        self._apply(self._read_state())

    def _apply(self, state: str) -> None:
        if self.css_provider is None or self.win is None:
            return
        self.css_provider.load_from_string(build_css(state))
        if state == "idle":
            self.win.set_visible(False)
        else:
            self.win.set_visible(True)
        # Auto-reset desde "error" a "idle" tras ERROR_RESET_MS.
        if self.reset_timer is not None:
            GLib.source_remove(self.reset_timer)
            self.reset_timer = None
        if state == "error":
            self.reset_timer = GLib.timeout_add(ERROR_RESET_MS, self._auto_reset)

    def _auto_reset(self) -> bool:
        self.reset_timer = None
        # Solo resetear si seguimos en error (el archivo puede haber cambiado).
        if self._read_state() == "error":
            try:
                STATE_FILE.write_text("idle")
            except OSError:
                pass
        self._apply("idle")
        return False  # one-shot


def main() -> int:
    app = Overlay()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
