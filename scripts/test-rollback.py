"""Usage: python scripts/test-rollback.py [scratch folder] [game folder]

Exercise the deploy roll back paths in a throwaway clone with a local bare 'origin' and fake Pages / live answers.
Nothing here reaches GitHub or the public site: the clone's origin is a local bare repository, wait_pages, live_check and
fetch are replaced, and the real publishing checkout is only read (its scripts are copied in)."""
import importlib.util
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time

REAL = pathlib.Path(__file__).resolve().parents[1]
GAME = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else REAL.parents[1] / 'ScrapWorkshop').resolve()
TMP = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else tempfile.mkdtemp(prefix='deploy-rollback-test-')).resolve()
OLD = '0d485cb91c3cccfa'
results = []


def check(ok, what):
    results.append((bool(ok), what))
    print(('PASS ' if ok else 'FAIL ') + what, flush=True)


def sh(*args, cwd=None):
    r = subprocess.run(args, cwd=cwd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if r.returncode:
        raise SystemExit(f'{args} failed: {r.stderr}')
    return r.stdout.strip()


if TMP.exists():
    shutil.rmtree(TMP, onerror=lambda f, p, e: (os.chmod(p, 0o700), f(p)))
TMP.mkdir(parents=True)
sh('git', 'clone', '-q', '--bare', str(REAL), str(TMP / 'origin.git'))
sh('git', 'clone', '-q', str(TMP / 'origin.git'), str(TMP / 'site'))
site = TMP / 'site'
for f in (REAL / 'scripts').glob('*.py'):
    shutil.copyfile(f, site / 'scripts' / f.name)
sh('git', '-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qam', 'test: working-tree scripts', cwd=site)
sh('git', 'push', '-q', 'origin', 'main', cwd=site)
check('glorious0628-coder' not in sh('git', 'remote', 'get-url', 'origin', cwd=site), 'the throwaway clone pushes to a local bare repo, not GitHub')

sys.path.insert(0, str(site / 'scripts'))
import gamesite as gs  # noqa: E402
spec = importlib.util.spec_from_file_location('deploy_game', site / 'scripts' / 'deploy-game.py')
deploy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deploy)
check(gs.SITE == site, f'scripts run against the clone ({gs.SITE})')
os.environ['GIT_AUTHOR_NAME'] = os.environ['GIT_COMMITTER_NAME'] = 'test'
os.environ['GIT_AUTHOR_EMAIL'] = os.environ['GIT_COMMITTER_EMAIL'] = 'test@example.invalid'

# 1. The old release has no manifest in its folder: it comes from history and its files are verified.
check(not (gs.DEST / 'releases' / OLD / 'release.json').exists(), f'{OLD} has no release.json in its folder (as audited)')
hm = gs.history_manifest(OLD)
check(hm and hm['version'] == OLD and 'source' not in hm, 'its historical root manifest is found, with nothing filled in from today')
m = gs.release_manifest(OLD)
check(m['files'] == hm['files'], 'release_manifest accepts it after checking lengths, SHA-256 and the dialogue modules')
# ... also when the folder has been pruned (deleted in a later commit): restored from history, then checked.
shutil.rmtree(gs.DEST / 'releases' / OLD)
sh('git', 'commit', '-qam', 'test: prune the old release', cwd=site)
m2 = gs.release_manifest(OLD)
check(m2['version'] == OLD and (gs.DEST / 'releases' / OLD / 'WebGL.wasm.unityweb').is_file(), 'a pruned old release is restored from history and verified')
deploy.put_back()
sh('git', 'reset', '-q', '--hard', 'origin/main', cwd=site)
# ... and a damaged file is refused.
p = gs.DEST / 'releases' / OLD / 'WebGL.loader.js'
p.write_bytes(p.read_bytes() + b'x')
try:
    gs.release_manifest(OLD)
    check(False, 'a release whose file does not match is refused')
except SystemExit:
    check(True, 'a release whose file does not match is refused')
deploy.put_back()

# 2. A download error in the live check no longer escapes: it becomes a failed check.
real_fetch = gs.fetch
new = gs.current_manifest()


def fake_fetch(url, timeout=60):
    if 'release.json' in url:
        return json.dumps({'version': new['version']}).encode()
    raise OSError('fake network error on ' + url)


gs.fetch = fake_fetch
deploy.time.sleep = lambda s: None
escaped = None
try:
    deploy.live_check(GAME, new, TMP / 'checks')
