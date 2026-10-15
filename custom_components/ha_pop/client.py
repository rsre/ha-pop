"""Small authenticated client for the Pi's local endpoint."""
import asyncio
import ipaddress
import re

import aiohttp


class InvalidAuth(Exception):
    """The panel rejected its shared token."""


class CannotConnect(Exception):
    """The panel could not complete a command."""


def validate_host(host):
    host = host.strip().rstrip('.')
    try:
        return str(ipaddress.ip_address(host))
    except ValueError:
        if not re.fullmatch(r'(?=.{1,253}$)(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?', host):
            raise ValueError('Use a hostname or IP address without a URL or port') from None
        return host.lower()


class PanelClient:
    def __init__(self, session, host, port, token):
        host = validate_host(host)
        if not isinstance(port, int) or not 1 <= port <= 65535:
            raise ValueError('Invalid port')
        if not re.fullmatch(r'[A-Za-z0-9_-]{32,128}', token):
            raise ValueError('Invalid panel token')
        address = f'[{host}]' if ':' in host else host
        self._base = f'http://{address}:{port}'
        self._session = session
        self._headers = {'Authorization': f'Bearer {token}'}

    async def _request(self, method, path):
        try:
            async with asyncio.timeout(10):
                async with self._session.request(method, self._base + path, headers=self._headers, allow_redirects=False) as response:
                    if response.status in (401, 403):
                        raise InvalidAuth('Panel authentication failed')
                    if response.status != 200:
                        raise CannotConnect('Panel command failed')
                    if method == 'GET':
                        result = await response.json()
                        if not isinstance(result, dict) or not re.fullmatch(r'[a-f0-9]{32}', str(result.get('id', ''))):
                            raise CannotConnect('Panel health response is invalid')
                        return result
        except (aiohttp.ClientError, TimeoutError, ValueError) as error:
            raise CannotConnect('Panel request failed') from error

    async def health(self):
        return await self._request('GET', '/health')

    async def command(self, command):
        if command not in ('wake', 'sleep'):
            raise ValueError('Unsupported panel command')
        await self._request('POST', '/' + command)
