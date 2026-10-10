#!/usr/bin/env python3
"""Low-cost integrity checks for the historical tutorial assets."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

import numpy as np
from ase.io import read


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "csc_data_74.xyz"
MODEL = ROOT / "model" / "csc_ver.xml"


def digest(path: Path, algorithm: str) -> str:
    value = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def check_xyz() -> None:
    frames = read(DATA, index=":")
    if len(frames) != 74:
        fail(f"expected 74 frames, found {len(frames)}")
    if any(len(atoms) != 32 for atoms in frames):
        fail("not every frame contains 32 atoms")
    if any(atoms.get_chemical_formula() != "Fe16Se16" for atoms in frames):
        fail("not every frame has formula Fe16Se16")
    if any(atoms.calc is None or "energy" not in atoms.calc.results for atoms in frames):
        fail("one or more frames has no energy label")

    geometry_groups: dict[str, list[int]] = defaultdict(list)
    for index, atoms in enumerate(frames, start=1):
        numeric = np.concatenate((atoms.cell.array.ravel(), atoms.positions.ravel()))
        payload = "|".join(atoms.get_chemical_symbols()).encode()
        payload += np.round(numeric, 8).tobytes()
        geometry_groups[hashlib.sha256(payload).hexdigest()].append(index)

    if len(geometry_groups) != 59:
        fail(f"expected 59 unique geometries, found {len(geometry_groups)}")
    repeated = [indices for indices in geometry_groups.values() if len(indices) > 1]
    if repeated != [list(range(33, 49))]:
        fail(f"unexpected duplicate-frame groups: {repeated}")

    print("PASS XYZ: 74 records, 32 atoms each, 59 unique geometries")
    print("          duplicate geometry occurs in frames 33-48")


def check_model() -> None:
    root = ET.parse(MODEL).getroot()
    references = []
    for node in root.findall(".//gpCoordinates"):
        filename = node.attrib.get("sparseX_filename")
        expected_md5 = node.attrib.get("sparseX_md5sum")
        if filename:
            references.append((filename, expected_md5))

    if len(references) != 9:
        fail(f"expected 9 SparseX references, found {len(references)}")
    for filename, expected_md5 in references:
        sparse_file = MODEL.parent / filename
        if not sparse_file.is_file():
            fail(f"missing SparseX file: {sparse_file.name}")
        actual_md5 = digest(sparse_file, "md5")
        if expected_md5 != actual_md5:
            fail(
                f"MD5 mismatch for {sparse_file.name}: "
                f"XML={expected_md5}, file={actual_md5}"
            )

    print("PASS model: XML parses and all 9 referenced SparseX MD5 values match")
    print(f"            XML SHA256 {digest(MODEL, 'sha256')}")


def main() -> None:
    check_xyz()
    check_model()


if __name__ == "__main__":
    main()
