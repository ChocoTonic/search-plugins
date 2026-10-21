"""Offline certificate trust and actual client-argument coverage."""
import ast
import importlib
import ssl
from pathlib import Path
from unittest.mock import patch

import pytest

ENGINES = ('eztv', 'jackett', 'limetorrents', 'piratebay', 'solidtorrents', 'torlock', 'torrentproject', 'torrentscsv')


@pytest.mark.parametrize('name', ENGINES)
def test_engine_context_uses_patched_bundle_without_os_roots(name: str) -> None:
    engine = importlib.import_module('nova3.engines.' + name)
    context = engine._tls_context()  # pylint: disable=protected-access
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname
    assert len(context.get_ca_certs()) == 120
    assert not any('AAA Certificate Services' in str(cert['subject']) or 'emSign Root TLS CA - G3' in str(cert['subject']) for cert in context.get_ca_certs())


@pytest.mark.parametrize('name', ENGINES)
def test_every_tls_client_call_receives_context(name: str) -> None:
    # Check every actual client call in each standalone artifact, including the
    # old-qBittorrent EZTV fallback and Jackett's cookie-aware opener.
    source = Path(__file__).parents[1] / 'engines' / (name + '.py')
    tree = ast.parse(source.read_text())
    found = 0
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        call = ast.unparse(node.func)
        if call in ('retrieve_url', 'download_file', 'helpers.retrieve_url', 'helpers.download_file', 'urllib.request.urlopen'):
            keyword = 'context' if call == 'urllib.request.urlopen' else 'ssl_context'
            assert any(item.arg == keyword and isinstance(item.value, ast.Call) and isinstance(item.value.func, ast.Name) and item.value.func.id == '_tls_context' for item in node.keywords)
            found += 1
        if call == 'urllib.request.build_opener':
            assert any(isinstance(arg, ast.Call) and ast.unparse(arg.func) == 'urllib.request.HTTPSHandler' and any(item.arg == 'context' for item in arg.keywords) for arg in node.args)
            found += 1
    assert found


def test_urllib_fallback_receives_real_context() -> None:
    engine = importlib.import_module('nova3.engines.piratebay')
    with patch('urllib.request.urlopen', side_effect=RuntimeError('stop before network')) as opener:
        with pytest.raises(RuntimeError, match='stop before network'):
            engine.piratebay().retrieve_url('https://offline.invalid')
    assert isinstance(opener.call_args.kwargs['context'], ssl.SSLContext)
