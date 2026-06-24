from __future__ import annotations

import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from odt_utils import create_odt, create_review_odt
from runner import load_task
from verifier import verify


class VerifierTest(unittest.TestCase):
    def test_accepts_matching_document(self) -> None:
        task = load_task(ROOT / "tasks" / "task001.yaml")
        with TemporaryDirectory() as tmp:
            output = Path(tmp) / "output.odt"
            create_review_odt(output)
            result = verify(task, output)

        self.assertTrue(result.success)
        self.assertEqual(result.missing, [])

    def test_rejects_missing_required_text(self) -> None:
        task = load_task(ROOT / "tasks" / "task001.yaml")
        with TemporaryDirectory() as tmp:
            output = Path(tmp) / "output.odt"
            create_odt(output, task["expected"]["title"], ["## Executive Summary"])
            result = verify(task, output)

        self.assertFalse(result.success)
        self.assertIn("Net Revenue Retention", result.missing)
        self.assertIn("missing chart image: Pictures/monthly_revenue_margin_chart.svg", result.missing)


if __name__ == "__main__":
    unittest.main()
