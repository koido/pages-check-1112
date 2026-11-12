#!/usr/bin/env python3
"""図3 再現ツール（2024-01、自分用）

図3_input/ の CSV を3つ読んで、図3と同じ計算をして、入力ファイルの指紋を出す。
指紋は入力ファイルの控え。同じ3つのファイルを渡せば同じ値になる。

使い方:
  python make_fig3.py
    図3_input/ の CSV 3個を読む。
  python make_fig3.py <CSV1> <CSV2> <CSV3>
    3つとも直接渡す（図3_input/ は使わない）。
"""
from __future__ import annotations

import hashlib
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def read_instrument(path: Path) -> list[list[float]]:
    """装置のCSVとして読む。1行目が装置のヘッダーでなければ、そのCSVではないと判断する。"""
    raw = path.read_bytes()
    text = raw.decode("ascii", errors="replace")
    lines = text.splitlines()
    if not lines or not lines[0].startswith("Luminescence Monitor YH-8,"):
        sys.exit(f"装置のCSVではありません: {path}")
    rows = []
    for line in lines:
        cells = line.split(",")
        if len(cells) != 10 or any(c.strip() == "" for c in cells):
            continue
        try:
            rows.append([float(c) for c in cells])
        except ValueError:
            continue
    return rows


def fig3_table(paths: list[Path]) -> dict:
    dmso_series, k10_series, t_ref = [], [], None
    for p in paths:
        rows = read_instrument(p)
        if len(rows) < 2:
            sys.exit(f"{p} のデータ行が少なすぎる気がする。CSVが壊れてない？")
        t = [r[0] for r in rows]
        if t_ref is None:
            t_ref = t
        dmso = [sum(r[2:6]) / 4 for r in rows]
        k10 = [sum(r[6:10]) / 4 for r in rows]
        if dmso[0] == 0 or k10[0] == 0:
            sys.exit(f"{p} の最初の行の値が0でした。CSVが壊れてない？")
        dmso_series.append([v / dmso[0] for v in dmso])
        k10_series.append([v / k10[0] for v in k10])
    n = min(len(s) for s in dmso_series)
    dmso_mean, dmso_sd, k10_mean, k10_sd = [], [], [], []
    for i in range(n):
        dvals = [s[i] for s in dmso_series]
        kvals = [s[i] for s in k10_series]
        dmso_mean.append(statistics.mean(dvals))
        dmso_sd.append(statistics.stdev(dvals))
        k10_mean.append(statistics.mean(kvals))
        k10_sd.append(statistics.stdev(kvals))
    return dict(t=t_ref[:n], dmso_mean=dmso_mean, dmso_sd=dmso_sd, k10_mean=k10_mean, k10_sd=k10_sd)


def fingerprint_of(paths: list[Path]) -> str:
    """3つの入力ファイルの指紋。SHA-256を並べ替えてつないだもののSHA-256、先頭8文字。"""
    hashes = sorted(hashlib.sha256(p.read_bytes()).hexdigest() for p in paths)
    return hashlib.sha256("".join(hashes).encode("ascii")).hexdigest()[:8]


def resolve_paths(argv: list[str]) -> list[Path]:
    if len(argv) == 3:
        paths = [Path(a) for a in argv]
        for p in paths:
            if not p.is_file():
                sys.exit(f"見つかりません: {p}")
        return paths
    if len(argv) == 0:
        indir = HERE / "図3_input"
        if not indir.is_dir():
            sys.exit(f"見つかりません: {indir}")
        here_inputs = sorted(p for p in indir.iterdir() if p.is_file() and p.suffix.lower() == ".csv")
        if len(here_inputs) != 3:
            sys.exit(f"CSVが3個ではありません（{len(here_inputs)}個）")
        return here_inputs
    sys.exit(
        "使い方: python make_fig3.py\n"
        "     （図3_input/ の CSV 3個を読む）\n"
        "     または: python make_fig3.py <CSV1> <CSV2> <CSV3>\n"
        f"CSVが{len(argv)}個指定されています。"
    )


def main() -> None:
    paths = resolve_paths(sys.argv[1:])
    table = fig3_table(paths)
    fp = fingerprint_of(paths)
    print(f"入力ファイルの指紋: {fp}（図に残す控え）")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib が無いので図は描きません。")
        return

    fig, ax = plt.subplots(figsize=(5, 3.5))
    t = table["t"]
    dm, ds = table["dmso_mean"], table["dmso_sd"]
    km, ks = table["k10_mean"], table["k10_sd"]
    ax.plot(t, dm, color="black", label="DMSO")
    ax.fill_between(t, [a - b for a, b in zip(dm, ds)], [a + b for a, b in zip(dm, ds)], color="black", alpha=0.15)
    ax.plot(t, km, color="0.5", label="化合物K 10 µM")
    ax.fill_between(t, [a - b for a, b in zip(km, ks)], [a + b for a, b in zip(km, ks)], color="0.5", alpha=0.25)
    ax.set_xlim(0, 96)
    ax.set_xlabel("時間 (h)")
    ax.set_ylabel("正規化発光（開始時=1）")
    ax.set_title("図3  n = 3")
    ax.legend(fontsize=8)
    out = Path.cwd() / "図3_再現.png"
    try:
        fig.savefig(out, dpi=150)
    except PermissionError:
        print(f"{out} に書き込めませんでした。保存先を変えて実行してみてください。")
        return
    print(f"{out.name} を書き出しました。")


if __name__ == "__main__":
    main()
