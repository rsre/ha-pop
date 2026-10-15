#!/usr/bin/python3
"""Consume the complete first input gesture before revealing the dashboard."""

import os
import signal
import socket
import subprocess
import time


class WakeGate:
    """Never release input until all contacts/keys are up and events are quiet."""

    def __init__(self, quiet_seconds=0.35):
        self.quiet_seconds = quiet_seconds
        self.pressed = set()
        self.awake = False
        self.last_event = 0.0

    def wake(self, now):
        self.awake = True
        self.last_event = now

    def press(self, token, now):
        self.pressed.add(token)
        self.wake(now)

    def release(self, token, now):
        self.pressed.discard(token)
        self.wake(now)

    def can_reveal(self, now):
        return self.awake and not self.pressed and now - self.last_event >= self.quiet_seconds


def notify_ready():
    address = os.environ.get("NOTIFY_SOCKET")
    if not address:
        return
    if address.startswith("@"):
        address = "\0" + address[1:]
    with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as client:
        client.connect(address)
        client.sendall(b"READY=1\nSTATUS=Screen guarded; waiting for wake gesture")


def main():
    import gi

    gi.require_version("Gtk", "3.0")
    gi.require_version("Gdk", "3.0")
    gi.require_version("GtkLayerShell", "0.1")
    gi.require_foreign("cairo")
    from gi.repository import Gdk, GLib, Gtk, GtkLayerShell

    class Guard:
        def __init__(self):
            self.gate = WakeGate()
            self.touch_count = 0
            self.timer = None
            self.first_frame = False
            self.power_mode = None
            self.window = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
            self.window.set_title("Panel wake guard")
            self.window.set_decorated(False)
            GtkLayerShell.init_for_window(self.window)
            GtkLayerShell.set_namespace(self.window, "ha-panel-wake-guard")
            GtkLayerShell.set_layer(self.window, GtkLayerShell.Layer.OVERLAY)
            GtkLayerShell.set_keyboard_mode(self.window, GtkLayerShell.KeyboardMode.EXCLUSIVE)
            GtkLayerShell.set_exclusive_zone(self.window, -1)
            for edge in [GtkLayerShell.Edge.TOP, GtkLayerShell.Edge.BOTTOM, GtkLayerShell.Edge.LEFT, GtkLayerShell.Edge.RIGHT]:
                GtkLayerShell.set_anchor(self.window, edge, True)
            provider = Gtk.CssProvider()
            provider.load_from_data(b"window { background: #000; }")
            self.window.get_style_context().add_provider(provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
            self.window.add_events(
                Gdk.EventMask.TOUCH_MASK | Gdk.EventMask.BUTTON_PRESS_MASK
                | Gdk.EventMask.BUTTON_RELEASE_MASK | Gdk.EventMask.KEY_PRESS_MASK
                | Gdk.EventMask.KEY_RELEASE_MASK
            )
            self.window.connect("draw", self.draw)
            self.window.connect("touch-event", self.touch)
            self.window.connect("button-press-event", self.button)
            self.window.connect("button-release-event", self.button)
            self.window.connect("key-press-event", self.key)
            self.window.connect("key-release-event", self.key)
            self.window.connect("delete-event", lambda *_: True)
            GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGUSR1, self.resume)
            GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, self.stop)
            GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, self.stop)
            self.window.show_all()

        def power(self, mode):
            if mode != self.power_mode:
                subprocess.run(["/usr/bin/wlopm", f"--{mode}", "DSI-1"], check=True)
                self.power_mode = mode

        def draw(self, *_):
            if not self.first_frame:
                self.first_frame = True
                GLib.idle_add(self.sleep_after_frame)
            return False

        def sleep_after_frame(self):
            # Ensure the input-catching surface has reached the compositor first.
            Gdk.Display.get_default().sync()
            if not self.gate.awake:
                self.power("off")
            notify_ready()
            return GLib.SOURCE_REMOVE

        def schedule(self, milliseconds=400):
            if self.timer is not None:
                GLib.source_remove(self.timer)
            self.timer = GLib.timeout_add(milliseconds, self.reveal)

        def reveal(self):
            self.timer = None
            if self.gate.can_reveal(time.monotonic()):
                self.power("on")
                self.window.destroy()
                Gtk.main_quit()
            elif not self.gate.pressed:
                self.schedule()
            return GLib.SOURCE_REMOVE

        def resume(self):
            if not self.gate.awake:
                self.gate.wake(time.monotonic())
                # A compositor can report activity before routing its first touch.
                self.schedule(1000)
            self.power("on")
            return GLib.SOURCE_CONTINUE

        def touch(self, _window, event):
            if event.type == Gdk.EventType.TOUCH_BEGIN:
                self.touch_count += 1
            elif event.type in [Gdk.EventType.TOUCH_END, Gdk.EventType.TOUCH_CANCEL]:
                self.touch_count = max(0, self.touch_count - 1)
            if self.touch_count:
                self.gate.press("touch", time.monotonic())
            else:
                self.gate.release("touch", time.monotonic())
            self.schedule()
            self.power("on")
            return True

        def button(self, _window, event):
            token = ("button", event.button)
            if event.type == Gdk.EventType.BUTTON_PRESS:
                self.gate.press(token, time.monotonic())
            elif event.type == Gdk.EventType.BUTTON_RELEASE:
                self.gate.release(token, time.monotonic())
            self.schedule()
            self.power("on")
            return True

        def key(self, _window, event):
            token = ("key", event.hardware_keycode)
            if event.type == Gdk.EventType.KEY_PRESS:
                self.gate.press(token, time.monotonic())
            else:
                self.gate.release(token, time.monotonic())
            self.schedule()
            self.power("on")
            return True

        def stop(self):
            self.power("on")
            self.window.destroy()
            Gtk.main_quit()
            return GLib.SOURCE_REMOVE

    guard = Guard()
    try:
        Gtk.main()
    finally:
        guard.power("on")


if __name__ == "__main__":
    main()
