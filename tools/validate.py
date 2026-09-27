#!/usr/bin/env python3
"""Validate .mapson files against the mapson schema.

    pip install jsonschema
    tools/validate.py my-map.mapson other.mapson
    tools/validate.py --expect-invalid tests/invalid/*.mapson

Exits 1 when any file does not come out as expected.
"""
import argparse
import json
import pathlib
import sys

from jsonschema import Draft202012Validator

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCHEMA = ROOT / "schema" / "v1" / "mapson.schema.json"


def issues(validator, path):
    try:
        document = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        return [f"not readable JSON: {error}"]
    found = sorted(validator.iter_errors(document), key=lambda e: list(e.absolute_path))
    return [f"{e.json_path}: {e.message}" for e in found]


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("files", nargs="+")
    parser.add_argument("--expect-invalid", action="store_true",
                        help="every file must FAIL validation")
    parser.add_argument("--schema", default=str(SCHEMA))
    args = parser.parse_args()

    schema = json.loads(pathlib.Path(args.schema).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)

    failed = False
    for path in args.files:
        found = issues(validator, path)
        if args.expect_invalid:
            ok = bool(found)
            print(f"{'ok  ' if ok else 'FAIL'} {path}: "
                  f"{found[0] if found else 'validated, but should not have'}")
        else:
            ok = not found
            print(f"{'ok  ' if ok else 'FAIL'} {path}")
            for line in found:
                print(f"     {line}")
        failed |= not ok
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
