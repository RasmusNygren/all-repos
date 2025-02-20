from __future__ import annotations

import argparse
import functools
import getpass
import json
from typing import Any
from collections.abc import Sequence

import bitbucket_api
import git

from all_repos import cli
from all_repos import mapper
from all_repos.config import Config
from all_repos.config import load_config


def _request_headers(config: Config) -> dict[str, str]:
    return {
        'Authorization': f'Basic {config.source_settings.auth}',
        'Content-Type': 'application/json',
    }


# TODO: For whatever reason, this documented API is not actually working as expected.
def delete_branch(name: str, project: str, repo_slug: str, config: Config, *, target_commit=None) -> None:
    delete_url = f'https://{config.source_settings.base_url}/branch-utils/latest/projects/{project}/repos/{repo_slug}/branches' # noqa: E501
    data = {
        "name": name
    }
    if target_commit:
        data["endPoint"] = target_commit 

    data = json.dumps(data).encode()
    bitbucket_api.req_no_pagination(
        delete_url,
        headers=_request_headers(config),
        data=data,
    )
    return 

def merge_pr(pr_id: int, pr_version: int, project: str, repo_slug: str, config: Config) -> None:

    end_point = f'projects/{project}/repos/{repo_slug}/pull-requests'
    url = (
        f'https://{config.source_settings.base_url}/rest/api/1.0/{end_point}/{pr_id}'  # noqa: E501
    )

    url = f'{url}/merge?version={pr_version}'
    bitbucket_api.req_no_pagination(
        url,
        headers=_request_headers(config),
        method='POST',
    )

def approve_pr(pr_id: int, project: str, repo_slug: str, config: Config) -> None:

    end_point = f'projects/{project}/repos/{repo_slug}/pull-requests'
    pr_url = (
        f'https://{config.source_settings.base_url}/rest/api/1.0/{end_point}/{pr_id}'  # noqa: E501
    )
    user_slug = getpass.getuser()
    url = f'{pr_url}/participants/{user_slug}'
    data = json.dumps({
        'status': 'APPROVED',
    }).encode()

    bitbucket_api.req_no_pagination(
        url,
        headers=_request_headers(config),
        data=data,
        method='PUT',
    )

def find_prs(repo: str, title: str, config: Config) -> list[dict[str, Any]]:
    remote = git.remote(repo)
    remote_url = remote[:-len('.git')] if remote.endswith('.git') else remote
    *prefix, project, repo_slug = remote_url.split('/')

    end_point = f'projects/{project}/repos/{repo_slug}/pull-requests'
    prs = bitbucket_api.req(
        f'https://{config.source_settings.base_url}/rest/api/1.0/{end_point}',
        headers=_request_headers(config), method='GET',
    ).values
    return [pr for pr in prs if pr['title'] == title]


def run_approve_pr(
        repo: str,
        config: Config,
        title: str,
        merge: bool,
) -> int:
    remote = git.remote(repo)
    remote_url = remote[:-len('.git')] if remote.endswith('.git') else remote
    *prefix, project, repo_slug = remote_url.split('/')

    # Approve PR
    for pr in find_prs(repo, title, config):
        approve_pr(pr["id"], project, repo_slug, config)
        if merge:
            merge_pr(pr["id"], pr["version"], project, repo_slug, config)

    return 0

def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description='Similar to a distributed `git grep ...`.',
        usage='%(prog)s [options] [GIT_GREP_OPTIONS]',
        add_help=False,
    )
    # Handle --help like normal, pass -h through to git grep
    parser.add_argument(
        '--help', action='help', help='show this help message and exit',
    )
    parser.add_argument(
        '--repos', nargs='*',
        help=(
            'run against specific repositories instead.  This is especially '
            'useful with `xargs autofixer ... --repos`.  This can be used to '
            'specify repositories which are not managed by `all-repos`.'
        ),
    )
    parser.add_argument(
        '--title',
        help=(
            'specify PR title to be auto-approved'
        ),
        required=True,
    )
    parser.add_argument(
        '--merge', action='store_true',
        help=(
            'specify ticket number to be auto-approved'
        ),
    )

    cli.add_common_args(parser)
    args, _ = parser.parse_known_args(argv)

    config = load_config(args.config_filename)
    if args.repos:
        repos = args.repos
    else:
        repos = [f'{config.output_dir}/{x}' for x in config.get_cloned_repos()]

    func = functools.partial(
        run_approve_pr,
        title=args.title,
        config=config,
        merge=args.merge,
    )

    # TODO: allow configuring #jobs
    with mapper.process_mapper(8) as do_map:
        mapper.exhaust(do_map(func, repos))

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
