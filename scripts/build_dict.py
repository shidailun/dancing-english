# -*- coding: utf-8 -*-
"""The learner dictionary the reader pops up when a word is tapped:
public/dict.json = {word: {"ipa": ..., "zh": ...}}.

Same shape germanic-literature's build_dict.py produces (ipa + a short Chinese
gloss), keyed by the bare lowercase word, because that is all the reader can
recover from a tapped token.

    python scripts/build_dict.py --now --limit 200    # Messages API, a taste
    python scripts/build_dict.py                      # Batches API, half price
    python scripts/build_dict.py --now --chapter pas01   # one chapter's words
    python scripts/build_dict.py --now --words hunched     # a word she asked about

Rerun-safe: only words missing from dict.json are requested, so this can be run
again after a chapter is added without re-glossing the other 9,000 words.

Model: claude-sonnet-5 by default, not Opus. Glossing "hollow" or "amplifier" is
lexical lookup, not judgement, and the wordlist is large enough that the
difference is real money; --model claude-opus-5 if the glosses disappoint. The
prose translation in translate.py is the opposite case and uses Opus.
"""
import json, re, sys, io, time
from collections import Counter
from pathlib import Path
import anthropic
from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.messages.batch_create_params import Request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'build_data' / 'chapters'
DICT = ROOT / 'public' / 'dict.json'
STATE = ROOT / 'build_data' / 'dict_state.json'

MODEL = 'claude-sonnet-5'
CHUNK = 50                      # words per request; 100 truncated replies
MIN_LEN = 1                     # 'a' and 'I' are words too

