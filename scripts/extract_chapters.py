# -*- coding: utf-8 -*-
"""EPUBs -> build_data/chapters/{code}.txt (title on line 1, one paragraph per
line after), and each book's cover -> public/cover-{slug}.jpg.

    python scripts/extract_chapters.py          # all three
    python scripts/extract_chapters.py pas      # one book

The epubs live at build_data/epub/{slug}.epub and are gitignored, as is
everything extracted from them.

What differs from souls-reader's extractor: these are clean Draft2Digital
books. The dropcap is a real letter in span.first-letter, not an image, so
nothing needs recovering; get_text() with no separator rejoins "M" + "ark".
Scene breaks are ornamental images with no alt; they are dropped, since a
paragraph of "***" would be narrated and translated like any other.

The chapter title is h1 plus the h3 subtitle. The Pas de Deux numbers in h2 and
names the step in h1 ("Tombé", subtitle "(falling)"), so its title is
"Tombé (falling)". The other two put "Chapter 5" in h1 and the real title in
h3, so theirs is the h3 alone.
"""
import re, sys, io, zipfile
from pathlib import Path
from bs4 import BeautifulSoup
from books import BOOKS

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
ROOT = Path(__file__).resolve().parents[1]
EPUBS = ROOT / 'build_data' / 'epub'
OUT = ROOT / 'build_data' / 'chapters'
PUB = ROOT / 'public'


def clean(t):
    t = t.replace(' ', ' ')
    return re.sub(r'\s+', ' ', t).strip()


def spine(z):
    """(file name, path in zip) in reading order."""
    opf = next(n for n in z.namelist() if n.endswith('.opf'))
    o = z.read(opf).decode('utf-8')
    base = opf.rsplit('/', 1)[0] + '/' if '/' in opf else ''
    items = {}
    for tag in re.findall(r'<item\b[^>]*>', o):
        i, h = re.search(r'\bid="([^"]+)"', tag), re.search(r'href="([^"]+)"', tag)
        if i and h:
            items[i.group(1)] = base + h.group(1)
    return [(items[r].rsplit('/', 1)[-1], items[r])
            for r in re.findall(r'<itemref[^>]*idref="([^"]+)"', o) if r in items]


def page(z, path):
    soup = BeautifulSoup(z.read(path).decode('utf-8'), 'lxml')
    h1, h3 = soup.find('h1'), soup.find('h3')
    h1 = clean(h1.get_text()) if h1 else ''
    h3 = clean(h3.get_text()) if h3 else ''
    head = soup.find('div', class_='heading')
    if head:
        head.decompose()
    for img in soup.find_all('img'):
        img.decompose()
    paras = [t for t in (clean(p.get_text()) for p in soup.find_all('p')) if t]
    return h1, h3, paras


def cover(z, slug):
    """The cover is the image cover.xhtml shows; publish.py seals it with the rest."""
    for name, path in spine(z):
        if name == 'cover.xhtml':
            src = re.search(r'(?:src|xlink:href)="([^"]+)"', z.read(path).decode('utf-8')).group(1)
            img = (path.rsplit('/', 1)[0] + '/' + src).replace('/./', '/')
            parts = []
            for p in img.split('/'):           # resolve ../
                if p == '..':
                    parts.pop()
                else:
                    parts.append(p)
            (PUB / f'cover-{slug}.jpg').write_bytes(z.read('/'.join(parts)))
            return True
    return False


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    want = sys.argv[1:]
    for b in BOOKS:
        if want and b['slug'] not in want:
            continue
        with zipfile.ZipFile(EPUBS / f"{b['slug']}.epub") as z:
            print(f"== {b['title']}" + ('  cover ok' if cover(z, b['slug']) else '  NO COVER'))
            n, pending = 0, []
            for name, path in spine(z):
                stem = name.rsplit('.', 1)[0]
                if stem in b['sections']:
                    h1, _, paras = page(z, path)
                    pending += [h1] + paras          # heads the next chapter
                    continue
                if not re.fullmatch(r'chapter-\d+', stem):
                    continue
                n += 1
                h1, h3, paras = page(z, path)
                title = f'{h1} {h3}' if b['slug'] == 'pas' else h3
                code = f"{b['slug']}{n:02d}"
                (OUT / f'{code}.txt').write_text(
                    '\n'.join([title] + pending + paras) + '\n', encoding='utf-8')
                note = f'  (+ {pending[0]})' if pending else ''
                pending = []
                print(f'{code}  {title:<48} {len(paras):>4} paras{note}')
            if n != b['chapters']:
                sys.exit(f"{b['slug']}: found {n} chapters, books.py says {b['chapters']}")


if __name__ == '__main__':
    main()
