#!/usr/bin/env python3
"""Build the AI-Learning-Hub explorer: modules/*.md -> site/index.html.

Stdlib only. Markdown is the source of truth; this generates the view.
`--check` validates the corpus and exits non-zero on any violation, so CI
can gate on it (the hub doctrine: a check gate that actually runs).
"""
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODULES = ROOT / "modules"
LEDGER = ROOT / "ledger" / "recall-ledger.json"
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


def md_to_html(body: str) -> str:
    out, i = [], 0
    lines = body.splitlines()
    while i < len(lines):
        line = lines[i]
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
                mark = "☑" if m.group(1) == "x" else "☐"
                items.append(f"<li><span class='ck'>{mark}</span> {inline_md(m.group(2))}</li>")
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
        modules.append({**meta, "html": md_to_html(body),
                        "text": re.sub(r"\s+", " ", body).lower()})
    ledger = json.loads(LEDGER.read_text()) if LEDGER.exists() else {"passes": []}
    for entry in ledger.get("passes", []):
        if entry.get("module") not in seen:
            errors.append(f"ledger: pass references unknown module '{entry.get('module')}'")
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", entry.get("date", "")):
            errors.append(f"ledger: entry for '{entry.get('module')}' has invalid date")
    return topics, modules, ledger, errors


