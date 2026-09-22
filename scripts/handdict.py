# -*- coding: utf-8 -*-
"""Dictionary entries written by hand, in a Claude Code session, at no API cost -
the same arrangement handzh.py has for the translations.

    python scripts/handdict.py todo pas01          # words in pas01 not yet glossed
    python scripts/handdict.py apply               # merge build_data/dict/*.json

build_data/dict/<name>.json is {word: {"ipa": ..., "zh": ...}}, keyed by the
bare lowercase word exactly as build_dict.py's wordlist() tokenises it, since
that is all the reader recovers from a tapped token. `apply` rebuilds
public/dict.json from those files alone, so a bad gloss is fixed in its file
and not in the artifact.

Glosses are Simplified Chinese in Mainland usage, 1-3 senses separated by 、,
choosing the sense a ballet or ballroom novel is likely using.
"""
import json, re, sys, io
from pathlib import Path
from collections import Counter

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'build_data' / 'chapters'
HAND = ROOT / 'build_data' / 'dict'
DICT = ROOT / 'public' / 'dict.json'
WORD = re.compile(r"[^\W\d_][^\W\d_'’-]*")      # build_dict.py's tokeniser


def have():
    d = {}
    for f in sorted(HAND.glob('*.json')):
        d.update(json.loads(f.read_text(encoding='utf-8')))
    return d


def todo(codes):
    c = Counter()
    for code in codes:
        c.update(w.lower() for w in WORD.findall((SRC / f'{code}.txt').read_text(encoding='utf-8')))
    got = have()
    for w, _ in c.most_common():
        if w not in got:
            print(w)


def apply():
    d = {k.lower(): v for k, v in have().items() if v.get('ipa') and v.get('zh')}
    DICT.write_text(json.dumps(d, ensure_ascii=False, indent=0), encoding='utf-8')
    print(f'dict.json  {len(d)} entries')


if __name__ == '__main__':
    cmd, *rest = sys.argv[1:] or ['apply']
    todo(rest) if cmd == 'todo' else apply()
