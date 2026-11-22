#!/usr/bin/env python3
"""修复 md-raw 中因 CommonMark 左/右侧翼规则而无法解析的 **加粗**：
 - 闭合 ** 前一字符为标点（如 ）】）且后一字符为文字（如 为）→ 在闭合 ** 后补一个空格；
 - 开启 ** 后一字符为标点（如 （【）且前一字符为文字 → 在开启 ** 前补一个空格。
只处理 md-raw 内、行内代码与 $...$ 公式之外的 ** 配对；其余内容一字节不动。
用法：py -3 tools/fix_cjk_bold.py <html 文件> [--write]
"""
import re
import sys
import unicodedata
from pathlib import Path

RAW_RE = re.compile(r'(<script type="text/plain" id="md-raw">)(.*?)(</script>)', re.S)
PROTECT_RE = re.compile(r"```.*?```|`[^`\n]+`|\$\$.*?\$\$|\$[^$\n]+?\$", re.S)


def is_punct(ch):
    return unicodedata.category(ch).startswith(("P", "S"))


def is_word(ch):
    return not ch.isspace() and not is_punct(ch)


def fix_line(line):
    # 以占位符保护代码/公式
    saved = []
    def stash(m):
        saved.append(m.group(0))
        return "\x00%d\x00" % (len(saved) - 1)
    work = PROTECT_RE.sub(stash, line)
    toks = [m.start() for m in re.finditer(r"\*\*", work)]
    if len(toks) < 2 or len(toks) % 2:
        return line, 0
    inserts = []  # (位置, 空格)
    for i in range(0, len(toks), 2):
        o, c = toks[i], toks[i + 1]
        prev_o = work[o - 1] if o > 0 else " "
        next_o = work[o + 2] if o + 2 < len(work) else " "
        prev_c = work[c - 1]
        next_c = work[c + 2] if c + 2 < len(work) else " "
        if is_punct(next_o) and is_word(prev_o) and next_o != "\x00":
            inserts.append(o)
        if is_punct(prev_c) and is_word(next_c) and prev_c != "\x00":
            inserts.append(c + 2)
    for pos in sorted(inserts, reverse=True):
        work = work[:pos] + " " + work[pos:]
    work = re.sub(r"\x00(\d+)\x00", lambda m: saved[int(m.group(1))], work)
    return work, len(inserts)


def main():
    path = Path(sys.argv[1])
    write = "--write" in sys.argv
    data = path.read_bytes().decode("utf-8")
    m = RAW_RE.search(data)
    raw = m.group(2)
    out, total = [], 0
    for line in raw.split("\n"):
        new, n = fix_line(line)
        if n:
            total += n
            print("-", line.strip()[:100])
            print("+", new.strip()[:100])
        out.append(new)
    print("修复处数:", total)
    if write and total:
        data = data[: m.start(2)] + "\n".join(out) + data[m.end(2):]
        path.write_bytes(data.encode("utf-8"))
        print("已写入", path)


if __name__ == "__main__":
    main()
