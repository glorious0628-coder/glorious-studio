"""Checked deploy of ScrapWorkshop to https://glorious.ai.kr/games/scrap-workshop/ (GitHub Pages, main branch).

Usage (after a finished, checked change unit and a successful Unity WebGL build):
  python scripts/deploy-game.py [--game D:/Game/Web/ScrapWorkshop] [--dry-run] [--allow-same-build]
                                [--co-author "Name <email>"]

Order: preflight -> prepare -> local check -> commit + push -> GitHub Pages built -> live check. Stops before the push on
any failure (the public site keeps its last good release). After the push, any failure of Pages or the live check -
including network errors, timeouts and unreadable answers - rolls the entry back to the previous release and checks
that too. Every outcome is written to deploy-history.jsonl with its state: deployed / stopped_before_push /
failed_after_push, and for a roll back rollback_attempted and rollback_verified. It never builds Unity, never calls an
AI API, never forces a reload on players, and never stores credentials (git and gh use the login on this PC).
"""
import argparse
import hashlib
import json
import os
import pathlib
import re
import shutil
import socket
import subprocess
import sys
import time
from datetime import datetime

import gamesite as gs

KEEP = 3  # release folders kept in the site: the new one and the two before it (open tabs, quick roll back)
LOCK = gs.SITE / '.deploy.lock'
STALE = 2 * 3600


def say(msg):
    print(datetime.now().strftime('%H:%M:%S ') + msg, flush=True)


class Stop(Exception):
    pass


def stop(msg):
    raise Stop(msg)


