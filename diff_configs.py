#!/usr/bin/env python3
import argparse
import math
import os
import re
from pathlib import Path


def parse_list(s: str):
    s = s.strip()
    if s in ("-", ""):
        return None
    if s.startswith("[") and s.endswith("]"):
        s = s[1:-1]
    if not s:
        return []
    out = []
    for part in s.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            out.append(float(part))
        except ValueError:
            out.append(part)
    return out


def lists_equal(a, b, tol=1e-9):
    if a is None or b is None:
        return a == b
    if len(a) != len(b):
        return False
    for x, y in zip(a, b):
        try:
            if math.isfinite(x) and math.isfinite(y):
                if abs(x - y) > tol:
                    return False
            else:
                if x != y:
                    return False
        except Exception:
            if x != y:
                return False
    return True


def read_msgs(root):
    data = {}
    path = os.path.join(root, "msgs_data", "messages_resume.csv")
    if not os.path.exists(path):
        return data
    with open(path, "r", encoding="utf-8") as f:
        first = True
        for line in f:
            line = line.strip()
            if not line:
                continue
            if first:
                first = False
                continue
            parts = line.split("\t")
            if len(parts) < 9:
                continue
            key = tuple(parts[:8])
            val = parse_list(parts[8])
            data[key] = val
    return data


FILE_RE = re.compile(r"^(?P<algo>[OP])average_resume_r#(?P<runs>\d+)_a#(?P<arena>[^.]+)\.csv$")


def read_proc(root):
    data = {}
    p = Path(root) / "proc_data"
    if not p.exists():
        return data
    for fp in p.glob("*.csv"):
        m = FILE_RE.match(fp.name)
        if not m:
            continue
        algo = m.group("algo")
        runs = m.group("runs")
        arena = m.group("arena")
        with open(fp, "r", encoding="utf-8") as f:
            header = None
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if header is None:
                    header = line.split("\t")
                    continue
                parts = line.split("\t")
                if len(parts) < len(header):
                    parts = parts + [""] * (len(header) - len(parts))
                row = dict(zip(header, parts))
                key_fields = [row.get(h, "") for h in header[:9]]
                key = (algo, arena, runs, *key_fields)
                val = (
                    parse_list(row.get(header[9], "")) if len(header) > 9 else None,
                    parse_list(row.get(header[10], "")) if len(header) > 10 else None,
                )
                data[key] = val
    return data


def diff_dict(a, b):
    ak, bk = set(a.keys()), set(b.keys())
    only_a = sorted(ak - bk)
    only_b = sorted(bk - ak)
    diffs = []
    for k in sorted(ak & bk):
        va, vb = a[k], b[k]
        if isinstance(va, tuple) and isinstance(vb, tuple):
            if not (lists_equal(va[0], vb[0]) and lists_equal(va[1], vb[1])):
                diffs.append(k)
        else:
            if not lists_equal(va, vb):
                diffs.append(k)
    return only_a, only_b, diffs


def print_section(title, only_a, only_b, diffs, limit):
    print(title)
    print(f"  only in A: {len(only_a)}")
    print(f"  only in B: {len(only_b)}")
    print(f"  differing: {len(diffs)}")
    shown = 0
    for k in diffs[:limit]:
        print(f"  diff key: {k}")
        shown += 1
    if len(diffs) > shown:
        print("  ...")


def main():
    parser = argparse.ArgumentParser(
        description="Diff configuration keys between two roots (msgs_data/proc_data).",
    )
    parser.add_argument("root_a", nargs="?", default="dynamic_data", help="Root A (default: dynamic_data)")
    parser.add_argument("root_b", nargs="?", default=".", help="Root B (default: .)")
    parser.add_argument("--limit", type=int, default=50, help="Max keys to print per section")
    parser.add_argument("--mode", choices=["all", "msgs", "proc"], default="all", help="Which datasets to compare")
    args = parser.parse_args()

    if args.mode in ("all", "msgs"):
        msgs_a = read_msgs(args.root_a)
        msgs_b = read_msgs(args.root_b)
        only_a, only_b, diffs = diff_dict(msgs_a, msgs_b)
        print_section("MSGs:", only_a, only_b, diffs, args.limit)

    if args.mode in ("all", "proc"):
        proc_a = read_proc(args.root_a)
        proc_b = read_proc(args.root_b)
        only_a, only_b, diffs = diff_dict(proc_a, proc_b)
        print_section("\nPROC:", only_a, only_b, diffs, args.limit)


if __name__ == "__main__":
    main()
