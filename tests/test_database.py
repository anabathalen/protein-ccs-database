from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from sqlalchemy import select

from ccsdb.database import PAPER_SEED, Database, audit_log
from ccsdb.doi import normalize_doi, validate_doi


class DoiTests(unittest.TestCase):
    def test_normalizes_common_doi_forms(self) -> None:
        self.assertEqual(normalize_doi("https://doi.org/10.1021/ABC.123."), "10.1021/abc.123")
        self.assertEqual(validate_doi("doi:10.1002/jms.1383"), "10.1002/jms.1383")

    def test_rejects_non_doi_values(self) -> None:
        with self.assertRaises(ValueError):
            validate_doi("12978365.498765")


class DatabaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_directory = tempfile.TemporaryDirectory()
        database_path = Path(self.temp_directory.name) / "test.db"
        self.database = Database(f"sqlite:///{database_path}")
        self.database.initialize()

    def tearDown(self) -> None:
        self.database.engine.dispose()
        self.temp_directory.cleanup()

    def test_seed_contains_only_catalogue_papers(self) -> None:
        catalogue = json.loads(PAPER_SEED.read_text(encoding="utf-8"))
        self.assertEqual(len(catalogue), 532)
        self.assertTrue(all(item["source"] == "native_IM_MS_papers_20251215.csv" for item in catalogue))
        self.assertEqual(self.database.counts(), {"papers": 532, "entries": 0, "measurements": 0, "users": 0})

    def test_entry_global_ccs_export_and_leaderboard(self) -> None:
        user = self.database.ensure_user("ana@example.org", "Ana")
        self.database.update_nickname(user["id"], "Ana")
        paper = self.database.find_paper("10.1002/jms.1383")
        self.assertIsNotNone(paper)
        entry_id = self.database.create_entry(
            user["id"],
            paper["id"],
            {
                "protein": "Example protein",
                "ionisation_mode": "Positive",
                "instrument_family": "Synapt",
                "native": True,
                "ims_type": "TWIMS",
                "subunits": 2,
            },
            [
                {
                    "measurement_type": "charge_state",
                    "charge_state": 8,
                    "ccs_value": 2100.0,
                    "error": 20.0,
                },
                {
                    "measurement_type": "global",
                    "charge_state_min": 7,
                    "charge_state_max": 10,
                    "ccs_value": 2200.0,
                },
            ],
        )
        self.assertTrue(entry_id)
        self.assertEqual(self.database.find_paper("10.1002/jms.1383")["entry_count"], 1)
        export = self.database.export_data()
        self.assertEqual(len(export), 2)
        self.assertIn("logger_email", export.columns)
        self.assertIn("abstract", export.columns)
        self.assertEqual(set(export["measurement_type"]), {"charge_state", "global"})
        template = self.database.get_entry_template(entry_id)
        self.assertIsNotNone(template)
        self.assertEqual(template["paper"]["doi"], "10.1002/jms.1383")
        self.assertEqual(template["entry"]["protein"], "Example protein")
        self.assertEqual(len(template["measurements"]), 2)
        self.assertEqual(
            {row["measurement_type"] for row in template["measurements"]},
            {"charge_state", "global"},
        )
        original_created_at = template["entry"]["created_at"]
        self.database.update_entry(
            user["id"],
            entry_id,
            paper["id"],
            {
                "protein": "Corrected protein",
                "ionisation_mode": "Negative",
                "instrument_family": "Cyclic",
                "native": False,
                "ims_type": "TWIMS",
                "subunits": 1,
                "measurement_conditions": "Corrected conditions",
            },
            [
                {
                    "measurement_type": "charge_state",
                    "charge_state": 9,
                    "ccs_value": 2300.0,
                    "error": 15.0,
                    "provided": True,
                }
            ],
        )
        updated_template = self.database.get_entry_template(entry_id)
        self.assertEqual(updated_template["entry"]["protein"], "Corrected protein")
        self.assertEqual(updated_template["entry"]["measurement_conditions"], "Corrected conditions")
        self.assertEqual(updated_template["entry"]["created_at"], original_created_at)
        self.assertEqual(len(updated_template["measurements"]), 1)
        self.assertEqual(updated_template["measurements"][0]["charge_state"], 9)
        with self.database.engine.connect() as connection:
            actions = connection.execute(
                select(audit_log.c.action).where(audit_log.c.entity_id == entry_id)
            ).scalars().all()
        self.assertEqual(actions, ["created", "updated"])
        leaderboard = self.database.leaderboard().iloc[0]
        self.assertEqual(leaderboard["nickname"], "Ana")
        self.assertEqual(leaderboard["papers_logged"], 1)
        self.assertEqual(leaderboard["ccs_values"], 1)

    def test_only_original_contributor_can_edit_an_entry(self) -> None:
        owner = self.database.ensure_user("owner@example.org", "Owner")
        other = self.database.ensure_user("other@example.org", "Other")
        paper = self.database.find_paper("10.1002/jms.1383")
        entry_id = self.database.create_entry(
            owner["id"],
            paper["id"],
            {"protein": "Owner protein", "ims_type": "DTIMS"},
            [{"measurement_type": "charge_state", "charge_state": 5, "ccs_value": 1500.0}],
        )

        with self.assertRaisesRegex(PermissionError, "only edit entries you logged"):
            self.database.update_entry(
                other["id"],
                entry_id,
                paper["id"],
                {"protein": "Unauthorised change"},
                [{"measurement_type": "charge_state", "charge_state": 6, "ccs_value": 1600.0}],
            )

        unchanged = self.database.get_entry_template(entry_id)
        self.assertEqual(unchanged["entry"]["protein"], "Owner protein")
        self.assertEqual(unchanged["measurements"][0]["charge_state"], 5)


if __name__ == "__main__":
    unittest.main()
