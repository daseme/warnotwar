#!/usr/bin/env python3
"""Check data/conflicts.json against the rules written on the map page, and
compute the fields the page should never have to trust by hand.

Usage: scripts/check_conflicts.py [--write] [--quiet]

Without --write it reports and exits 1 on any failure. With --write it fills
the computed fields (evidence_to, single, source_counts, as_of counts) and
then checks. The pre-commit hook runs it without --write, so a commit with a
stale computed field fails until the script has been run with --write.

Rules checked (each is also written on the page):
- ids: every tie's backer, party, tier and kinds resolve; every source has a
  class from source_classes, a text, a publisher (null only for press with no
  outlet named), a date in YYYY, YYYY-MM or YYYY-MM-DD form or null, and a
  link that is http(s) or null.
- evidence_to is the latest dated source that counts (counts != false).
- since_precision is year or month when since is set; a month with precision
  year is placed in that month on the stepper and shown as the year.
- on the record needs a counting source from the backer or the side it helps,
  or a tracker that compiles governments' own announcements (class research,
  flagged open_on_tracker).
- documented needs a counting source of class document.
- reported with one publisher behind it (via counts as the publisher it
  relays) gets single = true; with two publishers or two classes, false.
- alleged has no counting source of class document, government or research.
- a tie that has ended has an ended month.
- bands: a war's band equals the band UCDP's window best implies, unless the
  entry names a lower counter in band_basis; the band_source sentence's first
  number, when it opens with "UCDP counted", equals UCDP's window best.
"""
import json
import os
from datetime import date
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, 'data', 'conflicts.json')
UCDP = os.path.join(ROOT, 'data', 'ucdp.json')
DATE = re.compile(r'^\d{4}(-\d{2}(-\d{2})?)?$')
BAND_EDGES = [(10000, '3'), (1500, '2'), (500, '1')]


def band_for(n):
    for edge, b in BAND_EDGES:
        if n >= edge:
            return b
    return None


