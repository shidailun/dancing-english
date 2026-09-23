# -*- coding: utf-8 -*-
"""Publish the reader to Cloudflare: https://dancing-english.shidailun.com/

Plain files, no sealing and no password, and no secret of any kind to keep.
The three books and their narration are for the class, not the open web:
worker/index.js (the reader gate) serves them only to a student number +
Lingnan email on the 503 or 506 roll. The page, sw.js, the manifest and icons
stay open, so the sign-in screen can draw.

    python scripts/publish.py               # build build_data/site/ + deploy
    python scripts/publish.py --dry-run     # build only

THE SEAL IS GONE (23 Sep 2026). Every data file used to be AES-256-GCM
encrypted under a key derived from a shared password, and the page asked for
it. He said what he wanted instead: the passcode "is going to just be student
no. and email", which is the gate the other readers already use. Ciphertext
behind the gate would protect nothing the gate does not, and a shared password
leaks the day one student passes it on, so the sealing, the password in
build_data/site_secret.json and the lock screen all came out. The secret file
is left where it is: nothing reads it any more, and it is gitignored.

files.json maps every data file to a hash of its content; the reader asks for
path?v=<hash>, so the service worker can keep a file for good offline and still
see a re-cut chapter as new. wrangler uploads only files whose content changed.

A Worker asset may be at most 25 MiB. Nothing on the shelf is near it today -
the longest chapter mp3 is a few MB - but a whole-book recording would be, so
the check below stops a publish that would fail rather than let wrangler find
out.
"""
import hashlib, json, shutil, subprocess, sys, time
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(__file__).resolve().parents[1]
PUB = ROOT / 'public'
SITE = ROOT / 'build_data' / 'site'
URL = 'https://dancing-english.shidailun.com/'
LIMIT = 25 * 1024 * 1024
SHELL = ['manifest.webmanifest', 'sw.js']


def data_files():
    """Everything the reader reads through getBytes, as site paths. The same
    list the seal used to cover, so nothing that was behind the password is in
    the clear now: the registry, the dictionary, one cover per book, every
    chapter pack (three books: pasNN, pieNN, winNN) and every mp3. Only the
    home-screen icons are open, because the sign-in screen is drawn before
    anyone has a cookie."""
    out = [PUB / 'texts' / 'registry.json', PUB / 'dict.json']
    out += sorted(PUB.glob('cover-*.jpg'))
    out += sorted((PUB / 'texts').glob('[a-z][a-z][a-z][0-9][0-9].json'))
    out += sorted((PUB / 'audio').glob('*.mp3'))
    return [f.relative_to(PUB).as_posix() for f in out if f.exists()]


def build():
    if SITE.exists():
        shutil.rmtree(SITE)
    SITE.mkdir(parents=True)
    index = {}
    for rel in data_files():
        src = PUB / rel
        if src.stat().st_size > LIMIT:
            sys.exit(f'{rel} is {src.stat().st_size / 2**20:.1f} MiB: over the 25 MiB asset limit')
        (SITE / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, SITE / rel)
        index[rel] = hashlib.sha256(src.read_bytes()).hexdigest()[:12]
    for rel in SHELL:
        shutil.copyfile(PUB / rel, SITE / rel)
    shutil.copytree(PUB / 'icons', SITE / 'icons')
    (SITE / 'files.json').write_text(json.dumps(index, separators=(',', ':')), encoding='utf-8')
    # Not for search engines: a reader for the class, not an edition of anyone.
    (SITE / 'robots.txt').write_text('User-agent: *\nDisallow: /\n', encoding='utf-8')

    # Stamp the page with this build, so an installed copy can tell it is stale:
    # the real minute, plus a hash so two publishes in one minute still differ.
    page = (PUB / 'index.html').read_text(encoding='utf-8')
    h = hashlib.sha256((page + json.dumps(index)).encode('utf-8')).hexdigest()[:8]
    stamp = time.strftime('%Y-%m-%d %H:%M') + ' ' + h
    (SITE / 'index.html').write_text(
        page.replace('<meta name="build" content="dev">', f'<meta name="build" content="{stamp}">'),
        encoding='utf-8')
    size = sum(f.stat().st_size for f in SITE.rglob('*') if f.is_file())
    print(f'site: {len(index)} data files, {size / 2**20:.1f} MiB, build {stamp}')


def main():
    build()
    if '--dry-run' in sys.argv:
        return
    subprocess.run('npx wrangler deploy', cwd=ROOT, shell=True, check=True)
    print(URL)


if __name__ == '__main__':
    main()
