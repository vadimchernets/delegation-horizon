"""Tests for the figure scripts (figures/). They need matplotlib and are skipped without it.
Run from the repository root: python3 -m unittest tests.test_figures"""
import importlib.util
import os
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "figures"))
import horizon  # noqa: E402
import figure_a4_checking_process as a4  # noqa: E402

HAVE_MPL = importlib.util.find_spec("matplotlib") is not None


def draw(folder, name):
    env = dict(os.environ, MPLCONFIGDIR=str(Path(folder) / "mpl"))
    r = subprocess.run([sys.executable, str(ROOT / "figures" / "figure_a4_checking_process.py"), "--out",
                        str(Path(folder) / name)], capture_output=True, text=True, timeout=180, env=env)
    return r


class FigureA4(unittest.TestCase):
    def test_credit_row_follows_the_rule(self):
        # the cells drawn as counting are exactly the checks horizon.py counts
        counted = {value for value in a4.RECORDED if value in horizon.INDEPENDENT}
        self.assertEqual(counted, {"other_family_with_sources", "hidden_tests"})
        self.assertIn(a4.RECORDED.index("same_family"), a4.NO_CREDIT)
        self.assertIn("no credit", a4.credit_row()[2])

    @unittest.skipUnless(HAVE_MPL, "matplotlib is not installed; the figure is drawn only where it is")
    def test_draws_the_same_png_and_svg_every_time(self):
        with tempfile.TemporaryDirectory() as d:
            first, second = draw(d, "a"), draw(d, "b")
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            png = (Path(d) / "a.png").read_bytes()
            self.assertEqual(png[:8], b"\x89PNG\r\n\x1a\n")
            self.assertEqual(struct.unpack(">II", png[16:24])[0], 2000)
            self.assertEqual(png, (Path(d) / "b.png").read_bytes())
            self.assertEqual((Path(d) / "a.svg").read_bytes(), (Path(d) / "b.svg").read_bytes())


if __name__ == "__main__":
    unittest.main()
