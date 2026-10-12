#!/usr/bin/env python3
"""Make a blind-grading packet for a second reader, and score the grades.

  scripts/blind_reader.py packet            writes data/blind_packet.json: every tie with its
                                            sources and the rules, the tier and stance stripped,
                                            in a shuffled order with a fixed seed
  scripts/blind_reader.py score grades.csv  reads "key,tier,why" lines (tier is open, shown,
                                            reported or claimed, or the words on the page) and
                                            prints the agreement rate and the disagreements, as
                                            a JSON block ready to paste into second_reader

A reader gets the packet and nothing else: no page, no news, no web. The key
is opaque so the reader cannot look the tie up. The tie's note is left out: it carries our reasoning. The reader grades each tie from
the sources and the rules alone and writes one line per tie.
"""
import csv
import hashlib
import json
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, 'data', 'conflicts.json')
OUT = os.path.join(ROOT, 'data', 'blind_packet.json')
WORDS = {'on the record': 'open', 'documented': 'shown', 'reported': 'reported', 'alleged': 'claimed'}


def key_of(c, t):
    n = [x for x in c['ties'] if x['backer'] == t['backer'] and x['party'] == t['party']].index(t)
    return hashlib.sha1(f"{c['id']}/{t['backer']}/{t['party']}/{n}".encode()).hexdigest()[:8]


def packet(d):
    rules = {'tiers': {k: v['word'] + ': ' + v['note'] for k, v in d['tiers'].items()}, 'finding_rule': d['finding_rule'],
             'source_classes': d['source_classes'], 'kinds': d['kinds'], 'how': 'Grade each tie from its sources and the rules alone. Write one line per tie: key, tier, why. Do not look anything up.'}
    items = []
    backers = {b['id']: b for b in d['backers']}
    for c in d['conflicts']:
        for t in c['ties']:
            party = next(p for p in c['parties'] if p['id'] == t['party'])
            items.append({'key': key_of(c, t), 'war': c['name'], 'backer': backers[t['backer']]['name'], 'helps': party['name'],
                          'kinds': [d['kinds'][k] for k in t['kinds']], 'ended': t.get('ended'),
                          'sources': [{k: s.get(k) for k in ('class', 'publisher', 'via', 'text', 'date', 'url', 'counts')} for s in t['sources']]})
    random.Random(2026).shuffle(items)
    json.dump({'rules': rules, 'ties': items}, open(OUT, 'w'), indent=1, ensure_ascii=False)
    print('wrote', OUT, len(items), 'ties')


def score(d, path):
    grades = {}
    for row in csv.reader(open(path)):
        if not row or row[0].startswith('#') or row[0] == 'key':
            continue
        key, tier = row[0].strip(), row[1].strip().lower()
        grades[key] = (WORDS.get(tier, tier), row[2].strip() if len(row) > 2 else '')
    backers = {b['id']: b for b in d['backers']}
    agreed, open_list, missing = 0, [], 0
    for c in d['conflicts']:
        for t in c['ties']:
            k = key_of(c, t)
            if k not in grades:
                missing += 1
                continue
            tier, why = grades[k]
            if tier == t['tier']:
                agreed += 1
            else:
                party = next(p for p in c['parties'] if p['id'] == t['party'])
                open_list.append({'tie': f"{backers[t['backer']]['short']} to {party['name']} in {c['short']}", 'ours': d['tiers'][t['tier']]['word'], 'reader': d['tiers'].get(tier, {}).get('word', tier), 'why': why})
    n = agreed + len(open_list)
    print(json.dumps({'ties': n, 'missing': missing, 'agreed': agreed, 'disagreed': len(open_list), 'open': open_list}, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    d = json.load(open(PATH))
    if len(sys.argv) > 1 and sys.argv[1] == 'packet':
        packet(d)
    elif len(sys.argv) > 2 and sys.argv[1] == 'score':
        score(d, sys.argv[2])
    else:
        sys.exit(__doc__)