TEMPLATE = """<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI-Learning-Hub</title>
<style>
:root{
  --bg:#f2f0ea; --panel:#fbfaf6; --sunk:#e6e3d9; --ink:#1c1a15; --muted:#6c6557;
  --line:#dcd8cc; --acc:#0d8a94; --acc-soft:#0d8a9418;
  --basic:#2f8f4e; --inter:#b0731e; --adv:#7a3aed;
  --mono:ui-monospace,"SF Mono","Cascadia Code",Menlo,Consolas,monospace;
  --sans:system-ui,-apple-system,"Segoe UI",sans-serif;
  --shadow:0 1px 2px rgba(28,26,21,.05),0 8px 24px rgba(28,26,21,.07);
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --bg:#12100b; --panel:#1b1811; --sunk:#0c0a06; --ink:#eae6db; --muted:#a49a87;
  --line:#2b2619; --acc:#28c3cf; --acc-soft:#28c3cf1c;
  --basic:#5fc27e; --inter:#e0a44e; --adv:#a78bfa;
  --shadow:0 1px 2px rgba(0,0,0,.45),0 12px 30px rgba(0,0,0,.4);}}
:root[data-theme="dark"]{
  --bg:#12100b; --panel:#1b1811; --sunk:#0c0a06; --ink:#eae6db; --muted:#a49a87;
  --line:#2b2619; --acc:#28c3cf; --acc-soft:#28c3cf1c;
  --basic:#5fc27e; --inter:#e0a44e; --adv:#a78bfa;
  --shadow:0 1px 2px rgba(0,0,0,.45),0 12px 30px rgba(0,0,0,.4);}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 var(--sans)}
main{max-width:1080px;margin:0 auto;padding:34px 18px 90px}
h1{font-family:var(--mono);font-size:clamp(1.5rem,4vw,2.2rem);letter-spacing:-.02em;margin:.1em 0 .2em}
.eyebrow{font-family:var(--mono);font-size:.72rem;letter-spacing:.18em;text-transform:uppercase;color:var(--acc)}
.dek{color:var(--muted);max-width:74ch;margin:.4em 0 0}
code{font-family:var(--mono);font-size:.85em;background:var(--sunk);border:1px solid var(--line);border-radius:5px;padding:.03em .35em}
pre{background:var(--sunk);border:1px solid var(--line);border-radius:10px;padding:12px 14px;overflow-x:auto}
pre code{background:none;border:none;padding:0}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px;margin:22px 0 0}
.tile{border:1px solid var(--line);border-radius:11px;background:var(--panel);box-shadow:var(--shadow);padding:11px 13px}
.tile b{font-family:var(--mono);font-size:1.3rem;color:var(--acc);display:block}
.tile span{font-size:.72rem;color:var(--muted)}
.bar{position:sticky;top:0;z-index:9;background:var(--bg);border-bottom:1px solid var(--line);
  padding:12px 0;margin-top:26px;display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.chip{font-family:var(--mono);font-size:.78rem;cursor:pointer;background:var(--panel);color:var(--muted);
  border:1px solid var(--line);border-radius:999px;padding:.4em .9em}
.chip[aria-pressed="true"]{background:var(--acc);color:#fff;border-color:transparent}
#q{flex:1 1 180px;min-width:140px;font:.85rem var(--mono);color:var(--ink);background:var(--panel);
  border:1px solid var(--line);border-radius:8px;padding:.5em .8em}
#theme{margin-left:auto}
section.topic{margin-top:30px}
.thead{display:flex;align-items:baseline;gap:12px;border-bottom:2px solid var(--acc);padding-bottom:6px;flex-wrap:wrap}
.thead h2{font-family:var(--mono);font-size:1.05rem;margin:0}
.thead .n{font-family:var(--mono);font-size:.7rem;color:var(--muted)}
.tdesc{color:var(--muted);font-size:.88rem;max-width:80ch;margin:.5em 0 0}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px;margin-top:12px}
.card{border:1px solid var(--line);border-radius:12px;background:var(--panel);box-shadow:var(--shadow);
  padding:13px 15px;cursor:pointer;text-align:left;font:inherit;color:inherit}
.card:hover{border-color:var(--acc)}
.card h3{margin:0;font-size:.95rem;line-height:1.3}
.card .meta{display:flex;gap:6px;flex-wrap:wrap;margin:.5em 0}
.card p{margin:0;font-size:.8rem;color:var(--muted)}
.lv{font-family:var(--mono);font-size:.64rem;letter-spacing:.05em;text-transform:uppercase;
  border-radius:5px;padding:.18em .55em;color:#fff}
.lv.basic{background:var(--basic)}.lv.intermediate{background:var(--inter)}.lv.advanced{background:var(--adv)}
.st,.tm{font-family:var(--mono);font-size:.64rem;color:var(--muted);background:var(--sunk);
  border-radius:5px;padding:.18em .55em}
.recall{font-family:var(--mono);font-size:.64rem;border-radius:5px;padding:.18em .55em}
.recall.pass{color:var(--basic);background:color-mix(in srgb,var(--basic) 14%,transparent)}
.recall.pending{color:var(--muted);background:var(--sunk)}
.empty{color:var(--muted);font-size:.84rem;font-style:italic;border:1px dashed var(--line);
  border-radius:10px;padding:12px 15px;margin-top:12px}
#reader{position:fixed;inset:0;background:color-mix(in srgb,var(--bg) 55%,transparent);
  display:none;align-items:flex-start;justify-content:center;overflow-y:auto;z-index:20;padding:4vh 14px}
#reader.open{display:flex}
#reader .paper{background:var(--panel);border:1px solid var(--line);border-radius:14px;
  box-shadow:var(--shadow);max-width:840px;width:100%;padding:26px 30px 40px;margin-bottom:6vh}
#reader h2{font-family:var(--mono);margin:.2em 0;letter-spacing:-.01em}
#reader h3{font-family:var(--mono);font-size:1.02rem;margin:1.4em 0 .4em;color:var(--acc)}
#reader h4{font-family:var(--mono);font-size:.9rem;margin:1.1em 0 .3em}
#reader .tblwrap{overflow-x:auto;border:1px solid var(--line);border-radius:9px;margin:.6em 0}
#reader table{border-collapse:collapse;width:100%;font-size:.85rem}
#reader th,#reader td{text-align:left;padding:7px 11px;border-top:1px solid var(--line);vertical-align:top}
#reader thead th{border-top:none;font-family:var(--mono);font-size:.7rem;color:var(--muted)}
#reader ul.checks{list-style:none;padding-left:0}
#reader ul.checks .ck{color:var(--acc);margin-right:.4em}
#close{float:right;font:1rem var(--mono);cursor:pointer;background:var(--sunk);color:var(--ink);
  border:1px solid var(--line);border-radius:8px;padding:.3em .8em}
footer{margin-top:56px;border-top:1px solid var(--line);padding-top:14px;
  font:.74rem var(--mono);color:var(--muted);display:flex;gap:14px;flex-wrap:wrap;justify-content:space-between}
a{color:var(--acc)}
button:focus-visible,input:focus-visible{outline:2px solid var(--acc);outline-offset:2px}
</style>
<body>
<main>
  <div class="eyebrow">AI-Learning-Hub · learning in the open</div>
  <h1>Maximize the potential of AI</h1>
  <p class="dek">A curriculum of leveled modules — <b>basic → intermediate → advanced</b> — for general
  purpose use, science &amp; development, coding, and beyond. Every module anchors to real work,
  ends in a runnable artifact, and is gated by a dated recall pass. Generated from
  <code>modules/*.md</code> by <code>tools/build_site.py</code>.</p>
  <div class="tiles" id="tiles"></div>
  <div class="bar">
    <button class="chip" data-lv="all" aria-pressed="true">All levels</button>
    <button class="chip" data-lv="basic" aria-pressed="false">Basic</button>
    <button class="chip" data-lv="intermediate" aria-pressed="false">Intermediate</button>
    <button class="chip" data-lv="advanced" aria-pressed="false">Advanced</button>
    <input id="q" type="search" placeholder="search modules…" autocomplete="off">
    <button class="chip" id="theme">◐ theme</button>
  </div>
  <div id="topics"></div>
  <footer>
    <span>faisalmahdy/AI-Learning-Hub</span>
    <span>markdown is the source of truth — this page is generated</span>
  </footer>
</main>
<div id="reader" role="dialog" aria-modal="true">
  <div class="paper">
    <button id="close">✕ close</button>
    <div id="rbody"></div>
  </div>
</div>
<script id="data" type="application/json">__DATA__</script>
<script>
"use strict";
const D=JSON.parse(document.getElementById("data").textContent);
const passes={};(D.ledger.passes||[]).forEach(p=>{if(p.result==="pass")(passes[p.module]=passes[p.module]||[]).push(p.date)});
let lv="all",q="";
const counts={basic:0,intermediate:0,advanced:0};
D.modules.forEach(m=>counts[m.level]++);
document.getElementById("tiles").innerHTML=[
 [D.modules.length,"modules"],[D.topics.length,"topics"],
 [counts.basic+" / "+counts.intermediate+" / "+counts.advanced,"basic / inter / adv"],
 [(D.ledger.passes||[]).filter(p=>p.result==="pass").length,"recall passes"]
].map(t=>`<div class="tile"><b>${t[0]}</b><span>${t[1]}</span></div>`).join("");
function card(m){
 const r=passes[m.id]?`<span class="recall pass">recall ✓ ${passes[m.id].slice(-1)[0]}</span>`
   :`<span class="recall pending">recall pending</span>`;
 return `<button class="card" data-id="${m.id}"><h3>${m.title}</h3>
  <div class="meta"><span class="lv ${m.level}">${m.level}</span>
  <span class="tm">${m.time}</span><span class="st">${m.status}</span>${r}</div>
  <p>${m.summary}</p></button>`;
}
function render(){
 const root=document.getElementById("topics");root.innerHTML="";
 D.topics.sort((a,b)=>a.order-b.order).forEach(t=>{
  const ms=D.modules.filter(m=>m.topic===t.id)
   .filter(m=>lv==="all"||m.level===lv)
   .filter(m=>!q||m.title.toLowerCase().includes(q)||m.text.includes(q)||m.summary.toLowerCase().includes(q));
  if(q&&!ms.length)return;
  const sec=document.createElement("section");sec.className="topic";
  sec.innerHTML=`<div class="thead"><h2>${t.order}. ${t.name}</h2>
   <span class="n">${ms.length} module${ms.length===1?"":"s"}</span></div>
   <p class="tdesc">${t.description}</p>`+
   (ms.length?`<div class="cards">${ms.map(card).join("")}</div>`
    :`<div class="empty">No modules at this filter yet — planned in CURRICULUM.md.</div>`);
  root.appendChild(sec);
 });
 root.querySelectorAll(".card").forEach(c=>c.addEventListener("click",()=>open(c.dataset.id)));
}
function open(id){
 const m=D.modules.find(x=>x.id===id);if(!m)return;
 document.getElementById("rbody").innerHTML=
  `<span class="lv ${m.level}">${m.level}</span> <span class="tm">${m.time}</span>
   <h2>${m.title}</h2>${m.html}`;
 document.getElementById("reader").classList.add("open");
 document.body.style.overflow="hidden";
}
function close(){document.getElementById("reader").classList.remove("open");document.body.style.overflow=""}
document.getElementById("close").addEventListener("click",close);
document.getElementById("reader").addEventListener("click",e=>{if(e.target.id==="reader")close()});
addEventListener("keydown",e=>{if(e.key==="Escape")close()});
document.querySelectorAll(".chip[data-lv]").forEach(c=>c.addEventListener("click",()=>{
 lv=c.dataset.lv;
 document.querySelectorAll(".chip[data-lv]").forEach(x=>x.setAttribute("aria-pressed",x===c?"true":"false"));
 render();
}));
document.getElementById("q").addEventListener("input",e=>{q=e.target.value.trim().toLowerCase();render()});
document.getElementById("theme").addEventListener("click",()=>{
 const r=document.documentElement,cur=r.dataset.theme;
 r.dataset.theme=cur==="dark"?"light":cur==="light"?"":"dark";
});
render();
</script>
</body>
</html>
"""


def main():
    topics, modules, ledger, errors = load()
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
    data = json.dumps({"topics": topics, "modules": modules, "ledger": ledger},
                      ensure_ascii=False).replace("</", "<\\/")
    SITE.mkdir(exist_ok=True)
    (SITE / "index.html").write_text(TEMPLATE.replace("__DATA__", data))
    print(f"built site/index.html — {len(modules)} modules, {len(topics)} topics")


if __name__ == "__main__":
    main()
