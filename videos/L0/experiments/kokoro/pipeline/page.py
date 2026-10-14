"""Make the v2 page from the section's original page: same content, shared engine/assets via <base>, v2 timeline."""
import os
import re


def rel(target, start):
    return os.path.relpath(target, start).replace(os.sep, "/")


def build(P):
    src = P["src_html"].read_text(encoding="utf-8")
    m = re.search(rf'src="([^"]*timeline_{re.escape(P["section"])}\.js)"', src)
    if not m or "<head>" not in src:
        raise SystemExit(f"{P['src_html']}: expected <head> and a timeline_{P['section']}.js script")
    # with <base> every relative URL resolves against the original page's folder, so point the timeline at kokoro/slides/
    base = P["src_html"].parent
    html = src.replace("<head>", f'<head>\n<base href="{rel(base, P["html"].parent)}/">', 1)
    html = html.replace(m[0], f'src="{rel(P["timeline_js"], base)}"')
    P["html"].parent.mkdir(parents=True, exist_ok=True)
    P["html"].write_text(html, encoding="utf-8")
    print(P["html"])
