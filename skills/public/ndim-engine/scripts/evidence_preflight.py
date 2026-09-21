#!/usr/bin/env python3
"""Check an evidence file before sending it to the NDIM engine.

Reports length against the engine limits, a heuristic language guess, and personal-data patterns.
Optionally splits an over-long file into chunks at paragraph boundaries.

    python evidence_preflight.py --file notes.txt [--json] [--split-dir DIR]

Exit codes: 0 ready to plan, 1 needs attention (length, language), 2 unreadable file.
Personal-data findings are warnings, not failures: the researcher decides what to do about them.
"""
import argparse
import json
import re
import sys
from pathlib import Path

MIN_CHARS, MAX_CHARS = 20, 20000

STOPWORDS = {
    'en': 'the and is are of to in that for with we they it was have not but this our their from at be as on'.split(),
    'fr': 'le la les des du est et une un pour dans que qui pas nous vous avec sur au aux ce cette sont ont'.split(),
    'rw': ("ni na mu ku ya wa za cya bya rya kandi ariko cyangwa uko iyo abantu nta ntabwo byose ndetse "
           "nk'").split(),
}
PII = {
    'email': re.compile(r'[\w.+-]+@[\w-]+(?:\.[\w-]+)+'),
    'phone': re.compile(r'(?<!\d)(?:\+?250[\s-]?|0)7[2389](?:[\s-]?\d){7}(?!\d)'),
    'national_id_16_digits': re.compile(r'(?<!\d)(?:\d[ -]?){15}\d(?!\d)'),
}


def guess_language(text):
    tokens = re.findall(r"[a-zA-Z']+", text.lower())
    if not tokens:
        return {'likely': 'unknown', 'scores': {}}
    scores = {lang: sum(token in words for token in tokens) / len(tokens) for lang, words in
              ((lang, set(words)) for lang, words in STOPWORDS.items())}
    best = max(scores, key=scores.get)
    runner_up = sorted(scores.values())[-2]
    if scores[best] < 0.04 or len(tokens) < 8:
        return {'likely': 'unknown', 'scores': {k: round(v, 3) for k, v in scores.items()}}
    return {'likely': best if scores[best] > 1.5 * runner_up else 'unknown',
            'scores': {k: round(v, 3) for k, v in scores.items()}}


def find_pii(text):
    hits = {}
    for kind, pattern in PII.items():
        found = [match.group(0) for match in pattern.finditer(text)]
        if found:
            hits[kind] = {'count': len(found), 'examples_masked': [value[:2] + '***' for value in found[:3]]}
    return hits


def split_text(text, limit=MAX_CHARS):
    """Split at blank lines; an over-long paragraph is split at the last sentence end or space before the limit."""
    chunks, current = [], ''
    for paragraph in re.split(r'\n\s*\n', text):
        while len(paragraph) > limit:
            cut = max(paragraph.rfind('. ', 0, limit), paragraph.rfind(' ', 0, limit))
            cut = cut + 1 if cut > 0 else limit
            head, paragraph = paragraph[:cut].strip(), paragraph[cut:].strip()
            if current:
                chunks.append(current)
                current = ''
            chunks.append(head)
        candidate = f'{current}\n\n{paragraph}' if current else paragraph
        if len(candidate) > limit:
            chunks.append(current)
            candidate = paragraph
        current = candidate
    if current.strip():
        chunks.append(current)
    return [chunk.strip() for chunk in chunks if chunk.strip()]


def check(text):
    length = len(text.strip())
    language = guess_language(text)
    pii = find_pii(text)
    problems, warnings = [], []
    if length < MIN_CHARS:
        problems.append(f'Too short: {length} characters; the engine needs at least {MIN_CHARS}.')
    if length > MAX_CHARS:
        problems.append(f'Too long: {length} characters; the engine accepts at most {MAX_CHARS}. '
                        'Split it (--split-dir) and plan one experiment per chunk. Do not truncate silently.')
    if language['likely'] in {'fr', 'rw'}:
        problems.append(f"Looks {language['likely'].upper()}, not English. The engine blocks non-English evidence. "
                        'Ask the researcher about translation first (see workflows.md, Translation).')
    elif language['likely'] == 'unknown':
        warnings.append('Language could not be determined confidently. Check that the text is English.')
    if pii:
        warnings.append('Possible personal data found. Tell the researcher before sending: the engine stores the evidence text. '
                        'Names and places are not detected by this check.')
    return {'characters': length, 'words': len(text.split()), 'language': language, 'personal_data': pii,
            'problems': problems, 'warnings': warnings, 'ready_to_plan': not problems}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--file', required=True, type=Path)
    parser.add_argument('--json', action='store_true', help='machine-readable output')
    parser.add_argument('--split-dir', type=Path, help='write chunk_NN.txt files here when the text is too long')
    args = parser.parse_args(argv)
    try:
        text = args.file.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError) as exc:
        print(f'Cannot read {args.file}: {exc}', file=sys.stderr)
        return 2
    report = check(text)
    if args.split_dir and report['characters'] > MAX_CHARS:
        args.split_dir.mkdir(parents=True, exist_ok=True)
        chunks = split_text(text)
        report['chunks'] = []
        for index, chunk in enumerate(chunks, 1):
            path = args.split_dir / f'chunk_{index:02d}.txt'
            path.write_text(chunk, encoding='utf-8')
            report['chunks'].append({'file': str(path), 'characters': len(chunk)})
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"{args.file}: {report['characters']} characters, {report['words']} words, "
              f"likely language: {report['language']['likely']}")
        for kind, hit in report['personal_data'].items():
            print(f"  personal data: {kind} x{hit['count']} (e.g. {', '.join(hit['examples_masked'])})")
        for line in report['problems']:
            print(f'  PROBLEM: {line}')
        for line in report['warnings']:
            print(f'  WARNING: {line}')
        for chunk in report.get('chunks', []):
            print(f"  wrote {chunk['file']} ({chunk['characters']} characters)")
        print('READY to plan.' if report['ready_to_plan'] else 'NOT ready: resolve the problems above.')
    return 0 if report['ready_to_plan'] else 1


if __name__ == '__main__':
    sys.exit(main())
