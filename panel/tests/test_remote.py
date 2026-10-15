import importlib.util
from pathlib import Path
import subprocess
import threading
import unittest
from http.client import HTTPConnection
from http.server import HTTPServer

spec = importlib.util.spec_from_file_location('remote', Path(__file__).parents[1] / 'ha-panel-remote.py')
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

    def test_http_requires_authentication_and_rejects_unknown_commands(self):
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

    def test_sleep_cancels_wake_hold_and_waits_for_guard(self):
        now, calls = [0], []
        controller = remote.WakeController(run=lambda args, **kw: calls.append(args), clock=lambda: now[0])
        controller.wake()
        controller.sleep()
        self.assertIsNone(controller.deadline)
        self.assertEqual(calls[-2], ('/usr/bin/systemctl', '--user', 'kill', '--kill-whom=main', '--signal=SIGUSR1', 'ha-panel-idle.service'))
        self.assertEqual(calls[-1], ('/usr/bin/systemctl', '--user', 'start', 'ha-panel-wake-guard.service'))
        count = len(calls)
        now[0] = 301
        controller.tick()
        self.assertEqual(len(calls), count)

    def test_sleep_endpoint_is_authenticated(self):
        class Controller:
            slept = False
            def sleep(self):
                self.slept = True
        controller = Controller()
        with HTTPServer(('127.0.0.1', 0), remote.handler('test-token', controller)) as server:
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            try:
                for auth, status in [('', 401), ('Bearer test-token', 200)]:
                    connection = HTTPConnection(*server.server_address)
                    connection.request('POST', '/sleep', headers={'Authorization': auth})
                    self.assertEqual(connection.getresponse().status, status)
                    connection.close()
                    self.assertEqual(controller.slept, status == 200)
            finally:
                server.shutdown()
                worker.join()


if __name__ == '__main__':
    unittest.main()

class HealthTests(unittest.TestCase):
    def test_health_authentication_does_not_execute_a_command(self):
        import json
        calls = []
        controller = remote.WakeController(run=lambda args, **kw: calls.append(args))
        with HTTPServer(('127.0.0.1', 0), remote.handler('test-token', controller, 'a' * 32)) as server:
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            try:
                for auth, status in [('', 401), ('Bearer test-token', 200)]:
                    connection = HTTPConnection(*server.server_address)
                    connection.request('GET', '/health', headers={'Authorization': auth})
                    response = connection.getresponse()
                    self.assertEqual(response.status, status)
                    data = response.read()
                    if status == 200:
                        self.assertEqual(json.loads(data)['id'], 'a' * 32)
                        self.assertEqual(json.loads(data)['version'], remote.VERSION)
                        self.assertNotIn(b'test-token', data)
                    connection.close()
                self.assertEqual(calls, [])
            finally:
                server.shutdown()
                worker.join()

    def test_identity_is_persistent_and_private(self):
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'remote-id'
            first = remote.load_panel_id(path)
            self.assertEqual(remote.load_panel_id(path), first)
            self.assertEqual(len(first), 32)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)


class BrowserTests(unittest.TestCase):
    def browser(self, handled=False, navigation_error=None):
        import io,json,tempfile
        from unittest.mock import Mock
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        url = Path(folder.name) / 'url'
        url.write_text('https://example.test/ha-pop-panel/home')
        ws = Mock()
        replies = []
        def send(payload):
            command = json.loads(payload)
            result = {'result': {'value': handled}} if command['method'] == 'Runtime.evaluate' else {}
            if command['method'] == 'Page.navigate' and navigation_error:
                result = {'errorText': navigation_error}
            replies.append(json.dumps({'id':command['id'], 'result':result}))
        ws.send.side_effect = send
        ws.recv.side_effect = lambda: replies.pop(0)
        pages = [{'type':'page','webSocketDebuggerUrl':'ws://127.0.0.1:9222/devtools/page/test'}]
        opener = Mock(side_effect=lambda *a,**k: io.BytesIO(json.dumps(pages).encode()))
        browser = remote.PanelBrowser(url, open_url=opener, connect=Mock(return_value=ws))
        return browser,ws

    def test_away_browser_navigates_configured_dashboard_with_fresh_popup_request(self):
        import json
        browser,ws = self.browser()
        browser.show_doorbell()
        commands = [json.loads(c.args[0]) for c in ws.send.call_args_list]
        navigation = next(c for c in commands if c['method']=='Page.navigate')
        self.assertTrue(navigation['params']['url'].startswith('https://example.test/ha-pop-panel/home?ha_pop_doorbell='))
        ws.close.assert_called_once()

    def test_open_dashboard_handles_repeat_without_navigation(self):
        import json
        browser,ws = self.browser(handled=True)
        browser.show_doorbell()
        self.assertNotIn('Page.navigate',[json.loads(c.args[0])['method'] for c in ws.send.call_args_list])

    def test_sleep_dismisses_popup_without_navigation_or_foregrounding_browser(self):
        import json
        browser,ws = self.browser()
        browser.dismiss_popup()
        commands = [json.loads(c.args[0]) for c in ws.send.call_args_list]
        self.assertEqual([c['method'] for c in commands], ['Runtime.evaluate'])
        self.assertIn('_closePopup(true)', commands[0]['params']['expression'])
        ws.close.assert_called_once()

    def test_browser_navigation_failure_is_actionable_and_closes_connection(self):
        browser,ws = self.browser(navigation_error='net::ERR_FAILED')
        with self.assertRaisesRegex(remote.BrowserError,'dashboard URL'):
            browser.show_doorbell()
        ws.close.assert_called_once()

    def test_doorbell_wakes_before_browser_command(self):
        from unittest.mock import Mock
        calls=[]
        browser=Mock()
        browser.show_doorbell.side_effect=lambda:calls.append('browser')
        controller=remote.WakeController(run=lambda *a,**k:calls.append('wake'),browser=browser)
        controller.doorbell()
        self.assertEqual(calls,['wake','wake','browser'])


