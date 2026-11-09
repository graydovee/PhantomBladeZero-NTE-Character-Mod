"""Read current PBZ loader evidence and report matching log lines."""

import argparse
import glob
import io
import os
import re
import sys
import time
from datetime import datetime

# PBZModLoader 每次运行一个 evidence\<时间戳>-<pid>-dll\loader.log
DEFAULT_LOG_DIR = r"D:\Program Files (x86)\Steam\steamapps\common\PBZ\ProjectPBZ\PBZModLoader\evidence"

# 关键词：通用出错词 + 本项目的实体名。大小写不敏感。
DEFAULT_KEYWORDS = [
    "[PBZMOD]",          # loader 自己的日志行（加载了哪些 mod）
    "error", "warning", "exception", "fail", "crash",
    "missing", "not found", "fatal", "assert",
    "skeleton", "retarget", "anim", "montage",   # 骨骼 / 动画
    "pak", "mount", "utoc", "ucas",              # 打包 / 挂载
    "zzz_NteZero", "Hun_", "Zero",               # 本项目的资产名
]

# 出现即硬失败的行，输出时打 "!!" 前缀
HARD_FAIL = re.compile(r"LogStreaming: Error|Failed to load|Cannot find|Assertion failed|Fatal error", re.I)


def fit_console():
    """输出编码：真控制台按控制台代码页（中文 Windows 是 936），
    管道/重定向则一律 UTF-8 —— 否则写进管道的 GBK 字节在任何 UTF-8 消费者那里都是乱码。"""
    try:
        import ctypes
        cp = ctypes.windll.kernel32.GetConsoleOutputCP() if sys.stdout.isatty() else 0
        enc = ("cp%d" % cp) if cp else "utf-8"
        for stream in (sys.stdout, sys.stderr):
            try:
                stream.reconfigure(encoding=enc, errors="replace")
            except (AttributeError, ValueError):
                pass
    except Exception:
        pass


def now():
    return datetime.now().strftime("%H:%M:%S")


def pick_log(explicit=None):
    """没给 --log 就自己找最新的一份。"""
    if explicit:
        return explicit if os.path.isfile(explicit) else None
    cands = glob.glob(os.path.join(DEFAULT_LOG_DIR, "*", "loader.log"))
    return max(cands, key=os.path.getmtime) if cands else None


def scan_once(path, rule, out, tail):
    """事后回看：扫整份（或最后 tail 行），报匹配行。"""
    with io.open(path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    total = len(lines)
    if tail and tail > 0:
        lines = lines[-tail:]
    hits = [ln.rstrip("\r\n") for ln in lines if ln.strip() and rule.search(ln)]

    print("[{}] 回看 {}：共 {} 行，看最后 {} 行，命中 {} 条".format(
        now(), os.path.basename(os.path.dirname(path)), total, len(lines), len(hits)))
    fatal = 0
    for ln in hits:
        bad = bool(HARD_FAIL.search(ln))
        fatal += bad
        print("{} {}".format("!!" if bad else "  ", ln))

    with io.open(out, "w", encoding="utf-8") as w:
        w.write("# 哨兵回看 {}，命中 {} 条（硬失败 {} 条）\n".format(
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"), len(hits), fatal))
        for ln in hits:
            w.write(ln + "\n")
    print("[{}] 结果写入：{}".format(now(), out))
    return 0


def _tail_pos(path):
    with io.open(path, "r", encoding="utf-8", errors="replace") as f:
        f.seek(0, os.SEEK_END)
        return f.tell()


def _read_from(path, pos):
    """从 pos 读到末尾；返回 (新位置, 文本)。每轮重新打开，避免长时间占用句柄。"""
    with io.open(path, "r", encoding="utf-8", errors="replace") as f:
        f.seek(pos)
        chunk = f.read()
        return f.tell(), chunk


def watch(path, rule, out, interval, minutes):
    """在线盯：从当前文件末尾开始，只报新行。"""
    hits = []
    carry = ""            # 上一轮读到一半的行，留到下一轮补全
    deadline = time.time() + minutes * 60
    pos = _tail_pos(path)

    print("[{}] 哨兵挂上：{}".format(now(), path))
    print("[{}] 基线 {} 字节，只看这之后的新行；每 {} 秒看一眼，最多 {} 分钟。".format(
        now(), pos, interval, minutes))

    while time.time() < deadline:
        time.sleep(interval)
        try:
            size = os.path.getsize(path)
        except OSError:
            continue
        if size < pos:                      # 日志被清空 / 轮转：位置拨回开头，否则永远读到空
            print("[{}] 日志变小（{} → {}），位置拨回开头".format(now(), pos, size))
            pos, carry = 0, ""
        elif size == pos:
            continue

        pos, chunk = _read_from(path, pos)
        text = carry + chunk
        lines = text.splitlines(keepends=True)
        if lines and not lines[-1].endswith(("\n", "\r")):
            carry = lines.pop()             # 最后一行还没写完
        else:
            carry = ""

        for ln in lines:
            ln = ln.rstrip("\r\n")
            if not ln.strip() or not rule.search(ln):
                continue
            bad = bool(HARD_FAIL.search(ln))
            print("[{}] {} {}".format(now(), "!!" if bad else "  ", ln))
            hits.append(ln)

        if hits:                            # 每抓到就落盘，中途关掉也不丢
            with io.open(out, "w", encoding="utf-8") as w:
                w.write("# 哨兵抓到 {} 条，{}\n".format(
                    len(hits), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                for x in hits:
                    w.write(x + "\n")

    print("[{}] 哨兵下班，共抓到 {} 条。结果：{}".format(now(), len(hits), out))
    return 0


def main():
    fit_console()          # 必须在 argparse 之前：否则 --help 中文也会乱码
    ap = argparse.ArgumentParser(description="只读新增行的 PBZ 日志哨兵")
    ap.add_argument("--log", help="要盯的日志；不填自动取最新 evidence\\*\\loader.log")
    ap.add_argument("--keywords", default="", help="逗号分隔；不填用 PBZ 默认组")
    ap.add_argument("--out", default="pbz-sentinel-hits.txt", help="命中行存哪（默认当前目录）")
    ap.add_argument("--interval", type=int, default=2, help="每几秒看一眼（默认 2）")
    ap.add_argument("--minutes", type=int, default=30, help="最多盯几分钟（默认 30）")
    ap.add_argument("--tail", type=int, default=0, help="配合 --once：只看最后 N 行（0=全部）")
    ap.add_argument("--once", action="store_true", help="只扫一遍就退出（事后回看）")
    a = ap.parse_args()

    path = pick_log(a.log)
    if not path:
        print("找不到日志文件。看过的位置：{}".format(a.log or DEFAULT_LOG_DIR))
        print("  → 先确认游戏真的启动过一次、且 loader 注入成功（evidence 下应有本次目录）。")
        return 1

    kws = [x.strip() for x in a.keywords.split(",") if x.strip()] or DEFAULT_KEYWORDS
    rule = re.compile("|".join(re.escape(k) for k in kws), re.IGNORECASE)
    if a.once:
        return scan_once(path, rule, a.out, a.tail)
    return watch(path, rule, a.out, a.interval, a.minutes)


if __name__ == "__main__":
    sys.exit(main())
