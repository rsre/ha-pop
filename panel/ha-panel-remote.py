#!/usr/bin/python3
"""Authenticated panel commands with browser control restricted to localhost."""

import hmac
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
import os
from pathlib import Path
import subprocess
import time
import uuid
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from urllib.request import urlopen


class BrowserError(Exception):
    """The kiosk browser could not display the doorbell."""


class PanelBrowser:
    def __init__(self, url_file=None, open_url=urlopen, connect=None):
        self.url_file = url_file or Path.home() / '.config/ha-panel/url'
        self.open_url = open_url
        self.connect = connect

    def show_doorbell(self):
        try:
            url = self.url_file.read_text().strip()
            target = urlsplit(url)
            if target.scheme not in ('http', 'https') or not target.netloc:
                raise ValueError('Invalid configured dashboard URL')
            with self.open_url('http://127.0.0.1:9222/json/list', timeout=2) as response:
                pages = [p for p in json.load(response) if p.get('type') == 'page']
            if len(pages) != 1:
                raise BrowserError('The kiosk must have exactly one browser tab open. Restart the panel browser.')
            address = pages[0]['webSocketDebuggerUrl']
            if urlsplit(address).hostname not in ('127.0.0.1', 'localhost'):
                raise ValueError('Browser control must use localhost')
            if self.connect is None:
                from websocket import create_connection
                connect = create_connection
            else:
                connect = self.connect
            ws = connect(address, timeout=2, suppress_origin=True)
            try:
                sequence = 0
                def command(method, **params):
                    nonlocal sequence
                    sequence += 1
                    ws.send(json.dumps({'id': sequence, 'method': method, 'params': params}))
                    for _ in range(100):
                        reply = json.loads(ws.recv())
                        if reply.get('id') == sequence:
                            if 'error' in reply:
                                raise BrowserError('The browser rejected the doorbell command. Restart the panel browser.')
                            return reply.get('result', {})
                    raise BrowserError('The browser did not acknowledge the doorbell command.')
                # An attached panel handles the event without rebuilding its live camera.
                expression = ('location.origin === ' + json.dumps(f'{target.scheme}://{target.netloc}')
                              + ' && location.pathname === ' + json.dumps(target.path)
                              + ' && !window.dispatchEvent(new Event("ha-pop-doorbell", {cancelable:true}))')
                result = command('Runtime.evaluate', expression=expression, returnByValue=True)
                if result.get('result', {}).get('value') is not True:
                    query = dict(parse_qsl(target.query))
                    query['ha_pop_doorbell'] = str(int(time.time() * 1000))
                    destination = urlunsplit(target._replace(query=urlencode(query)))
                    result = command('Page.navigate', url=destination)
                    if result.get('errorText'):
                        raise BrowserError('The panel could not load its dashboard. Check the configured dashboard URL.')
                command('Page.bringToFront')
            finally:
                ws.close()
        except BrowserError:
            raise
        except Exception as error:
            raise BrowserError('Cannot control the kiosk browser. Check that Chromium is running with local browser control enabled.') from error


class WakeController:
    def __init__(self, hold_seconds=300, run=subprocess.run, clock=time.monotonic, browser=None):
        self.hold_seconds = hold_seconds
        self.run = run
        self.clock = clock
        self.deadline = None
        self.browser = browser or PanelBrowser()

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

    def doorbell(self):
        self.wake()
        self.browser.show_doorbell()

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
                self.reply(200, {'id': panel_id, 'version': '0.2.1'})

        def do_POST(self):
            if not self.authorized():
                self.reply(401)
                return
            if self.path not in ('/wake', '/sleep', '/doorbell'):
                self.reply(404)
                return
            try:
                if self.path == '/wake':
                    controller.wake()
                elif self.path == '/doorbell':
                    controller.doorbell()
                else:
                    controller.sleep()
            except BrowserError as error:
                self.reply(503, {'error': str(error)})
                return
            except (OSError, subprocess.SubprocessError):
                self.reply(503, {'error': 'The panel could not change display power. Check its graphical session and panel services.'})
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
