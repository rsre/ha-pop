import importlib.util
from pathlib import Path
import subprocess
import threading
import unittest
from http.client import HTTPConnection
from http.server import HTTPServer

spec = importlib.util.spec_from_file_location('remote', Path(__file__).parents[1] / 'kiosk/ha-panel-remote.py')
remote = importlib.util.module_from_spec(spec)
spec.loader.exec_module(remote)


class RemoteTests(unittest.TestCase):
    def test_wake_removes_guard_without_touch_and_repeated_wake_extends_hold(self):
        now, calls = [10], []
        controller = remote.WakeController(run=lambda args, **kw: calls.append(args), clock=lambda: now[0])
        controller.wake()
        self.assertEqual(calls[0], ('/usr/bin/systemctl', '--user', 'stop', 'ha-panel-idle.service'))
        self.assertEqual(calls[1], ('/usr/bin/wlopm', '--on', 'DSI-1'))
        now[0] = 200
        controller.wake()
        now[0] = 311
        controller.tick()
        self.assertEqual(len(calls), 4)
        now[0] = 500
        controller.tick()
        self.assertEqual(calls[-1], ('/usr/bin/systemctl', '--user', 'start', 'ha-panel-idle.service'))
        self.assertIsNone(controller.deadline)

    def test_failed_wake_still_restores_idle_after_hold(self):
        now = [0]
        def run(args, **kw):
            if '--on' in args:
                raise subprocess.CalledProcessError(1, args)
        controller = remote.WakeController(run=run, clock=lambda: now[0])
        with self.assertRaises(subprocess.CalledProcessError):
            controller.wake()
        now[0] = 301
        controller.tick()
        self.assertIsNone(controller.deadline)

    def test_http_requires_authentication_and_only_exposes_wake(self):
        calls = []
        controller = remote.WakeController(run=lambda args, **kw: calls.append(args))
        with HTTPServer(('127.0.0.1', 0), remote.handler('test-token', controller)) as server:
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            try:
                for path, auth, expected in [('/wake', '', 401), ('/wake', 'Bearer wrong', 401), ('/shell', 'Bearer test-token', 404), ('/wake', 'Bearer test-token', 200)]:
                    connection = HTTPConnection(*server.server_address)
                    connection.request('POST', path, headers={'Authorization': auth})
                    response = connection.getresponse()
                    self.assertEqual(response.status, expected)
                    response.read()
                    connection.close()
                    if expected != 200:
                        self.assertEqual(calls, [])
                self.assertEqual(len(calls), 2)
            finally:
                server.shutdown()
                worker.join()


if __name__ == '__main__':
    unittest.main()
