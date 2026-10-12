#!/usr/bin/env python3
"""Write data/ties_esd.csv: the map's ties in the row shape of UCDP's External
Support Dataset (ESD), one row per supporter, recipient and year, with one
column per ESD kind of support and an alleged flag.

The ESD stops at 2017. This file lets someone splice our ties (2025 on) after
it. Our sixteen kinds fold into ESD's categories as KINDS_TO_ESD says; a kind
that ESD does not have goes to `other` with its name in `other_kinds`.
"""
import csv
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ESD_COLS = ['troops', 'access_territory', 'weapons', 'materiel', 'training', 'funding', 'intelligence', 'other']
KINDS_TO_ESD = {
    'troops': 'troops', 'air': 'troops', 'shield': 'troops', 'police': 'troops', 'seize': 'troops',
    'bases': 'access_territory', 'transit': 'access_territory', 'harbor': 'access_territory', 'hosts': 'access_territory',
    'arms': 'weapons', 'drones': 'weapons', 'parts': 'weapons',
    'oil': 'materiel',
    'training': 'training',
    'money': 'funding',
    'intel': 'intelligence',
    'cover': 'other',
}


def main():
    D = json.load(open(os.path.join(ROOT, 'data', 'conflicts.json')))
    backers = {b['id']: b for b in D['backers']}
    win_from, win_to = D['window']['from'], D['window']['to']
    years = sorted(set([win_from[:4], win_to[:4]]))
    rows = []
    for c in D['conflicts']:
        parties = {p['id']: p for p in c['parties']}
        for t in c['ties']:
            b = backers[t['backer']]
            p = parties.get(t['party'], {'name': t['party'], 'state': None})
            for y in years:
                if t.get('since') and t['since'][:4] > y:
                    continue
                if t.get('ended') and str(t['ended'])[:4] < y:
                    continue
                row = {
                    'war': c['id'], 'war_name': c['name'], 'entry_kind': c.get('kind') or 'war',
                    'supporter': t['backer'], 'supporter_name': b['name'], 'supporter_iso': ';'.join(b['iso']) if isinstance(b.get('iso'), list) else (b.get('iso') or ''),
                    'recipient': t['party'], 'recipient_name': p['name'], 'recipient_state': ';'.join(p['state']) if isinstance(p.get('state'), list) else (p.get('state') or ''),
                    'year': y,
                }
                for k in ESD_COLS:
                    row[k] = 0
                other = []
                for k in t['kinds']:
                    col = KINDS_TO_ESD.get(k, 'other')
                    row[col] = 1
                    if col == 'other':
                        other.append(k)
                row['other_kinds'] = ';'.join(other)
                row['kinds_ours'] = ';'.join(t['kinds'])
                row['alleged'] = 1 if t['tier'] == 'claimed' else 0
                row['tier'] = D['tiers'][t['tier']]['word']
                row['backer_says'] = t.get('stance') or ''
                row['since'] = t.get('since') or ''
                row['ended'] = t.get('ended') or ''
                row['evidence_to'] = t.get('evidence_to') or ''
                row['sources'] = len(t['sources'])
                row['sources_linked'] = sum(1 for e in t['sources'] if e.get('url'))
                row['entered'] = t.get('entered') or ''
                rows.append(row)
    out = os.path.join(ROOT, 'data', 'ties_esd.csv')
    with open(out, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print('wrote', out, len(rows), 'rows')


if __name__ == '__main__':
    main()
