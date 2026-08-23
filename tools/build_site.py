#!/usr/bin/env python3
"""Build the AI-Learning-Hub explorer: modules/*.md -> site/index.html.

Mission Control design (chosen in the 2026-08-19 design round).
Stdlib only. Markdown is the source of truth; this generates the view.
Honest-data rule: every progress visual renders only what the repo's
data actually contains (modules/, ledger/recall-ledger.json, data/*.json).
`--check` validates the corpus and exits non-zero on any violation.
"""
import html
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODULES = ROOT / "modules"
LEDGER = ROOT / "ledger" / "recall-ledger.json"
DATA = ROOT / "data"
SITE = ROOT / "site"

LEVELS = ("basic", "intermediate", "advanced")
STATUSES = ("draft", "ready")
REQUIRED = ("id", "title", "topic", "level", "status", "time", "summary")


def parse_frontmatter(text: str, path: Path):
    if not text.startswith("---"):
        raise ValueError(f"{path}: missing frontmatter")
    try:
        _, fm, body = text.split("---", 2)
    except ValueError:
        raise ValueError(f"{path}: unterminated frontmatter") from None
    meta = {}
    for line in fm.strip().splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip()
    return meta, body.strip()


# --- minimal markdown -> html ------------------------------------------------

def inline_md(s: str) -> str:
    s = html.escape(s, quote=False)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", s)
    s = re.sub(
        r"\[([^\]]+)\]\((https?://[^)\s]+)\)",
        r'<a href="\2" target="_blank" rel="noopener">\1</a>', s)
    s = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r"\1", s)  # relative links: text only
    return s


IMG_LINE = re.compile(r'^!\[([^\]]*)\]\(([^)\s"]+)(?:\s+"([^"]*)")?\)\s*$')
VIDEO_EXT = (".mp4", ".webm")


def asset_url(src: str, topic: str) -> str:
    if src.startswith(("http://", "https://", "assets/")):
        return src
    return f"assets/{topic}/{src}"


def md_to_html(body: str, topic: str = "", asset_refs=None) -> str:
    out, i = [], 0
    lines = body.splitlines()
    while i < len(lines):
        line = lines[i]
        if line.lstrip().startswith("<svg"):
            svg = []
            while i < len(lines):
                svg.append(lines[i])
                if "</svg>" in lines[i]:
                    break
                i += 1
            i += 1
            cap = ""
            if i < len(lines) and lines[i].startswith("^ "):
                cap = f"<figcaption>{inline_md(lines[i][2:])}</figcaption>"
                i += 1
            out.append("<figure class='fig'>" + "\n".join(svg) + cap + "</figure>")
            continue
        m = IMG_LINE.match(line)
        if m:
            alt, src, cap = m.group(1), m.group(2), m.group(3) or ""
            if asset_refs is not None and not src.startswith(("http://", "https://")):
                asset_refs.append(src)
            url = asset_url(src, topic)
            if src.lower().endswith(VIDEO_EXT):
                tag = (f"<video src='{url}' controls muted loop playsinline "
                       f"aria-label='{html.escape(alt)}'></video>")
            else:
                tag = f"<img src='{url}' alt='{html.escape(alt)}' loading='lazy'>"
            capel = f"<figcaption>{inline_md(cap)}</figcaption>" if cap else ""
            out.append(f"<figure class='fig media'>{tag}{capel}</figure>")
            i += 1
            continue
        if line.startswith("```"):
            code = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                code.append(lines[i])
                i += 1
            i += 1
            out.append("<pre><code>" + html.escape("\n".join(code)) + "</code></pre>")
            continue
        if line.startswith("### "):
            out.append(f"<h4>{inline_md(line[4:])}</h4>")
        elif line.startswith("## "):
            out.append(f"<h3>{inline_md(line[3:])}</h3>")
        elif re.match(r"^\s*[-*] \[[ x]\] ", line):
            items = []
            while i < len(lines) and re.match(r"^\s*[-*] \[[ x]\] ", lines[i]):
                m = re.match(r"^\s*[-*] \[([ x])\] (.*)", lines[i])
                cls = "done" if m.group(1) == "x" else "todo"
                items.append(f"<li class='{cls}'><span class='ckbox'></span><span>{inline_md(m.group(2))}</span></li>")
                i += 1
            out.append("<ul class='checks'>" + "".join(items) + "</ul>")
            continue
        elif re.match(r"^\s*[-*] ", line):
            items = []
            while i < len(lines) and re.match(r"^\s*[-*] ", lines[i]):
                item = re.sub(r"^\s*[-*] ", "", lines[i])
                items.append(f"<li>{inline_md(item)}</li>")
                i += 1
            out.append("<ul>" + "".join(items) + "</ul>")
            continue
        elif re.match(r"^\s*\d+\. ", line):
            items = []
            while i < len(lines) and re.match(r"^\s*\d+\. ", lines[i]):
                item = re.sub(r"^\s*\d+\. ", "", lines[i])
                items.append(f"<li>{inline_md(item)}</li>")
                i += 1
            out.append("<ol>" + "".join(items) + "</ol>")
            continue
        elif line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append(lines[i])
                i += 1
            cells = [[c.strip() for c in r.strip("|").split("|")] for r in rows]
            if len(cells) >= 2 and all(re.match(r"^:?-+:?$", c) for c in cells[1]):
                head = "".join(f"<th>{inline_md(c)}</th>" for c in cells[0])
                body_rows = "".join(
                    "<tr>" + "".join(f"<td>{inline_md(c)}</td>" for c in r) + "</tr>"
                    for r in cells[2:])
                out.append(f"<div class='tblwrap'><table><thead><tr>{head}</tr></thead>"
                           f"<tbody>{body_rows}</tbody></table></div>")
            continue
        elif line.strip():
            out.append(f"<p>{inline_md(line)}</p>")
        i += 1
    return "\n".join(out)


# --- corpus loading & checking ------------------------------------------------

