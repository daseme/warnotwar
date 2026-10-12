#!/usr/bin/env python3
"""Build the map's base files, data/world_110m.json and data/world_50m.json, from Natural Earth.

Usage: scripts/build_topo.py <dir with ne_110m_admin_0_countries.geojson and ne_50m_admin_0_countries.geojson> [--npx "<command prefix>"]

Natural Earth GeoJSON (public domain): https://github.com/nvkelso/natural-earth-vector/tree/master/geojson
Steps: drop Antarctica and every property but ADM0_A3, ISO_A2 and NAME; run the TopoJSON tools
(geo2topo, toposimplify -p 0.02 for the 50m file, topoquantize 1e4 / 1e5); then write the page's
projection constants under "map", taken from data/world_paths.json so the province shapes in
data/war_areas.json still fit. The TopoJSON tools are node packages; on this machine node lives on
the Windows side, so pass --npx 'cmd.exe /c npx -y' and a directory under /mnt/c, or run the three
npx commands by hand and rerun this script to inject the constants.
"""
import json
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def prune(src, dst):
    g = json.load(open(src))
    feats = []
    for x in g['features']:
        p = x['properties']
        if p.get('ADM0_A3') == 'ATA':
            continue
        x['properties'] = {'id': p.get('ADM0_A3'), 'iso2': p.get('ISO_A2'), 'name': p.get('NAME')}
        x['id'] = p.get('ADM0_A3')
        feats.append(x)
    json.dump({'type': 'FeatureCollection', 'features': feats}, open(dst, 'w'))
    return len(feats)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    d = sys.argv[1]
    npx = sys.argv[sys.argv.index('--npx') + 1] if '--npx' in sys.argv else 'npx -y'
    wp = json.load(open(os.path.join(ROOT, 'data', 'world_paths.json')))
    meta = {'k': wp['k'], 'cx': wp['cx'], 'cy': wp['cy'], 'viewBox': wp['viewBox']}
    for res, q, simplify in (('110m', '1e4', ''), ('50m', '1e5', ' -p 0.02')):
        src = os.path.join(d, f'ne_{res}_admin_0_countries.geojson')
        pruned = os.path.join(d, f'countries_{res}.geojson')
        if os.path.exists(src):
            print(res, prune(src, pruned), 'countries after pruning')
        topo = os.path.join(d, f'world_{res}.json')
        if not os.path.exists(topo):
            cmd = f'{npx} -p topojson-server -p topojson-simplify -p topojson-client sh -c "geo2topo countries=countries_{res}.geojson' + (f' | toposimplify -f{simplify}' if simplify else '') + f' | topoquantize {q} > world_{res}.json"'
            print('running:', cmd)
            subprocess.run(cmd, shell=True, cwd=d, check=True)
        t = json.load(open(topo))
        t['map'] = {'projection': 'equal-earth', **meta, 'source': f'Natural Earth 1:{res} admin-0 countries (public domain), Antarctica dropped; TopoJSON via geo2topo{", toposimplify -p 0.02" if simplify else ""}, topoquantize {q}'}
        out = os.path.join(ROOT, 'data', f'world_{res}.json')
        json.dump(t, open(out, 'w'), separators=(',', ':'))
        print('wrote', out, len(t['objects']['countries']['geometries']), 'countries', os.path.getsize(out) // 1024, 'KB')


if __name__ == '__main__':
    main()
