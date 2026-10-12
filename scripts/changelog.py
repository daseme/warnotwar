#!/usr/bin/env python3
"""Write data/changes.json: what changed in data/conflicts.json, commit by commit.

Usage: scripts/changelog.py

Reads every commit that touched the data file, diffs each against the one
before, and writes one dated line per change a reader would care about: a war
or square entered or removed, a tie entered or removed, a tier moved, a tie
ended, a band moved, sources added. Only committed versions count: the
pre-commit hook runs this before a data commit, and the post-commit hook adds a
follow-up commit when the new commit changed the list. Nothing here is hand-written;
the corrections log on the page is, and stays separate.
"""
import json
import os
import subprocess
import sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILE = 'data/conflicts.json'


def git(*a):
    return subprocess.run(['git', *a], cwd=ROOT, capture_output=True, text=True).stdout


def load(rev):
    txt = git('show', f'{rev}:{FILE}')
    try:
        return json.loads(txt)
    except json.JSONDecodeError:
        return None


def ties_of(d):
    out, seen = {}, {}
    for c in d.get('conflicts', []):
        for t in c.get('ties', []):
            pair = (c['id'], t['backer'], t['party'])
            seen[pair] = seen.get(pair, 0) + 1
            out[pair + ((str(seen[pair]),) if seen[pair] > 1 else ())] = (c, t)
    return out


def main():
    revs = git('log', '--format=%H %ad', '--date=short', '--', FILE).strip().splitlines()
    revs = [r.split() for r in revs][::-1]   # oldest first
    versions = [(load(h), dt, h[:7]) for h, dt in revs]
    # committed versions only: the working tree is not a version a reader can see
    changes = []
    prev = None
    for d, dt, h in versions:
        if d is None:
            continue
        if prev is not None:
            tiers = d.get('tiers', {})
            word = lambda t: tiers.get(t, {}).get('word', t)
            bands = d.get('bands', {})
            pc = {c['id']: c for c in prev.get('conflicts', [])}
            cc = {c['id']: c for c in d.get('conflicts', [])}
            names = {b['id']: b.get('short', b['id']) for b in d.get('backers', [])}
            pname = lambda c, pid: next((p.get('short') or p['name'] for p in c.get('parties', []) if p['id'] == pid), pid)
            for cid in cc:
                if cid not in pc:
                    changes.append({'date': dt, 'commit': h, 'entry': cid, 'kind': 'entry', 'what': f"{cc[cid]['name']} entered" + (' as force short of war' if cc[cid].get('kind') == 'pressure' else '')})
                elif str(pc[cid].get('band')) != str(cc[cid].get('band')) and cc[cid].get('band'):
                    changes.append({'date': dt, 'commit': h, 'entry': cid, 'kind': 'band', 'what': f"{cc[cid]['name']}: deaths band moved from {bands.get(str(pc[cid].get('band')), 'not entered')} to {bands.get(str(cc[cid]['band']))}"})
            for cid in pc:
                if cid not in cc:
                    changes.append({'date': dt, 'commit': h, 'entry': cid, 'kind': 'entry', 'what': f"{pc[cid]['name']} removed"})
            pt, ct = ties_of(prev), ties_of(d)
            for k, (c, t) in ct.items():
                label = f"{names.get(t['backer'], t['backer'])} to {pname(c, t['party'])} in {c.get('short') or c['name']}"
                if k not in pt:
                    changes.append({'date': dt, 'commit': h, 'entry': c['id'], 'tie': '/'.join(k), 'kind': 'tie', 'what': f"{label}: entered, {word(t['tier'])}"})
                    continue
                o = pt[k][1]
                if o['tier'] != t['tier']:
                    changes.append({'date': dt, 'commit': h, 'entry': c['id'], 'tie': '/'.join(k), 'kind': 'tier', 'what': f"{label}: {word(o['tier'])} to {word(t['tier'])}"})
                if not o.get('ended') and t.get('ended'):
                    changes.append({'date': dt, 'commit': h, 'entry': c['id'], 'tie': '/'.join(k), 'kind': 'ended', 'what': f"{label}: ended {t['ended']}"})
                os_, ns = o.get('sources') or [], t.get('sources') or []
                if isinstance(os_, list) and isinstance(ns, list):
                    same = lambda x, s: (x.get('url') and x.get('url') == s.get('url')) or (x.get('text') == s.get('text'))
                    added = [s for s in ns if isinstance(s, dict) and not any(isinstance(x, dict) and same(x, s) for x in os_)]
                    if added and len(ns) > len(os_):
                        changes.append({'date': dt, 'commit': h, 'entry': c['id'], 'tie': '/'.join(k), 'kind': 'sources', 'what': f"{label}: {len(added)} {'source' if len(added) == 1 else 'sources'} added"})
                if o.get('evidence_to') != t.get('evidence_to') and t.get('evidence_to') and (o.get('evidence_to') or '') < t['evidence_to']:
                    changes.append({'date': dt, 'commit': h, 'entry': c['id'], 'tie': '/'.join(k), 'kind': 'evidence', 'what': f"{label}: evidence now to {t['evidence_to']}"})
                if not o.get('checked') and t.get('checked'):
                    changes.append({'date': dt, 'commit': h, 'entry': c['id'], 'tie': '/'.join(k), 'kind': 'checked', 'what': f"{label}: checked {t['checked']}"})
            for k, (c, t) in pt.items():
                if k not in ct:
                    changes.append({'date': dt, 'commit': h, 'entry': c['id'], 'tie': '/'.join(k), 'kind': 'tie', 'what': f"{names.get(t['backer'], t['backer'])} to {pname(c, t['party'])} in {c.get('short') or c['name']}: removed"})
        prev = d
    first = versions[0][1] if versions else None
    out = {'rule': 'Computed from every saved version of the data file, one line per change a reader would care about, dated by the save. Hand-written reasons are in the corrections log; this list has none.', 'first': first, 'built': date.today().isoformat(), 'changes': changes}
    json.dump(out, open(os.path.join(ROOT, 'data', 'changes.json'), 'w'), indent=1, ensure_ascii=False)
    print('wrote data/changes.json:', len(changes), 'changes over', len(versions), 'versions')


if __name__ == '__main__':
    main()