def load():
    errors = []
    topics = json.loads((MODULES / "topics.json").read_text())
    topic_ids = {t["id"] for t in topics}
    modules, seen = [], set()
    for path in sorted(MODULES.glob("*/*.md")):
        if path.name.startswith((".", "_")) or path.parent == MODULES:
            continue
        try:
            meta, body = parse_frontmatter(path.read_text(), path)
        except ValueError as e:
            errors.append(str(e))
            continue
        for key in REQUIRED:
            if not meta.get(key):
                errors.append(f"{path}: missing frontmatter key '{key}'")
        if meta.get("id") in seen:
            errors.append(f"{path}: duplicate id '{meta.get('id')}'")
        seen.add(meta.get("id"))
        if meta.get("topic") not in topic_ids:
            errors.append(f"{path}: unknown topic '{meta.get('topic')}'")
        if meta.get("topic") != path.parent.name:
            errors.append(f"{path}: topic '{meta.get('topic')}' != folder '{path.parent.name}'")
        if meta.get("level") not in LEVELS:
            errors.append(f"{path}: level must be one of {LEVELS}")
        if meta.get("status") not in STATUSES:
            errors.append(f"{path}: status must be one of {STATUSES}")
        refs = []
        rendered = md_to_html(body, topic=path.parent.name, asset_refs=refs)
        assets_dir = path.parent / "assets"
        for r in refs:
            if not r.startswith("assets/") and not (assets_dir / r).exists():
                errors.append(f"{path}: referenced asset '{r}' not found in {assets_dir}")
        if meta.get("hero") and not (assets_dir / meta["hero"]).exists():
            errors.append(f"{path}: hero asset '{meta['hero']}' not found in {assets_dir}")
        modules.append({**meta, "html": rendered,
                        "text": re.sub(r"\s+", " ", body).lower()})
    ledger = json.loads(LEDGER.read_text()) if LEDGER.exists() else {"passes": []}
    for entry in ledger.get("passes", []):
        if entry.get("module") not in seen:
            errors.append(f"ledger: pass references unknown module '{entry.get('module')}'")
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", entry.get("date", "")):
            errors.append(f"ledger: entry for '{entry.get('module')}' has invalid date")
        if entry.get("result") not in ("pass", "fail"):
            errors.append(f"ledger: entry for '{entry.get('module')}' result must be pass|fail")
    hub = json.loads((DATA / "hub.json").read_text()) if (DATA / "hub.json").exists() else {}
    skills = json.loads((DATA / "skills.json").read_text()) if (DATA / "skills.json").exists() else {"clusters": []}
    for c in skills.get("clusters", []):
        if not (0 <= c.get("score", -1) <= 1):
            errors.append(f"skills.json: cluster '{c.get('id')}' score must be 0..1")
    manifest_path = DATA / "assets-manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        for a in manifest.get("assets", []):
            f = ROOT / a.get("file", "")
            if not f.exists():
                errors.append(f"assets-manifest: file '{a.get('file')}' does not exist")
            for key in ("file", "kind", "prompt", "model", "date"):
                if not a.get(key):
                    errors.append(f"assets-manifest: entry '{a.get('file', '?')}' missing '{key}'")
    return topics, modules, ledger, hub, skills, errors


