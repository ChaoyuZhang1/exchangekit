#!/usr/bin/env python3
"""Build an inline SVG world land path for the ExchangeKit map.

Downloads Natural Earth 110m land TopoJSON (via jsDelivr) and converts it to a
single projected SVG path (equirectangular, 1000x500). Output: data/world_land.json
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "world_land_110m.json"
OUT = ROOT / "data" / "world_land.json"
URL = "https://cdn.jsdelivr.net/npm/world-atlas@2/land-110m.json"
W, H = 1000.0, 500.0


def fetch() -> dict:
    if CACHE.exists() and CACHE.stat().st_size > 1000:
        return json.loads(CACHE.read_text(encoding="utf-8"))
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    curl = shutil.which("curl.exe") or shutil.which("curl") or "curl"
    subprocess.run([curl, "-s", "--max-time", "90", "-o", str(CACHE), URL], check=False, timeout=120)
    if not CACHE.exists() or CACHE.stat().st_size < 1000:
        raise SystemExit("failed to download world-atlas land-110m.json")
    return json.loads(CACHE.read_text(encoding="utf-8"))


def project(lon: float, lat: float) -> tuple[float, float]:
    return ((lon + 180.0) / 360.0 * W, (90.0 - lat) / 180.0 * H)


def main() -> int:
    topo = fetch()
    scale = topo["transform"]["scale"]
    translate = topo["transform"]["translate"]
    raw_arcs = topo["arcs"]

    arcs: list[list[tuple[float, float]]] = []
    for arc in raw_arcs:
        pts: list[tuple[float, float]] = []
        x = y = 0.0
        for dx, dy in arc:
            x += dx
            y += dy
            pts.append((x * scale[0] + translate[0], y * scale[1] + translate[1]))
        arcs.append(pts)

    def ring(arc_ids: list[int]) -> list[tuple[float, float]]:
        pts: list[tuple[float, float]] = []
        for idx in arc_ids:
            seg = arcs[idx] if idx >= 0 else list(reversed(arcs[~idx]))
            if pts:
                seg = seg[1:]
            pts.extend(seg)
        return pts

    def path_for_rings(rings: list[list[tuple[float, float]]]) -> str:
        parts = []
        for pts in rings:
            if len(pts) < 3:
                continue
            xy = [project(lon, lat) for lon, lat in pts]
            d = "M" + " ".join(
                (f"{x:.0f}" if x == int(x) else f"{x:.1f}") + "," +
                (f"{y:.0f}" if y == int(y) else f"{y:.1f}")
                for x, y in xy
            ) + "Z"
            parts.append(d)
        return "".join(parts)

    land = topo["objects"]["land"]
    rings_all: list[list[tuple[float, float]]] = []
    if land["type"] == "GeometryCollection":
        for geom in land["geometries"]:
            if geom["type"] == "Polygon":
                rings_all += [ring(r) for r in geom["arcs"]]
            elif geom["type"] == "MultiPolygon":
                for poly in geom["arcs"]:
                    rings_all += [ring(r) for r in poly]
    elif land["type"] == "MultiPolygon":
        for poly in land["arcs"]:
            rings_all += [ring(r) for r in poly]
    elif land["type"] == "Polygon":
        rings_all = [ring(r) for r in land["arcs"]]
    path = path_for_rings(rings_all)

    payload = {"w": int(W), "h": int(H), "path": path}
    OUT.write_text(json.dumps(payload), encoding="utf-8")
    print(f"world path chars={len(path)} -> {OUT} ({OUT.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
