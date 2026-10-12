#!/usr/bin/env python3
"""Project the provinces under war to the map's coordinates.

Reads the `areas` list on each entry in data/conflicts.json (country code +
admin-1 name as Natural Earth spells it), pulls those provinces from a
Natural Earth 1:10m admin-1 GeoJSON, projects them with the same Equal Earth
constants as scripts/build_map.py, simplifies them, and writes
data/war_areas.json as one SVG path per entry.

Usage: python3 scripts/build_areas.py path/to/ne_10m_admin_1_states_provinces.geojson
"""
import json, math, os, sys, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A1, A2, A3, A4 = 1.340264, -0.081106, 0.000893, 0.003796
M = math.sqrt(3) / 2

def equal_earth(lon, lat):
    lam, phi = math.radians(lon), math.radians(lat)
    theta = math.asin(M * math.sin(phi))
    t2 = theta * theta; t6 = t2 * t2 * t2
    x = lam * math.cos(theta) / (M * (A1 + 3 * A2 * t2 + t6 * (7 * A3 + 9 * A4 * t2)))
    y = theta * (A1 + A2 * t2 + t6 * (A3 + A4 * t2))
    return x, y

def fold(s):
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c)).lower().replace("'", "").replace("`", "").replace("-", " ").replace("  ", " ").strip()

def simplify(pts, tol):
    """Douglas-Peucker on projected points."""
    if len(pts) < 3:
        return pts
    def dist(p, a, b):
        (x, y), (x1, y1), (x2, y2) = p, a, b
        dx, dy = x2 - x1, y2 - y1
        if dx == 0 and dy == 0:
            return math.hypot(x - x1, y - y1)
        t = max(0, min(1, ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy)))
        return math.hypot(x - (x1 + t * dx), y - (y1 + t * dy))
    keep = [False] * len(pts); keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        i, j = stack.pop()
        best, bi = 0, -1
        for k in range(i + 1, j):
            d = dist(pts[k], pts[i], pts[j])
            if d > best:
                best, bi = d, k
        if best > tol:
            keep[bi] = True; stack.append((i, bi)); stack.append((bi, j))
    return [p for p, k in zip(pts, keep) if k]

ISO_ALIAS = {"PSE": "PSX", "SSD": "SDS"}  # Natural Earth's own codes for Palestine and South Sudan

def main(src):
    world = json.load(open(os.path.join(ROOT, "data", "world_paths.json")))
    k, cx, cy = world["k"], world["cx"], world["cy"]
    conflicts = json.load(open(os.path.join(ROOT, "data", "conflicts.json")))["conflicts"]
    wanted = {}
    for c in conflicts:
        for a in c.get("areas", []):
            iso = a.get("ne") or ISO_ALIAS.get(a["country"], a["country"])
            wanted.setdefault((iso, fold(a["name"])), []).append(c["id"])
    gj = json.load(open(src))
    index = {}
    for f in gj["features"]:
        p = f["properties"]
        for key in (p.get("name"), p.get("name_en")):
            if key:
                index[(p.get("adm0_a3"), fold(key))] = f
    out, missing = {}, []
    for (iso, name), ids in wanted.items():
        f = index.get((iso, name))
        if not f:
            missing.append(f"{iso}:{name}"); continue
        g = f["geometry"]
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        d = []
        for poly in polys:
            ring = poly[0]  # outer ring only; holes are rare at this scale
            pts = [(round(cx + k * x, 1), round(cy - k * y, 1)) for x, y in (equal_earth(lon, lat) for lon, lat in ring)]
            pts = simplify(pts, 0.35)
            dedup = [pts[0]]
            for q in pts[1:]:
                if q != dedup[-1]: dedup.append(q)
            if len(dedup) >= 3:
                d.append("M" + " ".join(f"{x:g},{y:g}" for x, y in dedup) + "Z")
        for cid in ids:
            out.setdefault(cid, {"regions": [], "d": ""})
            out[cid]["regions"].append(f["properties"].get("name"))
            out[cid]["d"] += "".join(d)
    if missing:
        print("NOT FOUND in Natural Earth (fix the name in conflicts.json):", ", ".join(sorted(missing)))
    result = {"source": "Natural Earth 1:10m admin-1 states and provinces (public domain), Equal Earth projection, simplified", "areas": out}
    path = os.path.join(ROOT, "data", "war_areas.json")
    json.dump(result, open(path, "w"), separators=(",", ":"))
    print(f"{len(out)} entries, {sum(len(v['regions']) for v in out.values())} regions, {os.path.getsize(path)//1024} KB -> {path}")

if __name__ == "__main__":
    main(sys.argv[1])
