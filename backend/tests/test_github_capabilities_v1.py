from dataclasses import replace
import hashlib
import subprocess

import pytest

from palwakf_local_agents import github_capabilities_v1 as gh
from palwakf_local_agents.outbound_capabilities_v1 import (
    CapabilityContextV1, CapabilityError, default_capability_registry_v1,
)


def git(repo, *args):
    return subprocess.run(['git', *args], cwd=repo, check=True, capture_output=True,
                          text=True, shell=False).stdout.strip()


@pytest.fixture
def setup(tmp_path, monkeypatch):
    repo = tmp_path / 'repo'
    remote = tmp_path / 'remote.git'
    repo.mkdir()
    git(repo, 'init', '-b', 'main')
    git(repo, 'config', 'user.name', 'Test')
    git(repo, 'config', 'user.email', 'test@example.invalid')
    git(repo, 'config', 'core.autocrlf', 'false')
    (repo / 'src').mkdir()
    (repo / 'src/a.txt').write_text('before', encoding='utf-8')
    (repo / 'other.txt').write_text('other', encoding='utf-8')
    git(repo, 'add', '--', 'src/a.txt', 'other.txt')
    git(repo, 'commit', '-m', 'base')
    git(tmp_path, 'init', '--bare', str(remote))
    git(repo, 'remote', 'add', 'origin', 'https://github.com/example/repo.git')
    base = git(repo, 'rev-parse', 'HEAD')
    ctx = CapabilityContextV1('test', 'example/repo', (str(tmp_path),),
                              ('src',), 'task/test', base)
    original = gh._run
    calls = []

    def local_transport(argv, **kwargs):
        calls.append(argv[:])
        if argv[:2] in (['git', 'push'], ['git', 'ls-remote']):
            assert 'origin' in argv
            argv = [str(remote) if value == 'origin' else value for value in argv]
        return original(argv, **kwargs)

    monkeypatch.setattr(gh, '_run', local_transport)
    return repo, remote, ctx, calls


def call(setup, name, **args):
    repo, _, ctx, _ = setup
    return default_capability_registry_v1().resolve('github.' + name).handler(
        ctx, dict(repo_root=str(repo), **args))


def branch(setup):
    return call(setup, 'branch.create', branch=setup[2].task_branch,
                base_sha=setup[2].expected_base_sha)


def write(setup):
    return call(setup, 'file.write_bounded', path='src/a.txt', content='after',
                expected_sha256=hashlib.sha256(b'before').hexdigest())


def test_local_roundtrip_and_reads(setup):
    repo, remote, ctx, calls = setup
    assert call(setup, 'repo.read')['branch'] == 'main'
    assert call(setup, 'file.read', path='src/a.txt', max_bytes=2)['truncated']
    assert call(setup, 'branch.read')['remote_sha'] is None
    branch(setup)
    write(setup)
    result = call(setup, 'commit.create', paths=['src/a.txt'], message='bounded')
    assert 'after' in call(setup, 'diff.read', paths=['src/a.txt'])['diff']
    pushed = call(setup, 'task_branch.push', branch=ctx.task_branch,
                  expected_remote_head=ctx.expected_base_sha)
    assert pushed['after_remote_sha'] == result['commit_sha']
    assert pushed['force'] is False
    assert git(remote, 'rev-parse', 'refs/heads/task/test') == result['commit_sha']
    assert git(repo, 'rev-parse', 'main') == ctx.expected_base_sha
    assert all('--force' not in arg and not arg.startswith('+') for argv in calls for arg in argv)
    assert ['git', 'add', '--', '.'] not in calls


@pytest.mark.parametrize('origin', ['https://github.com/other/repo.git',
    'https://github.com.evil/example/repo.git', 'file:///tmp/repo'])
def test_origin_binding(setup, origin):
    git(setup[0], 'remote', 'set-url', 'origin', origin)
    with pytest.raises(CapabilityError, match='ORIGIN_MISMATCH'):
        call(setup, 'repo.read')


def test_push_url_binding(setup):
    git(setup[0], 'config', 'remote.origin.pushurl', 'https://github.com/evil/repo.git')
    with pytest.raises(CapabilityError, match='ORIGIN_MISMATCH'):
        call(setup, 'repo.read')


def test_allowed_root(setup):
    repo, remote, ctx, calls = setup
    with pytest.raises(CapabilityError, match='OUTSIDE_ALLOWED_ROOTS'):
        call((repo, remote, replace(ctx, allowed_roots=(str(remote),)), calls), 'repo.read')


