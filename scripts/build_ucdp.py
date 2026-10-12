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
        'side_a', 'side_b', 'country', 'best', 'low', 'high', 'date_start', 'code_status', 'where_prec', 'latitude', 'longitude']

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
MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
month_word = lambda m: MONTHS[int(m[5:7]) - 1] + ' ' + m[:4]

# UCDP's "Government of X" names -> our backer ids, where the spelling differs
GOV_TO_BACKER = {'United States of America': 'usa', 'Russia (Soviet Union)': 'russia', 'Turkey': 'turkey', 'United Arab Emirates': 'uae',
                 'Saudi Arabia': 'saudi', 'South Africa': 'safrica', 'North Korea': 'nkorea', 'United Kingdom': 'britain', 'El Salvador': 'elsalvador',
                 'Dominican Republic': 'dominican', 'Trinidad and Tobago': 'trinidad'}
# kinds of help that UCDP would code as a secondary warring party (fighting on a side)
FIGHTING_KINDS = {'troops', 'air', 'police'}


def secondary_audit(d, conf, last_year):
    """Compare UCDP's secondary warring parties (UCDP/PRIO Armed Conflict Dataset) with our fighting ties, per entry."""
    files = glob.glob(os.path.join(d, 'UcdpPrioConflict_v*.csv'))
    if not files:
        return None, None
    a = pd.read_csv(sorted(files)[-1], low_memory=False)
    a = a[a.year == last_year]
    version = os.path.basename(sorted(files)[-1])
    backers = {b['id']: b for b in conf['backers']}
    by_name = {b['name']: b['id'] for b in conf['backers']}
    def to_id(gov):
        gov = gov.strip().replace('Government of ', '')
        return GOV_TO_BACKER.get(gov) or by_name.get(gov) or gov
    out = {}
    for c in conf['conflicts']:
        cid = c['id']
        all_conf = [i for v in BY_CONFLICT.values() for i in v]
        if cid in BY_COUNTRY:
            rows = a[a.location.apply(lambda s: bool(set(str(s).split(', ')) & set(BY_COUNTRY[cid]))) & ~a.conflict_id.isin(all_conf)]
        elif cid in BY_CONFLICT:
            rows = a[a.conflict_id.isin(BY_CONFLICT[cid])]
        else:
            continue
        ucdp = set()
        for col in ('side_a_2nd', 'side_b_2nd'):
            for v in rows[col].dropna():
                for g in str(v).split(','):
                    if g.strip():
                        ucdp.add(to_id(g))
        # the entry's own state parties are not secondary parties of their own war
        own_ids = set()
        for p in c['parties']:
            s = p.get('state')
            for v in (s if isinstance(s, list) else [s]):
                if v:
                    own_ids.add(v)
        ucdp -= own_ids
        ours = set(t['backer'] for t in c['ties'] if set(t['kinds']) & FIGHTING_KINDS and not (t.get('ended') and str(t['ended'])[:4] < str(last_year)) and not (t.get('since') and str(t['since'])[:4] > str(last_year)))
        name = lambda i: backers[i]['short'] if i in backers else i
        out[cid] = {'ucdp': sorted(name(i) for i in ucdp), 'ours': sorted(name(i) for i in ours),
                    'only_ucdp': sorted(name(i) for i in ucdp - ours), 'only_ours': sorted(name(i) for i in ours - ucdp)}
    return out, version


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
    win_by_entry = {}
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
        win_by_entry[cid] = w
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
    sec, sec_version = secondary_audit(d, conf, last_year)
    if sec:
        out['secondary'] = {'year': last_year, 'source': sec_version, 'rule': 'UCDP names a state that sends troops to fight on a side as a secondary warring party. Our ties with troops, air strikes or police are the same thing. The two lists should match; where they do not, both are shown.', 'entries': sec}
        for cid, s in sec.items():
            if cid in out['entries']:
                out['entries'][cid]['secondary'] = s
    for country in NOT_ON_MAP:
        x = df[df.country == country]
        w = x[(x.month >= win_from) & (x.month <= win_to)]
        out['not_on_map'].append({'country': country, 'last_year': {'year': last_year, **sums(x[x.year == last_year])},
                                  'this_year': {'year': this_year, **sums(x[x.year == this_year])}, 'window': sums(w),
                                  'by_type': {TYPES[k]: int(v) for k, v in w.groupby('type_of_violence').best.sum().items()}})
    # the level: UCDP's best by month for every entry and for the map as a whole, over the window months UCDP has reached
    months = []
    y, m = map(int, win_from.split('-'))
    while f'{y}-{m:02d}' <= min(win_to, reach):
        months.append(f'{y}-{m:02d}'); m += 1
        if m > 12: m, y = 1, y + 1
    def by_month(x):
        g = x.groupby('month').agg(best=('best', 'sum'), low=('low', 'sum'), high=('high', 'sum'))
        return {'best': [int(g.best.get(k, 0)) for k in months], 'low': [int(g.low.get(k, 0)) for k in months], 'high': [int(g.high.get(k, 0)) for k in months]}
    for cid, w in win_by_entry.items():
        out['entries'][cid]['months'] = by_month(w)
    on_map = pd.concat(list(win_by_entry.values())).drop_duplicates('id')
    world = df[(df.month >= win_from) & (df.month <= win_to)]
    # the dyads the page says it leaves out are left out of the world sums and the cells too
    for cid, dyads in EXCLUDE_DYAD.items():
        for dyad in dyads:
            world = world[~((world.dyad_name == dyad) & world.country.isin(BY_COUNTRY.get(cid, DYAD_COUNTRIES.get(cid, []))))]
    cand_months = sorted(set(df[df['_cand'] == True].month))
    out['months'] = {'keys': months, 'map': by_month(on_map), 'world': by_month(world), 'candidate_from': cand_months[0] if cand_months else None,
                     'rule': 'UCDP\'s best, low and high estimates of deaths by the month the event began, summed over the wars on this map (by each entry\'s basis) and over the whole dataset, less the rows the page says it leaves out. Months from the candidate files are provisional: about six weeks behind, and a share of their rows still carry a check flag.'}
    # where Uppsala counted: one-degree cells over the window, from events placed to a province or better (where_prec 1 to 4);
    # events placed only to a country are not drawn, and their deaths are given per entry so the reader knows what is missing
    placed = world[world.where_prec <= 4].copy()
    placed['cx'] = (placed.longitude // 1).astype(int); placed['cy'] = (placed.latitude // 1).astype(int)
    entry_of = {}
    for cid in out['entries']:
        if cid in BY_COUNTRY:
            for cn in BY_COUNTRY[cid]: entry_of[('country', cn)] = cid
        else:
            for k in BY_CONFLICT[cid]: entry_of[('conflict', k)] = cid
    def tag(r):
        return entry_of.get(('conflict', int(r.conflict_new_id))) or entry_of.get(('country', r.country))
    placed['entry'] = [tag(r) for r in placed.itertuples()]
    cells = []
    for (cx, cy), g in placed.groupby(['cx', 'cy']):
        per = g.groupby('month').best.sum()
        ent = g.groupby('entry').best.sum()
        cells.append({'lon': int(cx) + 0.5, 'lat': int(cy) + 0.5, 'best': int(g.best.sum()), 'n': int(len(g)),
                      'months': [int(per.get(k, 0)) for k in months], 'entry': (ent.idxmax() if len(ent) and ent.max() > 0 else None)})
    cells = [c for c in cells if c['best'] > 0]
    unplaced = {cid: int(w[w.where_prec > 4].best.sum()) for cid, w in win_by_entry.items()}
    json.dump({'rule': 'UCDP events of the window, ' + month_word(win_from) + ' to the last month reached, summed in one-degree cells by the month the event began. Only events placed to a province or better are drawn; deaths UCDP could place only to a country are listed by war and not drawn. Cell size is the square root of deaths, so area is deaths.',
               'window': out['window'], 'months': months, 'versions': out['versions'], 'pulled': pulled, 'cells': cells, 'unplaced': unplaced,
               'unplaced_total': int(world[world.where_prec > 4].best.sum()), 'placed_total': int(placed.best.sum())},
              open(os.path.join(root, 'data', 'ucdp_grid.json'), 'w'), separators=(',', ':'), ensure_ascii=False)
    print('wrote data/ucdp_grid.json:', len(cells), 'cells, placed', int(placed.best.sum()), 'unplaced', int(world[world.where_prec > 4].best.sum()))
    # the level since 1989, from UCDP's country-year file, if it is in the directory
    cy = glob.glob(os.path.join(d, 'OrganizedViolenceCYDataSet*.csv'))
    if cy:
        c = pd.read_csv(sorted(cy)[-1], low_memory=False)
        g = c.groupby('year').agg(best=('cumulative_total_deaths_in_orgvio_best', 'sum'), low=('cumulative_total_deaths_in_orgvio_low', 'sum'), high=('cumulative_total_deaths_in_orgvio_high', 'sum'),
                                  sb=('sb_total_deaths_best', 'sum'), ns=('ns_total_deaths_best', 'sum'), os=('os_total_deaths_best', 'sum'))
        wars = c[c.cumulative_total_deaths_in_orgvio_best >= 1000].groupby('year').country.nunique()
        years = [{'year': int(yr), 'best': int(r.best), 'low': int(r.low), 'high': int(r.high), 'state': int(r.sb), 'nonstate': int(r.ns), 'onesided': int(r.os), 'countries_over_1000': int(wars.get(yr, 0))} for yr, r in g.iterrows()]
        json.dump({'rule': 'UCDP\'s best, low and high estimates of deaths in organized violence by year, summed over every country, from the UCDP Organized Violence Country-Year Dataset; deaths in fighting, deaths in fighting between armed groups, and civilians killed on purpose, shown apart. Countries over 1,000 is the number of countries with a thousand or more deaths that year.',
                   'version': str(c.Version.iloc[0]), 'years': years}, open(os.path.join(root, 'data', 'ucdp_years.json'), 'w'), indent=1)
        print('wrote data/ucdp_years.json:', len(years), 'years')
    json.dump(out, open(os.path.join(root, 'data', 'ucdp.json'), 'w'), indent=1, ensure_ascii=False)   # again, now with the months
    # keep every pull, so a version change shows as a change: data/ucdp_history.json, one row per pull per entry
    hpath = os.path.join(root, 'data', 'ucdp_history.json')
    hist = json.load(open(hpath)) if os.path.exists(hpath) else {'rule': 'One row per pull: the versions pulled, the month reached, and each entry\'s window sum as it stood. A later pull that moves a number is a revision by UCDP or a change in our basis, and the page shows the move.', 'pulls': []}
    hist['pulls'] = [h for h in hist['pulls'] if h['pulled'] != pulled]
    hist['pulls'].append({'pulled': pulled, 'versions': out['versions'], 'reach': reach, 'window': out['window'], 'flagged_share': flagged,
                          'entries': {cid: {'window': e['window'], 'last_year': e['last_year'], 'this_year': e['this_year'], 'basis': e['basis']} for cid, e in out['entries'].items()}})
    hist['pulls'].sort(key=lambda h: h['pulled'])
    json.dump(hist, open(hpath, 'w'), indent=1, ensure_ascii=False)
    print('wrote data/ucdp.json:', len(out['entries']), 'entries, versions', out['versions'], 'reach', reach, 'flagged', flagged)


if __name__ == '__main__':
    main()
