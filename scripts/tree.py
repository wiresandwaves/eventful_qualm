#!/usr/bin/env python
"""
Print a clean tree of the repo (filters out venv/cache/build stuff).
Usage:
  python tools/tree.py                # prints to stdout
  python tools/tree.py --markdown     # markdown code block
  python tools/tree.py --max-depth 4  # limit depth
  python tools/tree.py --out repo_tree.txt
"""
from __future__ import annotations

import argparse
import pathlib
import sys

DEFAULT_EXCLUDES = {
    ".git",
    ".venv",
    "__pycache__",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    "dist",
    "build",
    ".idea",
    ".vscode",
    ".coverage",
    "htmlcov",
    ".DS_Store",
}


def iter_tree(root: pathlib.Path, max_depth: int, excludes: set[str]):
    root = root.resolve()

    def walk(dirpath: pathlib.Path, prefix: str, depth: int):
        if depth > max_depth:
            return
        entries = []
        for p in sorted(dirpath.iterdir(), key=lambda p: (p.is_file(), p.name.lower())):
            name = p.name
            if name in excludes:
                continue
            # filter “hidden” files you don’t care about
            if name.endswith(".pyc"):
                continue
            entries.append(p)
        count = len(entries)
        for i, p in enumerate(entries):
            connector = "└── " if i == count - 1 else "├── "
            line = f"{prefix}{connector}{p.name}"
            yield line
            if p.is_dir():
                extension = "    " if i == count - 1 else "│   "
                yield from walk(p, prefix + extension, depth + 1)

    yield root.name
    yield from walk(root, "", 1)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", default=".")
    ap.add_argument("--max-depth", type=int, default=8)
    ap.add_argument("--markdown", action="store_true", help="wrap output in ```text code fence")
    ap.add_argument(
        "--exclude", action="append", default=[], help="extra names to exclude (dir or file names)"
    )
    ap.add_argument("--out", default="", help="write to file instead of stdout")
    args = ap.parse_args(argv)

    root = pathlib.Path(args.path)
    excludes = DEFAULT_EXCLUDES.union(set(args.exclude))
    lines = list(iter_tree(root, args.max_depth, excludes))

    output = "\n".join(lines)
    if args.markdown:
        output = "```text\n" + output + "\n```"

    if args.out:
        pathlib.Path(args.out).write_text(output, encoding="utf-8")
        print(f"Wrote {args.out}")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
