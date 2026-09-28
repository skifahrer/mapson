#!/usr/bin/env python3
"""Validate .mapson and .serverson files against their schemas.

    pip install jsonschema
    tools/validate.py my-map.mapson my-servers.serverson
    tools/validate.py --expect-invalid tests/invalid/*.mapson

Each file is checked against the schema its extension names.
Exits 1 when any file does not come out as expected.
"""
import argparse
import json
import pathlib
import sys

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCHEMAS = ROOT / "schema" / "v1"
KINDS = {".mapson": "mapson", ".rikimap": "mapson", ".serverson": "serverson"}


def load(name):
    return json.loads((SCHEMAS / f"{name}.schema.json").read_text(encoding="utf-8"))


def validators(override=None):
    schemas = {name: load(name) for name in set(KINDS.values())}
    if override:
        schema = json.loads(pathlib.Path(override).read_text(encoding="utf-8"))
        schemas = {name: schema for name in schemas}
    # serverson's $refs point into mapson's $defs
    registry = Registry().with_resources(
        (schema["$id"], Resource.from_contents(schema)) for schema in schemas.values())
    made = {}
    for name, schema in schemas.items():
        Draft202012Validator.check_schema(schema)
        made[name] = Draft202012Validator(schema, registry=registry)
    return made


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
    parser.add_argument("--schema", help="check every file against this schema instead")
    args = parser.parse_args()

    checking = validators(args.schema)

    failed = False
    for path in args.files:
        kind = KINDS.get(pathlib.Path(path).suffix.lower(), "mapson")
        found = issues(checking[kind], path)
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
