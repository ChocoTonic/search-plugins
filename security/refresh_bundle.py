"""Refresh standalone engine trust data from the vendored public CA bundle."""
import base64
import re
import textwrap
import zlib
from pathlib import Path

root = Path(__file__).resolve().parents[1]
pem = ''.join(re.findall(r'-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----\n', (root / 'security/cacert.pem').read_text(), re.S))
encoded = base64.b64encode(zlib.compress(pem.encode('ascii'), 9)).decode('ascii')
for path in (root / 'nova3/engines').glob('*.py'):
    content = path.read_text()
    if '_TLS_CA_BUNDLE = (' not in content:
        continue
    start = content.index('_TLS_CA_BUNDLE = (')
    end = content.index('\n)', start) + 2
    replacement = '_TLS_CA_BUNDLE = (\n' + ''.join('    ' + repr(chunk) + '\n' for chunk in textwrap.wrap(encoded, 900)) + ')'
    path.write_text(content[:start] + replacement + content[end:])