@pytest.mark.parametrize('path', ['../escape', '.git/config', 'src/../../escape',
    'other.txt', 'src/*.txt', ':(glob)**', '.', 'src/../other.txt'])
def test_write_paths_fail_closed(setup, path):
    branch(setup)
    with pytest.raises(CapabilityError):
        call(setup, 'file.write_bounded', path=path, content='bad')


def test_content_drift_and_size(setup):
    branch(setup)
    with pytest.raises(CapabilityError, match='FILE_CONTENT_DRIFT'):
        call(setup, 'file.write_bounded', path='src/a.txt', content='bad', expected_sha256='0'*64)
    with pytest.raises(CapabilityError, match='TOO_LARGE'):
        call(setup, 'file.write_bounded', path='src/new', content='a'*262145)
    assert (setup[0] / 'src/a.txt').read_text() == 'before'
    assert call(setup, 'file.write_bounded', path='src/new', content='new')['before_sha256'] is None


def test_main_never_writable_even_if_signed(setup):
    repo, remote, ctx, calls = setup
    main = (repo, remote, replace(ctx, task_branch='main'), calls)
    for name, args in [('file.write_bounded', dict(path='src/a.txt', content='bad')),
                       ('commit.create', dict(paths=['src/a.txt'], message='bad')),
                       ('task_branch.push', dict(branch='main', expected_remote_head=ctx.expected_base_sha))]:
        with pytest.raises(CapabilityError, match='TASK_BRANCH_MISMATCH'):
            call(main, name, **args)


def test_head_drift(setup):
    git(setup[0], 'commit', '--allow-empty', '-m', 'drift')
    with pytest.raises(CapabilityError, match='HEAD_DRIFT'):
        branch(setup)


def test_commit_exact_paths_and_preserves_unrelated_index(setup):
    repo = setup[0]
    branch(setup)
    write(setup)
    (repo / 'other.txt').write_text('unrelated')
    git(repo, 'add', '--', 'other.txt')
    before = git(repo, 'diff', '--cached')
    with pytest.raises(CapabilityError, match='STAGED_PATH_SET_MISMATCH'):
        call(setup, 'commit.create', paths=['src/a.txt'], message='bounded')
    assert git(repo, 'diff', '--cached') == before
    for paths in [['.'], ['src'], ['src/*.txt'], ['other.txt']]:
        with pytest.raises(CapabilityError):
            call(setup, 'commit.create', paths=paths, message='bad')


def test_remote_drift(setup):
    repo, remote, ctx, _ = setup
    branch(setup)
    write(setup)
    commit = call(setup, 'commit.create', paths=['src/a.txt'], message='bounded')['commit_sha']
    git(repo, 'push', str(remote), f'{commit}:refs/heads/task/test')
    with pytest.raises(CapabilityError, match='REMOTE_HEAD_DRIFT'):
        call(setup, 'task_branch.push', branch=ctx.task_branch, expected_remote_head=ctx.expected_base_sha)


def test_push_rejects_out_of_scope_commit(setup):
    branch(setup)
    (setup[0] / 'other.txt').write_text('bad')
    git(setup[0], 'add', '--', 'other.txt')
    git(setup[0], 'commit', '-m', 'outside')
    with pytest.raises(CapabilityError, match='OUTSIDE_SIGNED_SCOPE'):
        call(setup, 'task_branch.push', branch=setup[2].task_branch,
             expected_remote_head=setup[2].expected_base_sha)


def test_readback_failure(setup, monkeypatch):
    branch(setup)
    original = gh._run
    reads = 0
    def fail_readback(argv, **kwargs):
        nonlocal reads
        result = original(argv, **kwargs)
        if argv[:2] == ['git', 'ls-remote']:
            reads += 1
            if reads == 2:
                result['exit_code'] = 1
        return result
    monkeypatch.setattr(gh, '_run', fail_readback)
    with pytest.raises(CapabilityError, match='READBACK_MISMATCH'):
        call(setup, 'task_branch.push', branch=setup[2].task_branch,
             expected_remote_head=setup[2].expected_base_sha)


def test_run_never_uses_shell(tmp_path, monkeypatch):
    def fake(argv, **kwargs):
        assert kwargs['shell'] is False
        return subprocess.CompletedProcess(argv, 0, b'ok', b'')
    monkeypatch.setattr(gh.subprocess, 'run', fake)
    assert gh._run(['git', 'status'], cwd=tmp_path)['stdout'] == 'ok'
