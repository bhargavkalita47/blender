#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Blender for Web contributors
# SPDX-License-Identifier: GPL-2.0-or-later
"""Resolve and install an OFFICIAL Blender binary built from the pinned source.

Uses Blender Buildbot's documented JSON API; refuses unrelated 5.4 Alpha builds,
other commits or unofficial mirrors. The actual bpy.app.build_hash is checked
again inside the Blender reference script before comparison.
"""
import hashlib
import json
import pathlib
import subprocess
import sys
import urllib.parse
import urllib.request

PINNED = "67e5a5f874cf37e2a114cebd24f219d8c44a16ad"
PREFIX = PINNED[:12]
API = ("https://builder.blender.org/download/daily/?format=json&v=2",
       "https://builder.blender.org/download/daily/archive/?format=json&v=2")
MAX_BYTES = 1_200_000_000
CHUNK = 2 * 1024 * 1024


def load_api(url):
    req = urllib.request.Request(url, headers={"User-Agent": "BlenderWebPinnedReference/1.0"})
    with urllib.request.urlopen(req, timeout=45) as response:
        body = response.read(15 * 1024 * 1024)
    obj = json.loads(body)
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        return obj.get("builds", obj.get("data", []))
    raise ValueError("Unexpected Blender Buildbot metadata shape")


def matching(entry):
    if not isinstance(entry, dict):
        return False
    if not str(entry.get("hash", "")).lower().startswith(PREFIX):
        return False
    if str(entry.get("app", "Blender")).lower() != "blender":
        return False
    if not str(entry.get("version", "")).startswith("5.4.0"):
        return False
    if str(entry.get("platform", "")).lower() != "linux":
        return False
    if str(entry.get("architecture", "")).lower() not in ("x86_64", "amd64"):
        return False
    if str(entry.get("file_extension", "")).lower() not in ("xz", "tar.xz"):
        return False
    url = str(entry.get("url", ""))
    host = urllib.parse.urlparse(url)
    if host.scheme != "https" or host.netloc not in ("cdn.builder.blender.org", "builder.blender.org"):
        return False
    basename = pathlib.PurePosixPath(host.path).name
    return PREFIX in basename and basename.endswith(".tar.xz")


def main():
    out = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else
                       "build/blender_web/pinned_reference").resolve()
    out.mkdir(parents=True, exist_ok=True)
    errors = []
    matches = []
    for api in API:
        try:
            rows = load_api(api)
            if not isinstance(rows, list):
                raise ValueError("Build list not an array")
            matches += [entry for entry in rows if matching(entry)]
        except Exception as err:
            errors.append(f"{api}: {type(err).__name__} {err}")
    if not matches:
        raise RuntimeError("No official Blender Linux build for exact pinned "
                           f"SHA prefix {PREFIX}. API errors: {errors}")
    item = sorted(matches, key=lambda a: int(a.get("file_mtime", 0)), reverse=True)[0]
    url = str(item["url"])
    archive = out / pathlib.PurePosixPath(urllib.parse.urlparse(url).path).name
    expected_size = int(item.get("file_size") or 0)
    assert 10_000_000 <= expected_size <= MAX_BYTES, "Unexpected Blender archive size"
    req = urllib.request.Request(url, headers={"User-Agent": "BlenderWebPinnedReference/1.0"})
    digest = hashlib.sha256()
    total = 0
    with urllib.request.urlopen(req, timeout=180) as src, archive.open("wb") as dest:
        while True:
            chunk = src.read(CHUNK)
            if not chunk:
                break
            total += len(chunk)
            assert total <= MAX_BYTES, "Blender archive download exceeds safety limit"
            digest.update(chunk)
            dest.write(chunk)
    assert total == expected_size, (
        f"Incomplete official archive: expected {expected_size}, received {total}")
    subprocess.run(["tar", "-xJf", str(archive), "-C", str(out)],
                   check=True, timeout=150)
    candidates = sorted(p for p in out.glob("blender-*/blender") if p.is_file())
    assert len(candidates) == 1, f"Expected exactly one unpacked Blender binary, got {candidates}"
    binary = candidates[0]
    binary.chmod(binary.stat().st_mode | 0o111)
    # Preserve evidence and make the binary path available to the workflow.
    provenance = {"source": "Official Blender Buildbot API",
                  "pinned_git_sha": PINNED,
                  "build_metadata_hash": item["hash"],
                  "download_url": url,
                  "archive_name": archive.name,
                  "archive_size_bytes": total,
                  "archive_sha256": digest.hexdigest(),
                  "blender_binary": str(binary),
                  "metadata_api_errors": errors}
    (out / "reference_provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    (out / "blender_path.txt").write_text(str(binary) + "\n")
    print("Pinned Blender binary:", binary)
    print("Reference source SHA:", item["hash"])
    print("Archive SHA256:", digest.hexdigest())


if __name__ == "__main__":
    main()
