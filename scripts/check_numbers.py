#!/usr/bin/env python3
"""Fail on numbers that cannot be true.

The other checks ask whether the pages agree with the data files. This one asks
whether the data files can be right at all: a count below zero, parts that do
not add up to their whole, a past year larger than the war that holds it, sums
that were never compared with UCDP's own totals. Any of these is exit 1, never
a note.

  python3 scripts/check_numbers.py          # print what it found; exit 1 on a failure
  python3 scripts/check_numbers.py --quiet  # print failures only

scripts/build_ucdp.py runs the same rules on its output before it writes a file,
scripts/check_conflicts.py runs this script at its end, and the pre-commit hook
runs it when a UCDP data file or one of the pages below is staged.

The rules of the house, which this script enforces where a script can:

1. An impossible number stops the build. It is not explained to the reader.
2. A number that looks wrong is traced to its rows or left off the page.
3. The sums are UCDP's or they are not shown. The build compares them with
   UCDP's own published country-year totals and stops on one difference.
4. UCDP's low and high are shown on no page. They are kept in the data as UCDP
   gives them, but they do not reliably hold the best count between them (some
   rows carry a high below the best count; UCDP's own totals show the same).
   The rows are counted in data/ucdp_anomalies.json.
5. A new number comes with its test. A field this script has no rule for is a
   failure: add the rule in the commit that adds the field.
"""
import json
import re
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent
KINDS = {'state-based', 'non-state', 'one-sided'}

# every field the rules below know. A field that is not here has no test, and that is a failure (rule 3).
TOP_KEYS = {'versions', 'pulled', 'reach', 'window', 'flagged_share', 'rule', 'entries', 'not_on_map', 'secondary', 'months', 'range_note', 'reconciled', 'early_rows'}
ENTRY_KEYS = {'basis', 'last_year', 'this_year', 'window', 'whole', 'flagged_share_window', 'conflicts', 'dyad_ids', 'excluded',
              'secondary', 'months'}
SUM_KEYS = {'low', 'best', 'high', 'year', 'from', 'to', 'by_type'}
YEAR_KEYS = {'year', 'best', 'low', 'high', 'state', 'nonstate', 'onesided', 'countries_over_1000'}


def check_sum(s, where, fails):
    """One low, best, high: whole numbers, none below zero. Low and high are UCDP's as given and are not ordered against best (rule 4)."""
    for k in ('low', 'best', 'high'):
        v = s.get(k)
        if not isinstance(v, int) or isinstance(v, bool) or v < 0:
            fails.append(f'{where}: {k} is {v!r}; a count is a whole number, zero or more')
            return
    extra = set(s) - SUM_KEYS
    if extra:
        fails.append(f'{where}: new field {sorted(extra)} has no rule in scripts/check_numbers.py; add its test in the same commit')
    bt = s.get('by_type')
    if bt is not None:
        if set(bt) != KINDS:
            fails.append(f'{where}: the kinds of death are {sorted(bt)}, not the three UCDP counts')
        elif sum(bt.values()) != s['best'] or min(bt.values()) < 0:
            fails.append(f"{where}: the three kinds add to {sum(bt.values()):,}, the best count is {s['best']:,}")


def check_months(m, keys, where, fails):
    for k in ('best', 'low', 'high'):
        if len(m.get(k) or []) != len(keys):
            fails.append(f'{where}: {k} has {len(m.get(k) or [])} months, the window has {len(keys)}')
            return
    for i, key in enumerate(keys):
        check_sum({'low': m['low'][i], 'best': m['best'][i], 'high': m['high'][i]}, f'{where} {key}', fails)


