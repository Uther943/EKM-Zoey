"""Checks, preview frames and the full render for the v2 page, reusing check_subs / check_layout / render.py."""
import json
import subprocess
import sys

import check_layout
import render
from playwright.sync_api import sync_playwright
from tts import join_parts, split_parts

from . import ROOT, VIDEO


def check(P):
    # script text vs source, line lengths, en/zh splits (the original checker; the script is shared)
    subprocess.run([sys.executable, str(ROOT / "check_subs.py"), "--video", VIDEO, "--section", P["section"]], check=True, cwd=ROOT)
    script = json.loads(P["script"].read_text(encoding="utf-8"))
    tl = json.loads(P["timeline"].read_text(encoding="utf-8"))
    if [u["en"] for u in tl["units"]] != [join_parts(split_parts(u["en"])) for u in script["units"]]:
        sys.exit(f"{P['timeline'].name} is stale: re-run the tts step")
    print(f"OK: {P['timeline'].name} is in sync with the script.")
    check_layout.paths = lambda *_: P   # check_layout reads everything through paths()
    check_layout.main(P["id"], VIDEO)


def preview(P, times):
    P["preview"].mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser, page = render.open_page(p, P["html"])
        for t in times:
            page.evaluate(f"renderAt({t})")
            path = P["preview"] / f"{P['id']}_{t:06.2f}.png"
            page.screenshot(path=str(path))
            print(path)
        browser.close()


def full(P, workers):
    render.render(P, workers=workers)
