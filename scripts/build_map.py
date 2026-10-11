#!/usr/bin/env python3
"""Project Natural Earth 110m countries to Equal Earth and write SVG paths.

Input : a Natural Earth 110m admin-0 countries GeoJSON (public domain), e.g.
        https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_admin_0_countries.geojson
Output: data/world_paths.json — one SVG path per country in a 1000-wide viewBox,
        plus the projection constants so the page can place points the same way.
Usage : python3 scripts/build_map.py path/to/ne_110m_admin_0_countries.geojson
"""
import json, math, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

A1, A2, A3, A4 = 1.340264, -0.081106, 0.000893, 0.003796
M = math.sqrt(3) / 2

def equal_earth(lon, lat):
    lam, phi = math.radians(lon), math.radians(lat)
    theta = math.asin(M * math.sin(phi))
    t2 = theta * theta
    t6 = t2 * t2 * t2
    x = lam * math.cos(theta) / (M * (A1 + 3 * A2 * t2 + t6 * (7 * A3 + 9 * A4 * t2)))
    y = theta * (A1 + A2 * t2 + t6 * (A3 + A4 * t2))
    return x, y

WIDTH = 1000.0
DROP = {"ATA"}  # Antarctica: the map stops at the southern tip of South America

def main(src):
    gj = json.load(open(src))
    feats = [f for f in gj["features"] if f["properties"].get("ADM0_A3") not in DROP]
    # projected rings per country
    countries = []
    xs, ys = [], []
    for f in feats:
        p = f["properties"]
        g = f["geometry"]
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        rings = []
        for poly in polys:
            for ring in poly:
                pr = [equal_earth(lon, lat) for lon, lat in ring]
                rings.append(pr)
                xs.extend(x for x, _ in pr); ys.extend(y for _, y in pr)
        countries.append({"id": p.get("ADM0_A3"), "iso2": p.get("ISO_A2"), "name": p.get("NAME"), "rings": rings})
    # frame: full sphere outline horizontally, data extent vertically
    x_edge = equal_earth(180, 0)[0]
    k = WIDTH / (2 * x_edge)
    y_top, y_bot = max(ys), min(ys)
    pad = 0.02
    height = k * (y_top - y_bot) * (1 + 2 * pad)
    cx = WIDTH / 2
    cy = k * y_top + k * (y_top - y_bot) * pad
    def px(x): return round(cx + k * x, 1)
    def py(y): return round(cy - k * y, 1)
    out = []
    for c in countries:
        d = []
        for ring in c["rings"]:
            pts = [(px(x), py(y)) for x, y in ring]
            # drop consecutive duplicates after rounding
            dedup = [pts[0]]
            for q in pts[1:]:
                if q != dedup[-1]:
                    dedup.append(q)
            if len(dedup) < 3:
                continue
            d.append("M" + " ".join(f"{x:g},{y:g}" for x, y in dedup) + "Z")
        out.append({"id": c["id"], "iso2": c["iso2"], "name": c["name"], "d": "".join(d)})
    # sphere outline (the edge of the projection) for a hairline frame
    edge = []
    for lat in range(-90, 91, 2):
        edge.append(equal_earth(-180, lat))
    for lat in range(90, -91, -2):
        edge.append(equal_earth(180, lat))
    outline = "M" + " ".join(f"{px(x):g},{py(y):g}" for x, y in edge) + "Z"
    # graticule every 30 degrees, clipped to the drawn latitude band
    grat = []
    lat_lo, lat_hi = -60, 90
    for lon in range(-150, 181, 30):
        grat.append("M" + " ".join(f"{px(x):g},{py(y):g}" for x, y in (equal_earth(lon, la) for la in range(lat_lo, lat_hi + 1, 3))))
    for lat in range(-60, 91, 30):
        grat.append("M" + " ".join(f"{px(x):g},{py(y):g}" for x, y in (equal_earth(lo, lat) for lo in range(-180, 181, 5))))
    result = {
        "source": "Natural Earth 1:110m admin-0 countries (public domain)",
        "projection": "equal-earth",
        "viewBox": [0, 0, WIDTH, round(height, 1)],
        "k": k, "cx": cx, "cy": cy,
        "outline": outline,
        "graticule": "".join(grat),
        "countries": out,
    }
    json.dump(result, open(os.path.join(ROOT, "data", "world_paths.json"), "w"), separators=(",", ":"))
    print(f"{len(out)} countries, viewBox {result['viewBox']}, k={k:.3f}, cy={cy:.2f}")

if __name__ == "__main__":
    main(sys.argv[1])