TEMPLATE = """<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI-Learning-Hub</title>
<link rel="icon" type="image/svg+xml" href="favicon.svg">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<style>
:root{
  --bg:#eceff3; --panel:#ffffff; --sunk:#f6f8fa; --grid:#e3e9ef; --line:#d6dde5;
  --ink:#1a2028; --mid:#4d5a68; --muted:#6b7a8c; --faint:#9aa8b8;
  --rail:#10151c; --rail-line:#2a323d; --rail-dim:#5d6b7c; --rail-lit:#e8edf4;
  --acc:#f97316; --acc-ink:#c2410c; --acc-soft:#fff7ed; --acc-line:#fed7aa; --acc-hi:#fdba74;
  --basic:#15803d; --basic-soft:#dcfce7; --inter:#b45309; --inter-soft:#fef3c7;
  --adv:#7c3aed; --adv-soft:#ede9fe;
  --s1:#ea580c; --s2:#2563eb; /* chart series — validated pair, light surface */
  --mono:'IBM Plex Mono',ui-monospace,Menlo,Consolas,monospace;
  --sans:'IBM Plex Sans',system-ui,-apple-system,sans-serif;
  --shadow:0 1px 2px rgba(26,32,40,.05),0 6px 18px rgba(26,32,40,.06);
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --bg:#0d1117; --panel:#161c24; --sunk:#10151c; --grid:#232c37; --line:#2a3542;
  --ink:#e8edf4; --mid:#b9c4d1; --muted:#8b99aa; --faint:#5d6b7c;
  --rail:#0a0e13; --rail-line:#232c37;
  --acc:#fb923c; --acc-ink:#fdba74; --acc-soft:#2a1a0c; --acc-line:#7c3a12; --acc-hi:#fdba74;
  --basic:#4ade80; --basic-soft:#0d2818; --inter:#fbbf24; --inter-soft:#2a2108;
  --adv:#a78bfa; --adv-soft:#1e1633;
  --s1:#e06a10; --s2:#4278d6; /* chart series — validated pair, dark surface */
  --shadow:0 1px 2px rgba(0,0,0,.4),0 8px 22px rgba(0,0,0,.35);}}
:root[data-theme="dark"]{
  --bg:#0d1117; --panel:#161c24; --sunk:#10151c; --grid:#232c37; --line:#2a3542;
  --ink:#e8edf4; --mid:#b9c4d1; --muted:#8b99aa; --faint:#5d6b7c;
  --rail:#0a0e13; --rail-line:#232c37;
  --acc:#fb923c; --acc-ink:#fdba74; --acc-soft:#2a1a0c; --acc-line:#7c3a12; --acc-hi:#fdba74;
  --basic:#4ade80; --basic-soft:#0d2818; --inter:#fbbf24; --inter-soft:#2a2108;
  --adv:#a78bfa; --adv-soft:#1e1633;
  --s1:#e06a10; --s2:#4278d6;
  --shadow:0 1px 2px rgba(0,0,0,.4),0 8px 22px rgba(0,0,0,.35);}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 var(--sans);display:flex;min-height:100vh}
button{font:inherit;color:inherit;background:none;border:none;cursor:pointer;padding:0;text-align:left}
button:focus-visible,input:focus-visible{outline:2px solid var(--acc);outline-offset:2px}
code{font-family:var(--mono);font-size:.85em;background:var(--sunk);border:1px solid var(--grid);border-radius:4px;padding:.05em .35em}
pre{background:var(--sunk);border:1px solid var(--grid);border-radius:8px;padding:12px 14px;overflow-x:auto}
pre code{background:none;border:none;padding:0}
a{color:var(--acc-ink)}
.klabel{font-family:var(--mono);font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--muted)}

nav.rail{width:60px;flex-shrink:0;background:var(--rail);display:flex;flex-direction:column;align-items:center;gap:8px;padding:18px 0;position:sticky;top:0;height:100vh}
nav.rail .logo{margin-bottom:6px}
nav.rail .sep{width:26px;height:1px;background:var(--rail-line);margin:4px 0}
nav.rail button{width:40px;height:40px;border-radius:9px;display:flex;align-items:center;justify-content:center}
nav.rail button svg{stroke:var(--rail-dim)}
nav.rail button[aria-pressed="true"]{background:#f9731622}
nav.rail button[aria-pressed="true"] svg{stroke:var(--acc-hi, #fdba74)}
nav.rail button:hover svg{stroke:var(--rail-lit)}
nav.rail .theme{margin-top:auto}

main{flex:1;padding:22px 30px 70px;max-width:1200px}
header.top{display:flex;align-items:center;gap:14px;flex-wrap:wrap;margin-bottom:16px}
header.top .brand{font-family:var(--mono);font-weight:600;font-size:15px;letter-spacing:.06em}
header.top .brand b{color:var(--acc);font-weight:600}
header.top .chip{font-family:var(--mono);font-size:11px;color:var(--muted);background:var(--panel);border:1px solid var(--line);border-radius:4px;padding:4px 10px}
header.top .doctrine{margin-left:auto;font-family:var(--mono);font-size:11px;color:var(--muted)}

.view{display:none}.view.active{display:block}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-bottom:14px}
.kpi{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:14px 16px;box-shadow:var(--shadow)}
.kpi b{font-family:var(--mono);font-size:26px;font-weight:600;display:block;line-height:1.1}
.kpi b small{color:var(--faint);font-size:15px;font-weight:400}
.kpi span{font-size:11px;color:var(--muted);letter-spacing:.05em;text-transform:uppercase}
.kpi.dark{background:var(--rail);border-color:var(--rail)}
.kpi.dark b{font-size:15px;color:var(--acc-hi, #fdba74);font-weight:500;padding-top:5px}
.kpi.dark span{color:#8b99aa}

.grid3{display:grid;grid-template-columns:1.15fr 1fr 1.25fr;gap:12px;align-items:stretch;margin-bottom:14px}
@media(max-width:1020px){.grid3{grid-template-columns:1fr}}
.card{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:16px 18px;box-shadow:var(--shadow);display:flex;flex-direction:column;gap:10px}
.card .foot{font-size:11px;color:var(--muted);line-height:1.5}
.heat{display:grid;grid-template-columns:repeat(12,minmax(0,1fr));gap:4px}
.heat i{aspect-ratio:1;border-radius:2px;background:var(--grid)}
.heat i.pass{background:var(--acc-hi, #fdba74)}
.heat i.due{background:var(--acc-soft);border:1.5px dashed var(--acc-hi, #fdba74)}
.callout{margin-top:auto;background:var(--acc-soft);border:1px solid var(--acc-line);border-radius:6px;padding:10px 12px;display:flex;gap:10px;align-items:center;font-size:12px;color:var(--acc-ink);line-height:1.45}
.ladders{display:flex;flex-direction:column;gap:7px;font-size:12.5px}
.ladders .row{display:grid;grid-template-columns:150px 1fr;gap:10px;align-items:center}
.ladders .row .nm{color:var(--mid)}
.ladders .row.hot .nm{color:var(--ink);font-weight:500}
.ladders .segs{display:flex;gap:3px}
.ladders .segs i{flex:1;height:9px;border-radius:2px;background:var(--grid)}
.ladders .segs i.present{background:var(--acc-soft);border:1.5px solid var(--acc-hi, #fdba74)}
.ladders .segs i.passed{background:var(--acc)}
.queue{display:flex;flex-direction:column;gap:8px}
.qhead,.qrow{display:grid;grid-template-columns:2.4fr 1.2fr .7fr .6fr 1fr;gap:10px;align-items:center}
.qhead{font-family:var(--mono);font-size:10.5px;color:var(--faint);text-transform:uppercase;letter-spacing:.05em;border-bottom:1px solid var(--grid);padding-bottom:6px}
.qrow{font-size:13px}
.qrow .t{font-weight:500;cursor:pointer}
.qrow .t:hover{color:var(--acc-ink)}
.qrow .mono{font-family:var(--mono);font-size:11px}
.st-building{color:var(--acc-ink)}.st-passed{color:var(--basic)}.st-queued{color:var(--faint)}

.bar{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:16px}
.fchip{font-family:var(--mono);font-size:12px;background:var(--panel);color:var(--muted);border:1px solid var(--line);border-radius:999px;padding:6px 14px}
.fchip[aria-pressed="true"]{background:var(--rail);color:#fdba74;border-color:var(--rail)}
#q{flex:1 1 200px;min-width:150px;font:13px var(--mono);color:var(--ink);background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:8px 12px}
section.topic{margin-bottom:26px}
.thead{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap}
.thead h2{font-family:var(--mono);font-size:15px;letter-spacing:.02em;margin:0}
.thead .n{font-family:var(--mono);font-size:10.5px;color:var(--faint)}
.tdesc{color:var(--muted);font-size:12.5px;max-width:86ch;margin:4px 0 10px}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px}
.mcard{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:14px 16px;box-shadow:var(--shadow);display:flex;flex-direction:column;gap:8px;font:inherit;color:inherit}
.mcard:hover{border-color:var(--acc)}
.mcard.building{border-color:var(--acc);box-shadow:0 2px 10px rgba(249,115,22,.12)}
.mcard img.hero{width:100%;max-height:140px;object-fit:cover;border-radius:6px;border:1px solid var(--grid)}
.mcard h3{margin:0;font-size:14.5px;font-weight:600;line-height:1.35}
.mcard p{margin:0;font-size:12px;color:var(--muted);line-height:1.5}
.mcard .eli5{margin:0;font-size:11.5px;color:var(--ink);background:var(--acc-soft);border:1px solid var(--acc-line);border-radius:6px;padding:7px 9px;line-height:1.5}
.mcard .eli5 span{font-family:var(--mono);font-size:9px;color:var(--acc-ink);letter-spacing:.6px;margin-right:7px}
.mcard .meta{display:flex;gap:6px;flex-wrap:wrap;align-items:center}
.lv{font-family:var(--mono);font-size:10px;font-weight:600;letter-spacing:.05em;border-radius:4px;padding:2px 8px;text-transform:uppercase}
.lv.basic{background:var(--basic-soft);color:var(--basic)}
.lv.intermediate{background:var(--inter-soft);color:var(--inter)}
.lv.advanced{background:var(--adv-soft);color:var(--adv)}
.tm,.stc{font-family:var(--mono);font-size:10px;border-radius:4px;padding:2px 8px;background:var(--sunk);color:var(--mid);border:1px solid var(--grid)}
.stc.building{background:var(--acc-soft);border-color:var(--acc-line);color:var(--acc-ink)}
.recall{font-family:var(--mono);font-size:10px;border-radius:4px;padding:2px 8px;margin-left:auto}
.recall.pass{background:var(--basic-soft);color:var(--basic)}
.recall.pending{background:var(--sunk);color:var(--faint);border:1px solid var(--grid)}
.empty{color:var(--faint);font-size:12.5px;font-style:italic;border:1px dashed var(--line);border-radius:8px;padding:11px 14px}

.ltable{display:flex;flex-direction:column;gap:8px}
.lhead,.lrow{display:grid;grid-template-columns:1fr 2.2fr 1.2fr .8fr 1.6fr;gap:10px}
.lhead{font-family:var(--mono);font-size:10.5px;color:var(--faint);text-transform:uppercase;letter-spacing:.05em;border-bottom:1px solid var(--grid);padding-bottom:6px}
.lrow{font-size:13px;align-items:center}
.lempty{display:flex;flex-direction:column;align-items:center;gap:10px;padding:34px 20px;text-align:center}
.lempty .big{font-size:14px;font-weight:500;color:var(--mid)}
.lempty .why{font-size:12.5px;color:var(--faint);max-width:54ch;line-height:1.6}
.rules{background:var(--rail);border-radius:8px;padding:16px 18px;color:#b9c4d1;display:flex;flex-direction:column;gap:9px}
.rules .klabel{color:#fdba74}
.rules .r{display:flex;gap:9px;font-size:12.5px;line-height:1.55}
.rules .r b{font-family:var(--mono);color:#fdba74;font-weight:500}
.rules code{background:#1a222c;border-color:#2a3542;color:#9fb3c8}

/* no top padding here: the scrollport's content edge is where the sticky progress bar
   parks, and any padding would leave a strip of text scrolling above it */
#reader{position:fixed;inset:0;background:rgba(10,14,19,.45);display:none;align-items:flex-start;justify-content:center;overflow-y:auto;overscroll-behavior:contain;z-index:20;padding:0 14px}
#reader.open{display:flex}
#reader .paper{--pad-x:34px;--pad-y:28px;--radius:12px;
  background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);box-shadow:var(--shadow);
  max-width:860px;width:100%;padding:var(--pad-y) var(--pad-x) 52px;margin:4vh 0 6vh}
/* slim reader chrome: progress bar + close, parked on the paper's top edge.
   Opaque so the article scrolls under it instead of colliding with it. */
#reader .rtop{position:sticky;top:0;z-index:4;display:flex;flex-direction:column;
  background:var(--panel);border-radius:var(--radius) var(--radius) 0 0;
  margin:calc(var(--pad-y) * -1) calc(var(--pad-x) * -1) 12px;padding:0 var(--pad-x) 10px}
#reader.scrolled .rtop{border-bottom:1px solid var(--grid);box-shadow:0 10px 16px -14px rgba(10,14,19,.55)}
/* reading progress — fills as #reader (the scroll container) scrolls */
#reader .rprog{height:3px;overflow:hidden;background:var(--grid);
  border-radius:var(--radius) var(--radius) 0 0;margin:0 calc(var(--pad-x) * -1) 10px}
#reader .rprog i{display:block;height:100%;width:0;background:var(--acc);border-radius:0 2px 2px 0;transition:width .1s linear}
@media(prefers-reduced-motion:reduce){#reader .rprog i{transition:none}}
#reader .rbar{display:flex;align-items:center;justify-content:space-between;gap:14px}
#reader .rid{font:11px var(--mono);letter-spacing:.1em;text-transform:uppercase;color:var(--faint);
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#reader h2{font-size:22px;letter-spacing:-.01em;margin:.4em 0 .5em;line-height:1.3}
#reader #rbody{counter-reset:sec}
#reader h3{counter-increment:sec;font-family:var(--mono);font-size:12px;letter-spacing:.1em;text-transform:uppercase;color:var(--acc-ink);margin:2.1em 0 .7em;padding-bottom:6px;border-bottom:1px solid var(--grid)}
#reader h3::before{content:counter(sec,decimal-leading-zero);display:inline-block;margin-right:9px;padding:2px 6px;
  border-radius:4px;background:color-mix(in srgb,var(--acc) 14%,transparent);color:var(--acc-ink);letter-spacing:.06em}
#reader h4{font-family:var(--mono);font-size:13px;margin:1.4em 0 .3em}
#reader p{color:var(--mid);font-size:14px;line-height:1.7}
/* Takeaway line (style spec, Move 16): a bolded sentence alone in its own paragraph.
   Pure CSS cannot select it: `p:has(> b:only-child)` over-fires, because :only-child
   counts element siblings only — an ordinary paragraph with prose *around* a bold run
   matches it too (verified in Chromium). So the reader tags the genuinely standalone
   lines with .takeaway (see markTakeaways) and the callout keys off that. */
#reader p.takeaway{margin:1.6em 0;padding:13px 18px;font-size:15.5px;line-height:1.62;color:var(--ink);
  border-left:3px solid var(--acc);border-radius:0 8px 8px 0;
  background:color-mix(in srgb,var(--acc) 9%,transparent)}
#reader p.takeaway b,#reader p.takeaway strong{font-weight:600;color:var(--ink)}
#reader pre{font-family:var(--mono);font-size:12.5px;line-height:1.6;padding:15px 18px;margin:1.2em 0;
  border-top:2px solid var(--acc-line);border-radius:8px;overflow-x:auto}
#reader pre code{font-size:inherit;line-height:inherit;overflow-wrap:normal}
/* long paths/identifiers in inline code must break rather than push the paper sideways */
#reader code{overflow-wrap:anywhere}
#reader li{color:var(--mid);font-size:13.5px;line-height:1.65;margin:.25em 0}
#reader .tblwrap{overflow-x:auto;border:1px solid var(--grid);border-radius:8px;margin:.6em 0}
#reader table{border-collapse:collapse;width:100%;font-size:13px}
#reader th,#reader td{text-align:left;padding:7px 11px;border-top:1px solid var(--grid);vertical-align:top}
#reader thead th{border-top:none;font-family:var(--mono);font-size:10.5px;color:var(--faint);text-transform:uppercase;letter-spacing:.05em}
#reader ul.checks{list-style:none;padding-left:0}
#reader ul.checks li{display:flex;gap:9px;align-items:flex-start}
#reader .ckbox{width:14px;height:14px;border:1.5px solid var(--faint);border-radius:4px;flex-shrink:0;margin-top:4px}
#reader ul.checks li.done .ckbox{background:var(--basic);border-color:var(--basic)}
#reader figure.fig{margin:1.6em 0;background:var(--sunk);border:1px solid var(--grid);border-radius:8px;padding:18px 20px 16px;overflow-x:auto}
#reader figure.fig svg{display:block;width:100%;height:auto}
#reader figure.fig.media{padding:10px 10px 8px}
#reader figure.fig img,#reader figure.fig video{display:block;max-width:100%;border-radius:6px}
#reader figcaption{font:11px/1.6 var(--mono);color:var(--muted);letter-spacing:.03em;
  margin-top:16px;padding-top:11px;border-top:1px solid var(--grid)}
#reader figure.fig.media figcaption{margin:12px 4px 2px;padding-top:10px}
/* in the sticky chrome, so a long module can always be closed — on mobile there is no backdrop to tap */
#reader .rbtns{display:flex;gap:8px;flex-shrink:0}
#close{flex-shrink:0;font:13px var(--mono);background:var(--sunk);
  border:1px solid var(--grid);border-radius:7px;padding:5px 12px}
#close:hover{border-color:var(--acc);color:var(--acc-ink)}
#ask{flex-shrink:0;font:13px var(--mono);color:var(--acc-ink);background:var(--acc-soft);
  border:1px solid var(--acc-line);border-radius:7px;padding:5px 12px}
#ask:hover{border-color:var(--acc)}
@media(max-width:620px){#ask{font-size:12px;padding:5px 9px}}
@media(max-width:620px){
  #reader{padding:0}
  #reader .paper{--pad-x:18px;--pad-y:18px;--radius:0;border-width:0;min-height:100%;margin:0;padding-bottom:40px}
  #reader h2{font-size:19px}
  #reader p.takeaway{padding:12px 14px;font-size:15px}
  #reader figure.fig{padding:14px 12px 12px}
}
footer{margin-top:44px;border-top:1px solid var(--line);padding-top:14px;font:11.5px var(--mono);color:var(--faint);display:flex;gap:14px;flex-wrap:wrap;justify-content:space-between}
</style>
<body>
<nav class="rail" aria-label="views">
  <span class="logo" title="AI-Learning-Hub"><img src="logo-dark.svg" width="30" height="30" alt="AI-Learning-Hub"></span>
  <span class="sep"></span>
  <button data-view="dash" aria-pressed="true" title="Dashboard"><svg width="21" height="21" viewBox="0 0 24 24" fill="none" stroke-width="1.8"><rect x="3" y="3" width="8" height="8" rx="1.5"></rect><rect x="13" y="3" width="8" height="8" rx="1.5"></rect><rect x="3" y="13" width="8" height="8" rx="1.5"></rect><rect x="13" y="13" width="8" height="8" rx="1.5"></rect></svg></button>
  <button data-view="mods" aria-pressed="false" title="Modules"><svg width="21" height="21" viewBox="0 0 24 24" fill="none" stroke-width="1.8"><path d="M12 3 L20 7.5 V16.5 L12 21 L4 16.5 V7.5 Z"></path><path d="M12 12 L20 7.5 M12 12 V21 M12 12 L4 7.5"></path></svg></button>
  <button data-view="ledger" aria-pressed="false" title="Recall ledger"><svg width="21" height="21" viewBox="0 0 24 24" fill="none" stroke-width="1.8"><rect x="4" y="5" width="16" height="15" rx="1.5"></rect><path d="M4 9.5 H20 M8 3 V6.5 M16 3 V6.5"></path></svg></button>
  <button class="theme" id="theme" title="Theme"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke-width="1.8"><circle cx="12" cy="12" r="8"></circle><path d="M12 4 A8 8 0 0 1 12 20 Z" fill="currentColor" stroke="none" opacity=".55"></path></svg></button>
</nav>
<main>
  <header class="top">
    <span class="brand">AI-LEARNING-HUB <b>/ CONTROL</b></span>
    <span class="chip" id="phase-chip"></span>
    <span class="doctrine" id="doctrine"></span>
  </header>

  <div class="view active" id="view-dash">
    <div class="kpis" id="kpis"></div>
    <div class="grid3">
      <div class="card">
        <div class="klabel">Skill coverage — clusters of the 35-skill matrix</div>
        <svg id="radar" width="100%" height="256" viewBox="0 0 320 256"></svg>
        <div class="foot" id="radar-foot"></div>
      </div>
      <div class="card">
        <div class="klabel">Recall heat — last 12 weeks</div>
        <div class="heat" id="heat"></div>
        <div class="foot">one cell per week · fills with dated passes · dashed = this week, no pass yet</div>
        <div class="callout" id="next-callout"></div>
      </div>
      <div class="card">
        <div class="klabel">Topic ladders · basic / inter / adv</div>
        <div class="ladders" id="ladders"></div>
      </div>
    </div>
    <div class="card">
      <div class="klabel">Module queue</div>
      <div class="queue" id="queue"></div>
    </div>
  </div>

  <div class="view" id="view-mods">
    <div class="bar">
      <button class="fchip" data-lv="all" aria-pressed="true">ALL</button>
      <button class="fchip" data-lv="basic" aria-pressed="false">BASIC</button>
      <button class="fchip" data-lv="intermediate" aria-pressed="false">INTERMEDIATE</button>
      <button class="fchip" data-lv="advanced" aria-pressed="false">ADVANCED</button>
      <input id="q" type="search" placeholder="search modules…" autocomplete="off">
    </div>
    <div id="topics"></div>
  </div>

  <div class="view" id="view-ledger">
    <div class="grid3" style="grid-template-columns:2.2fr 1fr">
      <div class="card">
        <div class="lhead"><span>date</span><span>module</span><span>topic</span><span>result</span><span>notes</span></div>
        <div class="ltable" id="ledger-rows"></div>
      </div>
      <div class="rules">
        <div class="klabel">Rules of the ledger</div>
        <div class="r"><b>01</b><span>From memory, no notes — the boss fight is closed-book.</span></div>
        <div class="r"><b>02</b><span>A pass is a dated commit to <code>ledger/recall-ledger.json</code>; this page renders only what that file contains.</span></div>
        <div class="r"><b>03</b><span>A fail is logged too, with notes — it schedules a retry, never a shortcut.</span></div>
        <div class="r"><b>04</b><span>No pass, no done. The module stays open whatever else shipped.</span></div>
      </div>
    </div>
  </div>

  <footer>
    <span>faisalmahdy/AI-Learning-Hub · Mission Control</span>
    <span>markdown is the source of truth — this page is generated by tools/build_site.py</span>
  </footer>
</main>
<div id="reader" role="dialog" aria-modal="true"><div class="paper"><div class="rtop"><div class="rprog" aria-hidden="true"><i id="rprog"></i></div><div class="rbar"><span class="rid" id="rid"></span><span class="rbtns"><button id="ask" title="Open claude.ai with this module preloaded — uses your own Claude subscription">✳ ASK CLAUDE</button><button id="close">✕ CLOSE</button></span></div></div><div id="rbody"></div></div></div>
<script id="data" type="application/json">__DATA__</script>
<script>
"use strict";
const D=JSON.parse(document.getElementById("data").textContent);
const passes={};(D.ledger.passes||[]).forEach(p=>{if(p.result==="pass")(passes[p.module]=passes[p.module]||[]).push(p.date)});
const passCount=(D.ledger.passes||[]).filter(p=>p.result==="pass").length;
const topicsById={};D.topics.forEach(t=>topicsById[t.id]=t);
D.topics.sort((a,b)=>a.order-b.order);
const LV=["basic","intermediate","advanced"];

function state(m){
  if(passes[m.id]) return "passed";
  return "building";
}
const firstOpen=D.modules.find(m=>!passes[m.id]);

/* header */
const hub=D.hub||{};
document.getElementById("phase-chip").textContent=hub.phase?("phase "+hub.phase.number+" · "+hub.phase.name.toLowerCase()+" · weeks "+hub.phase.weeks):"";
document.getElementById("doctrine").textContent=hub.doctrine_line?("doctrine: "+hub.doctrine_line):"";

/* KPIs */
const started=new Set(D.modules.map(m=>m.topic)).size;
document.getElementById("kpis").innerHTML=
 `<div class="kpi"><b>${D.modules.length}</b><span>module${D.modules.length===1?"":"s"} in flight</span></div>`+
 `<div class="kpi"><b style="color:var(--acc-ink)">${passCount}</b><span>recall passes</span></div>`+
 `<div class="kpi"><b>${started}<small>/${D.topics.length}</small></b><span>topics started</span></div>`+
 (firstOpen?`<div class="kpi dark"><b>${firstOpen.id}</b><span>next action · ${passes[firstOpen.id]?"review":"resume build"}</span></div>`:`<div class="kpi dark"><b>all clear</b><span>next action</span></div>`);

/* radar */
(function(){
  const cs=(D.skills.clusters||[]);const svg=document.getElementById("radar");
  if(!cs.length){svg.outerHTML="<div class='empty'>no skills data</div>";return}
  const cx=160,cy=128,R=102,n=cs.length;
  const axis=i=>{const a=-Math.PI/2+i*2*Math.PI/n;return [cx+R*Math.cos(a),cy+R*Math.sin(a)]};
  const at=(i,t)=>{const [x,y]=axis(i);return [cx+(x-cx)*t,cy+(y-cy)*t]};
  let g="";
  [1,.667,.333].forEach(t=>{g+=`<polygon points="${cs.map((_,i)=>at(i,t).map(v=>v.toFixed(1)).join(",")).join(" ")}" fill="none" stroke="var(--grid)"/>`});
  cs.forEach((_,i)=>{const [x,y]=axis(i);g+=`<line x1="${cx}" y1="${cy}" x2="${x.toFixed(1)}" y2="${y.toFixed(1)}" stroke="var(--grid)"/>`});
  g+=`<polygon points="${cs.map((c,i)=>at(i,Math.max(c.score,.03)).map(v=>v.toFixed(1)).join(",")).join(" ")}" fill="var(--acc)" fill-opacity=".16" stroke="var(--acc)" stroke-width="2"/>`;
  cs.forEach((c,i)=>{const [x,y]=at(i,1.16);g+=`<text x="${x.toFixed(1)}" y="${(y+3).toFixed(1)}" font-family="var(--mono)" font-size="10" fill="var(--mid)" text-anchor="middle">${c.label}</text>`});
  svg.innerHTML=g;
  document.getElementById("radar-foot").textContent=(D.skills.scale_note||"")+" · source: docs/skills-matrix.md";
})();

/* heat: last 12 weeks from today */
(function(){
  const el=document.getElementById("heat");const now=new Date();
  const week=d=>{const x=new Date(d);x.setHours(0,0,0,0);x.setDate(x.getDate()-((x.getDay()+6)%7));return x.getTime()};
  const weeks=[];for(let i=11;i>=0;i--){weeks.push(week(new Date(now-i*7*864e5)))}
  const byWeek={};(D.ledger.passes||[]).forEach(p=>{if(p.result!=="pass")return;const w=week(p.date+"T12:00:00");byWeek[w]=(byWeek[w]||0)+1});
  el.innerHTML=weeks.map((w,i)=>{
    if(byWeek[w])return '<i class="pass" title="'+byWeek[w]+' pass(es)"></i>';
    if(i===11)return '<i class="due" title="this week — no pass yet"></i>';
    return '<i></i>';
  }).join("");
  const co=document.getElementById("next-callout");
  co.innerHTML='<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="flex-shrink:0"><path d="M12 3 L14.5 9 L21 9.5 L16 13.8 L17.8 20.5 L12 16.8 L6.2 20.5 L8 13.8 L3 9.5 L9.5 9 Z"></path></svg><span>'+
    (firstOpen?('<b>Next flag:</b> finish <b>'+firstOpen.title+'</b>, then take its boss fight.'):'<b>All modules passed.</b> Author the next one.')+'</span>';
})();

/* ladders */
document.getElementById("ladders").innerHTML=D.topics.map(t=>{
  const ms=D.modules.filter(m=>m.topic===t.id);
  const segs=LV.map(lv=>{
    const has=ms.some(m=>m.level===lv);
    const done=ms.some(m=>m.level===lv&&passes[m.id]);
    return `<i class="${done?"passed":has?"present":""}" title="${lv}"></i>`;
  }).join("");
  return `<div class="row ${ms.length?"hot":""}"><span class="nm">${t.name}</span><span class="segs">${segs}</span></div>`;
}).join("");

/* queue */
document.getElementById("queue").innerHTML=
 '<div class="qhead"><span>module</span><span>topic</span><span>level</span><span>est.</span><span>state</span></div>'+
 D.modules.map(m=>{
   const s=passes[m.id]?["st-passed","✓ PASSED "+passes[m.id].slice(-1)[0]]:(m===firstOpen?["st-building","● BUILDING"]:["st-queued","○ QUEUED"]);
   return `<div class="qrow"><span class="t" data-id="${m.id}">${m.title}</span><span style="color:var(--mid)">${(topicsById[m.topic]||{}).name||m.topic}</span><span class="mono lv ${m.level}" style="justify-self:start">${m.level.slice(0,5).toUpperCase()}</span><span style="color:var(--mid)">${m.time}</span><span class="mono ${s[0]}">${s[1]}</span></div>`;
 }).join("");

/* modules view */
let lv="all",q="";
function card(m){
 const st=passes[m.id]?'<span class="recall pass">RECALL ✓ '+passes[m.id].slice(-1)[0]+'</span>':'<span class="recall pending">RECALL PENDING</span>';
 const building=(m===firstOpen);
 const hero=m.hero?`<img class="hero" src="assets/${m.topic}/${m.hero}" alt="" loading="lazy">`:"";
 return `<button class="mcard ${building?"building":""}" data-id="${m.id}">${hero}<h3>${m.title}</h3><p>${m.summary}</p>`+
  (m.eli5?`<p class="eli5"><span>ELI5</span>${m.eli5}</p>`:"")+
  `<div class="meta"><span class="lv ${m.level}">${m.level}</span><span class="tm">${m.time.toUpperCase()}</span>`+
  (building?'<span class="stc building">● BUILDING</span>':'')+st+`</div></button>`;
}
function render(){
 const root=document.getElementById("topics");root.innerHTML="";
 D.topics.forEach(t=>{
  const ms=D.modules.filter(m=>m.topic===t.id)
   .filter(m=>lv==="all"||m.level===lv)
   .filter(m=>!q||m.title.toLowerCase().includes(q)||m.text.includes(q)||m.summary.toLowerCase().includes(q));
  if(q&&!ms.length)return;
  const sec=document.createElement("section");sec.className="topic";
  sec.innerHTML=`<div class="thead"><h2>${t.order}. ${t.name.toUpperCase()}</h2><span class="n">${ms.length} MODULE${ms.length===1?"":"S"}</span></div><p class="tdesc">${t.description}</p>`+
   (ms.length?`<div class="cards">${ms.map(card).join("")}</div>`:`<div class="empty">No modules at this filter yet — planned in CURRICULUM.md.</div>`);
  root.appendChild(sec);
 });
 root.querySelectorAll(".mcard").forEach(c=>c.addEventListener("click",()=>open(c.dataset.id)));
}
render();

/* ledger view */
(function(){
  const rows=document.getElementById("ledger-rows");const entries=D.ledger.passes||[];
  if(!entries.length){
    rows.innerHTML=`<div class="lempty">
      <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="var(--faint)" stroke-width="1.4"><rect x="4" y="5" width="16" height="15" rx="1.5"></rect><path d="M4 9.5 H20 M8 3 V6.5 M16 3 V6.5"></path><path d="M9 14 L11 16 L15 12" stroke="var(--acc)" stroke-width="1.8"></path></svg>
      <div class="big">No entries yet — the ledger starts empty on purpose.</div>
      <div class="why">The 2026-08 scan found recall machinery built across the labs but never run: zero dated passes. This page exists so that stops being true.${firstOpen?" First candidate: the boss fight at the end of <b>"+firstOpen.id+"</b>.":""}</div>
    </div>`;
    return;
  }
  rows.innerHTML=entries.slice().reverse().map(e=>`<div class="lrow"><span class="mono">${e.date}</span><span>${e.module}</span><span style="color:var(--mid)">${(topicsById[(D.modules.find(m=>m.id===e.module)||{}).topic]||{}).name||""}</span><span class="mono ${e.result==="pass"?"st-passed":"st-building"}">${e.result.toUpperCase()}</span><span style="color:var(--muted);font-size:12px">${e.notes||""}</span></div>`).join("");
})();

/* reader */
const rdr=document.getElementById("reader"),rbody=document.getElementById("rbody"),rprog=document.getElementById("rprog");
let curMod=null;
/* reading progress: #reader is the scroll container, the bar rides the paper's top edge */
function progress(){
 const max=rdr.scrollHeight-rdr.clientHeight;
 rprog.style.width=(max>4?Math.min(100,Math.max(0,rdr.scrollTop/max*100)):0).toFixed(2)+"%";
 rdr.classList.toggle("scrolled",rdr.scrollTop>6);
}
rdr.addEventListener("scroll",progress,{passive:true});
addEventListener("resize",progress);
/* a takeaway line is a bolded sentence alone in its own paragraph — tag it for the callout */
function markTakeaways(root){
 root.querySelectorAll("p").forEach(p=>{
  const k=p.childNodes;
  if(k.length===1&&k[0].nodeType===1&&(k[0].tagName==="B"||k[0].tagName==="STRONG"))p.classList.add("takeaway");
 });
}
function open(id){
 const m=D.modules.find(x=>x.id===id);if(!m)return;
 curMod=m;
 rbody.innerHTML=
  `<div style="display:flex;gap:6px;align-items:center"><span class="lv ${m.level}">${m.level}</span><span class="tm">${m.time.toUpperCase()}</span>`+
  (passes[m.id]?'<span class="recall pass">RECALL ✓ '+passes[m.id].slice(-1)[0]+'</span>':'<span class="recall pending">RECALL PENDING</span>')+
  `</div><h2>${m.title}</h2>${m.html}`;
 markTakeaways(rbody);
 document.getElementById("rid").textContent=((topicsById[m.topic]||{}).name||m.topic)+" / "+m.id;
 rdr.classList.add("open");document.body.style.overflow="hidden";
 rdr.scrollTop=0;progress();requestAnimationFrame(progress);
}
function close(){rdr.classList.remove("open");document.body.style.overflow="";rprog.style.width="0%";if(location.hash.startsWith("#m="))history.replaceState(null,"",location.pathname)}
document.getElementById("close").addEventListener("click",close);
/* "Ask Claude": opens claude.ai (the reader's own subscription) with the module source
   and their current section preloaded — the hub itself never holds any credentials */
document.getElementById("ask").addEventListener("click",()=>{
 if(!curMod)return;
 let sec="";
 rbody.querySelectorAll("h3").forEach(h=>{if(h.getBoundingClientRect().top<130)sec=h.textContent.trim()});
 const src=`https://raw.githubusercontent.com/faisalmahdy/AI-Learning-Hub/main/modules/${curMod.topic}/${curMod.id}.md`;
 const q=`I am studying the module "${curMod.title}" (level: ${curMod.level}) from my AI-Learning-Hub. Its full source is here — please fetch and read it before answering: ${src}`+
  (sec?` I am currently in the section "${sec}".`:"")+
  ` Act as a patient tutor in the spirit of the module: small concrete numbers, ask me to predict before you reveal an answer, and quiz me from memory at the end. Start by asking what part I want to understand better.`;
 window.open("https://claude.ai/new?q="+encodeURIComponent(q),"_blank","noopener");
});
document.getElementById("reader").addEventListener("click",e=>{if(e.target.id==="reader")close()});
addEventListener("keydown",e=>{if(e.key==="Escape")close()});
document.querySelectorAll(".qrow .t").forEach(t=>t.addEventListener("click",()=>open(t.dataset.id)));

/* view switching */
document.querySelectorAll("nav.rail button[data-view]").forEach(b=>b.addEventListener("click",()=>{
 document.querySelectorAll("nav.rail button[data-view]").forEach(x=>x.setAttribute("aria-pressed",x===b?"true":"false"));
 document.querySelectorAll(".view").forEach(v=>v.classList.remove("active"));
 document.getElementById("view-"+b.dataset.view).classList.add("active");
}));
document.querySelectorAll(".fchip[data-lv]").forEach(c=>c.addEventListener("click",()=>{
 lv=c.dataset.lv;
 document.querySelectorAll(".fchip[data-lv]").forEach(x=>x.setAttribute("aria-pressed",x===c?"true":"false"));
 render();
}));
document.getElementById("q").addEventListener("input",e=>{q=e.target.value.trim().toLowerCase();render()});
document.getElementById("theme").addEventListener("click",()=>{
 const r=document.documentElement,cur=r.dataset.theme;
 r.dataset.theme=cur==="dark"?"light":cur==="light"?"":"dark";
});

/* deep link: #m=<module-id> opens the reader directly */
(function(){const h=location.hash.match(/^#m=(.+)$/);if(h)open(decodeURIComponent(h[1]))})();
</script>
</body>
</html>
"""