# Written out here rather than asked of the model. Contractions are a closed
# class: there are sixty of them in the three novels and no more are coming, and
# what each one stands for is a fact, not a judgement call. They are also 5,138
# of the 6,193 taps that answered "not in the dictionary yet" - 83% of every
# miss on the shelf - so they are the entries worth not waiting on an API for.
# Merged on every run, before anything is sent anywhere, so this half works with
# no key and no credit.
#
# Not here: possessives (he's, that's, Mark's), which lookup() already strips to
# he, that and mark; hyphenated compounds, which lookup() now resolves to their
# head; and the handful of one-off jokes the books spell with hyphens all
# through, which no dictionary should carry.
HAND = {
    "didn't":    {'ipa': 'ˈdɪdənt',  'zh': 'did not 的缩写：没有、不曾'},
    "i'd":       {'ipa': 'aɪd',      'zh': 'I would / I had 的缩写：我会、我曾'},
    "he'd":      {'ipa': 'hid',      'zh': 'he would / he had 的缩写：他会、他曾'},
    "i'm":       {'ipa': 'aɪm',      'zh': 'I am 的缩写：我是'},
    "couldn't":  {'ipa': 'ˈkʊdənt',  'zh': 'could not 的缩写：不能、不会'},
    "wasn't":    {'ipa': 'ˈwʌzənt',  'zh': 'was not 的缩写：不是、没有'},
    "she'd":     {'ipa': 'ʃid',      'zh': 'she would / she had 的缩写：她会、她曾'},
    "don't":     {'ipa': 'doʊnt',    'zh': 'do not 的缩写：不、不要'},
    "hadn't":    {'ipa': 'ˈhædənt',  'zh': 'had not 的缩写：不曾、没有'},
    "you're":    {'ipa': 'jʊɹ',      'zh': 'you are 的缩写：你是、你们是'},
    "wouldn't":  {'ipa': 'ˈwʊdənt',  'zh': 'would not 的缩写：不会、不愿'},
    "i've":      {'ipa': 'aɪv',      'zh': 'I have 的缩写：我已经'},
    "we'd":      {'ipa': 'wid',      'zh': 'we would / we had 的缩写：我们会、我们曾'},
    "can't":     {'ipa': 'kænt',     'zh': 'cannot 的缩写：不能、不会'},
    "they'd":    {'ipa': 'ðeɪd',     'zh': 'they would / they had 的缩写：他们会、他们曾'},
    "it'd":      {'ipa': 'ˈɪtəd',    'zh': 'it would / it had 的缩写：它会、它曾'},
    "i'll":      {'ipa': 'aɪl',      'zh': 'I will 的缩写：我将、我会'},
    "we're":     {'ipa': 'wɪɹ',      'zh': 'we are 的缩写：我们是'},
    "you've":    {'ipa': 'juv',      'zh': 'you have 的缩写：你已经'},
    "who'd":     {'ipa': 'hud',      'zh': 'who would / who had 的缩写：谁会、谁曾'},
    "weren't":   {'ipa': 'wɜɹnt',    'zh': 'were not 的缩写：不是、没有'},
    "doesn't":   {'ipa': 'ˈdʌzənt',  'zh': 'does not 的缩写：不、不是'},
    "won't":     {'ipa': 'woʊnt',    'zh': 'will not 的缩写：不会、不愿'},
    "they're":   {'ipa': 'ðɛɹ',      'zh': 'they are 的缩写：他们是'},
    "haven't":   {'ipa': 'ˈhævənt',  'zh': 'have not 的缩写：还没有'},
    "you'll":    {'ipa': 'jul',      'zh': 'you will 的缩写：你将、你会'},
    "isn't":     {'ipa': 'ˈɪzənt',   'zh': 'is not 的缩写：不是'},
    "you'd":     {'ipa': 'jud',      'zh': 'you would / you had 的缩写：你会、你曾'},
    "we'll":     {'ipa': 'wil',      'zh': 'we will 的缩写：我们将、我们会'},
    "there'd":   {'ipa': 'ðɛɹd',     'zh': 'there would / there had 的缩写：将会有、曾经有'},
    "aren't":    {'ipa': 'ɑɹnt',     'zh': 'are not 的缩写：不是'},
    "we've":     {'ipa': 'wiv',      'zh': 'we have 的缩写：我们已经'},
    "how'd":     {'ipa': 'haʊd',     'zh': 'how did / how would 的缩写：怎么会、怎样'},
    "shouldn't": {'ipa': 'ˈʃʊdənt',  'zh': 'should not 的缩写：不应该'},
    "hasn't":    {'ipa': 'ˈhæzənt',  'zh': 'has not 的缩写：还没有'},
    "it'll":     {'ipa': 'ˈɪtəl',    'zh': 'it will 的缩写：它将、它会'},
    "they'll":   {'ipa': 'ðeɪl',     'zh': 'they will 的缩写：他们将、他们会'},
    "y'know":    {'ipa': 'jəˈnoʊ',   'zh': 'you know 的口语缩写：你知道、（口头禅）'},
    "he'll":     {'ipa': 'hil',      'zh': 'he will 的缩写：他将、他会'},
    "would've":  {'ipa': 'ˈwʊdəv',   'zh': 'would have 的缩写：本来会'},
    "that'll":   {'ipa': 'ˈðætəl',   'zh': 'that will 的缩写：那将、那会'},
    "o'clock":   {'ipa': 'əˈklɑk',   'zh': '点钟'},
    "must've":   {'ipa': 'ˈmʌstəv',  'zh': 'must have 的缩写：一定已经'},
    "why'd":     {'ipa': 'waɪd',     'zh': 'why did / why would 的缩写：为什么'},
    "they've":   {'ipa': 'ðeɪv',     'zh': 'they have 的缩写：他们已经'},
    "should've": {'ipa': 'ˈʃʊdəv',   'zh': 'should have 的缩写：本来应该'},
    "y'all":     {'ipa': 'jɔl',      'zh': 'you all 的缩写（美国南方）：你们'},
    "who're":    {'ipa': 'ˈhuɚ',     'zh': 'who are 的缩写：是谁'},
    "who'll":    {'ipa': 'hul',      'zh': 'who will 的缩写：谁将、谁会'},
    "where've":  {'ipa': 'ˈwɛɹəv',   'zh': 'where have 的缩写：在哪里'},
    "what'd":    {'ipa': 'ˈwʌtəd',   'zh': 'what did / what would 的缩写：什么'},
    "she'll":    {'ipa': 'ʃil',      'zh': 'she will 的缩写：她将、她会'},
    "how're":    {'ipa': 'ˈhaʊɚ',    'zh': 'how are 的缩写：怎么样'},
    "could've":  {'ipa': 'ˈkʊdəv',   'zh': 'could have 的缩写：本来可以'},
    "might've":  {'ipa': 'ˈmaɪtəv',  'zh': 'might have 的缩写：可能已经'},
    "c'mon":     {'ipa': 'kəˈmɑn',   'zh': 'come on 的口语写法：来吧、快点'},
    # Not a contraction: the interval between two acts, and a word these books
    # use for what it means on a programme.
    "entr'acte": {'ipa': 'ˈɑntɹˌækt', 'zh': '幕间休息、幕间表演'},
}

