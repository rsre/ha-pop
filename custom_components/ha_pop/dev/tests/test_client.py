import importlib.util
from pathlib import Path
import unittest

from aiohttp import ClientSession, web

spec = importlib.util.spec_from_file_location('panel_client', Path(__file__).parents[2] / 'client.py')
client = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client)


class ClientTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.calls = []
        self.status = 200
        self.payload = {'id': 'a' * 32, 'version': '0.2.0'}
        async def handle(request):
            self.calls.append((request.method, request.path, request.headers.get('Authorization')))
            if request.path == '/health':
                return web.json_response(self.payload, status=self.status)
            return web.Response(status=self.status)
        app = web.Application()
        app.router.add_route('*', '/{path:.*}', handle)
        self.runner = web.AppRunner(app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, '127.0.0.1', 0)
        await self.site.start()
        port = self.site._server.sockets[0].getsockname()[1]
        self.session = ClientSession()
        self.panel = client.PanelClient(self.session, '127.0.0.1', port, 't' * 48)

    async def asyncTearDown(self):
        await self.session.close()
        await self.runner.cleanup()

    async def test_health_validates_without_waking_and_commands_are_allowlisted(self):
        self.assertEqual((await self.panel.health())['id'], 'a' * 32)
        self.assertEqual(self.calls[0][:2], ('GET', '/health'))
        await self.panel.command('wake')
        await self.panel.command('sleep')
        self.assertEqual([c[:2] for c in self.calls[1:]], [('POST', '/wake'), ('POST', '/sleep')])
        with self.assertRaises(ValueError):
            await self.panel.command('shell')
        self.assertEqual(len(self.calls), 3)

    async def test_auth_failure_is_distinct_from_unavailable(self):
        self.status = 401
        with self.assertRaises(client.InvalidAuth):
            await self.panel.health()
        self.status = 503
        with self.assertRaises(client.CannotConnect):
            await self.panel.command('wake')

    async def test_malformed_health_is_rejected(self):
        self.payload = {'token': 'not-an-identity'}
        with self.assertRaises(client.CannotConnect):
            await self.panel.health()

    async def test_redirect_does_not_forward_the_credential(self):
        self.status = 302
        with self.assertRaises(client.CannotConnect):
            await self.panel.command('wake')
        self.assertEqual(len(self.calls), 1)


class HostTests(unittest.TestCase):
    def test_url_and_credential_injection_are_rejected(self):
        for host in ['http://example.test', 'user@example.test', 'example.test:8765', 'example.test/path', 'example.test\nHeader: bad']:
            with self.assertRaises(ValueError):
                client.validate_host(host)
        self.assertEqual(client.validate_host('Panel.Local.'), 'panel.local')
        self.assertEqual(client.validate_host('::1'), '::1')
