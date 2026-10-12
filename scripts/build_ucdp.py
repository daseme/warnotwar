#!/usr/bin/env python3
"""Sum UCDP georeferenced events by map entry and write data/ucdp.json.

Usage: scripts/build_ucdp.py <dir with UCDP csv files> [--pulled YYYY-MM-DD]

The directory holds the yearly GED file (GEDEvent_v<major>_<minor>.csv) and any
candidate files for the current year (GEDEvent_v<major>_0_<month>.csv or the
quarterly GEDEvent_v<major>_01_<major>_06.csv). Rows are deduplicated on id;
a later candidate file wins. Raw files never enter the repo (see .gitignore).

Each map entry is summed over the UCDP countries it covers, except entries
listed in BY_CONFLICT, which are summed over named UCDP conflicts because a
country sum would mix in other wars. EXCLUDE drops single rows by id, with the
reason written into the output so the reader can see it.
"""
import glob
import json
import os
import re
import sys
from datetime import date

import pandas as pd

COLS = ['id', 'year', 'type_of_violence', 'conflict_new_id', 'conflict_name', 'dyad_new_id', 'dyad_name',
        'side_a', 'side_b', 'country', 'best', 'low', 'high', 'date_start', 'code_status']

# map entry id -> UCDP country names (as spelled in the country column)
BY_COUNTRY = {
    'ukraine': ['Ukraine', 'Russia (Soviet Union)'],
    'sudan': ['Sudan'],
    'gaza': ['Israel', 'Lebanon', 'Palestine'],
    'yemen': ['Yemen (North Yemen)'],
    'myanmar': ['Myanmar (Burma)'],
    'congo': ['DR Congo (Zaire)'],
    'sahel': ['Burkina Faso', 'Mali', 'Niger'],
    'somalia': ['Somalia'],
    'syria': ['Syria'],
    'haiti': ['Haiti'],
    'pakistan': ['Pakistan', 'Afghanistan'],
    'ethiopia': ['Ethiopia', 'Eritrea'],
    'southsudan': ['South Sudan'],
    'nigeria': ['Nigeria'],
}
# map entry id -> UCDP conflict_new_id list (summed across every country the events fall in)
BY_CONFLICT = {
    'gulf': [14609, 16905],  # Iran - Israel; Iran - Israel, United States of America
}
# rows left out of the sums, by UCDP event id, with the reason shown on the page
EXCLUDE = {}
# a dyad in the entry's countries that is not in its sum, shown with the reason
EXCLUDE_DYAD = {
    'gulf': {'Government of Iran - Civilians': 'one row flagged for review puts civilians killed by Iran at 19,900 in January 2026; it is a separate one-sided conflict, not the war'},
}
DYAD_COUNTRIES = {'gulf': ['Iran']}
# entries above UCDP's war line that are not on the map
NOT_ON_MAP = ['Mexico', 'Colombia', 'Tanzania']

TYPES = {1: 'state-based', 2: 'non-state', 3: 'one-sided'}


def load(d):
    yearly = sorted(glob.glob(os.path.join(d, 'GEDEvent_v??_?.csv')) + glob.glob(os.path.join(d, 'GEDEvent_v??_??.csv')))
    yearly = [f for f in yearly if re.search(r'GEDEvent_v\d\d_\d{1,2}\.csv$', f)]
    numkey = lambda f: [int(x) for x in re.findall(r'\d+', os.path.basename(f))]
    cands = sorted(glob.glob(os.path.join(d, 'GEDEvent_v??_01_??_??.csv')), key=numkey) + sorted(glob.glob(os.path.join(d, 'GEDEvent_v??_0_*.csv')), key=numkey)
    if not yearly:
        sys.exit('no yearly GED file in ' + d)
    frames, versions = [], []
    for f in yearly:
        g = pd.read_csv(f, usecols=COLS, low_memory=False)
        frames.append(g)
        versions.append('GED ' + re.search(r'v(\d\d)_(\d{1,2})', f).group(1) + '.' + re.search(r'v(\d\d)_(\d{1,2})', f).group(2))
    cand_versions = []
    for f in cands:
        c = pd.read_csv(f, usecols=COLS, low_memory=False)
        c['_cand'] = True
        frames.append(c)
        m = re.search(r'v(\d\d)_0_(\d+)', f)
        q = re.search(r'v(\d\d)_(\d\d)_(\d\d)_(\d\d)', f)
        cand_versions.append(('Candidate %s.0.%s' % (m.group(1), m.group(2))) if m else ('Candidate %s.%s to %s.%s' % q.groups()) if q else 'Candidate ' + os.path.basename(f))
    df = pd.concat(frames, ignore_index=True)
    df['_cand'] = df['_cand'].eq(True) if '_cand' in df else False
    df = df.drop_duplicates('id', keep='last')
    df['month'] = df['date_start'].astype(str).str.slice(0, 7)
    return df, versions, cand_versions