SYSTEM = (
    # This prompt arrived from germanic-literature still describing that
    # shelf's horror novel, heavy metal and Traditional Chinese, none of which
    # is true here: these are Erin Bomboy's three dance novels, and all 13,770
    # glosses already in dict.json are Simplified. It was steering 'set',
    # 'turn', 'lift' and 'company' to the wrong sense for a ballet book.
    "You are building a learner dictionary for a Hong Kong university student "
    "reading an American dance novel in English.\n"
    "For each word give:\n"
    "- ipa: General American IPA, no enclosing slashes (e.g. kjʊɹiˈɑsəti)\n"
    "- zh: a short Simplified Chinese gloss, 1-3 senses "
    "separated by 、, no example sentences, no part-of-speech labels.\n"
    "Gloss the sense the novel is likely using: these are books about classical "
    "ballet, ballroom competition and a choreographer's company, so 'turn', "
    "'lift', 'company' and 'piece' are more likely the dance senses.\n"
    "A contraction is a headword like any other: gloss didn't, I'd and he'd as "
    "themselves, showing what they stand for.\n"
    "If a word is a proper name, give its ipa and put the person, ballet or "
    "place in zh (e.g. 芭蕾舞剧名、人名).\n"
    "Output STRICT JSON only: {word: {\"ipa\": ..., \"zh\": ...}, ...}. "
    "No commentary, no markdown fences."
)


def _anthropic_key():
    """ANTHROPIC_API_KEY from the environment, falling back to User scope in the
    registry. Never from a file."""
    import os, winreg
    k = os.environ.get('ANTHROPIC_API_KEY')
    if k:
        return k
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment') as h:
        return winreg.QueryValueEx(h, 'ANTHROPIC_API_KEY')[0]


client = anthropic.Anthropic(api_key=_anthropic_key())


WORD = re.compile(r"[^\W\d_](?:[^\W\d_]|['-])*")


def wordlist(chapter=None):
    """Every word the book uses, commonest first - so a --limit run glosses the
    words the reader will actually meet first rather than an alphabetical slice.

    The pattern used to be [^\\W\\d_][^\\W\\d_'’-]*, whose second class is
    negated: it excluded the apostrophe and the hyphen instead of allowing them,
    so "didn't" entered the list as "didn" and no contraction was ever glossed.
    dict.json held 13,770 words and not one with an apostrophe, while the books
    say didn't 634 times, I'd 582 and he'd 475 - every one of them a tap that
    answered "not in the dictionary yet".

    Curly apostrophes are folded to straight ones here and in the reader's
    clean(), so one entry serves both spellings: the books use both, 634 didn’t
    against 80 didn't.
    """
    c = Counter()
    for f in sorted(SRC.glob(f'{chapter}.txt' if chapter else '*.txt')):
        text = f.read_text(encoding='utf-8').replace('’', "'")
        c.update(w.lower().strip("'-") for w in WORD.findall(text))
    return [w for w, _ in c.most_common() if w and len(w) >= MIN_LEN]


def load():
    return json.loads(DICT.read_text(encoding='utf-8')) if DICT.exists() else {}


def save(d):
    DICT.parent.mkdir(parents=True, exist_ok=True)
    DICT.write_text(json.dumps(d, ensure_ascii=False, indent=0), encoding='utf-8')


