#!/usr/bin/env python3
"""Check that today's wars (wars.html) can still fill its copy from the data.

The page computes every number and quotes several sentences from the map's data
files each time it loads. If a lookup finds nothing, the page leaves that
sentence out and says so only in the browser console. This script runs the same
lookups against the files on disk, so a refresh that breaks one fails here
instead of on the page.

  python3 scripts/check_wars.py          # print what it found; exit 1 on a failure
  python3 scripts/check_wars.py --quiet  # print failures only

FAIL: a sentence, number or example would be missing from the page.
note: the data moved and the page switches to its other wording or drops a
      sentence by design (for example the latest year is no longer the record).
      Read the step once; nothing is broken.

It mirrors the lookups in wars.html. If the page's token code changes, change
this with it.
"""
import json
import re
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent
load = lambda p: json.load(open(R / p, encoding='utf-8'))

SENT = re.compile(r'(?<=[.?!])\s+(?=[A-Z0-9“"\'‘\[{])')
TOKEN = re.compile(r'\{(\w+)\}')


def sentences(s):
    return SENT.split(str(s or ''))


def main():
    quiet = '--quiet' in sys.argv
    fails, notes = [], []
    try:
        D, U, L, Y, AR, C = (load(p) for p in ('data/conflicts.json', 'data/ucdp.json', 'data/level.json',
                                                 'data/ucdp_years.json', 'data/war_areas.json', 'data/wars.json'))
        page = open(R / 'wars.html', encoding='utf-8').read()
    except Exception as e:  # a missing or broken file is the plainest failure there is
        print('FAIL: could not read the files:', e)
        sys.exit(1)

    by_id = {c['id']: c for c in D['conflicts']}
    backers = {b['id']: b for b in D['backers']}
    wars = [c for c in D['conflicts'] if c.get('kind') != 'pressure']
    steps = {s['id']: s for s in C['steps']}

    # ---- quoted sentences: {from, pick, cut} must still find its sentence ----
    def field_of(path):
        file, *rest = path.split('.')
        if file == 'entry':
            c = by_id.get(rest[0])
            return c.get(rest[1]) if c else None
        if file == 'conflicts' and rest[0] == 'reading':
            s = next((x for x in D.get('reading', {}).get('steps', []) if x.get('id') == rest[1]), None)
            return s.get('text') if s else None
        v = {'conflicts': D, 'level': L, 'years': Y, 'ucdp': U, 'areas': AR}.get(file)
        for k in rest:
            v = v.get(k) if isinstance(v, dict) else None
        return v

    def quote(ref):
        text = field_of(ref['from'])
        if not text:
            return None
        if ref.get('pick'):
            return next((x for x in sentences(text) if ref['pick'] in x), None)
        return text

    quotes = {}

    def walk(o, where):
        if isinstance(o, dict):
            if isinstance(o.get('from'), str) and '.' in o['from']:
                got = quote(o)
                if where.startswith('quotes/'):
                    quotes[where.split('/')[1]] = got
                if not got:
                    fails.append(f"{where}: nothing found for {o['from']}" + (f" with the phrase \"{o['pick']}\"" if o.get('pick') else '')
                                 + '. The sentence was reworded or the field is gone; fix the phrase in data/wars.json.')
            for k, v in o.items():
                walk(v, f'{where}/{k}' if where else k)
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, f'{where}/{i}')
    walk(C, '')

    # ---- tokens the page computes; None means the sentence that uses it is dropped ----
    T = dict(quotes)

    def need(name, fn):
        try:
            v = fn()
        except Exception as e:
            v = None
            fails.append(f'{{{name}}}: {type(e).__name__} {e}')
            T[name] = None
            return
        T[name] = v
        if v is None or v == '':
            fails.append(f'{{{name}}} has no value')

    years, yy = L.get('years') or [], Y.get('years') or []
    last_y = years[-1] if years else {}
    need('as_of', lambda: D['as_of'])
    need('rule', lambda: D['rule'])
    need('ucdp_reach', lambda: U['reach'])
    need('ucdp_pulled', lambda: U['pulled'])
    need('ucdp_versions', lambda: U['versions'])
    need('win_from', lambda: U['window']['from'])
    need('win_to', lambda: U['window']['to'])
    need('flag_pct', lambda: U['flagged_share'])
    need('ucdp_n', lambda: last_y['n'])
    need('ucdp_year', lambda: last_y['year'])
    need('ucdp_wars', lambda: last_y['wars'])
    need('interstate', lambda: last_y['interstate'])
    need('acd_version', lambda: L['versions']['conflicts'])

    rule = str(L.get('rule') or '')
    for name, rx, flags in (('acd_bar', r'with ([\d,]+) or more deaths', 0), ('war_bar', r'war level means ([\d,]+) or more deaths', re.I)):
        m = re.search(rx, rule, flags)
        T[name] = m.group(1) if m else None
        if not m:
            fails.append(f"{{{name}}}: level.json's rule no longer has the wording the page reads the number from (/{rx}/). "
                         'The opening step and the glossary lose their threshold sentences.')

    # Sudan is the worked example
    sudan = by_id.get('sudan')
    if not sudan:
        fails.append('no entry with id "sudan": the worked example is gone and the page will not draw')
    else:
        need('sudan_start', lambda: sudan['start'])
        need('sudan_prov', lambda: len(sudan['areas']) or None)
        if len(sudan.get('parties', [])) != 2:
            fails.append(f"sudan has {len(sudan.get('parties', []))} parties; step 4 names exactly two")
        if len({p.get('side') for p in sudan.get('parties', [])}) != 2:
            fails.append('sudan no longer has two sides; step 4 says two sides fight')
        need('sudan_backers', lambda: len({t['backer'] for t in sudan['ties'] if not t.get('ended')}) or None)
    if 'usa' not in backers:
        fails.append('no backer with id "usa": step 7 and step 8 name the United States')
    if not any(b.get('hue') for b in D['backers']):
        fails.append('no backer carries a hue: step 7 has no states to pick')
    for c in wars:
        if not c.get('region'):
            fails.append(f"{c['id']}: no region, so step 1's count by region is short")
        if not c.get('band'):
            fails.append(f"{c['id']}: no band, so its dot has no size")
        if not (U.get('entries', {}).get(c['id']) or {}).get('window'):
            notes.append(f"{c['id']}: no UCDP window count, so it has no bar in step 3")

    # step 3: the three wars of the guess
    for wid in (steps.get('size', {}).get('guess') or {}).get('options', []):
        if wid not in by_id:
            fails.append(f'step 3 guess: no war with id "{wid}"')
        elif not (U.get('entries', {}).get(wid) or {}).get('window'):
            fails.append(f'step 3 guess: UCDP has no window count for "{wid}"')

    # step 6: one real line per grade
    tier_ids = list(D.get('tiers', {}))
    for k in steps.get('know', {}).get('tier_defs', {}):
        if k not in tier_ids:
            fails.append(f'step 6: the data has no grade "{k}"')
    for x in steps.get('know', {}).get('examples', []):
        c = by_id.get(x['war'])
        t = c and next((t for t in c['ties'] if t['backer'] == x['backer'] and t['party'] == x['party']
                        and (not x.get('tier') or t['tier'] == x['tier'])), None)
        label = f"{x['backer']} to {x['party']} in {x['war']} as {x.get('tier')}"
        if not t:
            fails.append(f'step 6 example: no line {label}. It moved grade or was removed; pick another example in data/wars.json.')
        elif t.get('ended'):
            fails.append(f'step 6 example: the line {label} has ended')
        elif not any(s.get('url') for s in t.get('sources', [])):
            notes.append(f'step 6 example: the line {label} has no linked source')

    # step 7: two states on the same side in one war and opposite sides in another
    pair = (steps.get('same', {}).get('pair') or {}).get('states', [])
    if len(pair) == 2:
        for b in pair:
            if b not in backers:
                fails.append(f'step 7 pair: no backer with id "{b}"')
        same = split = 0
        for c in wars:
            sides = []
            for b in pair:
                t = next((t for t in c['ties'] if t['backer'] == b and not t.get('ended')), None)
                p = t and next((p for p in c['parties'] if p['id'] == t['party']), None)
                sides.append(p and p.get('side'))
            if all(sides):
                same += sides[0] == sides[1]
                split += sides[0] != sides[1]
        if not same or not split:
            fails.append(f'step 7 pair: {pair[0]} and {pair[1]} now share a side in {same} wars and oppose in {split}; '
                         'the step says both happen. Check the quoted sentence against the lines.')
    else:
        fails.append('step 7 pair: data/wars.json should name two states')

    # ---- by-design switches: say when the page changes its wording ----
    try:
        if last_y['n'] <= max(r['n'] for r in years[:-1]):
            notes.append(f"step 9: {last_y['year']} is no longer the year with the most conflicts; the page uses its other wording")
        avgs = [(yy[i]['year'], sum(q['best'] for q in yy[i - 4:i + 1]) / 5) for i in range(4, len(yy))]
        rank = sorted(avgs, key=lambda a: -a[1]).index(avgs[-1])
        if rank > 1:
            notes.append('step 9: the latest five-year average is no longer in the top two; the page drops the comparison')
        peak = max(yy, key=lambda r: r['best'])
        rows = (L.get('deaths') or {}).get(str(peak['year'])) or {}
        top = max(rows.items(), key=lambda kv: kv[1][0]) if rows else None
        if not top or top[1][0] * 2 <= peak['best'] or top[0] not in (L.get('names') or {}):
            notes.append(f"step 9: no one country holds over half of {peak['year']}'s deaths (or it has no name); the page drops that sentence")
        live = [t for c in wars for t in c['ties'] if not t.get('ended')]
        if sum(t['tier'] == 'open' for t in live) * 2 <= len(live):
            notes.append('step 6: on-the-record lines are no longer most of the lines; the page drops "Most help is given in the open."')
    except Exception as e:
        fails.append(f'step 9 series: {type(e).__name__} {e}')

    # ---- every {token} in the copy must be one the page knows ----
    defined = set(re.findall(r'\bT\.(\w+)\s*=', page)) | set(C.get('quotes', {}))
    used = {}

    def strings(o, where):
        if isinstance(o, str):
            for k in TOKEN.findall(o):
                used.setdefault(k, where)
        elif isinstance(o, dict):
            for k, v in o.items():
                strings(v, f'{where}/{k}' if where else k)
        elif isinstance(o, list):
            for i, v in enumerate(o):
                strings(v, f'{where}/{i}')
    strings(C, '')
    for k, where in sorted(used.items()):
        if k in defined:
            if k in T and T[k] is None:
                fails.append(f'{where}: the sentence with {{{k}}} is left out on the page')
        elif not re.search(r'\b' + re.escape(k) + r'\b', page):
            fails.append(f'{where}: {{{k}}} is not a number the page computes (a typo in data/wars.json?)')

    for n in notes:
        if not quiet:
            print('note:', n)
    for f in fails:
        print('FAIL:', f)
    if not quiet or fails:
        print(f"today's wars: {len(used)} tokens, {len(fails)} failures, {len(notes)} notes")
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