def main():
    write = '--write' in sys.argv
    quiet = '--quiet' in sys.argv
    d = json.load(open(PATH))
    u = json.load(open(UCDP)) if os.path.exists(UCDP) else None
    fails, warns = [], []
    backers = {b['id']: b for b in d['backers']}
    classes = set(d['source_classes'])
    win_from = d['window']['from']
    counts = dict(ties=0, live=0, open=0, shown=0, reported=0, claimed=0, ended=0, reference_only=0, open_on_tracker=0, no_outlet=0,
                  document_unlinked=0, single_publisher=0, prewindow=0, undated=0, weapons=0, weapons_sipri=0, sources=0, sources_unlinked=0,
                  sources_undated=0, sources_unopened=0, checked=0, one_class=0)
    for c in d['conflicts']:
        parties = {p['id'] for p in c.get('parties', [])}
        for t in c.get('ties', []):
            tid = f"{c['id']}/{t['backer']}/{t['party']}"
            counts['ties'] += 1
            if t['backer'] not in backers: fails.append(f'{tid}: unknown backer')
            if t['party'] not in parties: fails.append(f'{tid}: unknown party')
            if t['tier'] not in d['tiers']: fails.append(f'{tid}: unknown tier {t["tier"]}'); continue
            for k in t.get('kinds', []):
                if k not in d['kinds']: fails.append(f'{tid}: unknown kind {k}')
            if not t.get('kinds'): fails.append(f'{tid}: no kinds')
            srcs = t.get('sources') or []
            if not srcs: fails.append(f'{tid}: no sources'); continue
            dated = []
            pubs, cls = set(), set()
            for i, s in enumerate(srcs):
                counts['sources'] += 1
                sid = f'{tid}#{i}'
                if s.get('class') not in classes: fails.append(f'{sid}: unknown class {s.get("class")}')
                if not s.get('text'): fails.append(f'{sid}: no text')
                if 'publisher' not in s: fails.append(f'{sid}: no publisher field')
                elif s['publisher'] is None:
                    if s.get('class') != 'press': fails.append(f'{sid}: publisher null on a non-press source')
                    counts['no_outlet'] += 1
                if s.get('date') is not None and not DATE.match(str(s['date'])): fails.append(f'{sid}: bad date {s["date"]}')
                if s.get('url') is not None and not re.match(r'^https?://', str(s['url'])): fails.append(f'{sid}: bad url')
                if not s.get('url'): counts['sources_unlinked'] += 1
                if not s.get('date'): counts['sources_undated'] += 1
                if s.get('seen'): counts['sources_unopened'] += 1
                if s.get('class') == 'document' and not s.get('url'): counts['document_unlinked'] += 1
                if s.get('counts', True):
                    if s.get('date'): dated.append(str(s['date']))
                    cls.add(s.get('class'))
                    if s.get('via') or s.get('publisher'): pubs.add(s.get('via') or s.get('publisher'))   # an unnamed outlet never counts as a second publisher
            # evidence_to
            ev = max(dated) if dated else None
            if write: t['evidence_to'] = ev
            elif t.get('evidence_to') != ev: fails.append(f'{tid}: evidence_to is {t.get("evidence_to")}, sources say {ev}')
            # since
            if t.get('since'):
                # a month with precision year means the line is placed in that month on the stepper but shown as the year
                if t.get('since_precision') not in ('year', 'month'): fails.append(f'{tid}: since {t["since"]} needs since_precision year or month')
                elif t['since_precision'] == 'month' and len(str(t['since'])) < 7: fails.append(f'{tid}: since {t["since"]} is not a month')
            elif t.get('since_precision'): fails.append(f'{tid}: since_precision without since')
            if t.get('ended') and not DATE.match(str(t['ended'])): fails.append(f'{tid}: bad ended {t["ended"]}')
            # tiers
            tier = t['tier']
            counts[tier] += 1
            if t.get('ended'): counts['ended'] += 1
            live = not t.get('ended')
            if live: counts['live'] += 1
            if tier == 'open':
                if not ({'backer', 'recipient'} & cls):
                    if 'research' in cls: counts['open_on_tracker'] += 1; t['open_on_tracker'] = True
                    else: fails.append(f'{tid}: on the record without a backer, recipient or tracker source')
                elif 'open_on_tracker' in t: del t['open_on_tracker']
            if tier == 'shown' and 'document' not in cls: fails.append(f'{tid}: documented without a document source')
            if tier == 'reported':
                single = len(pubs) < 2 and len(cls) < 2
                if write: t['single'] = single
                elif bool(t.get('single')) != single: fails.append(f'{tid}: single should be {single} (publishers {sorted(pubs)}, classes {sorted(cls)})')
                if single and live: counts['single_publisher'] += 1
            elif 'single' in t and t['single']: fails.append(f'{tid}: single is only for reported ties')
            if tier == 'claimed' and ({'document', 'government', 'research'} & cls): fails.append(f'{tid}: alleged with an outside source; should be higher')
            if cls == {'reference'}: counts['reference_only'] += 1
            if live and tier != 'open' and len(cls) < 2: counts['one_class'] += 1
            if live and ev and ev < win_from and not (len(ev) == 4 and ev >= win_from[:4]): counts['prewindow'] += 1
            if live and not ev: counts['undated'] += 1
            if live and ({'arms', 'drones', 'parts'} & set(t['kinds'])):
                counts['weapons'] += 1
                if any('sipri' in (s.get('url') or '').lower() or 'sipri' in (s.get('publisher') or '').lower() for s in srcs): counts['weapons_sipri'] += 1
            if t.get('checked'): counts['checked'] += 1
            if t.get('checked') and not DATE.match(str(t['checked'])): fails.append(f'{tid}: bad checked {t["checked"]}')
            if 'entered' not in t: fails.append(f'{tid}: no entered date')
        # bands
        if c.get('kind', 'war') != 'pressure':
            if u and u.get('entries', {}).get(c['id']):
                best = u['entries'][c['id']]['window']['best']
                want = band_for(best)
                if c.get('band_basis'):
                    pass  # a lower counter named by hand sets the band; say so on the card
                elif str(c.get('band')) != str(want):
                    fails.append(f"{c['id']}: band {c.get('band')} but UCDP's window best {best:,} implies {want}; name a lower counter in band_basis or fix the band")
                m = re.match(r'UCDP counted ([\d,]+)', c.get('band_source', ''))
                if m and int(m.group(1).replace(',', '')) != best:
                    fails.append(f"{c['id']}: band_source says UCDP counted {m.group(1)}, data/ucdp.json says {best:,} for the window")
            elif not c.get('band'):
                warns.append(f"{c['id']}: no band and no UCDP entry")
    if write:
        d['source_counts'] = counts
        d['as_of'] = date.today().isoformat()
        json.dump(d, open(PATH, 'w'), indent=1, ensure_ascii=False)
        with open(PATH, 'a') as f:
            f.write('\n')
    elif d.get('source_counts') != counts:
        diff = {k: (d.get('source_counts', {}).get(k), v) for k, v in counts.items() if d.get('source_counts', {}).get(k) != v}
        fails.append('source_counts are stale (file, computed): ' + json.dumps(diff) + ' — run with --write')
    if not quiet:
        for w in warns: print('warn:', w)
        for f in fails: print('FAIL:', f)
        print(f"{counts['ties']} ties, {counts['sources']} sources; {len(fails)} failures, {len(warns)} warnings" + (' (written)' if write else ''))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
