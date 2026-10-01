#!/usr/bin/env python3
"""Write a .mapszip from a map and its files, every entry stored as it is.

    tools/pack-mapszip.py out.mapszip my-map.mapson tiles/<cacheKey>/tiles.pmtiles=local.pmtiles
"""
import hashlib
import json
import pathlib
import struct
import sys

MAGIC = b"RKZS"
VERSION = 2


def pack(out, entries):
    """`entries` is `(path, bytes)`, `map.mapson` among them."""
    manifest = {"entries": [{"path": path, "size": len(body), "compressedSize": len(body),
                             "sha256": hashlib.sha256(body).hexdigest(), "stored": True}
                            for path, body in entries]}
    head = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    with open(out, "wb") as f:
        f.write(MAGIC + bytes([VERSION]) + struct.pack(">I", len(head)) + head)
        for _path, body in entries:
            f.write(body)


def main(args):
    if len(args) < 2:
        raise SystemExit(__doc__)
    out, mapson, *rest = args
    entries = [("map.mapson", pathlib.Path(mapson).read_bytes())]
    for pair in rest:
        path, _, local = pair.partition("=")
        entries.append((path, pathlib.Path(local).read_bytes()))
    pack(out, entries)


if __name__ == "__main__":
    main(sys.argv[1:])
