"""Move the files of a local proc_data into the proc_data on the external disk, merging
every file with the file of the same name (same path inside proc_data) already there.

    merge_proc_data.py <src proc_data> <dst proc_data>

Called by loop_runs.sh (offload_proc_data in resources.sh) with no job running.
For every file in <src>:
  - no file with the same name in <dst>: moved there;
  - .csv: its rows (header left out) are added at the end of the file in <dst>;
    a different header is an error and the local file is kept;
  - .pkl: rows concatenated, then the rows of a setting processed again replace the old ones;
  - processed_settings.txt: union of the lines, and the local copy stays
    (loop_runs.sh and dump_results.py read it to skip the settings already done);
  - anything else (e.g. images): the local version replaces the one in <dst>.
Every file in <dst> is written to a .tmp file and then renamed, and the local file is removed
only after that. Exit status 1 if some file could not be merged (it stays in <src>).
"""
import os, sys, shutil
from pathlib import Path
import pandas as pd
import data_extractor as dex

MARKER = ".offloaded"


def replace_with(tmp: Path, dst: Path) -> None:
    with open(tmp, "rb+") as f:
        os.fsync(f.fileno())
    os.replace(tmp, dst)


def merge_csv(src: Path, dst: Path, tmp: Path) -> None:
    with open(src, newline="") as f:
        src_lines = f.readlines()
    if not src_lines:
        return
    with open(dst, newline="") as f:
        dst_header = f.readline()
    if dst_header.rstrip("\r\n") != src_lines[0].rstrip("\r\n"):
        raise ValueError(f"header of {src} differs from {dst}")
    shutil.copyfile(dst, tmp)
    with open(tmp, "rb+") as f:
        f.seek(0, os.SEEK_END)
        if f.tell() > 0:
            f.seek(-1, os.SEEK_END)
            if f.read(1) != b"\n":
                f.write(b"\n")
    with open(tmp, "a", newline="") as f:
        for line in src_lines[1:]:
            f.write(line if line.endswith("\n") else line + "\n")


def merge_pkl(src: Path, dst: Path, tmp: Path) -> None:
    df = pd.concat([pd.read_pickle(dst), pd.read_pickle(src)], ignore_index=True)
    dex.dedup_settings(df).to_pickle(tmp)


def merge_done_list(src: Path, dst: Path, tmp: Path) -> None:
    lines = []
    for p in (dst, src):
        if p.exists():
            with open(p) as f:
                lines += [l.rstrip("\n") for l in f if l.strip()]
    with open(tmp, "w") as f:
        f.writelines(l + "\n" for l in dict.fromkeys(lines))


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    src_root, dst_root = Path(sys.argv[1]), Path(sys.argv[2])
    if not src_root.is_dir():
        print(f"{src_root} is not a folder", file=sys.stderr)
        return 1
    dst_root.mkdir(parents=True, exist_ok=True)

    merged = moved = failed = 0
    for src in sorted(p for p in src_root.rglob("*") if p.is_file() or p.is_symlink()):
        rel = src.relative_to(src_root)
        if rel.name == MARKER or rel.name.endswith(".tmp"):
            continue
        dst = dst_root / rel
        tmp = dst.with_name(dst.name + ".tmp")
        keep_local = rel.name == dex.DONE_LIST
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            if keep_local:
                merge_done_list(src, dst, tmp)
            elif not dst.exists():
                shutil.copyfile(src, tmp)
            elif src.suffix == ".csv":
                merge_csv(src, dst, tmp)
            elif src.suffix == ".pkl":
                merge_pkl(src, dst, tmp)
            else:
                shutil.copyfile(src, tmp)
            existed = dst.exists()
            if tmp.exists():
                replace_with(tmp, dst)
            if not keep_local:
                src.unlink()
            if existed:
                merged += 1
            else:
                moved += 1
        except Exception as e:
            failed += 1
            tmp.unlink(missing_ok=True)
            print(f"Merge failed for {rel}: {e} (kept in {src_root})", file=sys.stderr)

    # Folders left empty by the move (the root stays)
    for d in sorted((p for p in src_root.rglob("*") if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
        try:
            d.rmdir()
        except OSError:
            pass

    print(f"proc_data merge into {dst_root}: {merged} merged, {moved} moved, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
