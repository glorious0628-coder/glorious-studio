"""Checked deploy of ScrapWorkshop to https://glorious.ai.kr/games/scrap-workshop/ (GitHub Pages, main branch).

Usage (after a finished, checked change unit and a successful Unity WebGL build):
  python scripts/deploy-game.py [--game D:/Game/Web/ScrapWorkshop] [--dry-run] [--allow-same-build]
                                [--co-author "Name <email>"]

Order: preflight -> prepare -> local check -> commit + push -> GitHub Pages built -> live check. Stops before the push on
any failure (the public site keeps its last good release). If Pages or the live check fails after the push, it rolls
the entry back to the previous release and pushes that. It never builds Unity, never calls an AI API, never forces a
reload on players, and never stores credentials (git and gh use the login already on this PC).
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


def say(msg):
    print(datetime.now().strftime('%H:%M:%S ') + msg, flush=True)


def stop(msg):
    raise SystemExit('DEPLOY STOPPED: ' + msg)


class Lock:
    def __enter__(self):
        if LOCK.exists() and time.time() - LOCK.stat().st_mtime < 2 * 3600:
            stop(f'another deploy is running ({LOCK.read_text(encoding="utf-8").strip()}). If it is not, delete {LOCK}')
        LOCK.write_text(f'pid {os.getpid()} at {datetime.now().isoformat(timespec="seconds")}', encoding='utf-8')
        return self

    def __exit__(self, *exc):
        LOCK.unlink(missing_ok=True)


def unity_building(game):
    """A Unity process with this project open (editor or batch build): never copy a build while it runs."""
    ps = ['powershell', '-NoProfile', '-Command',
          "Get-CimInstance Win32_Process -Filter \"Name='Unity.exe'\" | ForEach-Object { $_.CommandLine }"]
    out = subprocess.run(ps, capture_output=True, text=True).stdout.lower()
    return str(game).lower().replace('/', '\\') in out.replace('/', '\\') or (out.strip() and '-projectpath' not in out)


def sources_newer_than_build(game):
    built = (game / 'Build/WebGL/Build/WebGL.wasm.unityweb').stat().st_mtime
    names = gs.git('ls-files', '--cached', '--others', '--exclude-standard', '--', *gs.GAME_SOURCES, cwd=game).splitlines()
    newer = [n for n in names if (game / n).is_file() and (game / n).stat().st_mtime > built + 1]
    return newer


def free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def drive(game, url, steps, out, port):
    """Headless Chrome steps (Tools/cdp/drive.mjs in the game). True when every step passed."""
    r = subprocess.run(['node', str(game / 'Tools/cdp/drive.mjs'), url, str(out), str(steps), str(port)],
                       capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=600)
    (pathlib.Path(out) / 'drive.txt').write_text(r.stdout + r.stderr, encoding='utf-8')
    m = re.search(r'STEPS (\d+) FAILED (\d+)', r.stdout)
    problems = len(re.findall(r'^PROBLEM ', r.stdout, re.M))
    say(f'  {url} -> {m.group(0) if m else "no result"}, browser problems {problems}')
    return bool(m) and m.group(2) == '0' and r.returncode == 0


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
    ok = drive(game, base_url, gs.SITE / 'scripts/homepage-smoke.json', out / f'{tag}-root', 9352) and ok
    return ok


def local_check(game, version, out):
    port = free_port()
    server = subprocess.Popen([sys.executable, '-m', 'http.server', str(port), '--bind', '127.0.0.1', '--directory', str(gs.SITE)],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        time.sleep(1.5)
        return checks(game, f'http://127.0.0.1:{port}/', version, out, 'local')
    finally:
        server.terminate()


def wait_pages(sha, timeout=900):
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
        time.sleep(15)
    say('  GitHub Pages did not report the build in time')
    return False


def live_check(game, manifest, out, wait=420):
    version = manifest['version']
    end = time.time() + wait
    while time.time() < end:
        try:
            if json.loads(gs.fetch(gs.LIVE_GAME + f'release.json?t={int(time.time())}'))['version'] == version:
                break
        except Exception:
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


def commit_and_push(message):
    gs.git('add', '-A', 'games/scrap-workshop', '.nojekyll')
    r = subprocess.run(['git', 'commit', '-q', '-F', '-'], cwd=gs.SITE, input=message, text=True, encoding='utf-8', capture_output=True)
    if r.returncode:
        stop('git commit failed: ' + r.stderr.strip())
    sha = gs.git('rev-parse', 'HEAD')
    r = subprocess.run(['git', 'push', 'origin', 'main'], cwd=gs.SITE, capture_output=True, text=True)
    if r.returncode:
        stop('git push failed (the public site is unchanged; the commit is only local): ' + r.stderr.strip())
    return sha


def roll_back_to(version, game, out, co_author):
    say(f'ROLLING BACK the public entry to {version}')
    gs.restore_release(version)
    manifest = json.loads((gs.DEST / 'releases' / version / 'release.json').read_text(encoding='utf-8'))
    manifest['publishedUtc'] = gs.now_utc()
    manifest['rolledBack'] = True
    gs.write_entry(manifest)
    msg = f'Roll back ScrapWorkshop to {version[:8]}\n\nAutomatic roll back by scripts/deploy-game.py after a failed check.\n'
    if co_author:
        msg += f'\nCo-Authored-By: {co_author}\n'
    sha = commit_and_push(msg)
    ok = wait_pages(sha) and live_check(game, manifest, out / 'rollback')
    say('roll back ' + ('verified' if ok else 'NOT verified - check the site by hand (scripts/rollback-game.py)'))
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--game', default=str(gs.SITE.parents[1] / 'ScrapWorkshop'))
    ap.add_argument('--dry-run', action='store_true', help='prepare and check locally, then put the site back; no push')
    ap.add_argument('--allow-same-build', action='store_true', help='redeploy the entry (page/tool change) with the same build')
    ap.add_argument('--co-author', default='')
    a = ap.parse_args()
    game = pathlib.Path(a.game).resolve()
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')

    with Lock():
        say('1/7 preflight')
        if subprocess.run(['gh', 'auth', 'status'], capture_output=True).returncode:
            stop('GitHub CLI is not logged in on this PC. Run `gh auth login` once (no token goes into files).')
        if gs.git('rev-parse', '--abbrev-ref', 'HEAD') != 'main':
            stop('the publishing checkout is not on main')
        if gs.git('status', '--porcelain'):
            stop('the publishing checkout has uncommitted changes; commit or remove them first')
        gs.git('fetch', '-q', 'origin')
        behind = gs.git('rev-list', '--count', 'HEAD..origin/main')
        if behind != '0':
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

        say('2/7 prepare')
        manifest = gs.prepare(game)
        version = manifest['version']
        if previous and previous['version'] == version and not a.allow_same_build:
            gs.git('checkout', '--', 'games/scrap-workshop')
            gs.git('clean', '-fdq', '--', 'games/scrap-workshop')
            say(f'nothing to deploy: the public site already runs this build ({version})')
            return
        manifest['publishedUtc'] = gs.now_utc()
        gs.write_entry(manifest)
        keep = [version] + [v for v in gs.deployed_versions() if v != version][:KEEP - 1]
        removed = prune(keep)
        out = gs.SITE.parent / 'checks' / f'{stamp}-{version[:8]}'

        say(f'3/7 local check of {version} (kept releases: {", ".join(k[:8] for k in keep)}; removed: {", ".join(r[:8] for r in removed) or "none"})')
        if not local_check(game, version, out):
            gs.git('checkout', '--', 'games/scrap-workshop')
            gs.git('clean', '-fdq', '--', 'games/scrap-workshop')
            stop(f'local check failed; the site files are put back. Results: {out}')
        if a.dry_run:
            gs.git('checkout', '--', 'games/scrap-workshop')
            gs.git('clean', '-fdq', '--', 'games/scrap-workshop')
            say(f'dry run passed; the site files are put back. Results: {out}')
            return

        say('4/7 commit and push')
        src = manifest['source']['commit'][:7]
        msg = (f'Deploy ScrapWorkshop {version[:8]} (game {src})\n\n'
               f'Release {version} from game commit {manifest["source"]["commit"]}.\n'
               f'Local checks passed (game flow and site entry). Prepared by scripts/deploy-game.py.\n')
        if a.co_author:
            msg += f'\nCo-Authored-By: {a.co_author}\n'
        sha = commit_and_push(msg)
        say(f'  pushed {sha[:7]}')

        say('5/7 GitHub Pages')
        ok = wait_pages(sha)
        say('6/7 live check')
        ok = ok and live_check(game, manifest, out)
        if not ok:
            if previous:
                roll_back_to(previous['version'], game, out, a.co_author)
            stop(f'the new release did not pass on the live site. Results: {out}')

        say('7/7 done')
        record = {'version': version, 'gameCommit': manifest['source']['commit'], 'siteCommit': sha,
                  'publishedUtc': manifest['publishedUtc'], 'previous': previous and previous['version'], 'checks': str(out)}
        with open(gs.SITE.parent / 'deploy-history.jsonl', 'a', encoding='utf-8') as f:
            f.write(json.dumps(record) + '\n')
        print('DEPLOYED ' + json.dumps(record, ensure_ascii=False))


if __name__ == '__main__':
    main()