def ucdp_fails(U, starts=None):
    """Rules for data/ucdp.json. starts maps a war's id to the month the map says it began."""
    fails = []
    extra = set(U) - TOP_KEYS
    if extra:
        fails.append(f'ucdp.json: new field {sorted(extra)} has no rule in scripts/check_numbers.py; add its test in the same commit')
    win = U.get('window') or {}
    keys = (U.get('months') or {}).get('keys') or []
    fs = U.get('flagged_share')
    if fs is not None and not 0 <= fs <= 1:
        fails.append(f'ucdp.json: flagged_share is {fs}; a share is between 0 and 1')
    rc = U.get('reconciled') or {}
    if rc.get('differences') != 0 or not rc.get('country_years') or not rc.get('against'):
        fails.append("ucdp.json: no record that the sums were compared with UCDP's own country-year totals and matched (reconciled); rebuild with scripts/build_ucdp.py")
    if not U.get('range_note'):
        fails.append('ucdp.json: range_note is missing; the pages quote it to say why no low and high are shown')
    if keys and (keys[0] != win.get('from') or keys[-1] != win.get('to')):
        fails.append(f"ucdp.json: the months run {keys[0]} to {keys[-1]}, the window says {win.get('from')} to {win.get('to')}")
    for cid, e in (U.get('entries') or {}).items():
        w = f'ucdp.json {cid}'
        extra = set(e) - ENTRY_KEYS
        if extra:
            fails.append(f'{w}: new field {sorted(extra)} has no rule in scripts/check_numbers.py; add its test in the same commit')
        for part in ('last_year', 'this_year', 'window'):
            if not isinstance(e.get(part), dict):
                fails.append(f'{w}: no {part}')
            else:
                check_sum(e[part], f'{w} {part}', fails)
        if e.get('whole'):
            check_sum(e['whole'], f'{w} whole', fails)
        if e.get('months'):
            check_months(e['months'], keys, f'{w} months', fails)
            if isinstance(e.get('window'), dict):
                for k in ('best', 'low', 'high'):
                    if sum(e['months'][k]) != e['window'].get(k):
                        fails.append(f"{w}: its months add to {sum(e['months'][k]):,} {k}, its window says {e['window'].get(k):,}")
        fw = e.get('flagged_share_window')
        if fw is not None and not 0 <= fw <= 1:
            fails.append(f'{w}: flagged_share_window is {fw}; a share is between 0 and 1')
        # the past year and the whole war: one holds the other, by which began first
        start = (starts or {}).get(cid) or (e.get('whole') or {}).get('from')
        if e.get('whole') and isinstance(e.get('window'), dict) and start and win.get('from'):
            if e['whole'].get('from') != start:
                fails.append(f"{w}: the whole-war count starts {e['whole'].get('from')}, the map says the war began {start}")
            for k in ('low', 'best', 'high'):
                a, b = e['window'].get(k), e['whole'].get(k)
                if not isinstance(a, int) or not isinstance(b, int):
                    continue
                if start <= win['from'] and b < a:
                    fails.append(f"{w}: {k} since the war began ({b:,}) is below {k} for the past year alone ({a:,})")
                if start >= win['from'] and b > a:
                    fails.append(f"{w}: the war began inside the past year, yet {k} since it began ({b:,}) is above {k} for the past year ({a:,})")
        for c in e.get('conflicts') or []:
            if not isinstance(c.get('best_window'), int) or c['best_window'] < 0:
                fails.append(f"{w}: conflict {c.get('name')} has best_window {c.get('best_window')!r}")
        if e.get('conflicts') and isinstance(e.get('window'), dict) and len(e['conflicts']) < 12 and isinstance(e['window'].get('best'), int):
            if sum(c.get('best_window') or 0 for c in e['conflicts']) > e['window']['best']:
                fails.append(f"{w}: its conflicts add to more than its window count")
        for x in e.get('excluded') or []:
            if not isinstance(x.get('best_this_year'), int) or x['best_this_year'] < 0 or not x.get('why'):
                fails.append(f"{w}: a row left out needs a count and a reason: {x}")
    for x in U.get('not_on_map') or []:
        for part in ('last_year', 'this_year', 'window'):
            if isinstance(x.get(part), dict):
                check_sum({k: v for k, v in x[part].items() if k != 'year'}, f"ucdp.json not_on_map {x.get('country')} {part}", fails)
    M = U.get('months') or {}
    for part in ('map', 'world'):
        if M.get(part):
            check_months(M[part], keys, f'ucdp.json months {part}', fails)
    if M.get('map') and M.get('world') and len(M['map'].get('best') or []) == len(keys) == len(M['world'].get('best') or []):
        for i, key in enumerate(keys):
            if M['map']['best'][i] > M['world']['best'][i]:
                fails.append(f"ucdp.json months {key}: the wars on the map hold {M['map']['best'][i]:,}, more than the world's {M['world']['best'][i]:,}")
    return fails


