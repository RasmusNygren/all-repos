from __future__ import annotations

import subprocess


def remote(path: str) -> str:
    return subprocess.check_output((
        'git', '-C', path, 'config', 'remote.origin.url',
    )).decode().strip()


def repo_name(path: str) -> str:
    return remote(path).split('/')[-1].split('.git')[0]
