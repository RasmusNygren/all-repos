from typing import NamedTuple

from all_repos import autofix_lib


class Settings(NamedTuple):
    force: bool = False


def push(settings: Settings, branch_name: str) -> None:
    cmd = ['git', 'push', 'origin', f'HEAD:{branch_name}', '--quiet']
    if settings.force:
        cmd.append('--force')
    autofix_lib.run(*cmd)