def years_fails(Y):
    fails = []
    prev = None
    for r in Y.get('years') or []:
        w = f"ucdp_years.json {r.get('year')}"
        extra = set(r) - YEAR_KEYS
        if extra:
            fails.append(f'{w}: new field {sorted(extra)} has no rule in scripts/check_numbers.py; add its test in the same commit')
        check_sum({k: r.get(k) for k in ('low', 'best', 'high')}, w, fails)
        parts = [r.get('state'), r.get('nonstate'), r.get('onesided')]
        if all(isinstance(v, int) for v in parts) and isinstance(r.get('best'), int) and sum(parts) != r['best']:
            fails.append(f"{w}: the three kinds add to {sum(parts):,}, the best count is {r['best']:,}")
        if prev is not None and r.get('year') != prev + 1:
            fails.append(f'{w}: follows {prev}; a year is missing or repeated')
        prev = r.get('year')
    if not Y.get('years'):
        fails.append('ucdp_years.json: no years')
    return fails


def grid_fails(G, U):
    fails = []
    world = sum(((U.get('months') or {}).get('world') or {}).get('best') or [])
    if isinstance(G.get('placed_total'), int) and isinstance(G.get('unplaced_total'), int) and world:
        if G['placed_total'] + G['unplaced_total'] != world:
            fails.append(f"ucdp_grid.json: placed {G['placed_total']:,} and unplaced {G['unplaced_total']:,} do not add to the world's {world:,} for the window")
    for cid, n in (G.get('unplaced') or {}).items():
        best = (((U.get('entries') or {}).get(cid) or {}).get('window') or {}).get('best')
        if isinstance(best, int) and (not isinstance(n, int) or n < 0 or n > best):
            fails.append(f'ucdp_grid.json {cid}: {n!r} deaths not placed to a province, of a window count of {best:,}')
    if G.get('window') != U.get('window') or G.get('versions') != U.get('versions'):
        fails.append('ucdp_grid.json: built from a different pull or window than ucdp.json')
    return fails


def early_fails(E, U):
    """Every large early row this pull counted or left out has been read and logged, with a verdict and a reason."""
    fails = []
    log = {r.get('id'): r for r in E.get('rows') or []}
    for i, r in log.items():
        if r.get('verdict') not in ('keep', 'leave out'):
            fails.append(f"ucdp_early_rows.json: row {i} has no verdict (keep, or leave out)")
        for k in ('why', 'read', 'by'):
            if not str(r.get(k) or '').strip():
                fails.append(f"ucdp_early_rows.json: row {i} has no '{k}'")
    er = U.get('early_rows')
    if not isinstance(er, dict) or not isinstance(er.get('rows'), list) or not er.get('line'):
        return fails + ['ucdp.json: no record that the large early rows were read (early_rows); rebuild with scripts/build_ucdp.py']
    if E.get('line') != er['line']:
        fails.append(f"ucdp_early_rows.json: its line ({E.get('line')}) is not the build's ({er['line']})")
    for r in er['rows']:
        e = log.get(r.get('id'))
        if not e or e.get('best') != r.get('best') or e.get('verdict') != r.get('verdict'):
            fails.append(f"ucdp.json: early row {r.get('id')} ({r.get('best'):,} deaths) is in the build but not in ucdp_early_rows.json as read, or differs from it")
        if r.get('best', 0) < er['line']:
            fails.append(f"ucdp.json: early row {r.get('id')} is listed as large but is under the line")
    return fails


