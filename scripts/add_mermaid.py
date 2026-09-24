# -*- coding: utf-8 -*-
"""Bring The Mermaid's Tale onto the shelf from its audiobook alignment.

The other three books are epubs narrated here by TTS. This one arrives whole:
Lee Wei-Jing's novel in Darryl Sterk's translation (MS "final", 25 Aug 2021,
tracked changes accepted), read by the Simon & Schuster Audio narrator, and
already aligned to that reading word by word with Whisper large-v3 in
OneDrive/Recordings/mermaid_alignment (book.json; 98.5% of the book's words
found in the recording). This script only converts that into the shelf's shape:

  src/data/merNN.json + public/texts/merNN.json   the pack, as build_pack writes it
  public/audio/merNN.mp3                          the chapter, cut and re-encoded
                                                  to the shelf's 48 kbps mono, with
                                                  every timing made chapter-relative
  public/cover-mer.jpg                            the S&S cover, 800 px wide
  public/texts/registry.json                      the work, its 12 chapters, readers

    python scripts/add_mermaid.py            # everything
    python scripts/add_mermaid.py --no-audio # packs, cover, registry only

Translations are left null, as build_pack leaves them. Rerunning keeps any
translation already in a pack (matched by sentence text), so this can be run
again after the alignment is redone without losing that work.
"""
import io, json, re, shutil, subprocess, sys
from datetime import datetime
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, str(Path(__file__).resolve().parent))
from books import BY_SLUG, work_entry  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA, PUB = ROOT / 'src' / 'data', ROOT / 'public'
ALIGN = Path.home() / 'OneDrive - Lingnan University' / 'Recordings' / 'mermaid_alignment'
MP3 = ALIGN.parent / 'mermaid.mp3'
BOOK = BY_SLUG['mer']

WORD = re.compile(r"\S+\s*")                 # build_pack's word: text plus its space
DASH = r"[-‐‑–—―]"                           # the alignment split words on these too
LEAD = 1.0                                   # seconds kept before a chapter's first word
TAIL = 1.5                                   # ...and after its last

# Typos in the manuscript, fixed here rather than in the .docx so a re-import
# keeps them. The alignment is unaffected: only punctuation changes.
# Chapter 5: Donny's reported speech turns direct at "Passion doesn't pay the
# bills" and closes with ’ a paragraph later, but never opened. British style
# opens a quotation again at each new paragraph and closes it once, at the end.
FIXES = {
    'Passion doesn’t pay the bills.': '‘Passion doesn’t pay the bills.',
    'If I had to support myself teaching dance, I’d become another kind of person.’':
        '‘If I had to support myself teaching dance, I’d become another kind of person.’',
}


def norm(w):
    return re.sub(r"[^a-z0-9]", "", w.lower().replace("’", "'"))


def token_times(text, parts):
    """The alignment timed hyphen-split parts ('mid', 'air'); the reader times
    whitespace words ('mid-air, '). Fold the parts back into words."""
    out, k = [], 0
    for tok in WORD.findall(text):
        n = len([x for x in re.split(DASH, tok.strip()) if norm(x)])
        mine = parts[k:k + n]
        k += n
        ts = [p for p in mine if p[1] is not None]
        out.append([tok, ts[0][1] if ts else None, ts[-1][2] if ts else None])
    if k != len(parts):
        raise ValueError(f'{len(parts)} timed parts for {k} in {text[:60]!r}')
    return out


def fill(words, s, e):
    """Words the alignment left untimed (a lone dash) sit between their neighbours."""
    for i, w in enumerate(words):
        if w[1] is None:
            prev = next((words[j][2] for j in range(i - 1, -1, -1) if words[j][2] is not None), s)
            nxt = next((words[j][1] for j in range(i + 1, len(words)) if words[j][1] is not None), e)
            w[1], w[2] = prev, max(prev, nxt)
    return words