def main():
    topics, modules, ledger, hub, skills, errors = load()
    if "--check" in sys.argv:
        for e in errors:
            print("ERROR:", e)
        print(f"checked {len(modules)} modules across {len(topics)} topics — "
              f"{len(errors)} error(s)")
        sys.exit(1 if errors else 0)
    if errors:
        for e in errors:
            print("ERROR:", e)
        sys.exit(1)
    data = json.dumps({"topics": topics, "modules": modules, "ledger": ledger,
                       "hub": hub, "skills": skills},
                      ensure_ascii=False).replace("</", "<\\/")
    SITE.mkdir(exist_ok=True)
    brand = ROOT / "brand"
    if (brand / "logo.svg").exists():
        shutil.copy(brand / "logo.svg", SITE / "favicon.svg")
    if (brand / "logo-dark.svg").exists():
        shutil.copy(brand / "logo-dark.svg", SITE / "logo-dark.svg")
    copied = 0
    for tdir in sorted(MODULES.iterdir()):
        adir = tdir / "assets"
        if adir.is_dir():
            shutil.copytree(adir, SITE / "assets" / tdir.name, dirs_exist_ok=True)
            copied += sum(1 for f in adir.iterdir() if f.is_file())
    (SITE / "index.html").write_text(TEMPLATE.replace("__DATA__", data))
    print(f"built site/index.html — {len(modules)} modules, {len(topics)} topics, "
          f"{len(ledger.get('passes', []))} ledger entries, {copied} assets")


if __name__ == "__main__":
    main()
