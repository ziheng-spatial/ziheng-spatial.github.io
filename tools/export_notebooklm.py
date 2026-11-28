#!/usr/bin/env python3
r"""从 static/review/<course>/*.html 的 <script id="md-raw"> 提取纯 Markdown 文本，
按科目导出至 E:\notebooklm_upload\ 下的四个子目录，确保与线上复习站 100% 同步。

用法：py -3 tools/export_notebooklm.py
"""
import io
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
REVIEW_ROOT = REPO / "static" / "review"
EXPORT_ROOT = Path(r"E:\notebooklm_upload")

SUBJECT_MAP = [
    ("photogrammetry", "01_photogrammetry"),
    ("gnss", "02_gnss"),
    ("gis", "03_gis"),
    ("remote_sensing", "04_remote_sensing"),
]

RAW_RE = re.compile(r'<script type="text/plain" id="md-raw">(.*?)</script>', re.S)


def export_all() -> int:
    EXPORT_ROOT.mkdir(parents=True, exist_ok=True)
    total_files = 0
    for src_dir_name, dst_dir_name in SUBJECT_MAP:
        src_dir = REVIEW_ROOT / src_dir_name
        dst_dir = EXPORT_ROOT / dst_dir_name
        dst_dir.mkdir(parents=True, exist_ok=True)

        html_files = sorted(src_dir.glob("*.html"))
        expected_md_names = {f"{p.stem}.md" for p in html_files}

        for old_md in dst_dir.glob("*.md"):
            if old_md.name not in expected_md_names:
                old_md.unlink()
                print(f"[removed stale] {old_md}")

        print(f"=== {dst_dir_name} ({len(html_files)} 篇) ===")
        for html_path in html_files:
            content = html_path.read_text(encoding="utf-8")
            m = RAW_RE.search(content)
            if not m:
                raise RuntimeError(f"未在 {html_path} 中找到 <script type=\"text/plain\" id=\"md-raw\">")
            md_text = m.group(1).replace("\r\n", "\n").strip("\n") + "\n"
            out_path = dst_dir / f"{html_path.stem}.md"
            with io.open(out_path, "w", encoding="utf-8", newline="\n") as f:
                f.write(md_text)
            total_files += 1
            print(f"  -> {out_path.name} ({out_path.stat().st_size} bytes)")

    print(f"\n导出完成：共 {len(SUBJECT_MAP)} 个科目，{total_files} 份 Markdown 文件已同步至 {EXPORT_ROOT}")
    return 0


if __name__ == "__main__":
    sys.exit(export_all())
