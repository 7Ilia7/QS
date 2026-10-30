"""Offline read-only export of exactly predeclared sanitized synthetic receipts.

Operator-only tool, never a public route. Does not load env or call network.
"""
import argparse
import json
import os
from pathlib import Path
import stat
import sys
from server import Store, valid_id


def inspect(path):
    path = Path(path)
    if path.is_symlink() or path.parent.is_symlink() or path.parent.stat().st_mode & 0o077:
        raise ValueError('private path required')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
        mode = os.fstat(stream.fileno()).st_mode
        if not stat.S_ISREG(mode) or mode & 0o077:
            raise ValueError('private regular file required')
        raw = stream.read(5*1024*1024+1)
    if len(raw) > 5*1024*1024:
        raise ValueError('size')
    data = json.loads(raw)
    pairs = data['synthetic_pairs']
    if len(pairs) != 2 or sorted(pairs.values()) != ['callback','review'] or not all(valid_id(k) for k in pairs):
        raise ValueError('predeclaration')
    view = object.__new__(Store)
    view.pairs = pairs
    result = []
    for rid, kind in sorted(pairs.items()):
        record = data['records'].get(rid, {})
        if record.get('status') == 'delivered' and view.receipt_valid(rid, record):
            result.append(record['provider_receipt'])
        else:
            result.append({'request_id': rid, 'type': kind, 'status': 'unknown', 'retry_safe': False})
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('private_outcomes_file')
    args = parser.parse_args()
    try:
        print(json.dumps(inspect(args.private_outcomes_file), separators=(',', ':')))
    except Exception:
        print('receipt inspection unavailable; unknown, do not resend', file=sys.stderr)
        sys.exit(1)