def sums(x):
    return {'low': int(x.low.sum()), 'best': int(x.best.sum()), 'high': int(x.high.sum())}


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    d = sys.argv[1]
    pulled = sys.argv[sys.argv.index('--pulled') + 1] if '--pulled' in sys.argv else date.today().isoformat()
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    conf = json.load(open(os.path.join(root, 'data', 'conflicts.json')))
    win_from, win_to = conf['window']['from'], conf['window']['to']
    df, versions, cand_versions = load(d)
    df = df[~df.id.isin(list(map(int, EXCLUDE)))]
    this_year = int(df.year.max())
    last_year = this_year - 1
    cand = df[df['_cand'] == True]
    reach = df.month.max()
    flagged = round(float((cand.code_status != 'Clear').mean()), 3) if len(cand) else None

    out = {
        'versions': ', '.join(versions + cand_versions),
        'pulled': pulled,
        'reach': reach,
        'window': {'from': win_from, 'to': min(win_to, reach)},
        'flagged_share': flagged,
        'rule': 'Sums of UCDP best, low and high estimates by entry: by the countries each entry covers, or by named conflicts where a country sum would mix in other wars. The window is the months of the map\'s twelve that UCDP has reached. Candidate rows are not fully reviewed.',
        'entries': {},
        'not_on_map': [],
    }
    for cid in [c['id'] for c in conf['conflicts']]:
        if cid in BY_COUNTRY:
            x = df[df.country.isin(BY_COUNTRY[cid])]
            basis = 'countries: ' + ', '.join(BY_COUNTRY[cid])
        elif cid in BY_CONFLICT:
            x = df[df.conflict_new_id.isin(BY_CONFLICT[cid])]
            basis = 'conflicts: ' + ', '.join(sorted(set(x.conflict_name)))
        else:
            continue
        excluded = []
        for dyad, why in EXCLUDE_DYAD.get(cid, {}).items():
            y = df[(df.country.isin(BY_COUNTRY.get(cid, DYAD_COUNTRIES.get(cid, [])))) & (df.dyad_name == dyad)]
            if len(y):
                excluded.append({'dyad': dyad, 'best_this_year': int(y[y.year == this_year].best.sum()), 'why': why})
            x = x[x.dyad_name != dyad]
        w = x[(x.month >= win_from) & (x.month <= win_to)]
        confs = (x[x.year >= last_year].groupby(['conflict_new_id', 'conflict_name', 'type_of_violence'])
                 .agg(best=('best', 'sum')).reset_index().sort_values('best', ascending=False))
        conflicts = [{'id': int(r.conflict_new_id), 'name': re.sub(r'XXX\d+', 'unnamed groups', r.conflict_name), 'type': TYPES.get(int(r.type_of_violence)),
                      'best_window': int(w[(w.conflict_new_id == r.conflict_new_id) & (w.type_of_violence == r.type_of_violence)].best.sum())}
                     for r in confs.itertuples()]
        dyads = sorted(set(int(v) for v in w.dyad_new_id.dropna()))
        out['entries'][cid] = {
            'basis': basis,
            'last_year': {'year': last_year, **sums(x[x.year == last_year])},
            'this_year': {'year': this_year, 'to': reach, **sums(x[x.year == this_year])},
            'window': {'from': win_from, 'to': min(win_to, reach), **sums(w)},
            'flagged_share_window': round(float((w[w['_cand'] == True].code_status != 'Clear').mean()), 3) if len(w[w['_cand'] == True]) else None,
            'conflicts': conflicts[:12],
            'dyad_ids': dyads,
            'excluded': excluded,
        }
    for country in NOT_ON_MAP:
        x = df[df.country == country]
        w = x[(x.month >= win_from) & (x.month <= win_to)]
        out['not_on_map'].append({'country': country, 'last_year': {'year': last_year, **sums(x[x.year == last_year])},
                                  'this_year': {'year': this_year, **sums(x[x.year == this_year])}, 'window': sums(w),
                                  'by_type': {TYPES[k]: int(v) for k, v in w.groupby('type_of_violence').best.sum().items()}})
    json.dump(out, open(os.path.join(root, 'data', 'ucdp.json'), 'w'), indent=1, ensure_ascii=False)
    print('wrote data/ucdp.json:', len(out['entries']), 'entries, versions', out['versions'], 'reach', reach, 'flagged', flagged)


if __name__ == '__main__':
    main()
