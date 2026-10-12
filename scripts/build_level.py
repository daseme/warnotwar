#!/usr/bin/env python3
"""Write data/level.json for the level page: every year UCDP reaches.

Usage: scripts/build_level.py <dir with UcdpPrioConflict_v*.csv and OrganizedViolenceCYDataSet*.csv>

From the UCDP/PRIO Armed Conflict Dataset (1946 on): conflicts active per year,
how many at war level (a thousand or more deaths in the year), how many between
states, and which countries they were fought in. From the UCDP country-year file
(1989 on): deaths by country and year, best, low and high, split into fighting
between a state and another side, fighting between armed groups, and civilians
killed on purpose. Countries are keyed by the ISO3 code of the base map; states
that no longer exist are placed on the shape that holds their capital today.
"""
import csv
import glob
import json
import os
import sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# UCDP's names to the base map's ISO3 (Natural Earth 1:110m); a name in brackets is UCDP's older name for the same state
NAMES = {
    'Afghanistan': 'AFG', 'Albania': 'ALB', 'Algeria': 'DZA', 'Angola': 'AGO', 'Argentina': 'ARG', 'Armenia': 'ARM', 'Australia': 'AUS', 'Austria': 'AUT',
    'Azerbaijan': 'AZE', 'Bangladesh': 'BGD', 'Belarus': 'BLR', 'Belgium': 'BEL', 'Benin': 'BEN', 'Bhutan': 'BTN', 'Bolivia': 'BOL',
    'Bosnia-Herzegovina': 'BIH', 'Botswana': 'BWA', 'Brazil': 'BRA', 'Brunei': 'BRN', 'Bulgaria': 'BGR', 'Burkina Faso': 'BFA', 'Burundi': 'BDI',
    'Cambodia (Kampuchea)': 'KHM', 'Cameroon': 'CMR', 'Canada': 'CAN', 'Central African Republic': 'CAF', 'Chad': 'TCD', 'Chile': 'CHL', 'China': 'CHN',
    'Colombia': 'COL', 'Congo': 'COG', 'Costa Rica': 'CRI', 'Croatia': 'HRV', 'Cuba': 'CUB', 'Cyprus': 'CYP', 'Czech Republic': 'CZE',
    'Czechoslovakia': 'CZE', 'DR Congo (Zaire)': 'COD', 'Denmark': 'DNK', 'Djibouti': 'DJI', 'Dominican Republic': 'DOM', 'Ecuador': 'ECU', 'Egypt': 'EGY',
    'El Salvador': 'SLV', 'Equatorial Guinea': 'GNQ', 'Eritrea': 'ERI', 'Estonia': 'EST', 'Ethiopia': 'ETH', 'Fiji': 'FJI', 'Finland': 'FIN', 'France': 'FRA',
    'Gabon': 'GAB', 'Gambia': 'GMB', 'Georgia': 'GEO', 'German Democratic Republic': 'DEU', 'Germany': 'DEU', 'Germany (East)': 'DEU', 'Ghana': 'GHA',
    'Greece': 'GRC', 'Guatemala': 'GTM', 'Guinea': 'GIN', 'Guinea-Bissau': 'GNB', 'Guyana': 'GUY', 'Haiti': 'HTI', 'Honduras': 'HND',
    'Hungary': 'HUN', 'Hyderabad': 'IND', 'India': 'IND', 'Indonesia': 'IDN', 'Iran': 'IRN', 'Iraq': 'IRQ', 'Ireland': 'IRL', 'Israel': 'ISR', 'Italy': 'ITA',
    'Ivory Coast': 'CIV', 'Jamaica': 'JAM', 'Japan': 'JPN', 'Jordan': 'JOR', 'Kazakhstan': 'KAZ', 'Kenya': 'KEN', 'Kosovo': 'KOS', 'Kuwait': 'KWT',
    'Kyrgyzstan': 'KGZ', 'Laos': 'LAO', 'Latvia': 'LVA', 'Lebanon': 'LBN', 'Lesotho': 'LSO', 'Liberia': 'LBR', 'Libya': 'LBY', 'Lithuania': 'LTU',
    'Macedonia, FYR': 'MKD', 'North Macedonia': 'MKD', 'Madagascar (Malagasy)': 'MDG', 'Malawi': 'MWI', 'Malaysia': 'MYS', 'Mali': 'MLI', 'Mauritania': 'MRT',
    'Mexico': 'MEX', 'Moldova': 'MDA', 'Mongolia': 'MNG', 'Montenegro': 'MNE', 'Morocco': 'MAR', 'Mozambique': 'MOZ', 'Myanmar (Burma)': 'MMR', 'Namibia': 'NAM',
    'Nepal': 'NPL', 'Netherlands': 'NLD', 'New Zealand': 'NZL', 'Nicaragua': 'NIC', 'Niger': 'NER', 'Nigeria': 'NGA', 'North Korea': 'PRK', 'Norway': 'NOR',
    'Oman': 'OMN', 'Pakistan': 'PAK', 'Panama': 'PAN', 'Papua New Guinea': 'PNG', 'Paraguay': 'PRY', 'Peru': 'PER', 'Philippines': 'PHL', 'Poland': 'POL',
    'Portugal': 'PRT', 'Qatar': 'QAT', 'Romania': 'ROU', 'Russia (Soviet Union)': 'RUS', 'Rwanda': 'RWA', 'Saudi Arabia': 'SAU', 'Senegal': 'SEN',
    'Serbia (Yugoslavia)': 'SRB', 'Sierra Leone': 'SLE', 'Slovenia': 'SVN', 'Somalia': 'SOM', 'South Africa': 'ZAF', 'South Korea': 'KOR', 'South Sudan': 'SDS',
    'South Vietnam': 'VNM', 'South Yemen': 'YEM', 'Spain': 'ESP', 'Sri Lanka': 'LKA', 'Sudan': 'SDN', 'Suriname': 'SUR', 'Sweden': 'SWE', 'Switzerland': 'CHE',
    'Syria': 'SYR', 'Taiwan': 'TWN', 'Tajikistan': 'TJK', 'Tanzania': 'TZA', 'Thailand': 'THA', 'Tibet': 'CHN', 'Togo': 'TGO', 'Trinidad and Tobago': 'TTO',
    'Tunisia': 'TUN', 'Turkey': 'TUR', 'Türkiye': 'TUR', 'Turkmenistan': 'TKM', 'Uganda': 'UGA', 'Ukraine': 'UKR', 'United Arab Emirates': 'ARE',
    'United Kingdom': 'GBR', 'United States of America': 'USA', 'Uruguay': 'URY', 'Uzbekistan': 'UZB', 'Venezuela': 'VEN', 'Vietnam (North Vietnam)': 'VNM',
    'Yemen (North Yemen)': 'YEM', 'Zambia': 'ZMB', 'Zimbabwe (Rhodesia)': 'ZWE', 'Zanzibar': 'TZA', 'Mauritius': 'MUS', 'Maldives': 'MDV', 
    'Solomon Islands': 'SLB', 'Swaziland': 'SWZ', 'Eswatini': 'SWZ', 'Timor-Leste': 'TLS', 'East Timor': 'TLS', 'Vanuatu': 'VUT', 'Vietnam': 'VNM',
    'Palestine': 'PSX', 'Western Sahara': 'SAH', 'Yugoslavia': 'SRB', 'Serbia': 'SRB', 'Slovakia': 'SVK', 'Luxembourg': 'LUX', 'Iceland': 'ISL', 'Cape Verde': 'CPV',
    'Sao Tome and Principe': 'STP', 'Seychelles': 'SYC', 'Singapore': 'SGP', 'Bahamas': 'BHS', 'Barbados': 'BRB', 'Belize': 'BLZ', 'Antigua and Barbuda': 'ATG',
    'Hong Kong': 'CHN', 'Rhodesia': 'ZWE', 'Yemen (South Yemen)': 'YEM', 'Kingdom of eSwatini (Swaziland)': 'SWZ', 'Samoa (Western Samoa)': 'WSM', 'Antigua & Barbuda': 'ATG',
}
# states too small for the base map; UCDP lists them with no deaths
SKIP = {'Grenada', 'Bahrain', 'Comoros', 'Malta', 'Andorra', 'Dominica', 'Federated States of Micronesia', 'Kiribati', 'Liechtenstein', 'Marshall Islands', 'Monaco', 'Nauru', 'Palau', 'Saint Kitts and Nevis', 'Saint Lucia', 'Saint Vincent and the Grenadines', 'San Marino', 'Tonga', 'Tuvalu', 'Vatican City State'}
PLAIN = {'DR Congo (Zaire)': 'DR Congo', 'Yemen (North Yemen)': 'Yemen', 'Russia (Soviet Union)': 'Russia', 'Myanmar (Burma)': 'Myanmar', 'Cambodia (Kampuchea)': 'Cambodia',
         'Madagascar (Malagasy)': 'Madagascar', 'Zimbabwe (Rhodesia)': 'Zimbabwe', 'Serbia (Yugoslavia)': 'Serbia', 'Vietnam (North Vietnam)': 'Vietnam',
         'United States of America': 'United States', 'Bosnia-Herzegovina': 'Bosnia', 'Central African Republic': 'Central African Rep.', 'Turkey': 'Türkiye',
         'Kingdom of eSwatini (Swaziland)': 'Eswatini', 'Macedonia, FYR': 'North Macedonia', 'United Kingdom': 'Britain', 'Israel': 'Israel and Palestine'}