class DoorbellEndpointTests(unittest.TestCase):
    def test_doorbell_authentication_and_browser_failure_detail(self):
        import json
        from unittest.mock import Mock
        controller=Mock()
        controller.doorbell.side_effect=remote.BrowserError('Restart the panel browser.')
        with HTTPServer(('127.0.0.1',0),remote.handler('test-token',controller)) as server:
            worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
            try:
                for auth,status in [('',401),('Bearer test-token',503)]:
                    connection=HTTPConnection(*server.server_address)
                    connection.request('POST','/doorbell',headers={'Authorization':auth})
                    response=connection.getresponse();self.assertEqual(response.status,status)
                    body=response.read();connection.close()
                    if status==401:controller.doorbell.assert_not_called()
                    else:self.assertEqual(json.loads(body)['error'],'Restart the panel browser.')
            finally:server.shutdown();worker.join()


class RebootTests(unittest.TestCase):
    def test_reboot_checks_system_watcher_without_sudo_before_recording_request(self):
        import tempfile
        calls = []
        with tempfile.TemporaryDirectory() as folder:
            request = Path(folder) / 'reboot-request'
            def run(args, **kw):
                self.assertFalse(request.exists())
                calls.append(args)
            controller = remote.WakeController(run=run, reboot_file=request)
            controller.reboot()
            self.assertEqual(calls, [('/usr/bin/systemctl', 'is-active', '--quiet', 'ha-panel-reboot.path')])
            self.assertTrue(request.read_text().strip())

    def test_inactive_or_unqueryable_watcher_does_not_write_reboot_request(self):
        import tempfile
        for error in [subprocess.CalledProcessError(3, 'systemctl'),
                      subprocess.TimeoutExpired('systemctl', 15), FileNotFoundError('systemctl')]:
            with self.subTest(error=type(error).__name__), tempfile.TemporaryDirectory() as folder:
                request = Path(folder) / 'reboot-request'
                def run(*args, **kwargs):
                    raise error
                controller = remote.WakeController(run=run, reboot_file=request)
                with self.assertRaisesRegex(remote.RebootError, 'Panel reboot service is not running'):
                    controller.reboot()
                self.assertFalse(request.exists())
                request.write_text('previous request\n')
                with self.assertRaises(remote.RebootError):
                    controller.reboot()
                self.assertEqual(request.read_text(), 'previous request\n')

    def test_missing_reboot_service_is_reported_actionably(self):
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            blocker = Path(folder) / 'blocker'
            blocker.write_text('not a directory')
            controller = remote.WakeController(run=lambda *a, **k: None, reboot_file=blocker / 'reboot-request')
            with self.assertRaisesRegex(remote.RebootError, 'ha-panel-reboot service'):
                controller.reboot()

    def test_reboot_endpoint_is_authenticated_and_reports_scheduling_failure(self):
        import json
        from unittest.mock import Mock
        controller = Mock()
        controller.reboot.side_effect = remote.RebootError('Check that the ha-panel-reboot service is installed.')
        with HTTPServer(('127.0.0.1', 0), remote.handler('test-token', controller)) as server:
            worker = threading.Thread(target=server.serve_forever, daemon=True); worker.start()
            try:
                for auth, status in [('', 401), ('Bearer test-token', 503)]:
                    connection = HTTPConnection(*server.server_address)
                    connection.request('POST', '/reboot', headers={'Authorization': auth})
                    response = connection.getresponse(); self.assertEqual(response.status, status)
                    body = response.read(); connection.close()
                    if status == 401: controller.reboot.assert_not_called()
                    else: self.assertIn('ha-panel-reboot service', json.loads(body)['error'])
            finally: server.shutdown(); worker.join()
