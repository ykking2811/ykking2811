import datetime
import json
import os
import re
import urllib.request
from pathlib import Path

USERNAME = os.environ.get("GITHUB_USER", "ykking2811")
OUT_PATH = Path(__file__).resolve().parents[2] / "assets" / "contribution-graph.svg"

LEVEL_COLORS = {
    0: "#18181B",  # Midnight charcoal (empty)
    1: "#450A0A",  # Deep crimson
    2: "#7F1D1D",  # Dark crimson
    3: "#B91C1C",  # Structural crimson
    4: "#DC2626",  # Electric crimson
}


def fetch_via_graphql(token: str) -> tuple[int, list[dict]]:
    query = """
    query($login: String!) {
      user(login: $login) {
        contributionsCollection {
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                date
                contributionLevel
                contributionCount
              }
            }
          }
        }
      }
    }
    """
    level_map = {
        "NONE": 0,
        "FIRST_QUARTILE": 1,
        "SECOND_QUARTILE": 2,
        "THIRD_QUARTILE": 3,
        "FOURTH_QUARTILE": 4,
    }
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": {"login": USERNAME}}).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "ykking2811-contrib-svg",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    cal = payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    days = []
    for week in cal["weeks"]:
        for d in week["contributionDays"]:
            days.append(
                {
                    "date": d["date"],
                    "level": level_map.get(d["contributionLevel"], 0),
                    "count": d["contributionCount"],
                }
            )
    return cal["totalContributions"], days


def fetch_via_public_html() -> tuple[str, list[dict]]:
    req = urllib.request.Request(
        f"https://github.com/users/{USERNAME}/contributions",
        headers={"User-Agent": "ykking2811-contrib-svg"},
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        html = resp.read().decode("utf-8", errors="replace")

    total_match = re.search(r"([\d,]+)\s+contributions?\s+in\s+the\s+last\s+year", html)
    total_label = f"{total_match.group(1)} CONTRIBUTIONS IN THE LAST YEAR" if total_match else "CONTRIBUTION TELEMETRY"

    cells = re.findall(
        r'data-date="(\d{4}-\d{2}-\d{2})"[^>]*data-level="([0-4])"',
        html,
    )
    if not cells:
        cells = [
            (d, l)
            for l, d in re.findall(
                r'data-level="([0-4])"[^>]*data-date="(\d{4}-\d{2}-\d{2})"',
                html,
            )
        ]

    days = [{"date": d, "level": int(l), "count": None} for d, l in sorted(set(cells), key=lambda x: x[0])]
    return total_label, days


def render_svg(header_label: str, days: list[dict]) -> str:
    # Group into 7-day columns starting on Sunday
    if not days:
        raise RuntimeError("No contribution days retrieved.")

    first_date = datetime.date.fromisoformat(days[0]["date"])
    # GitHub weekday: Sunday=0 .. Saturday=6
    first_wd = (first_date.weekday() + 1) % 7
    padded = [{"date": "", "level": -1}] * first_wd + days

    weeks = [padded[i : i + 7] for i in range(0, len(padded), 7)]
    weeks = weeks[-53:]  # Max 53 columns

    cell = 15
    gap = 5
    step = cell + gap
    origin_x = 68
    origin_y = 66

    cells_svg = []
    month_labels = []
    last_month = None

    for w_idx, week in enumerate(weeks):
        x = origin_x + w_idx * step
        for d_idx, day in enumerate(week):
            if day["level"] < 0:
                continue
            y = origin_y + d_idx * step
            color = LEVEL_COLORS[day["level"]]
            stroke = "#27272A" if day["level"] == 0 else "none"
            cells_svg.append(
                f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="3" fill="{color}" stroke="{stroke}" stroke-width="0.8"/>'
            )
            if d_idx == 0 and day["date"]:
                m = datetime.date.fromisoformat(day["date"]).strftime("%b").upper()
                if m != last_month:
                    month_labels.append(
                        f'<text x="{x}" y="52" fill="#A1A1AA" font-size="10" letter-spacing="1.2" class="mono">{m}</text>'
                    )
                    last_month = m

    day_labels = [
        (1, "MON"),
        (3, "WED"),
        (5, "FRI"),
    ]
    day_labels_svg = [
        f'<text x="26" y="{origin_y + idx * step + 11}" fill="#71717A" font-size="9.5" letter-spacing="1.2" class="mono">{lbl}</text>'
        for idx, lbl in day_labels
    ]

    legend_x = 996
    legend_svg = [
        f'<text x="{legend_x - 36}" y="238" fill="#71717A" font-size="9.5" letter-spacing="1.2" class="mono">LESS</text>'
    ]
    for lvl in range(5):
        lx = legend_x + lvl * 20
        stroke = "#27272A" if lvl == 0 else "none"
        legend_svg.append(
            f'<rect x="{lx}" y="227" width="14" height="14" rx="3" fill="{LEVEL_COLORS[lvl]}" stroke="{stroke}" stroke-width="0.8"/>'
        )
    legend_svg.append(
        f'<text x="{legend_x + 106}" y="238" fill="#A1A1AA" font-size="9.5" letter-spacing="1.2" class="mono">MORE</text>'
    )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 260" width="1200" height="260" role="img" aria-label="{USERNAME} Contribution Matrix — {header_label}">
  <defs>
    <style>
      .mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }}
    </style>
  </defs>
  <rect width="1200" height="260" rx="10" fill="#09090B" stroke="#27272A" stroke-width="1.5"/>
  <rect x="0" y="0" width="6" height="260" rx="3" fill="#991B1B"/>
  <text x="26" y="28" fill="#E4E4E7" font-size="11" font-weight="700" letter-spacing="2" class="mono">SYS.03 // {header_label}</text>
  <text x="1174" y="28" text-anchor="end" fill="#DC2626" font-size="10.5" font-weight="600" letter-spacing="1.8" class="mono">@{USERNAME.upper()}</text>
  <line x1="26" y1="36" x2="1174" y2="36" stroke="#18181B" stroke-width="1"/>
  {"".join(month_labels)}
  {"".join(day_labels_svg)}
  {"".join(cells_svg)}
  <line x1="26" y1="214" x2="1174" y2="214" stroke="#18181B" stroke-width="1"/>
  <text x="26" y="238" fill="#A1A1AA" font-size="9.5" letter-spacing="1.5" class="mono">DAILY TELEMETRY SYNC · 60% BLACK / 25% CRIMSON / 15% SILVER</text>
  {"".join(legend_svg)}
</svg>
'''


def main() -> None:
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        total, days = fetch_via_graphql(token)
        header_label = f"{total:,} CONTRIBUTIONS IN THE LAST YEAR"
    else:
        header_label, days = fetch_via_public_html()

    svg = render_svg(header_label, days)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(svg, encoding="utf-8")
    print(f"Generated {OUT_PATH} ({len(days)} days)")


if __name__ == "__main__":
    main()
