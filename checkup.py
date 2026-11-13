# -*- coding: utf-8 -*-
"""
给远程 AI 做体检。本地跑，一条命令出一张报告。

用法：
    python checkup.py            # 正常跑
    python checkup.py -v         # 带上最近的错误明细
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
import config as cfg  # noqa: E402  配置在这
SSH = os.path.join(HERE, "_ssh.py")
PY = sys.executable


def sh_run(cmd, timeout=90):
    # 把 {DATA} / {LOG} / {SERVICE} 换成 config.py 里配的
    cmd = (cmd.replace("{DATA}", cfg.DATA)
              .replace("{LOG}", cfg.LOG)
              .replace("{SERVICE}", cfg.SERVICE))
    r = subprocess.run([PY, SSH, cmd], capture_output=True, text=True,
                       encoding="utf-8", errors="ignore", timeout=timeout)
    return (r.stdout or "").strip()


def g(pattern, text, default=0, cast=int):
    m = re.search(pattern, text)
    if not m:
        return default
    try:
        return cast(m.group(1))
    except Exception:
        return default


def main():
    verbose = "-v" in sys.argv
    out = []

    print("=" * 46)
    print("  AI 体检 · 现在 %s" % __import__("datetime").datetime.now().strftime("%m-%d %H:%M"))
    print("=" * 46)

    # 1 服务
    active = sh_run("systemctl is-active {SERVICE}").strip()
    print("\n[1] 服务      %s" % active)
    ok_service = active == "active"

    # 2 错误
    # 【11-11 修】原来只 grep 'ERR'，可日志里的报错长这样：「[主动] 出错 UnboundLocalError: …」
    # 中文「出错」一个 ERR 都不带，于是今天凌晨炸了 5 次，体检还报「今天 0 个」——假绿。
    err_pat = "出错|ERROR|Traceback|Exception"
    err_all = sh_run("grep -Ec '%s' {LOG}" % err_pat).strip()
    err_today = sh_run(
        "grep -E '%s' {LOG} | grep -c '%s'"
        % (err_pat, __import__("datetime").datetime.now().strftime("%Y-%m-%d"))).strip()
    print("[2] 错误      今天 %s 个 · 累计 %s 个" % (err_today or "0", err_all or "0"))
    if verbose:
        print(sh_run("grep -E '%s' {LOG} | tail -5" % err_pat))

    # 3 缓存命中
    hit = sh_run(
        "grep '缓存命中' {LOG} | tail -20 | "
        "awk -F'缓存命中 ' '{print $2}' | awk -F/ '{h+=$1; t+=$2; n++} "
        "END {printf \"%.1f %d\", h/t*100, n}'").strip()
    parts = hit.split()
    pct = float(parts[0]) if parts else 0.0
    n = int(parts[1]) if len(parts) > 1 else 0
    print("[3] 缓存命中  %.1f%%（最近 %d 轮）" % (pct, n))

    # 4 对话量
    d = __import__("datetime").datetime.now().strftime("%Y-%m-%d")
    turns = sh_run("grep -c '%s' {DATA}/chat_history.jsonl" % d).strip()
    print("[4] 今天对话  %s 条" % turns)

    # 5 资源
    disk = sh_run("df -h / | tail -1 | awk '{print $3\"/\"$2\" (\"$5\")\"}'").strip()
    mem = sh_run("free -m | awk 'NR==2{printf \"%dM/%dM\", $3, $2}'").strip()
    print("[5] 磁盘      %s" % disk)
    print("    内存      %s" % mem)

    # 6 记忆文件
    files = sh_run("ls -la {DATA}/*.md | awk '{print $5, $9}'").strip()
    print("[6] 记忆文件")
    for line in files.splitlines():
        p = line.split()
        if len(p) == 2:
            print("    %-7s %s" % (p[0], p[1].replace(cfg.DATA + "/", "")))

    # 7 模型
    model = sh_run("grep '\\[模型\\]' {LOG} | tail -1").strip()
    m = re.search(r"deepseek-[a-z0-9.\-]+", model)
    print("\n[7] 模型      %s" % (m.group(0) if m else "查不到"))

    # ---- 下面三项查的是「对不对」，上面七项查的是「活着没有」----
    # 11-09 加的：那天的 8 个 bug，上面七项一个都没发现。

    print("\n[8] 记忆重复")
    dup_raw = sh_run("grep '^## ' {DATA}/shared_memory.md | sort | uniq -c | sort -rn | head -1")
    dup_n = 0
    dup_top = ""
    try:
        if dup_raw:
            parts = dup_raw.strip().split(None, 1)
            if parts and parts[0].isdigit():
                dup_n = int(parts[0])
                dup_top = parts[1][:40] if len(parts) > 1 else ""
    except Exception:
        pass
    if dup_n > 1:
        print("    ⚠ 最多的一个标题出现 %d 次：%s" % (dup_n, dup_top))
    else:
        print("    没有重复块")

    print("\n[9] 流水新鲜度")
    mt_raw = sh_run("stat -c %Y {DATA}/auto_memory.md").strip()
    age_min = -1
    try:
        import time as _t
        age_min = int((_t.time() - int(mt_raw)) / 60)
    except Exception:
        pass
    if age_min < 0:
        print("    读不到")
    elif age_min > 120:
        print("    ⚠ %d 分钟没更新（%.1f 小时），提炼可能停了" % (age_min, age_min / 60.0))
    else:
        print("    %d 分钟前更新" % age_min)

    print("\n[10] 日志柜")
    all_n = sh_run("ls {DATA}/logs/ | wc -l").strip()
    date_n = sh_run("ls {DATA}/logs/ | grep -E '^[0-9]{4}-[0-9]{2}-[0-9]{2}[.]md$' | wc -l").strip()
    junk_n = 0
    try:
        junk_n = int(all_n) - int(date_n)
    except Exception:
        pass
    if junk_n > 0:
        print("    ⚠ %s 个文件里，%d 个不是日期日志" % (all_n, junk_n))
    else:
        print("    %s 个文件，全是日期日志" % all_n)

    # ---- 判断 ----
    print("\n" + "-" * 46)
    bad = []
    if not ok_service:
        bad.append("服务没在跑")
    if err_today and int(err_today) > 3:
        bad.append("今天错误 %s 个，偏多" % err_today)
    if pct and pct < 40:
        bad.append("缓存命中只有 %.0f%%，提示词里可能又混进了每轮变的东西" % pct)
    used = g(r"(\d+)%", disk, 0)
    if used and int(used) > 80:
        bad.append("磁盘用了 %s%%" % used)
    if dup_n > 2:
        bad.append("主记忆有标题重复 %d 次，该跑 merge_shared.py 去重了" % dup_n)
    if age_min > 120:
        bad.append("流水 %d 分钟没更新，提炼可能停了" % age_min)
    if junk_n > 0:
        bad.append("日志柜里混进 %d 个不是日期日志的文件" % junk_n)

    if bad:
        print("有 %d 处要看：" % len(bad))
        for b in bad:
            print("  · " + b)
    else:
        print("都正常。")
    print("-" * 46)


if __name__ == "__main__":
    main()