def one(path_glob):
    f = sorted(glob.glob(path_glob))
    if not f:
        sys.exit(f'missing {path_glob}')
    return f[-1]


def main():
    d = sys.argv[1]
    unmatched = set()

    def iso(name):
        name = name.strip()
        if name in NAMES:
            return NAMES[name]
        if name not in SKIP:
            unmatched.add(name)
        return None

    acd = list(csv.DictReader(open(one(os.path.join(d, 'UcdpPrioConflict_v*.csv')), encoding='utf-8-sig')))
    years = {}
    for r in acd:
        y = int(r['year'])
        row = years.setdefault(y, {'year': y, 'ids': set(), 'wars': set(), 'interstate': set(), 'active': {}, 'is': set(), 'per': {}})
        row['ids'].add(r['conflict_id'])
        if 'IS' in [x.strip() for x in r['side_b'].split(',')]:
            row['is'].add(r['conflict_id'])
        row['per'][r['location']] = row['per'].get(r['location'], 0) + 1
        if r['intensity_level'] == '2':
            row['wars'].add(r['conflict_id'])
        if r['type_of_conflict'] == '2':
            row['interstate'].add(r['conflict_id'])
        for loc in r['location'].split(', '):
            code = iso(loc)
            if code:
                row['active'][code] = max(row['active'].get(code, 0), int(r['intensity_level']))
    acd_version = acd[0].get('version') or acd[0].get('Version') or ''

    cy = list(csv.DictReader(open(one(os.path.join(d, 'OrganizedViolenceCYDataSet*.csv')), encoding='utf-8-sig')))
    deaths, names, top, named = {}, {}, {}, {}
    num = lambda v: int(float(v or 0))
    for r in cy:
        y = int(r['year'])
        code = iso(r['country'])
        if not code:
            continue
        sb, ns, os_ = num(r['sb_total_deaths_best']), num(r['ns_total_deaths_best']), num(r['os_total_deaths_best'])
        best = sb + ns + os_
        low = num(r['sb_total_deaths_low']) + num(r['ns_total_deaths_low']) + num(r['os_total_deaths_low'])
        high = num(r['sb_total_deaths_high']) + num(r['ns_total_deaths_high']) + num(r['os_total_deaths_high'])
        if best == 0 and high == 0:
            continue
        cell = deaths.setdefault(str(y), {}).get(code)
        if cell:   # two UCDP rows on one shape (a state that no longer exists): add them
            cell = [cell[0] + best, cell[1] + low, cell[2] + high, cell[3] + sb, cell[4] + ns, cell[5] + os_]
        else:
            cell = [best, low, high, sb, ns, os_]
        deaths[str(y)][code] = cell
        if code not in named or y >= named[code]:   # a shape that merges two UCDP states takes the later state's name
            names[code] = PLAIN.get(r['country'], r['country']); named[code] = y
    for y, row in deaths.items():
        top[y] = [[c, names[c], v[0]] for c, v in sorted(row.items(), key=lambda kv: -kv[1][0])[:5] if v[0] > 0]
    cy_version = cy[0].get('Version') or ''

    out = {
        'rule': "Conflicts per year are the UCDP/PRIO Armed Conflict Dataset, 1946 on: a conflict is one government against one side over who governs or over territory, with 25 or more deaths in fighting that year, so one movement fighting several governments is several conflicts and one country can hold several; at war level means a thousand or more that year; between states means the sides are states. Deaths by country and year are UCDP's country-year file, 1989 on: fighting between a state and another side, fighting between armed groups, and civilians killed on purpose, with UCDP's low and high. UCDP places deaths in the country where they happened, so one war can sit in two countries; this page's own label 'Israel and Palestine' is UCDP's Israel row. A state that no longer exists is drawn on the shape that holds its capital today, and a state that did not yet exist is counted in the one it was part of, so Eritrea's war before 1993 sits on Ethiopia and South Sudan's before 2011 on Sudan. UCDP revises recent years in each release; this page treats the last two as provisional.",
        'versions': {'conflicts': acd_version, 'deaths': cy_version},
        'built': date.today().isoformat(),
        'years': [{'year': y, 'n': len(r['ids']), 'wars': len(r['wars']), 'interstate': len(r['interstate']), 'is': len(r['is']), 'most': [PLAIN.get(k, k), v] if r['per'] else None, 'active': dict(sorted(r['active'].items()))} for y, r in sorted(years.items()) for k, v in [max(r['per'].items(), key=lambda kv: kv[1])]],
        'deaths': deaths,
        'top': top,
        'names': dict(sorted(names.items())),
    }
    # every code the page will look up must be a shape on the base map
    shapes = {g['id'] for g in json.load(open(os.path.join(ROOT, 'data', 'world_110m.json')))['objects']['countries']['geometries']}
    used = set(names) | {c for r in out['years'] for c in r['active']}
    bad = sorted(used - shapes)
    if unmatched or bad:
        sys.exit(f'not written: unmatched names {sorted(unmatched)}; codes with no shape on the base map {bad}')
    json.dump(out, open(os.path.join(ROOT, 'data', 'level.json'), 'w'), separators=(',', ':'), ensure_ascii=False)
    print('wrote data/level.json:', len(out['years']), 'years of conflicts,', len(deaths), 'years of deaths,', len(names), 'countries')


if __name__ == '__main__':
    main()
