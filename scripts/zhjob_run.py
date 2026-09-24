# -*- coding: utf-8 -*-
"""Runs on the proxy laptop, from the copied zhjob folder: every todo/*.tsv
without an out/*.json goes to `claude -p` (his Max plan), and a reply is kept
only if its id<TAB>Chinese lines cover every id, none empty, in Simplified characters.
Rerun-safe: finished chunks are skipped. Progress in run.log.

    python run.py            # 4 at a time
    python run.py 2          # fewer, if the plan's limit bites
"""
import json, os, subprocess, sys, shutil, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
TODO, OUT, LOG = HERE / 'todo', HERE / 'out', HERE / 'run.log'
EMPTY = HERE / 'cwd'          # no CLAUDE.md, no repo: the call sees only the prompt
NAMES = (HERE / 'names.md').read_text(encoding='utf-8')
# claude.exe from the native installer, or the npm install's claude.cmd.
CLAUDE = (shutil.which('claude.exe') or shutil.which('claude')
          or str(Path.home() / '.local' / 'bin' / 'claude.exe'))
# Without the API key, so a laptop that has one set still translates on the
# plan's login instead of billing the API (and failing on the key's warning).
ENV = {k: v for k, v in os.environ.items() if k != 'ANTHROPIC_API_KEY'}

# Characters that exist only in Traditional. One in a reply means the model
# slipped script, and the chunk is asked again.
TRAD = set('們這個說裡來為時會對開後過還麼國學無從發問經體實現樣認應點關兩頭門聽讓東車書見話變間長邊當覺讀寫進們給線錯頁愛與')

RULES = """You are translating a chunk of an English novel into Simplified Chinese for a
mainland Chinese university student who reads the English alongside it. The
translation is a crutch for the English, not a replacement: it must make each
English sentence intelligible, so stay close to its structure and never merge,
split or summarise sentences.

Rules:
- Simplified characters, Mainland usage, natural modern written Chinese.
- Names and terms exactly as in the list below. A name not listed: transliterate
  per Xinhua conventions, consistently.
- Keep the novel's register: dialogue sounds like speech, profanity and
  sensuality are the author's and are translated, not softened.
- The first line (#) is the book and chapter. CONTEXT lines are the sentences
  just before this chunk: read them, do not translate them.
- Chinese punctuation: full-width commas and stops, and curly quotation marks
  “ ” and ‘ ’ exactly where the English has them. Never straight " quotes.
- One translation per id line. A line that is only a section heading or a
  symbol still gets a translation (or the symbol itself). Never an empty string.

Output one line per id and nothing else: the id, a TAB, the translation.
Same order as the input. No commentary, no markdown fences, no JSON.

"""


def log(msg):
    line = time.strftime('%H:%M:%S ') + msg
    print(line, flush=True)
    with LOG.open('a', encoding='utf-8') as f:
        f.write(line + '\n')


def curly(zh, en):
    """A straight quote the model still wrote becomes the curly one the English
    has in the same place: the n-th " takes the n-th “ or ” of the English. A
    sentence of dialogue often opens or closes a quote the next one finishes,
    so pairing the straight quotes among themselves would get those wrong."""
    marks = [c for c in en if c in '“”']
    if zh.count('"') != len(marks):
        return zh
    it = iter(marks)
    return ''.join(next(it) if c == '"' else c for c in zh)


def check(reply, ids):
    # Lines, not JSON: a model writing dialogue drops straight quotes into the
    # Chinese, and one of those breaks a whole JSON reply.
    zh = {}
    for line in reply.splitlines():
        k, sep, v = line.strip().partition('\t')
        if sep and k in ids:
            zh[k] = curly(v.strip(), ids[k])
    missing = [i for i in ids if not zh.get(i)]
    if missing:
        return None, f'{len(missing)} missing, e.g. {missing[:3]}'
    trad = sorted({c for i in ids for c in zh[i] if c in TRAD})
    if trad:
        return None, f'Traditional characters {"".join(trad)}'
    return zh, None


def one(tsv):
    out = OUT / (tsv.stem + '.json')
    if out.exists():
        return 'skip'
    text = tsv.read_text(encoding='utf-8')
    ids = dict(l.split('\t', 1) for l in text.splitlines()
               if '\t' in l and not l.startswith('CONTEXT\t'))
    prompt = RULES + 'Names and terms:\n\n' + NAMES + '\n\nThe chunk:\n\n' + text
    for attempt in range(1, 4):
        try:
            r = subprocess.run([CLAUDE, '-p', '--model', 'opus', '--output-format', 'text'],
                               input=prompt, capture_output=True, text=True,
                               encoding='utf-8', cwd=EMPTY, env=ENV, timeout=1800)
            zh, why = check(r.stdout, ids) if r.returncode == 0 else (None, f'exit {r.returncode}: {r.stderr[:200] or r.stdout[:200]}')
        except subprocess.TimeoutExpired:
            zh, why = None, 'timeout'
        if zh:
            out.write_text(json.dumps(zh, ensure_ascii=False, indent=0), encoding='utf-8')
            log(f'{tsv.stem}  ok  {len(zh)}')
            return 'ok'
        log(f'{tsv.stem}  try {attempt}: {why}')
        if any(w in why.lower() for w in ('usage limit', 'rate limit', 'limit reached', 'hit your limit')):
            time.sleep(900)     # plan limit: wait it out rather than burn retries
    return 'fail'


if __name__ == '__main__':
    OUT.mkdir(exist_ok=True)
    EMPTY.mkdir(exist_ok=True)
    jobs = sorted(TODO.glob('*.tsv'))
    workers = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    log(f'start: {len(jobs)} chunks, {workers} at a time')
    with ThreadPoolExecutor(workers) as ex:
        res = list(ex.map(one, jobs))
    log(f'done: {res.count("ok")} ok, {res.count("skip")} skipped, {res.count("fail")} failed')
