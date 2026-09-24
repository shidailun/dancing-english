# -*- coding: utf-8 -*-
"""Simplified Chinese for the three books, translated by `claude -p` on the
proxy laptop (his Max plan, no API key) rather than by the Batches API.

    python scripts/zhjob.py make      # build_data/zhjob/: todo/*.tsv + names.md + run.py
    python scripts/zhjob.py make mer  # just these books (an audiobook is only reached this way)
    (copy build_data/zhjob to the proxy, run `python run.py` there, copy out/ back)
    python scripts/zhjob.py collect   # out/*.json -> build_data/zh/<code>.json
    python scripts/handzh.py apply    # into the packs

Sentences only, as in souls-reader: segments stay untranslated. A chunk is ~100
sentences with the three before it as context, so a pronoun or a clipped reply
at the top of a chunk is not translated blind.
"""
import json, sys, io, shutil
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'src' / 'data'
JOB = ROOT / 'build_data' / 'zhjob'
ZH = ROOT / 'build_data' / 'zh'
CHUNK = 100
sys.path.insert(0, str(Path(__file__).parent))
from books import BY_SLUG, codes  # noqa: E402
CODES = codes()


def sentences(pack):
    return [s for p in pack['paragraphs'] for s in p['sentences']]


def make(slugs=()):
    todo = JOB / 'todo'
    chosen = [f"{s}{n:02d}" for s in slugs for n in range(1, BY_SLUG[s]['chapters'] + 1)] or CODES
    todo.mkdir(parents=True, exist_ok=True)
    n = 0
    for code in chosen:
        pack = json.loads((DATA / f'{code}.json').read_text(encoding='utf-8'))
        ss = sentences(pack)
        have = json.loads((ZH / f'{code}.json').read_text(encoding='utf-8')) if (ZH / f'{code}.json').exists() else {}
        for i in range(0, len(ss), CHUNK):
            part = ss[i:i + CHUNK]
            if all(s.get('translation') or have.get(s['id']) for s in part):
                continue
            ctx = ss[max(0, i - 3):i]
            clean = lambda t: ' '.join(t.split())
            lines = [f'# {pack["title"]}']
            lines += [f'CONTEXT\t{clean(s["text"])}' for s in ctx]
            lines += [f'{s["id"]}\t{clean(s["text"])}' for s in part]
            (todo / f'{code}_{i // CHUNK:02d}.tsv').write_text('\n'.join(lines) + '\n', encoding='utf-8')
            n += 1
    shutil.copy(ROOT / 'build_data' / 'names.md', JOB / 'names.md')
    shutil.copy(Path(__file__).parent / 'zhjob_run.py', JOB / 'run.py')
    print(f'{n} chunks in {todo}')


def paired(zh, en=''):
    """Straight quotes the runner could not match to the English: nearly all
    are marks the model added around a word the English sets in italics or
    leaves bare (互相"砍头", 写着"早日康复"), so they open and close within the
    sentence and alternate “ ”.

    The one odd case with an answer is The Winner, whose English has straight
    quotes too: a speech running over two sentences opens in one and closes in
    the next, one " each. The English says which: at its start it opens,
    anywhere else it closes. Any other odd count is left alone, not guessed."""
    if zh.count('"') == 1 and en.count('"') == 1:
        return zh.replace('"', '“' if en.lstrip().startswith('"') else '”')
    if zh.count('"') % 2:
        return zh
    marks = iter('“”' * zh.count('"'))
    return ''.join(next(marks) if c == '"' else c for c in zh)


def collect():
    ZH.mkdir(parents=True, exist_ok=True)
    got, en = {}, {}
    for f in sorted((JOB / 'out').glob('*.json')):
        code = f.stem.rsplit('_', 1)[0]
        if code not in en:
            pack = json.loads((DATA / f'{code}.json').read_text(encoding='utf-8'))
            en[code] = {s['id']: s['text'] for s in sentences(pack)}
        got.setdefault(code, {}).update(
            {k: paired(v, en[code].get(k, ''))
             for k, v in json.loads(f.read_text(encoding='utf-8')).items()})
    for code, zh in got.items():
        old = json.loads((ZH / f'{code}.json').read_text(encoding='utf-8')) if (ZH / f'{code}.json').exists() else {}
        old.update(zh)
        (ZH / f'{code}.json').write_text(json.dumps(old, ensure_ascii=False, indent=0), encoding='utf-8')
    print(f'{sum(map(len, got.values()))} sentences over {len(got)} chapters')


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    if cmd == 'make':
        make(sys.argv[2:])
    else:
        {'collect': collect}.get(cmd, lambda: print(__doc__))()
