"""Check that no on-screen modules overlap and everything stays in the safe area.

For each content slide, renders the frame 0.5s before the slide ends (all elements in),
collects boxes of pills, node labels, bar rows and filled node circles (r >= 40),
and reports pairs closer than MIN_GAP px or boxes outside SAFE.
"""
import argparse
import json
import pathlib
import sys

from playwright.sync_api import sync_playwright

from sections import add_section_arg, paths

ROOT = pathlib.Path(__file__).resolve().parent
MIN_GAP = 12
SAFE = {"x1": 150, "y1": 90, "x2": 1840, "y2": 900}

JS = """() => {
  const out = {};
  document.querySelectorAll('.scene').forEach(sc => {
    if (getComputedStyle(sc).opacity === '0') return;
    const c = sc.querySelector('.content');
    if (!c) return;
    const boxes = [];
    // elements that have faded out again (data-out) are not on screen any more
    const op = e => { let o = 1; for (let n = e; n && n !== sc; n = n.parentNode) { const v = parseFloat(getComputedStyle(n).opacity); if (!isNaN(v)) o *= v; } return o; };
    const h = sc.querySelector('h1');
    if (h) { const r = h.getBoundingClientRect(); out[sc.id + ':title'] = {x1: r.left, y1: r.top, x2: r.right, y2: r.bottom}; }
    c.querySelectorAll('.pill, .nlabel, .barrow, .box').forEach(e => {
      if (op(e) < 0.05) return;
      const r = e.getBoundingClientRect();
      boxes.push({name: e.className.split(' ')[0] + ':' + e.textContent.trim().slice(0, 24), x1: r.left, y1: r.top, x2: r.right, y2: r.bottom});
    });
    c.querySelectorAll('circle').forEach(e => {
      if (+e.getAttribute('r') < 40 || e.getAttribute('fill') === 'none' || op(e) < 0.05) return;
      const r = e.getBoundingClientRect();
      boxes.push({name: `circle@${e.getAttribute('cx')},${e.getAttribute('cy')}`, x1: r.left, y1: r.top, x2: r.right, y2: r.bottom});
    });
    out[sc.id] = boxes;
  });
  return out;
}"""


# visible content boxes (pills, labels, filled circles, svg text) with their effective opacity, for one scene
VISIBLE_JS = """(id) => {
  const sc = document.getElementById(id), c = sc.querySelector('.content'), out = [];
  if (!c) return out;
  const op = e => { let o = 1; for (let n = e; n && n !== sc; n = n.parentNode) { const v = parseFloat(getComputedStyle(n).opacity); if (!isNaN(v)) o *= v; } return o; };
  c.querySelectorAll('.pill, .nlabel, .barrow, .box, circle, text').forEach(e => {
    if (e.tagName === 'circle' && (e.getAttribute('fill') === 'none' || +e.getAttribute('r') < 6)) return;
    if (op(e) < 0.05) return;
    const r = e.getBoundingClientRect();
    if (r.width && r.height) out.push({name: (e.className.baseVal !== undefined ? e.tagName : e.className.split(' ')[0]) + ':' + (e.textContent || '').trim().slice(0, 20), x1: r.left, y1: r.top, x2: r.right, y2: r.bottom});
  });
  return out;
}"""


def gap(a, b):
    dx = max(b["x1"] - a["x2"], a["x1"] - b["x2"])
    dy = max(b["y1"] - a["y2"], a["y1"] - b["y2"])
    return max(dx, dy)  # negative = overlap


def main(section, video):
    P = paths(section, video)
    tl = json.loads(P["timeline"].read_text(encoding="utf-8"))
    problems = 0
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        page.goto(P["html"].as_uri())
        page.evaluate("document.fonts.ready")
        dock = page.evaluate("window.ENGINE ? ENGINE.dockAt : {}")
        for s in tl["slides"]:
            if s["id"] == "S0":
                continue
            # while the big title is still at the top (until it has faded out), no content may sit under it
            if s["id"] in dock:
                d0 = dock[s["id"]]
                page.evaluate(f"renderAt({d0 - 0.05})")
                tb = page.evaluate(JS).get(s["id"] + ":title")
                for t_chk in (d0 - 0.05, d0 + 0.45):
                    page.evaluate(f"renderAt({t_chk})")
                    for b in page.evaluate(VISIBLE_JS, s["id"]):
                        if gap(tb, b) < MIN_GAP:
                            problems += 1
                            print(f"[{s['id']}] content under the top title at {t_chk:.2f}s: {b['name']} -> show it after the title docks")
            page.evaluate(f"renderAt({s['end'] - 0.5})")
            res = page.evaluate(JS)
            boxes = res.get(s["id"], [])
            tb = res.get(s["id"] + ":title")
            if tb and (tb["y1"] < 222 or tb["y2"] > 872 or tb["x2"] > 114):
                problems += 1
                print(f"[{s['id']}] docked title outside the strip left of the rail: ({tb['x1']:.0f},{tb['y1']:.0f})-({tb['x2']:.0f},{tb['y2']:.0f}) -> shorten the title")
            for i, a in enumerate(boxes):
                if a["x1"] < SAFE["x1"] or a["y1"] < SAFE["y1"] or a["x2"] > SAFE["x2"] or a["y2"] > SAFE["y2"]:
                    problems += 1
                    print(f"[{s['id']}] outside safe area: {a['name']} ({a['x1']:.0f},{a['y1']:.0f})-({a['x2']:.0f},{a['y2']:.0f})")
                for b in boxes[i + 1:]:
                    g = gap(a, b)
                    if g < MIN_GAP:
                        problems += 1
                        what = "OVERLAP" if g < 0 else f"gap {g:.0f}px"
                        print(f"[{s['id']}] {what}: {a['name']}  <->  {b['name']}")
            print(f"[{s['id']}] checked {len(boxes)} boxes")
        browser.close()
    if problems:
        sys.exit(f"{problems} layout problem(s)")
    print("OK: no overlaps, everything inside the safe area.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    add_section_arg(ap)
    a = ap.parse_args()
    main(a.section, a.video)