def anomalies_fails(A, U):
    """The rows behind every repair are on file, and they are the rows of this pull."""
    fails = []
    if A.get('versions') != U.get('versions') or A.get('pulled') != U.get('pulled'):
        fails.append('ucdp_anomalies.json: from a different pull than ucdp.json; rebuild both together')
    rows = A.get('rows') or []
    for r in rows:
        if not (r.get('high', 0) < r.get('best', 0) or r.get('low', 0) > r.get('best', 0)):
            fails.append(f"ucdp_anomalies.json: row {r.get('id')} is listed but its range holds its best count")
    for cid, t in (A.get('entries') or {}).items():
        if cid not in (U.get('entries') or {}) or t.get('rows', 0) < 1:
            fails.append(f'ucdp_anomalies.json: the tally for {cid} matches no entry or counts no row')
    return fails


# pages that draw on UCDP's counts. None may show its low or high (rule 4).
PAGES = ('conflicts.html', 'wars.html', 'level.html', 'moment.html', 'quadrant.html')
SHOWS_RANGE = re.compile(r'\.(?:low|high)\b|within a range|low to high|low and (?:the )?high|low, best|best, low')


def pages_fails():
    fails = []
    for name in PAGES:
        try:
            text = open(R / name, encoding='utf-8').read()
        except FileNotFoundError:
            continue
        for i, line in enumerate(text.split('\n'), 1):
            m = SHOWS_RANGE.search(line)
            if m:
                fails.append(f"{name}:{i}: reads or names UCDP's low or high ({m.group(0)!r}). The pages show the best count only.")
    for name, keys in (('data/conflicts.json', ('ucdp_note', 'band_note', 'years_note', 'level_note')), ('data/level.json', ('rule',)), ('data/ucdp_years.json', ('rule',)), ('data/wars.json', None)):
        try:
            text = open(R / name, encoding='utf-8').read()
        except FileNotFoundError:
            continue
        J = json.loads(text)
        blob = text if keys is None else ' '.join(str(J.get(k) or '') for k in keys)
        if name == 'data/conflicts.json':   # each war's count sentence and its UCDP note are reader-facing too
            blob += ' ' + ' '.join(str(c.get('band_source') or '') + ' ' + str((c.get('ucdp') or {}).get('note') or '') for c in J.get('conflicts') or [])
        m = re.search(r'low and (?:the )?high|high (?:here )?(?:reads )?below|high reads low|its low is|the low is|low, best|best, low|high count|low count|low-to-high|\{\w*(?:low|high|range)\w*\}', blob)
        if m and not (name == 'data/wars.json' and m.group(0) == '{band_ranges}'):
            fails.append(f"{name}: its reader-facing text names UCDP's low or high ({m.group(0)!r}). The pages show the best count only.")
    return fails


def all_fails():
    fails = []
    load = lambda p: json.load(open(R / 'data' / p, encoding='utf-8'))
    try:
        U = load('ucdp.json')
    except Exception as e:
        return [f'could not read data/ucdp.json: {e}']
    starts = {}
    try:
        starts = {c['id']: c.get('start') for c in load('conflicts.json')['conflicts']}
    except Exception as e:
        fails.append(f'could not read data/conflicts.json: {e}')
    fails += ucdp_fails(U, starts)
    fails += pages_fails()
    for name, fn in (('ucdp_years.json', lambda d: years_fails(d)), ('ucdp_grid.json', lambda d: grid_fails(d, U)),
                     ('ucdp_anomalies.json', lambda d: anomalies_fails(d, U)),
                     ('ucdp_early_rows.json', lambda d: early_fails(d, U))):
        try:
            fails += fn(load(name))
        except FileNotFoundError:
            fails.append(f'data/{name} is missing')
        except Exception as e:
            fails.append(f'data/{name}: {type(e).__name__} {e}')
    return fails


def main():
    quiet = '--quiet' in sys.argv
    fails = all_fails()
    for f in fails:
        print('FAIL:', f)
    if fails or not quiet:
        print(f'numbers: {len(fails)} that cannot be true')
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
