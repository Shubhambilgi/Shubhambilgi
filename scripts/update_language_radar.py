#!/usr/bin/env python3
"""Generate a radar/spider chart from GitHub Linguist language byte counts."""

import json
import os
import urllib.request
from pathlib import Path
from xml.sax.saxutils import escape

USERNAME = "Shubhambilgi"
PROFILE_REPO = "Shubhambilgi"
OUT = Path("assets/language-radar.svg")
MAX_LANGUAGES = 6


def get_json(url):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "Shubhambilgi-language-radar",
    }
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def collect_languages():
    repos = get_json(
        f"https://api.github.com/users/{USERNAME}/repos"
        "?per_page=100&type=owner&sort=updated"
    )

    totals = {}
    for repo in repos:
        full_name = repo["full_name"]
        if full_name == f"{USERNAME}/{PROFILE_REPO}" or repo.get("fork"):
            continue

        try:
            languages = get_json(
                f"https://api.github.com/repos/{full_name}/languages"
            )
        except Exception as exc:
            print(f"Skipping {full_name}: {exc}")
            continue

        for language, bytes_count in languages.items():
            totals[language] = totals.get(language, 0) + bytes_count

    return dict(sorted(totals.items(), key=lambda item: item[1], reverse=True)[:MAX_LANGUAGES])


def radar_svg(languages):
    width, height = 900, 620
    cx, cy = 450, 315
    radius = 205
    labels = list(languages.keys())

    if not labels:
        return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<rect width="100%" height="100%" rx="24" fill="#0d1117"/>
<text x="450" y="290" text-anchor="middle" fill="#f0f6fc" font-size="30" font-family="Arial,sans-serif" font-weight="700">GitHub Language Radar</text>
<text x="450" y="335" text-anchor="middle" fill="#8b949e" font-size="18" font-family="Arial,sans-serif">Waiting for GitHub language data...</text>
</svg>'''

    values = list(languages.values())
    max_value = max(values)
    count = len(labels)

    def point(index, value):
        import math
        angle = -math.pi / 2 + (2 * math.pi * index / count)
        r = radius * value
        return cx + r * math.cos(angle), cy + r * math.sin(angle)

    def polygon(points):
        return " ".join(f"{x:.1f},{y:.1f}" for x, y in points)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" rx="24" fill="#0d1117"/>',
        '<text x="450" y="48" text-anchor="middle" fill="#f0f6fc" font-size="28" font-family="Arial,sans-serif" font-weight="700">Programming Language Radar</text>',
        '<text x="450" y="76" text-anchor="middle" fill="#8b949e" font-size="14" font-family="Arial,sans-serif">Based on GitHub Linguist byte counts across public repositories</text>',
    ]

    import math
    for level in range(1, 6):
        r = radius * level / 5
        pts = []
        for i in range(count):
            angle = -math.pi / 2 + (2 * math.pi * i / count)
            pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
        parts.append(f'<polygon points="{polygon(pts)}" fill="none" stroke="#30363d" stroke-width="1"/>')

    for i, label in enumerate(labels):
        x, y = point(i, 1)
        parts.append(f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" stroke="#30363d" stroke-width="1"/>')

    data_points = []
    total = sum(values)
    for i, value in enumerate(values):
        fraction = value / max_value if max_value else 0
        data_points.append(point(i, fraction))

    parts.append(
        f'<polygon points="{polygon(data_points)}" fill="#58a6ff" fill-opacity="0.28" '
        'stroke="#58a6ff" stroke-width="3"/>'
    )

    for i, (label, value) in enumerate(zip(labels, values)):
        x, y = data_points[i]
        lx, ly = point(i, 1.18)
        pct = value / total * 100 if total else 0
        anchor = "middle"
        if lx < cx - 20:
            anchor = "end"
        elif lx > cx + 20:
            anchor = "start"

        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="#58a6ff"/>')
        parts.append(
            f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anchor}" fill="#f0f6fc" '
            f'font-size="16" font-family="Arial,sans-serif" font-weight="700">{escape(label)}</text>'
        )
        parts.append(
            f'<text x="{lx:.1f}" y="{ly + 20:.1f}" text-anchor="{anchor}" fill="#8b949e" '
            f'font-size="13" font-family="Arial,sans-serif">{pct:.1f}%</text>'
        )

    parts.append(
        '<text x="450" y="585" text-anchor="middle" fill="#8b949e" font-size="12" '
        'font-family="Arial,sans-serif">Automatically updated by GitHub Actions</text>'
    )
    parts.append("</svg>")
    return "\n".join(parts)


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    languages = collect_languages()
    print("Languages:", json.dumps(languages, indent=2))
    OUT.write_text(radar_svg(languages), encoding="utf-8")


if __name__ == "__main__":
    main()
