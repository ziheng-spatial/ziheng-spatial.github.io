#!/usr/bin/env python3
"""校验 static/review 下的复习页面改造：脚本引入完整、md-raw 与渲染管线未被破坏。

检查项（每个页面）：
 1. 恰好 1 处 review-ui.css 链接 + 1 处 review-ui.js（defer），且都位于 </head> 之前；
 2. review-ui.js 位于 KaTeX / auto-render 脚本之后（defer 顺序）；
 3. <script type="text/plain" id="md-raw"> 恰好 1 个，且其内容与 git 基线（--base，默认 HEAD）字节一致；
 4. 去掉新增的两行引入后，整个文件与基线字节完全一致（证明未改动任何原有内容）；
 5. 渲染管线顺序：占位符保护 $$ → $ → marked.parse → 还原 → renderMathInElement；
 6. 相对路径指向的 assets 文件存在。
另检查：全部页面覆盖、总目录页链接均有效、review-ui.js 不含对渲染函数的改写。
用法：py -3 tools/verify_review_ui.py [--base HEAD]
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ROOT = REPO / "static" / "review"
DIRS = ["photogrammetry", "gnss", "remote_sensing", "gis"]
RAW_RE = re.compile(rb'<script type="text/plain" id="md-raw">(.*?)</script>', re.S)
CSS_TAG = b'<link rel="stylesheet" href="../assets/review-ui.css">'
JS_TAG = b'<script defer src="../assets/review-ui.js"></script>'

# 动态校验：每个课程目录均至少包含 1 个复习页面，且与 index.html 条目数完全一致（可用 --expected 指定固定页数）
errors = []


def err(msg):
    errors.append(msg)
    print("  FAIL:", msg)


def git_show(base, rel):
    r = subprocess.run(["git", "show", f"{base}:{rel}"], cwd=REPO, capture_output=True)
    return r.stdout if r.returncode == 0 else None


def check_page(p, base):
    rel = p.relative_to(REPO).as_posix()
    data = p.read_bytes()
    head_end = data.find(b"</head>")

    for tag, name in ((CSS_TAG, "review-ui.css"), (JS_TAG, "review-ui.js")):
        n = data.count(tag)
        if n != 1:
            err(f"{rel}: {name} 引入次数为 {n}（应为 1）")
        elif data.find(tag) > head_end:
            err(f"{rel}: {name} 不在 <head> 内")

    j = data.find(JS_TAG)
    for lib in (b"katex.min.js", b"auto-render.min.js", b"marked.min.js"):
        k = data.find(lib)
        if k < 0:
            err(f"{rel}: 缺少 {lib.decode()}")
        elif 0 <= j < k:
            err(f"{rel}: review-ui.js 出现在 {lib.decode()} 之前")

    raws = RAW_RE.findall(data)
    if len(raws) != 1:
        err(f"{rel}: md-raw 数量为 {len(raws)}（应为 1）")
    elif not raws[0].strip():
        err(f"{rel}: md-raw 为空")

    baseline = git_show(base, rel)
    if baseline is not None:
        # core.autocrlf=true 时 git 对象为 LF，工作区为 CRLF：统一换行后再逐字节比对
        baseline = baseline.replace(b"\r\n", b"\n")
        data_n = data.replace(b"\r\n", b"\n")
    if baseline is None:
        print(f"  warn: {rel} 在 {base} 中不存在，跳过基线比对")
    else:
        braws = RAW_RE.findall(baseline)
        if len(braws) != 1 or (raws and braws[0] != raws[0].replace(b"\r\n", b"\n")):
            err(f"{rel}: md-raw 内容与基线不一致")
        stripped = data_n.replace(CSS_TAG + b"\n", b"", 1).replace(JS_TAG + b"\n", b"", 1)
        baseline_stripped = baseline.replace(CSS_TAG + b"\n", b"", 1).replace(JS_TAG + b"\n", b"", 1)
        if stripped != baseline_stripped:
            err(f"{rel}: 去除新增引入后与基线不一致（原有内容被改动）")

    text = data.decode("utf-8")
    inline = text[text.find("</script>", text.find('id="md-raw"')):]
    order = [
        'replace(/\\$\\$([\\s\\S]*?)\\$\\$/g',
        'replace(/\\$([^\\$\\n]+?)\\$/g',
        "marked.parse(",
        "KATEXMATHBLOCK(\\d+)END",
        "KATEXMATHINLINE(\\d+)END",
        "renderMathInElement(",
    ]
    pos = -1
    for s in order:
        q = inline.find(s, pos + 1)
        if q < 0:
            err(f"{rel}: 渲染管线缺少/乱序: {s}")
            break
        pos = q

    for asset in ("review-ui.css", "review-ui.js"):
        if not (p.parent.parent / "assets" / asset).is_file():
            err(f"{rel}: assets/{asset} 不存在")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="HEAD")
    ap.add_argument("--expected", type=int, default=0, help="可选：显式指定预期总页数，0 表示按各课程目录动态检测")
    args = ap.parse_args()
    base = args.base

    pages = []
    for d in DIRS:
        d_pages = sorted((ROOT / d).glob("*.html"))
        if not d_pages:
            err(f"课程目录 {d} 下未发现任何复习页面")
        pages.extend(d_pages)
    print(f"发现复习页面 {len(pages)} 个（按 {len(DIRS)} 个课程目录动态统计）")
    if args.expected > 0 and len(pages) != args.expected:
        err(f"页面总数为 {len(pages)}（应为 {args.expected}）")
    for p in pages:
        print("check", p.relative_to(ROOT).as_posix())
        check_page(p, base)

    js = (ROOT / "assets" / "review-ui.js")
    css = (ROOT / "assets" / "review-ui.css")
    if not js.is_file() or not css.is_file():
        err("assets 公共文件缺失")
    else:
        jt = js.read_text(encoding="utf-8")
        if re.search(r"renderMathInElement\s*=|window\.marked\s*=|marked\.parse\s*=", jt):
            err("review-ui.js 不应改写 renderMathInElement / marked")
        if "MutationObserver" not in jt:
            err("review-ui.js 缺少渲染完成后挂载逻辑")

    idx = ROOT / "index.html"
    it = idx.read_text(encoding="utf-8")
    hrefs = re.findall(r'class="item" href="([^"]+)"', it)
    if len(hrefs) != len(pages):
        err(f"index.html 条目数 {len(hrefs)} != 页面数 {len(pages)}")
    for h in hrefs:
        if not (ROOT / h).is_file():
            err(f"index.html 链接失效: {h}")

    print()
    if errors:
        print(f"校验失败：{len(errors)} 个问题")
        return 1
    print("校验通过：全部 %d 个页面均已引入公共资源，md-raw 与渲染管线未被改动。" % len(pages))
    return 0


if __name__ == "__main__":
    sys.exit(main())
