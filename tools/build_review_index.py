#!/usr/bin/env python3
"""生成 static/review/index.html（总目录页：卡片网格 + localStorage 掌握度进度条）。

- 扫描 4 个课程目录下的 *.html，自动生成卡片与条目；
- 从每页 <script id="md-raw"> 中统计 h2/h3 考点总数（忽略代码围栏），写入 data-total，
  作为尚未访问过的页面的兜底总数（访问过的页面由 review-ui.js 写入 rui:meta:* 覆盖）。
用法：py -3 tools/build_review_index.py
"""
import html
import io
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "static" / "review"

COURSES = [
    ("photogrammetry", "一", "数字摄影测量学", "Digital Photogrammetry · 期末重构版", "📐", "#58a6ff"),
    ("gnss", "二", "GNSS 原理与应用", "32 + 36 + 32 考题重构版", "🛰️", "#00ff80"),
    ("remote_sensing", "三", "遥感原理与应用", "Remote Sensing · 机制 / 对比 / 公式 / 大题", "🌍", "#ffa657"),
    ("gis", "四", "地理信息系统原理", "GIS · 期末重构版", "🗺️", "#d2a8ff"),
]

RAW_RE = re.compile(r'<script type="text/plain" id="md-raw">(.*?)</script>', re.S)
FENCE_RE = re.compile(r"^\s*(```|~~~)")
HEAD_RE = re.compile(r"^ {0,3}#{2,3}\s+\S")


def count_headings(page: Path) -> int:
    text = page.read_text(encoding="utf-8")
    m = RAW_RE.search(text)
    if not m:
        return 0
    n, in_fence = 0, False
    for line in m.group(1).splitlines():
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if not in_fence and HEAD_RE.match(line):
            n += 1
    return n


TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="color-scheme" content="dark">
<title>期末核心复习库 | 测绘遥感</title>
<style>
  :root { --bg:#0d1117; --panel:#161b22; --panel2:#1c2230; --border:#30363d; --text:#c9d1d9; --muted:#8b949e; --green:#00ff80; --blue:#58a6ff; }
  * { box-sizing: border-box; }
  body { margin:0; background: radial-gradient(1200px 500px at 50% -10%, #12202e 0%, var(--bg) 60%) no-repeat, var(--bg); color:var(--text);
         font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; line-height:1.6; min-height:100vh; }
  .wrap { max-width:1120px; margin:0 auto; padding:40px 20px 64px; }
  header.hero { display:flex; flex-wrap:wrap; align-items:flex-end; justify-content:space-between; gap:18px; padding-bottom:22px; border-bottom:1px solid #21262d; }
  h1 { margin:0; font-size:1.7rem; color:var(--green); letter-spacing:.01em; }
  .sub { margin:6px 0 0; color:var(--muted); font-size:.9rem; }
  .overall { min-width:240px; flex:0 1 320px; }
  .overall .row { display:flex; justify-content:space-between; font-size:.82rem; color:var(--muted); margin-bottom:6px; }
  .overall .row b { color:var(--green); font-size:.95rem; }
  .bar { height:8px; border-radius:4px; background:#21262d; overflow:hidden; }
  .bar > i { display:block; height:100%; width:0; background:linear-gradient(90deg,#00b4ff,#00ff80); transition:width .5s ease; }
  .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(min(100%,460px),1fr)); gap:20px; margin-top:28px; }
  .card { position:relative; background:linear-gradient(180deg,var(--panel2),var(--panel)); border:1px solid var(--border); border-radius:14px;
          padding:20px 20px 14px; overflow:hidden; transition:border-color .2s, transform .2s, box-shadow .2s; }
  .card::before { content:""; position:absolute; inset:0 0 auto 0; height:3px; background:var(--accent); opacity:.85; }
  .card:hover { border-color:var(--accent); transform:translateY(-2px); box-shadow:0 12px 30px rgba(0,0,0,.4); }
  .card-head { display:flex; gap:14px; align-items:center; }
  .ico { width:46px; height:46px; flex:none; border-radius:12px; display:flex; align-items:center; justify-content:center; font-size:1.5rem;
         background:color-mix(in srgb, var(--accent) 14%, transparent); border:1px solid color-mix(in srgb, var(--accent) 35%, transparent); }
  .card h2 { margin:0; font-size:1.08rem; color:#e6edf3; }
  .card h2 small { display:block; margin-top:2px; font-size:.78rem; font-weight:400; color:var(--muted); }
  .prog { margin:16px 0 12px; }
  .prog .row { display:flex; justify-content:space-between; font-size:.8rem; color:var(--muted); margin-bottom:6px; }
  .prog .row b { color:var(--accent); font-size:.9rem; }
  .prog .bar > i { background:var(--accent); }
  ul { list-style:none; margin:0; padding:0; }
  li + li { margin-top:8px; }
  a.item { display:flex; align-items:center; justify-content:space-between; gap:12px; text-decoration:none; color:#e6edf3; background:#0f141b;
           border:1px solid #262c36; border-radius:9px; padding:10px 14px; transition:border-color .2s, color .2s, background .2s; font-size:.92rem; }
  a.item:hover { border-color:var(--accent); color:var(--accent); background:#121923; }
  a.item .name { min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  a.item .chip { flex:none; font-size:.72rem; color:var(--muted); background:#161b22; border:1px solid var(--border); border-radius:999px; padding:2px 9px; font-variant-numeric:tabular-nums; }
  a.item .chip.done { color:#04140b; background:var(--green); border-color:var(--green); }
  a.item .chip.part { color:var(--accent); border-color:color-mix(in srgb, var(--accent) 50%, transparent); }
  footer { margin-top:30px; display:flex; flex-wrap:wrap; gap:12px; align-items:center; justify-content:space-between; color:#6e7681; font-size:.8rem; }
  footer button { background:transparent; color:var(--muted); border:1px solid var(--border); border-radius:8px; padding:6px 12px; cursor:pointer; font-size:.8rem; }
  footer button:hover { color:#ff7b72; border-color:#ff7b72; }
  @media (max-width:520px) { .wrap { padding:28px 14px 48px; } h1 { font-size:1.4rem; } .overall { flex-basis:100%; } }
</style>
</head>
<body>
<div class="wrap">
<header class="hero">
  <div>
    <h1>// 期末复习终端 (Mobile HUD)</h1>
    <p class="sub">4 门课程 · __PAGE_COUNT__ 份复习资料 · 进度仅保存在本机浏览器</p>
  </div>
  <div class="overall" id="overall">
    <div class="row"><span>总体掌握进度</span><span><b id="overall-pct">0%</b> · <span id="overall-num">0/0</span></span></div>
    <div class="bar"><i id="overall-bar"></i></div>
  </div>
</header>
<main class="grid">
__CARDS__
</main>
<footer>
  <span>在各复习页点击标题右侧的「✓ 已掌握」即可记录考点进度。</span>
  <button type="button" id="reset">清除本机掌握记录</button>
</footer>
</div>
<script>
(function () {
  var KEY_M = 'rui:m:', KEY_META = 'rui:meta:';
  var ls = null;
  try { ls = window.localStorage; ls.getItem('__rui'); } catch (e) { ls = null; }
  function pathOf(href) {
    var p = new URL(href, location.href).pathname;
    try { p = decodeURIComponent(p); } catch (e) { }
    return p;
  }
  function doneOf(path) {
    if (!ls) return 0;
    var prefix = KEY_M + path + '::', n = 0;
    for (var i = 0; i < ls.length; i++) {
      var k = ls.key(i);
      if (k && k.indexOf(prefix) === 0 && ls.getItem(k) === '1') n++;
    }
    return n;
  }
  function totalOf(path, fallback) {
    var m = ls ? parseInt(ls.getItem(KEY_META + path), 10) : NaN;
    return m > 0 ? m : fallback;
  }
  function pct(a, b) { return b ? Math.round(a * 100 / b) : 0; }

  function render() {
    var gDone = 0, gTotal = 0;
    var cards = document.querySelectorAll('.card');
    for (var c = 0; c < cards.length; c++) {
      var cd = 0, ct = 0;
      var items = cards[c].querySelectorAll('a.item');
      for (var i = 0; i < items.length; i++) {
        var a = items[i], path = pathOf(a.getAttribute('href'));
        var t = totalOf(path, parseInt(a.getAttribute('data-total'), 10) || 0);
        var d = Math.min(doneOf(path), t || Infinity);
        var chip = a.querySelector('.chip');
        chip.textContent = d + '/' + t;
        chip.className = 'chip' + (t && d >= t ? ' done' : d > 0 ? ' part' : '');
        cd += d; ct += t;
      }
      cards[c].querySelector('.p-num').textContent = cd + ' / ' + ct + ' 考点';
      cards[c].querySelector('.p-pct').textContent = pct(cd, ct) + '%';
      cards[c].querySelector('.bar > i').style.width = pct(cd, ct) + '%';
      gDone += cd; gTotal += ct;
    }
    document.getElementById('overall-pct').textContent = pct(gDone, gTotal) + '%';
    document.getElementById('overall-num').textContent = gDone + '/' + gTotal;
    document.getElementById('overall-bar').style.width = pct(gDone, gTotal) + '%';
  }
  render();
  window.addEventListener('storage', render);
  window.addEventListener('pageshow', render);   // 从复习页返回（含 bfcache）时刷新
  document.addEventListener('visibilitychange', function () { if (!document.hidden) render(); });
  document.getElementById('reset').addEventListener('click', function () {
    if (!ls || !confirm('确定清除本机所有考点掌握记录？此操作不可撤销。')) return;
    var del = [];
    for (var i = 0; i < ls.length; i++) { var k = ls.key(i); if (k && k.indexOf(KEY_M) === 0) del.push(k); }
    del.forEach(function (k) { ls.removeItem(k); });
    render();
  });
})();
</script>
</body>
</html>
"""


def build() -> str:
    cards, total_pages = [], 0
    for folder, num, title, subtitle, icon, accent in COURSES:
        pages = sorted((ROOT / folder).glob("*.html"))
        total_pages += len(pages)
        items = []
        for p in pages:
            name = p.stem
            href = f"{folder}/{p.name}"
            items.append(
                f'<li><a class="item" href="{html.escape(href, quote=True)}" '
                f'data-total="{count_headings(p)}"><span class="name">{html.escape(name)}</span>'
                f'<span class="chip">0/0</span></a></li>'
            )
        cards.append(
            f'<section class="card" data-course="{folder}" style="--accent:{accent}">\n'
            f'  <div class="card-head"><div class="ico">{icon}</div>'
            f'<h2>{num}、{html.escape(title)}<small>{html.escape(subtitle)} · {len(pages)} 篇</small></h2></div>\n'
            f'  <div class="prog"><div class="row"><span class="p-num">0 / 0 考点</span><b class="p-pct">0%</b></div>'
            f'<div class="bar"><i></i></div></div>\n'
            f'  <ul>\n    ' + "\n    ".join(items) + "\n  </ul>\n</section>"
        )
    return TEMPLATE.replace("__PAGE_COUNT__", str(total_pages)).replace("__CARDS__", "\n".join(cards))


if __name__ == "__main__":
    out = ROOT / "index.html"
    with io.open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(build())
    print(f"wrote {out}")
    sys.exit(0)