def record(state, **fields):
    entry = {'state': state, 'at': gs.now_utc(), **fields}
    with open(gs.SITE.parent / 'deploy-history.jsonl', 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    return entry


class Lock:
    """One deploy or roll back at a time. The lock file is created atomically (O_EXCL), so of two runs started together
    only one gets in; only its owner removes it. A lock older than two hours is treated as left behind by a crash."""
    def __enter__(self):
        self.token = f'pid {os.getpid()} at {datetime.now().isoformat(timespec="seconds")} {os.urandom(4).hex()}'
        for attempt in (1, 2):
            try:
                fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:
                try:
                    age = time.time() - LOCK.stat().st_mtime
                    held = LOCK.read_text(encoding='utf-8').strip()
                except OSError:
                    continue  # removed meanwhile; try once more
                if attempt == 1 and age > STALE:
                    say(f'removing a stale lock ({held})')
                    LOCK.unlink(missing_ok=True)
                    continue
                stop(f'another deploy is running ({held}). If it is not, delete {LOCK}')
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write(self.token)
            return self
        stop('could not take the deploy lock')

    def __exit__(self, *exc):
        try:
            if LOCK.read_text(encoding='utf-8').strip() == self.token:
                LOCK.unlink()
        except OSError:
            pass


def unity_building(game):
    """A Unity process with this project open (editor or batch build), or one whose project is unknown: never copy a
    build while it may be written."""
    ps = ['powershell', '-NoProfile', '-Command',
          "Get-CimInstance Win32_Process -Filter \"Name='Unity.exe'\" | ForEach-Object { $_.CommandLine }"]
    lines = [l.lower().replace('/', '\\') for l in subprocess.run(ps, capture_output=True, text=True).stdout.splitlines() if l.strip()]
    project = str(game).lower().replace('/', '\\')
    return any(project in l or '-projectpath' not in l for l in lines)


def sources_newer_than_build(game):
    built = (game / 'Build/WebGL/Build/WebGL.wasm.unityweb').stat().st_mtime
    names = gs.git('ls-files', '--cached', '--others', '--exclude-standard', '--', *gs.GAME_SOURCES, cwd=game).splitlines()
    return [n for n in names if (game / n).is_file() and (game / n).stat().st_mtime > built + 1]


def free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def drive(game, url, steps, out, port):
    """Headless Chrome steps (Tools/cdp/drive.mjs in the game). True only when every step passed and the page had no
    unexpected problem (an uncaught exception, an error log, a ledger mismatch) and no expected one went missing: the
    driver's PROBLEMS verdict line must be there and clean, so an older driver without it does not pass either."""
    return drive_verdict(*run_drive(game, url, steps, out, port), url)


def run_drive(game, url, steps, out, port):
    r = subprocess.run(['node', str(game / 'Tools/cdp/drive.mjs'), url, str(out), str(steps), str(port)],
                       capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=600)
    pathlib.Path(out).mkdir(parents=True, exist_ok=True)
    (pathlib.Path(out) / 'drive.txt').write_text(r.stdout + r.stderr, encoding='utf-8')
    return r.stdout, r.returncode


def drive_verdict(stdout, returncode, url=''):
    m = re.search(r'STEPS (\d+) FAILED (\d+)', stdout)
    p = re.search(r'PROBLEMS unexpected=(\d+) expected=(\d+) missing=(\d+)', stdout)
    listed = len(re.findall(r'^PROBLEM ', stdout, re.M))
    say(f'  {url} -> {m.group(0) if m else "no result"}, '
        + (f'browser problems {p.group(1)} (expected {p.group(2)}, missing {p.group(3)})' if p else 'no problem verdict'))
    return bool(m and p) and m.group(2) == '0' and p.group(1) == '0' and p.group(3) == '0' and listed == 0 and returncode == 0


def page_release(out):
    try:
        logs = json.loads((pathlib.Path(out) / 'report.json').read_text(encoding='utf-8'))['logs']
    except (OSError, ValueError, KeyError):
        return None
    for line in logs:
        m = re.search(r'PAGE_RELEASE version=([0-9a-f]{16})', line['text'])
        if m:
            return m.group(1)
    return None


def checks(game, base_url, version, out, tag):
    out.mkdir(parents=True, exist_ok=True)
    ok = drive(game, base_url + 'games/scrap-workshop/', gs.SITE / 'scripts/deploy-smoke.json', out / f'{tag}-game', 9351)
    seen = page_release(out / f'{tag}-game')
    if seen != version:
        say(f'  the page ran release {seen}, expected {version}')
        ok = False
    return drive(game, base_url, gs.SITE / 'scripts/homepage-smoke.json', out / f'{tag}-root', 9352) and ok


def local_check(game, version, out):
    port = free_port()
    server = subprocess.Popen([sys.executable, '-m', 'http.server', str(port), '--bind', '127.0.0.1', '--directory', str(gs.SITE)],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        time.sleep(1.5)
        return checks(game, f'http://127.0.0.1:{port}/', version, out, 'local')
    finally:
        server.terminate()


def guarded(name, fn, *args):
    """A step after the push: any exception (network, timeout, unreadable answer) counts as that step failing, so the
    roll back still runs."""
    try:
        return bool(fn(*args))
    except Exception as error:  # noqa: BLE001 - every failure here must reach the roll back
        say(f'  {name} failed with {type(error).__name__}: {error}')
        return False


def wait_pages(sha, timeout=900, version=None):
    """Waits for GitHub Pages to publish the pushed commit. Its builds API has been seen to stay "building" after the site
    was already up (2026-11-01); then the live release.json showing `version` counts as published too, and the live
    check that follows still verifies every file and the page."""
    end = time.time() + timeout
    while time.time() < end:
        r = subprocess.run(['gh', 'api', f'repos/{gs.REPO}/pages/builds/latest'], capture_output=True, text=True)
        if r.returncode == 0:
            b = json.loads(r.stdout)
            if b.get('commit') == sha and b.get('status') == 'built':
                say(f'  GitHub Pages built {sha[:7]}')
                return True
            if b.get('commit') == sha and b.get('status') == 'errored':
                say(f'  GitHub Pages build failed: {b.get("error")}')
                return False
        if version and live_version() == version:
            say(f'  GitHub Pages: the builds API has not said "built" for {sha[:7]}, but the live release.json shows {version}')
            return True
        time.sleep(15)
    say('  GitHub Pages did not report the build in time')
    return False


def live_version():
    """The release the public entry points at now (its release.json), or None when it cannot be read."""
    try:
        return json.loads(gs.fetch(gs.LIVE_GAME + f'release.json?t={int(time.time())}'))['version']
    except Exception:  # noqa: BLE001 - unreadable for any reason means "not known to be live"
        return None


def live_check(game, manifest, out, wait=420):
    version = manifest['version']
    end = time.time() + wait
    while time.time() < end:
        try:
            if json.loads(gs.fetch(gs.LIVE_GAME + f'release.json?t={int(time.time())}'))['version'] == version:
                break
        except Exception:  # noqa: BLE001 - not there yet; the loop tries again
            pass
        time.sleep(15)
    else:
        say('  the live release.json never showed the new version')
        return False
    for name, f in manifest['files'].items():
        data = gs.fetch(gs.LIVE_GAME + f'releases/{version}/{name}', timeout=180)
        if len(data) != f['bytes'] or hashlib.sha256(data).hexdigest() != f['sha256']:
            say(f'  live {name} differs from the release')
            return False
    say('  live files match release.json (bytes and SHA-256)')
    return checks(game, gs.LIVE_ROOT, version, out, 'live')


def prune(keep_versions):
    removed = []
    for folder in (gs.DEST / 'releases').iterdir():
        if folder.is_dir() and folder.name not in keep_versions:
            shutil.rmtree(folder)
            removed.append(folder.name)
    return removed


def put_back():
    """The site files as in HEAD again: unstaged first (restoring a pruned release from history stages it), then the
    working tree, then untracked files."""
    gs.git('reset', '-q', 'HEAD', '--', 'games/scrap-workshop')
    gs.git('checkout', '--', 'games/scrap-workshop')
    gs.git('clean', '-fdq', '--', 'games/scrap-workshop')


def commit_and_push(message):
    gs.git('add', '-A', 'games/scrap-workshop', '.nojekyll')
    r = subprocess.run(['git', 'commit', '-q', '-F', '-'], cwd=gs.SITE, input=message, text=True, encoding='utf-8', capture_output=True)
    if r.returncode:
        raise RuntimeError('git commit failed: ' + r.stderr.strip())
    sha = gs.git('rev-parse', 'HEAD')
    r = subprocess.run(['git', 'push', 'origin', 'main'], cwd=gs.SITE, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError('git push failed (the commit is only local): ' + r.stderr.strip())
    return sha


def roll_back_to(version, game, out, co_author, current=None):
    """Points the public entry at `version` again (its historical manifest, files verified), pushes and checks it.
    Returns (attempted, verified); never raises, so the caller can always record what happened."""
    say(f'ROLLING BACK the public entry to {version}')
    try:
        manifest = gs.release_manifest(version)
    except SystemExit as error:
        say(f'  cannot roll back: {error}')
        return False, False
    manifest = {**manifest, 'publishedUtc': gs.now_utc(), 'rollback': {'from': current, 'atUtc': gs.now_utc()}}
    try:
        gs.write_entry(manifest)
        msg = f'Roll back ScrapWorkshop to {version[:8]}\n\nRoll back by scripts/deploy-game.py.\n'
        if co_author:
            msg += f'\nCo-Authored-By: {co_author}\n'
        sha = commit_and_push(msg)
    except Exception as error:  # noqa: BLE001
        say(f'  roll back push failed: {error}')
        return True, False
    verified = guarded('GitHub Pages (roll back)', wait_pages, sha, 900, manifest['version']) and guarded('live check (roll back)', live_check, game, manifest, out / 'rollback')
    say('roll back ' + ('verified' if verified else 'NOT verified - check the site by hand (scripts/rollback-game.py --list)'))
    return True, verified


def deploy(a):
    game = pathlib.Path(a.game).resolve()
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    say('1/7 preflight')
    if subprocess.run(['gh', 'auth', 'status'], capture_output=True).returncode:
        stop('GitHub CLI is not logged in on this PC. Run `gh auth login` once (no token goes into files).')
    if gs.git('rev-parse', '--abbrev-ref', 'HEAD') != 'main':
        stop('the publishing checkout is not on main')
    if gs.git('status', '--porcelain'):
        stop('the publishing checkout has uncommitted changes; commit or remove them first')
    gs.git('fetch', '-q', 'origin')
    ahead = int(gs.git('rev-list', '--count', 'origin/main..HEAD'))
    behind = int(gs.git('rev-list', '--count', 'HEAD..origin/main'))
    subjects = gs.git('log', '--format=%h %s', 'origin/main..HEAD').splitlines() if ahead else []
    entry_unpushed = ahead and gs.git('diff', '--name-only', 'origin/main', 'HEAD', '--', 'games/scrap-workshop/release.json')
    if entry_unpushed or (ahead and behind):
        # Commits here that GitHub, and so the public site, does not have, and the release entry among them: a deploy or
        # roll back cut off between its commit and its push (or a checkout that has also fallen behind). That build is
        # not public and is never reported as such; nothing is forced or thrown away, the person running this decides.
        stop(f'the publishing checkout has {ahead} commit(s) that origin/main does not have'
             + (f' and is {behind} behind it' if behind else '')
             + (' and its release entry (release.json) differs from origin/main: an earlier deploy or roll back stopped'
                ' between its commit and its push?' if entry_unpushed else '') + ' Commits: ' + '; '.join(subjects[:5])
             + '. The public site does not run them. Check them, then push them (git push origin main) and run this again'
             + ' to verify the site, or undo them by hand; this tool neither forces a push nor discards commits.')
    if ahead:
        # Other local commits (the tools, the page around the game) leave the release entry alone: they go out with this
        # deploy's push, after its local check, as they always have.
        say(f'  {ahead} local commit(s) not on origin/main yet go out with this deploy: ' + '; '.join(subjects[:5]))
    if behind:
        gs.git('pull', '-q', '--ff-only', 'origin', 'main')
        say(f'  pulled {behind} commit(s) from origin/main')
    if unity_building(game):
        stop('Unity has the game project open (editor or build). Close it / wait for the build to finish.')
    dirty = gs.git('status', '--porcelain', '--', *gs.GAME_SOURCES, cwd=game)
    if dirty:
        stop('the game has uncommitted source changes; commit the finished change first:\n' + dirty)
    newer = sources_newer_than_build(game)
    if newer:
        stop('game sources changed after the last build; build again first: ' + ', '.join(newer[:5]))
    previous = gs.current_manifest()
    if previous:
        try:
            gs.release_manifest(previous['version'])  # the roll back target must be usable before anything is pushed
        except SystemExit as error:
            put_back()
            stop(f'the current public release {previous["version"]} could not be restored by a roll back: {error}')
        put_back()  # restoring a pruned folder for the check must not stay in the working tree

    say('2/7 prepare')
    manifest = gs.prepare(game)
    version = manifest['version']
    if previous and previous['version'] == version and not a.allow_same_build:
        put_back()
        # origin/main has this build (the checkout is level with it by now); the public site only if it says so.
        live = live_version()
        if live == version:
            say(f'nothing to deploy: origin/main and the public site already run this build ({version})'
                + (f'; the {ahead} local commit(s) above are still not pushed' if ahead else ''))
            return None
        stop(f'origin/main already has this build ({version}) but the public site shows {live or "no readable release.json"}:'
             ' GitHub Pages may still be building it or may have failed. Check the Pages run and the site'
             ' (scripts/rollback-game.py --list); --allow-same-build deploys the entry again.')
    manifest['publishedUtc'] = gs.now_utc()
    gs.write_entry(manifest)
    keep = [version] + [v for v in gs.deployed_versions() if v != version][:KEEP - 1]
    removed = prune(keep)
    out = gs.SITE.parent / 'checks' / f'{stamp}-{version[:8]}'

    say(f'3/7 local check of {version} (kept releases: {", ".join(k[:8] for k in keep)}; removed: {", ".join(r[:8] for r in removed) or "none"})')
    if not local_check(game, version, out):
        put_back()
        stop(f'local check failed; the site files are put back. Results: {out}')
    if a.dry_run:
        put_back()
        say(f'dry run passed; the site files are put back. Results: {out}')
        return None

    say('4/7 commit and push')
    src = manifest['source']['commit'][:7]
    msg = (f'Deploy ScrapWorkshop {version[:8]} (game {src})\n\n'
           f'Release {version} from game commit {manifest["source"]["commit"]}.\n'
           f'Local checks passed (game flow and site entry). Prepared by scripts/deploy-game.py.\n')
    if a.co_author:
        msg += f'\nCo-Authored-By: {a.co_author}\n'
    try:
        sha = commit_and_push(msg)
    except RuntimeError as error:
        gs.git('reset', '-q', '--hard', 'origin/main')
        stop(f'{error}; the local commit is undone and the public site is unchanged')
    say(f'  pushed {sha[:7]}')
    base = {'version': version, 'gameCommit': manifest['source']['commit'], 'siteCommit': sha,
            'previous': previous and previous['version'], 'checks': str(out)}

    say('5/7 GitHub Pages')
    ok = guarded('GitHub Pages', wait_pages, sha, 900, version)
    say('6/7 live check')
    ok = ok and guarded('live check', live_check, game, manifest, out)
    if not ok:
        attempted, verified = (False, False)
        if previous:
            attempted, verified = roll_back_to(previous['version'], game, out, a.co_author, current=version)
        entry = record('failed_after_push', **base, rollback_attempted=attempted, rollback_verified=verified)
        print('DEPLOY FAILED ' + json.dumps(entry, ensure_ascii=False))
        raise SystemExit(2 if verified else 3)

    say('7/7 done')
    entry = record('deployed', **base, publishedUtc=manifest['publishedUtc'])
    print('DEPLOYED ' + json.dumps(entry, ensure_ascii=False))
    return entry


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--game', default=str(gs.SITE.parents[1] / 'ScrapWorkshop'))
    ap.add_argument('--dry-run', action='store_true', help='prepare and check locally, then put the site back; no push')
    ap.add_argument('--allow-same-build', action='store_true', help='redeploy the entry (page/tool change) with the same build')
    ap.add_argument('--co-author', default='')
    a = ap.parse_args()
    try:
        with Lock():
            deploy(a)
    except Stop as why:
        record('stopped_before_push', reason=str(why))
        raise SystemExit('DEPLOY STOPPED: ' + str(why))


if __name__ == '__main__':
    main()
