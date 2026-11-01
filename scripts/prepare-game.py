"""Publish only a completed Unity WebGL build and cost-free dialogue assets.

Usage: python scripts/prepare-game.py D:/Game/Web/ScrapWorkshop
This prepares files; it never builds Unity, commits, pushes, or calls an AI API. The full checked deploy (local check,
push, GitHub Pages, live check, roll back on failure) is scripts/deploy-game.py.
"""
import json
import sys

import gamesite

manifest = gamesite.prepare(sys.argv[1])
print(json.dumps({'version': manifest['version'], 'bytes': sum(f['bytes'] for f in manifest['files'].values()), 'path': str(gamesite.DEST)}))
