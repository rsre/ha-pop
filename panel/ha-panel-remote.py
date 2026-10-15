#!/usr/bin/python3
"""Authenticated LAN wake endpoint; no browser debugging or shell command API."""

import hmac
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
import os
from pathlib import Path
import subprocess
import time
import uuid


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

    def sleep(self):
        self.resume()
        self.command('/usr/bin/systemctl', '--user', 'stop', 'ha-panel-wake-guard.service')
        self.command('/usr/bin/systemctl', '--user', 'kill', '--kill-whom=main', '--signal=SIGUSR1', 'ha-panel-idle.service')
        # Wait for the guard's ready notification, sent after display power-off.
        self.command('/usr/bin/systemctl', '--user', 'start', 'ha-panel-wake-guard.service')

    def tick(self):
        if self.deadline is not None and self.clock() >= self.deadline:
            self.resume()


def handler(token, controller, panel_id='0' * 32):
    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(5)

        def authorized(self):
            return hmac.compare_digest(self.headers.get('Authorization', '').encode(), f'Bearer {token}'.encode())

        def do_GET(self):
            if not self.authorized():
                self.reply(401)
            elif self.path != '/health':
                self.reply(404)
            else:
                self.reply(200, {'id': panel_id, 'version': '0.2.0'})

        def do_POST(self):
            if not self.authorized():
                self.reply(401)
                return
            if self.path not in ('/wake', '/sleep'):
                self.reply(404)
                return
            try:
                if self.path == '/wake':
                    controller.wake()
                else:
                    controller.sleep()
            except (OSError, subprocess.SubprocessError):
                self.reply(503)
                return
            self.reply(200)

        def reply(self, status, data=None):
            body = json.dumps(data).encode() if data is not None else b''
            self.send_response(status)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Content-Type', 'application/json')
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(body)
            self.close_connection = True

        def log_message(self, *_):
            pass  # Never log request headers or credentials.

    return Handler


def load_panel_id(path):
    if not path.exists():
        try:
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, 'w') as output:
                output.write(uuid.uuid4().hex + '\n')
        except FileExistsError:
            pass
    return uuid.UUID(hex=path.read_text().strip()).hex


def main():
    token = Path(os.environ['HA_PANEL_REMOTE_TOKEN_FILE']).read_text().strip()
    if len(token) < 32:
        raise ValueError('Remote token must contain at least 32 characters')
    controller = WakeController()
    address = os.environ.get('HA_PANEL_REMOTE_ADDRESS', '0.0.0.0')
    panel_id = load_panel_id(Path(os.environ['HA_PANEL_REMOTE_TOKEN_FILE']).with_name('remote-id'))
    with HTTPServer((address, 8765), handler(token, controller, panel_id)) as server:
        server.timeout = 1
        try:
            while True:
                server.handle_request()
                controller.tick()
        finally:
            controller.resume()


if __name__ == '__main__':
    main()
