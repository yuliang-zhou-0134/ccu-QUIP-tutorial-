"""Regression test for rattle.py. Run: python -m unittest test_rattle.py"""
import contextlib
import hashlib
import io
import os
from pathlib import Path
import runpy
import tempfile
import unittest

from ase import Atoms
from ase.io import write

SCRIPT = Path(__file__).with_name("rattle.py").resolve()


def generate(workdir):
    atoms = Atoms(
        symbols=["Fe", "Fe", "Se", "Se"],
        scaled_positions=[
            (0.75, 0.25, 0), (0.25, 0.75, 0),
            (0.25, 0.25, 0.2674), (0.75, 0.75, 0.7326),
        ],
        cell=[(3.55, 0, 0), (0, 3.55, 0), (0, 0, 5.20)],
        pbc=True,
    )
    write(workdir / "POSCAR", atoms, format="vasp", vasp5=True, direct=True)
    previous = Path.cwd()
    try:
        os.chdir(workdir)
        with contextlib.redirect_stdout(io.StringIO()):
            runpy.run_path(str(SCRIPT), run_name="__main__")
    finally:
        os.chdir(previous)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class RattleTests(unittest.TestCase):
    def test_fifty_unique_and_reproducible(self):
        with tempfile.TemporaryDirectory(prefix="rattle_a_") as a, \
             tempfile.TemporaryDirectory(prefix="rattle_b_") as b:
            a, b = Path(a), Path(b)
            generate(a)
            generate(b)
            hashes = []
            for i in range(1, 51):
                name = f"task_{i:03d}"
                scf = a / name / "scf" / "POSCAR"
                csc = a / name / "csc" / "POSCAR"
                self.assertTrue(scf.is_file() and csc.is_file(), name)
                self.assertEqual(digest(scf), digest(csc), name)
                self.assertEqual(digest(scf), digest(b / name / "scf" / "POSCAR"), name)
                hashes.append(digest(scf))
            self.assertEqual(len(set(hashes)), 50)

    def test_existing_directory_is_not_overwritten(self):
        with tempfile.TemporaryDirectory(prefix="rattle_existing_") as temp:
            wd = Path(temp)
            atoms = Atoms("FeSe", scaled_positions=[(0, 0, 0), (0.5, 0.5, 0.5)],
                          cell=[3, 3, 4], pbc=True)
            write(wd / "POSCAR", atoms, format="vasp")
            (wd / "task_001").mkdir()
            previous = Path.cwd()
            try:
                os.chdir(wd)
                with self.assertRaises(FileExistsError):
                    with contextlib.redirect_stdout(io.StringIO()):
                        runpy.run_path(str(SCRIPT), run_name="__main__")
            finally:
                os.chdir(previous)
            self.assertFalse((wd / "task_002").exists())


if __name__ == "__main__":
    unittest.main()
