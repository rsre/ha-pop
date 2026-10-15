#!/usr/bin/python3
"""Authenticated LAN wake endpoint; no browser debugging or shell command API."""

import hmac
from http.server import BaseHTTPRequestHandler, HTTPServer
import os
from pathlib import Path
import subprocess
import time


class WakeController:
    def __init__(self, hold_seconds=300, run=subprocess.run, clock=time.monotonic):
        self.hold_seconds = hold_seconds
        self.run = run
        self.clock = clock
        self.deadline = None

    def command(self, *args):
        self.run(args, check=True, timeout=15, stdout=subprocess.DEVNULL)

    def wake(self):
        # Pausing idle also removes its touch guard. No synthetic click is sent.
        self.deadline = self.clock() + self.hold_seconds
        self.command('/usr/bin/systemctl', '--user', 'stop', 'ha-panel-idle.service')
        self.command('/usr/bin/wlopm', '--on', 'DSI-1')

    def resume(self):
        self.command('/usr/bin/systemctl', '--user', 'start', 'ha-panel-idle.service')
        self.deadline = None

    def tick(self):
        if self.deadline is not None and self.clock() >= self.deadline:
            self.resume()


def handler(token, controller):
    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(5)

        def do_POST(self):
            if not hmac.compare_digest(self.headers.get('Authorization', '').encode(), f'Bearer {token}'.encode()):
                self.reply(401)
                return
            if self.path != '/wake':
                self.reply(404)
                return
            try:
                controller.wake()
            except (OSError, subprocess.SubprocessError):
                self.reply(503)
                return
            self.reply(200)

        def reply(self, status):
            self.send_response(status)
            self.send_header('Content-Length', '0')
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.close_connection = True

        def log_message(self, *_):
            pass  # Never log request headers or credentials.

    return Handler


def main():
    token = Path(os.environ['HA_PANEL_REMOTE_TOKEN_FILE']).read_text().strip()
    if len(token) < 32:
        raise ValueError('Remote token must contain at least 32 characters')
    controller = WakeController()
    address = os.environ.get('HA_PANEL_REMOTE_ADDRESS', '192.0.2.10')
    with HTTPServer((address, 8765), handler(token, controller)) as server:
        server.timeout = 1
        try:
            while True:
                server.handle_request()
                controller.tick()
        finally:
            controller.resume()


if __name__ == '__main__':
    main()
