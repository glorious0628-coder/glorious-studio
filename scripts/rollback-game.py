"""Point the public ScrapWorkshop back at an earlier release, then push and check it live.

Usage:
  python scripts/rollback-game.py --list                 releases the site has pointed at, newest first, and whether
                                                         each can be restored (files match their manifest)
  python scripts/rollback-game.py                        back to the release before the current one
  python scripts/rollback-game.py --to 0d485cb91c3cccfa  back to that release (restored from git history if pruned)
  [--co-author "Name <email>"] [--game D:/Game/Web/ScrapWorkshop]

No Unity build is needed: every release is kept in the repository history, and a release published before per-release
manifests existed is checked against its historical release.json. A tab still open on another release keeps working;
nobody's page is reloaded. The attempt and whether it was verified live are written to deploy-history.jsonl.
"""
import argparse
import importlib.util
import pathlib

import gamesite as gs

spec = importlib.util.spec_from_file_location('deploy_game', pathlib.Path(__file__).with_name('deploy-game.py'))
deploy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deploy)

ap = argparse.ArgumentParser()
ap.add_argument('--to')
ap.add_argument('--list', action='store_true')
ap.add_argument('--game', default=str(gs.SITE.parents[1] / 'ScrapWorkshop'))
ap.add_argument('--co-author', default='')
a = ap.parse_args()
versions = gs.deployed_versions()
current = gs.current_manifest()['version']
if a.list:
    for v in versions:
        try:
            gs.release_manifest(v)
            usable = 'restorable'
        except SystemExit as error:
            usable = f'NOT restorable: {error}'
        print(v, '(current)' if v == current else '', usable)
    deploy.put_back()  # a check may have restored a pruned folder
    raise SystemExit(0)
target = a.to or next((v for v in versions if v != current), None)
if not target or target == current:
    raise SystemExit('No earlier release to go back to (or it is already current).')
try:
    with deploy.Lock():
        if gs.git('status', '--porcelain'):
            deploy.stop('the publishing checkout has uncommitted changes; commit or remove them first')
        gs.git('pull', '-q', '--ff-only', 'origin', 'main')
        stamp = deploy.datetime.now().strftime('%Y%m%d-%H%M%S')
        out = gs.SITE.parent / 'checks' / f'{stamp}-rollback-{target[:8]}'
        attempted, verified = deploy.roll_back_to(target, pathlib.Path(a.game).resolve(), out, a.co_author, current=current)
        deploy.record('manual_rollback', version=target, previous=current, rollback_attempted=attempted, rollback_verified=verified, checks=str(out))
        raise SystemExit(0 if verified else 1)
except deploy.Stop as why:
    raise SystemExit('ROLL BACK STOPPED: ' + str(why))