except OSError as e:
    escaped = e
check(escaped is not None, 'unguarded, the fake download error escapes live_check (the audited problem reproduces)')
check(deploy.guarded('live check', deploy.live_check, GAME, new, TMP / 'checks') is False, 'guarded, the same error is a failed live check')
gs.fetch = real_fetch

# 3. A failed live check after the push: roll back to the old release (history manifest), recorded as attempted and
# verified. The clone's public entry is first put on the old release, so the deploy goes old -> current build.
deploy.say('test: point the clone at the old release first')
old = gs.release_manifest(OLD)
gs.write_entry({**old, 'publishedUtc': gs.now_utc()})
sh('git', 'add', '-A', cwd=site)
sh('git', 'commit', '-qm', 'test: old release public', cwd=site)
sh('git', 'push', '-q', 'origin', 'main', cwd=site)

calls = []
deploy.local_check = lambda game, version, out: True           # the real local check passed in the real deploy
deploy.wait_pages = lambda sha, timeout=900: calls.append(('pages', sha)) or True


def failing_then_ok(game, manifest, out, wait=420):
    calls.append(('live', manifest['version']))
    if manifest['version'] != OLD:
        raise OSError('fake: live download failed for the new release')
    return True


deploy.live_check = failing_then_ok


class Args:
    game = str(GAME)
    dry_run = False
    allow_same_build = False
    co_author = ''


hist = TMP / 'deploy-history.jsonl'
code = None
try:
    with deploy.Lock():
        deploy.deploy(Args())
except SystemExit as e:
    code = e.code
rows = [json.loads(l) for l in hist.read_text(encoding='utf-8').splitlines()] if hist.exists() else []
last = rows[-1] if rows else {}
origin_entry = json.loads(sh('git', '--git-dir', str(TMP / 'origin.git'), 'show', 'main:games/scrap-workshop/release.json'))
check(code == 2, f'the deploy ends with code 2 (failed, rolled back and verified): {code}')
check(last.get('state') == 'failed_after_push' and last.get('rollback_attempted') and last.get('rollback_verified'),
      f'recorded: failed_after_push, rollback_attempted, rollback_verified ({last})')
check(origin_entry['version'] == OLD and origin_entry.get('rollback', {}).get('from') == new['version'],
      'the bare origin ends on the old release, marked as a roll back from the new one')
check([c[0] for c in calls] == ['pages', 'live', 'pages', 'live'], f'pages and live checked for the deploy, then for the roll back ({calls})')
check(not (site / '.deploy.lock').exists(), 'the lock is released')

# 3b. The roll back itself cannot be verified: recorded as attempted but not verified, code 3.
deploy.live_check = lambda game, manifest, out, wait=420: False
code = None
try:
    with deploy.Lock():
        deploy.deploy(Args())
except SystemExit as e:
    code = e.code
last = json.loads(hist.read_text(encoding='utf-8').splitlines()[-1])
check(code == 3 and last['rollback_attempted'] and not last['rollback_verified'], f'an unverified roll back is recorded as such (code {code}, {last.get("rollback_verified")})')

# 4. Two runs started together: the atomic lock lets exactly one in.
runner = TMP / 'lock_runner.py'
runner.write_text(f'''import importlib.util, sys, time
sys.path.insert(0, r"{site / 'scripts'}")
spec = importlib.util.spec_from_file_location("d", r"{site / 'scripts' / 'deploy-game.py'}")
d = importlib.util.module_from_spec(spec); spec.loader.exec_module(d)
t0 = float(sys.argv[1])
while time.time() < t0: pass
try:
    with d.Lock():
        print("ENTERED", flush=True); time.sleep(2)
except d.Stop:
    print("STOPPED", flush=True)
''', encoding='utf-8')
t0 = time.time() + 2
procs = [subprocess.Popen([sys.executable, str(runner), str(t0)], stdout=subprocess.PIPE, text=True) for _ in range(2)]
outs = sorted(p.communicate()[0].strip() for p in procs)
check(outs == ['ENTERED', 'STOPPED'], f'two simultaneous runs: one enters, one is stopped ({outs})')
check(not (site / '.deploy.lock').exists(), 'the winner removed its own lock')

print(f'HARNESS {sum(ok for ok, _ in results)}/{len(results)} passed')
sys.exit(0 if all(ok for ok, _ in results) else 1)
