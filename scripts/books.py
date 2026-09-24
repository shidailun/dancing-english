# -*- coding: utf-8 -*-
"""The three books, in shelf order. Every script reads its chapter codes from
here rather than counting chapters itself, which is what souls-reader did with
range(1, 32) scattered through six files.

A chapter code is the book's slug and a two-digit number (pas01, win55, pie32):
unique across the shelf, so one dictionary, one Word Review deck and one audio
folder serve all three books without a clash.

All three epubs come from the same Draft2Digital template: a chapter is an
xhtml file in the spine whose name is chapter-NNN.xhtml, with its title in h1
and its subtitle in h3.
"""

BOOKS = [
    # The Pas de Deux names its chapters after ballet steps and groups them the
    # way a grand pas de deux is built (ENTREE, ADAGIO, the variations, CODA).
    # Those section pages are a sentence each; they go at the head of the
    # chapter that follows them rather than into the chapter list.
    {'slug': 'pas', 'title': 'The Pas de Deux', 'sub': 'A Classical Ballet Romance',
     'zh': '双人舞', 'year': 2018, 'chapters': 27, 'rev': [0.5, 0.556],
     'voice': 'en-US-AriaNeural',
     'sections': ['entree', 'adagio', 'male-variation', 'female-variation',
                  'coda', 'curtain-call']},
    {'slug': 'win', 'title': 'The Winner', 'sub': 'A Ballroom Dance Novel',
     'zh': '赢家', 'year': 2016, 'chapters': 55, 'sections': [], 'rev': [0.5, 0.90],
     'voice': 'en-US-AvaNeural'},
    {'slug': 'pie', 'title': 'The Piece', 'sub': 'A Contemporary Ballet Novel',
     'zh': '舞作', 'year': 2020, 'chapters': 32, 'sections': [], 'rev': [0.21, 0.5],
     'voice': 'en-US-MichelleNeural'},
]
# 'rev' is where the Word Review button sits on each cover, as fractions of
# the cover's width and height: a patch of plain ground on each (between the
# subtitle and the tiara; on the floorboards under the flourish; the black left
# of the dancer), as souls-reader put its button just below the guitar.
# The Winner's was .82, which put the button across "a ballroom dance novel";
# "word review a bit lower on the winner", 23 Sep, and .90 is the dark band
# between the flourish and her name.
# 'voice' is each book's narrator: three women, one per book, so the shelf
# does not sound like one reader doing all three. All en-US because all three
# novels are American. Aria and Michelle are the two voices Microsoft tags for
# novels; Ava, the most expressive, gets the ballroom book.
AUTHOR = 'Erin Bomboy'

# Books that arrive already recorded: a human narrator's audiobook, aligned to
# the text elsewhere (Recordings/mermaid_alignment) and brought in whole by
# scripts/add_mermaid.py. They are kept out of BOOKS on purpose, so codes() -
# and with it extract_chapters, build_pack, narrate and align - never sees them:
# there is no epub to extract, and a TTS narration or an MMS re-alignment would
# overwrite the reader's own voice and Whisper's word timings.
# The Mermaid's Tale is Lee Wei-Jing's 人魚紀 in Darryl Sterk's translation
# (ISBN 9781398507609), with the Simon & Schuster Audio recording. Its Word
# Review button sits in the pink right of "THE", above the apostrophe.
# 'note' heads its chapter list: the English departs freely from 人鱼纪, so its
# Chinese is a new crib of the English (build_data/names.md says so to the
# translator), and the reader should not take it for the novel's own text.
AUDIOBOOKS = [
    {'slug': 'mer', 'title': 'The Mermaid’s Tale',
     'zh': '人鱼纪', 'author': 'Lee Wei-Jing', 'translator': 'Darryl Sterk',
     'chapters': 12, 'rev': [0.76, 0.065],
     'note': {'en': 'The Chinese here is a crib: a close, sentence-by-sentence '
                    'rendering of this English, which is a free translation. '
                    'It is not Lee Wei-Jing’s original.',
              'zh': '这里的中文是逐句对照的直译稿，译自这个英文版本（英文本身是意译），'
                    '并非李维菁的原著《人鱼纪》。'}},
]

BY_SLUG = {b['slug']: b for b in BOOKS + AUDIOBOOKS}


def work_entry(b):
    """A book's entry in registry.json's 'works'."""
    return {'slug': b['slug'], 'dialect': 'english', 'title': b['title'],
            'author': b.get('author', AUTHOR), 'zh': b['zh'],
            'cover': f"cover-{b['slug']}.jpg", 'rev': b['rev'],
            'chapters': [f"{b['slug']}{n:02d}" for n in range(1, b['chapters'] + 1)],
            **({'note': b['note']} if 'note' in b else {})}


def codes(slug=None):
    """Every chapter code on the shelf, in reading order; or one book's."""
    return [f"{b['slug']}{n:02d}" for b in BOOKS if slug in (None, b['slug'])
            for n in range(1, b['chapters'] + 1)]


def book_of(code):
    return BY_SLUG[code[:3]]