def main():
    book = json.loads((ALIGN / 'book.json').read_text(encoding='utf-8'))
    chs = book['chapters']
    assert len(chs) == BOOK['chapters'], f"books.py says {BOOK['chapters']} chapters, alignment has {len(chs)}"
    cut_audio = '--no-audio' not in sys.argv
    reg_chapters = []

    for ci, ch in enumerate(chs):
        code = f"mer{ci + 1:02d}"
        sents = [s for p in ch['paragraphs'] for s in p['sentences'] if s['start'] is not None]
        a0 = max(0.0, sents[0]['start'] - LEAD)
        a1 = sents[-1]['end'] + TAIL
        if ci + 1 < len(chs):                     # never run into the next chapter's title
            nxt = next(s['start'] for p in chs[ci + 1]['paragraphs'] for s in p['sentences'] if s['start'] is not None)
            a1 = min(a1, nxt - 0.3)
        dur = a1 - a0
        rel = lambda t: round(max(0.0, t - a0), 3)

        # Titles as the list shows them: the list numbers chapters itself (01-12),
        # so "1. Nasty Creatures" loses its "1." and the Prelude keeps its name.
        title = re.sub(r"^\d+\.\s*", "", ch['title'])
        old = {}
        if (DATA / f'{code}.json').exists():
            prev = json.loads((DATA / f'{code}.json').read_text(encoding='utf-8'))
            old = {s['text']: s for p in prev['paragraphs'] for s in p['sentences']}

        pack = {'id': code, 'dialect': 'english', 'group': 'mer',
                'title': f"{BOOK['title']} · {title}", 'titleTranslation': None, 'paragraphs': []}
        prev_end, n_s = 0.0, 0
        for p in ch['paragraphs']:
            if p.get('section_break') or not p['sentences']:
                continue
            para = {'id': f"p{len(pack['paragraphs']) + 1:03d}", 'text': None, 'translation': None,
                    'audio': None, 'sentences': []}
            for s in p['sentences']:
                if s['start'] is None:            # unread (none are, today): no timing to give
                    continue
                text = FIXES.get(s['text'], s['text'])
                st = max(prev_end, rel(s['start']))
                en = max(st + 0.05, rel(s['end']))
                prev_end = en
                words = fill([[w, None if a is None else rel(a), None if b is None else rel(b)]
                              for w, a, b in token_times(text, s['words'])], st, en)
                o = old.get(text, {})
                para['sentences'].append({
                    'id': f"{para['id']}s{len(para['sentences']) + 1:02d}", 'text': text,
                    'translation': o.get('translation'), 'reading': None,
                    'audio': code, 'src': f'{code}.mp3', 'origin': 'audiobook',
                    'start': st, 'end': en, 'srcDur': round(dur),
                    'words': [{'text': w, 'start': max(st, min(a, en)), 'end': max(st, min(b, en))}
                              for w, a, b in words],
                    'segments': o.get('segments') or [],
                })
            if para['sentences']:
                pack['paragraphs'].append(para)
                n_s += len(para['sentences'])
        pack['titleTranslation'] = (json.loads((DATA / f'{code}.json').read_text(encoding='utf-8'))
                                    .get('titleTranslation') if old else None)

        (DATA / f'{code}.json').write_text(json.dumps(pack, ensure_ascii=False, indent=1), encoding='utf-8')
        (PUB / 'texts' / f'{code}.json').write_text(
            json.dumps(pack, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
        reg_chapters.append({'id': code, 'dialect': 'english', 'group': 'mer',
                             'title': pack['title'], 'titleTranslation': pack['titleTranslation'],
                             'sents': n_s})

        if cut_audio:
            # Re-encoded, not stream-copied: the shelf's 48 kbps mono keeps the
            # longest chapter (37 min) far under the 25 MiB asset limit, and
            # decoding from a0 makes the cut sample-accurate, which a copy is not.
            subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-ss', f'{a0:.3f}', '-t', f'{dur:.3f}',
                            '-i', str(MP3), '-ac', '1', '-ar', '24000', '-c:a', 'libmp3lame',
                            '-b:a', '48k', str(PUB / 'audio' / f'{code}.mp3')], check=True)
        print(f"{code}  {n_s:>4} sentences  {dur / 60:5.1f} min  {title}")

    # cover: the S&S jacket, at the width of the other three
    from PIL import Image
    im = Image.open(ALIGN / 'cover.jpg').convert('RGB')
    im.resize((800, round(im.height * 800 / im.width)), Image.LANCZOS).save(
        PUB / 'cover-mer.jpg', quality=88, optimize=True)

    # registry: replace this book's work, chapters and readers; touch nothing else
    reg_path = PUB / 'texts' / 'registry.json'
    reg = json.loads(reg_path.read_text(encoding='utf-8'))
    shutil.copy2(reg_path, reg_path.with_name(f"registry.{datetime.now():%Y%m%d-%H%M%S}.json"))
    codes = {c['id'] for c in reg_chapters}
    reg['works'] = [w for w in reg['works'] if w['slug'] != 'mer'] + [work_entry(BOOK)]
    reg['chapters'] = [c for c in reg['chapters'] if c['id'] not in codes] + reg_chapters
    reg['readers'] = {k: v for k, v in reg['readers'].items() if k not in codes}
    reg['readers'].update({c: 'Narration' for c in sorted(codes)})
    reg_path.write_text(json.dumps(reg, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print(f"registry.json  {len(reg['works'])} books  {len(reg['chapters'])} chapters")


if __name__ == '__main__':
    main()
