#!/usr/bin/env python3
"""Copy the license files of every installed package (and of Python itself) into a folder.

The build scripts run this with the build environment's Python, so the Windows zip and the
AppImage carry the real license texts of what they bundle (Qt / PySide6 are LGPL-3.0, which
requires shipping the license and telling people where the source is).

Usage: <build python> packaging/collect_licenses.py <destination folder>
"""
import importlib.metadata as md
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, ".."))
LICENSE_NAME = re.compile(r"(^|/)(licen[cs]e|copying|notice|authors)[^/]*$", re.IGNORECASE)


def safe(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", name)


def collect(dest: str) -> int:
    os.makedirs(dest, exist_ok=True)
    count = 0
    for dist in sorted(md.distributions(), key=lambda d: (d.metadata["Name"] or "").lower()):
        name = dist.metadata["Name"] or "unknown"
        target = os.path.join(dest, safe(f"{name}-{dist.version}"))
        for f in dist.files or []:
            path = str(f).replace("\\", "/")
            in_dist_info = ".dist-info/" in path
            if not LICENSE_NAME.search(path) or (not in_dist_info and path.count("/") > 2):
                continue
            src = f.locate()
            if not os.path.isfile(src):
                continue
            os.makedirs(target, exist_ok=True)
            out = os.path.join(target, safe(path.split(".dist-info/", 1)[-1]))
            shutil.copyfile(src, out)
            count += 1
        lic = dist.metadata.get("License-Expression") or dist.metadata.get("License") or ""
        if lic and len(lic) < 200:
            os.makedirs(target, exist_ok=True)
            with open(os.path.join(target, "LICENSE-NAME.txt"), "w", encoding="utf-8") as fh:
                fh.write(lic.strip() + "\n")
    for cand in (os.path.join(sys.base_prefix, "LICENSE.txt"),
                 os.path.join(sys.base_prefix, "lib", f"python{sys.version_info[0]}.{sys.version_info[1]}", "LICENSE.txt")):
        if os.path.isfile(cand):
            os.makedirs(os.path.join(dest, "Python"), exist_ok=True)
            shutil.copyfile(cand, os.path.join(dest, "Python", "LICENSE.txt"))
            count += 1
            break
    shutil.copyfile(os.path.join(REPO, "LICENSE"), os.path.join(dest, "GlucOSC-LICENSE.txt"))
    shutil.copyfile(os.path.join(REPO, "THIRD-PARTY-NOTICES.md"), os.path.join(dest, "THIRD-PARTY-NOTICES.md"))
    return count


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    n = collect(sys.argv[1])
    print(f"Copied {n} license files to {sys.argv[1]}")