def reply_text(message):
    """Opus thinks adaptively, so content[0] may be a ThinkingBlock."""
    return ''.join(b.text for b in message.content if b.type == 'text')


def parse(text):
    text = re.sub(r'^```(?:json)?|```$', '', text.strip(), flags=re.M).strip()
    got = json.loads(text)
    return {k.lower(): v for k, v in got.items()
            if isinstance(v, dict) and v.get('ipa') and v.get('zh')}


def chunks(words):
    for i in range(0, len(words), CHUNK):
        yield words[i:i + CHUNK]


def prompt(batch):
    return 'Gloss every word:\n\n' + '\n'.join(batch)


def run_now(todo):
    d = load()
    for i, batch in enumerate(chunks(todo), 1):
        r = client.messages.create(model=MODEL, max_tokens=8000, system=SYSTEM,
                                   messages=[{'role': 'user', 'content': prompt(batch)}])
        try:
            d.update(parse(reply_text(r)))
        except json.JSONDecodeError:
            print(f'  chunk {i}: unparseable reply ({r.stop_reason}), skipped')
        save(d)
        print(f'  chunk {i}: {len(d)} entries')


def run_batch(todo):
    state = json.loads(STATE.read_text(encoding='utf-8')) if STATE.exists() else {}
    if not state.get('batch_id'):
        reqs = [Request(custom_id=f'w{i:04d}',
                        params=MessageCreateParamsNonStreaming(
                            model=MODEL, max_tokens=8000, system=SYSTEM,
                            messages=[{'role': 'user', 'content': prompt(b)}]))
                for i, b in enumerate(chunks(todo))]
        b = client.messages.batches.create(requests=reqs)
        state = {'batch_id': b.id, 'requests': len(reqs)}
        STATE.write_text(json.dumps(state), encoding='utf-8')
        print(f'submitted {len(reqs)} requests as {b.id}')

    bid = state['batch_id']
    while True:
        b = client.messages.batches.retrieve(bid)
        print(f'{bid}  {b.processing_status}  {b.request_counts}')
        if b.processing_status == 'ended':
            break
        time.sleep(60)

    d = load()
    for r in client.messages.batches.results(bid):
        if r.result.type != 'succeeded':
            print(f'  {r.custom_id}: {r.result.type}')
            continue
        try:
            d.update(parse(reply_text(r.result.message)))
        except json.JSONDecodeError:
            print(f'  {r.custom_id}: unparseable reply, skipped')
    save(d)
    STATE.unlink(missing_ok=True)
    print(f'dict.json  {len(d)} entries')


def main():
    global MODEL, CHUNK
    argv = sys.argv[1:]
    if '--model' in argv:
        i = argv.index('--model')
        MODEL = argv[i + 1]
        del argv[i:i + 2]
    if '--chunk' in argv:               # smaller chunks: a refusal loses fewer words
        i = argv.index('--chunk')
        CHUNK = int(argv[i + 1])
        del argv[i:i + 2]
    limit = None
    if '--limit' in argv:
        i = argv.index('--limit')
        limit = int(argv[i + 1])
        del argv[i:i + 2]

    chapter = words = None
    if '--chapter' in argv:
        i = argv.index('--chapter')
        chapter = argv[i + 1]
        del argv[i:i + 2]
    if '--words' in argv:
        i = argv.index('--words')
        words = [w.lower() for w in argv[i + 1:] if not w.startswith('--')]
        del argv[i:i + 1 + len(words)]

    have = load()

    # The hand-written entries first, and saved straight away: they need no key,
    # and a run that dies on the API afterwards should still have delivered them.
    added = {w: e for w, e in HAND.items() if w not in have}
    if added:
        have.update(added)
        save(have)
        print(f'hand-written entries added: {len(added)}')

    todo = [w for w in (words or wordlist(chapter)) if w not in have]
    if limit:
        todo = todo[:limit]
    print(f'model: {MODEL}   have {len(have)}   to gloss {len(todo)}')
    if not todo:
        return
    run_now(todo) if '--now' in argv else run_batch(todo)


if __name__ == '__main__':
    main()
