#!/usr/bin/env python3
"""为 4 个目录下的全部 16 个复习页面批量引入 review-ui.css / review-ui.js（幂等）。

- 仅在 </head> 前插入两行，不改动 md-raw 与渲染脚本一字节；
- 保留各文件原有换行符（CRLF/LF）与编码（UTF-8，无 BOM 即无 BOM）；
- 用法：py -3 tools/inject_review_ui.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "static" / "review"
DIRS = ["photogrammetry", "gnss", "remote_sensing", "gis"]
CSS = '<link rel="stylesheet" href="../assets/review-ui.css">'
JS = '<script defer src="../assets/review-ui.js"></script>'


def main() -> int:
    changed = skipped = 0
    for d in DIRS:
        for p in sorted((ROOT / d).glob("*.html")):
            data = p.read_bytes()
            text = data.decode("utf-8")
            has_css, has_js = "assets/review-ui.css" in text, "assets/review-ui.js" in text
            if has_css and has_js:
                skipped += 1
                continue
            if text.count("</head>") != 1:
                print(f"ERROR: {p} 的 </head> 数量不为 1", file=sys.stderr)
                return 1
            nl = "\r\n" if "\r\n" in text else "\n"
            add = ""
            if not has_css:
                add += CSS + nl
            if not has_js:
                add += JS + nl
            text = text.replace("</head>", add + "</head>", 1)
            p.write_bytes(text.encode("utf-8"))
            changed += 1
            print(f"patched  {p.relative_to(ROOT)}")
    print(f"done: patched={changed} already-ok={skipped}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
