#!/usr/bin/env python3
"""Render the profile activity card.

Reads the contributor calendar (aggregate counts only, never repo names) and
writes a dark and a light PNG into assets/.

Rendered at SCALE x the display size so text stays crisp on retina screens.
"""
import datetime as dt
import json
import os
import sys
import urllib.request

LOGIN = "SnegOwo"
SCALE = 2  # render 1680x500, display at 840x250

THEME = {
    "dark": {
        "bg": (13, 17, 23),
        "border": (33, 38, 45),
        "title": (255, 210, 30),
        "big": (255, 255, 255),
        "muted": (139, 148, 158),
        "label": (88, 96, 105),
        "scale": [(22, 27, 34), (20, 55, 95), (30, 90, 150), (55, 130, 200), (255, 210, 30)],
    },
    "light": {
        "bg": (255, 255, 255),
        "border": (225, 228, 232),
        "title": (120, 90, 0),
        "big": (31, 35, 40),
        "muted": (87, 96, 106),
        "label": (140, 148, 158),
        "scale": [(235, 237, 240), (190, 215, 240), (130, 180, 225), (70, 140, 205), (255, 180, 0)],
    },
}

QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { contributionCount contributionLevel } }
      }
      totalCommitContributions
    }
  }
}
"""


def fetch(token, days=365):
    to = dt.datetime.now(dt.timezone.utc)
    from_ = to - dt.timedelta(days=days)
    body = json.dumps({
        "query": QUERY,
        "variables": {"login": LOGIN, "from": from_.strftime("%Y-%m-%dT%H:%M:%SZ"),
                      "to": to.strftime("%Y-%m-%dT%H:%M:%SZ")},
    }).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql", data=body,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        payload = json.load(r)
    if "errors" in payload:
        raise SystemExit(f"GraphQL error: {payload['errors']}")
    return payload["data"]["user"]["contributionsCollection"]


def pick_font(size, bold=True):
    from PIL import ImageFont
    size = size * SCALE
    wanted = ["DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
              "segoeuib.ttf" if bold else "segoeui.ttf"]
    dirs = [os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts"),
            "C:/Windows/Fonts", "/usr/share/fonts/truetype/dejavu",
            "/usr/share/fonts/TTF", "/usr/share/fonts/truetype/liberation",
            "/usr/share/fonts/truetype/freefont"]
    for name in wanted:
        for d in dirs:
            p = os.path.join(d, name)
            if os.path.exists(p):
                return ImageFont.truetype(p, size)
    print("warning: no TTF font found, using PIL default", file=sys.stderr)
    return ImageFont.load_default(size)


LEVEL_COLOR = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2,
               "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}


def render(mode, data, out_path):
    from PIL import Image, ImageDraw
    t = THEME[mode]
    pad = 26 * SCALE
    W, H = 840 * SCALE, 250 * SCALE
    img = Image.new("RGB", (W, H), t["bg"])
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, W - 1, H - 1], radius=12 * SCALE,
                        outline=t["border"], width=1 * SCALE)

    cal = data["contributionCalendar"]
    days = [day for week in cal["weeks"] for day in week["contributionDays"]]
    streak = active = best = 0
    for day in days:
        if day["contributionCount"] > 0:
            active += 1
            streak += 1
            best = max(best, streak)
        else:
            streak = 0

    f_title = pick_font(21)
    f_big = pick_font(46)
    f_sub = pick_font(14, bold=False)
    f_stat = pick_font(24)
    f_statlbl = pick_font(12, bold=False)
    f_small = pick_font(11, bold=False)

    # --- left column -------------------------------------------------------
    d.text((pad, pad), "GitHub Activity", font=f_title, fill=t["title"])
    total = cal["totalContributions"]
    d.text((pad - 2 * SCALE, pad + 34 * SCALE), str(total), font=f_big, fill=t["big"])
    tw = d.textlength(str(total), font=f_big)
    d.text((pad + tw + 12 * SCALE, pad + 68 * SCALE),
           "contributions\nin the last year", font=f_sub, fill=t["muted"], spacing=4 * SCALE)

    stats = [("Commits", data["totalCommitContributions"]),
             ("Best streak", f"{best}d"),
             ("Active days", str(active))]
    sy = pad + 132 * SCALE
    for i, (lbl, val) in enumerate(stats):
        x = pad + i * 132 * SCALE
        d.text((x, sy), str(val), font=f_stat, fill=t["big"])
        d.text((x, sy + 30 * SCALE), lbl, font=f_statlbl, fill=t["label"])

    # --- heatmap -----------------------------------------------------------
    weeks = cal["weeks"][-23:]
    cell, gap = 13 * SCALE, 3 * SCALE
    step = cell + gap
    hm_w = len(weeks) * step - gap
    hx = W - pad - hm_w
    hy = pad + 40 * SCALE
    d.text((hx, pad + 6 * SCALE), "Last 23 weeks", font=f_sub, fill=t["muted"])
    for wi, week in enumerate(weeks):
        for di, day in enumerate(week["contributionDays"]):
            x = hx + wi * step
            y = hy + di * step
            d.rounded_rectangle([x, y, x + cell, y + cell], radius=2 * SCALE,
                                fill=t["scale"][LEVEL_COLOR[day["contributionLevel"]]])
    legend_y = hy + 7 * step + 6 * SCALE
    lx = hx + hm_w - 152 * SCALE
    d.text((lx, legend_y + 1 * SCALE), "Less", font=f_small, fill=t["label"])
    for i in range(5):
        x = lx + 30 * SCALE + i * step
        d.rounded_rectangle([x, legend_y, x + cell, legend_y + cell],
                            radius=2 * SCALE, fill=t["scale"][i])
    d.text((lx + 30 * SCALE + 5 * step + 5 * SCALE, legend_y + 1 * SCALE),
           "More", font=f_small, fill=t["label"])

    img.save(out_path, optimize=True)
    return total


def main():
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit(
            "GH_TOKEN is not set. In GitHub Actions this means the PROFILE_TOKEN "
            "secret is missing or empty:  gh secret set PROFILE_TOKEN -R SnegOwo/SnegOwo"
        )
    data = fetch(token)
    here = os.path.dirname(os.path.abspath(__file__))
    assets = os.path.join(here, "assets")
    os.makedirs(assets, exist_ok=True)
    total = render("dark", data, os.path.join(assets, "activity-dark.png"))
    render("light", data, os.path.join(assets, "activity-light.png"))
    print(f"total contributions: {total}  ({SCALE}x scale)")


if __name__ == "__main__":
    main()
