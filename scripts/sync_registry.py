# -*- coding: utf-8 -*-
"""Push the book metadata in books.py into public/texts/registry.json without
touching the packs.

build_pack.py owns the registry, but only on a full 114-chapter build, which
re-segments every chapter and rewrites every pack. That is the wrong price for
nudging a Word Review button five percent up the cover: the packs carry the
alignment timings, and a rebuild puts all 22,482 of them through carry() for
nothing. This writes the per-book fields alone and leaves 'chapters',
'readers' and 'storyCodes' exactly as build_pack left them.

Run it after editing title, sub, zh, cover or rev in books.py. Anything that
changes the chapter list or the segmentation is a build_pack job, not this.
"""
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from books import BOOKS, AUDIOBOOKS, work_entry  # noqa: E402

PUB = Path(__file__).resolve().parent.parent / 'public' / 'texts'
REG = PUB / 'registry.json'


def main():
    if not REG.exists():
        sys.exit('no registry.json - run scripts/build_pack.py first')

    reg = json.loads(REG.read_text(encoding='utf-8'))
    before = {w['slug']: dict(w) for w in reg['works']}

    # An audiobook is listed only once add_mermaid.py has put its packs in.
    fresh = [work_entry(b) for b in BOOKS + AUDIOBOOKS if b['slug'] in before or b in BOOKS]

    # A book that gained or lost a chapter needs its packs built, not this.
    for w in fresh:
        old = before.get(w['slug'])
        if old and old['chapters'] != w['chapters']:
            sys.exit(f"{w['slug']}: chapter list changed - this is a build_pack.py job")

    changes = [(w['slug'], k, before[w['slug']].get(k), v)
               for w in fresh for k, v in w.items()
               if w['slug'] in before and before[w['slug']].get(k) != v]
    if not changes:
        print('registry.json already matches books.py - nothing written')
        return

    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    backup = REG.with_name(f'registry.{stamp}.json')
    shutil.copy2(REG, backup)

    reg['works'] = fresh
    REG.write_text(json.dumps(reg, ensure_ascii=False, separators=(',', ':')),
                   encoding='utf-8')

    print(f'backed up to {backup.name}')
    for slug, key, was, now in changes:
        print(f'  {slug}.{key}: {was} -> {now}')
    print(f"registry.json  {len(reg['chapters'])} chapters  {REG.stat().st_size} bytes")


if __name__ == '__main__':
    main()
