from __future__ import annotations

import unittest
from unittest.mock import patch

import pandas as pd

from ccsdb import pages


class EntryTemplateTests(unittest.TestCase):
    def test_complete_entry_is_loaded_as_a_new_entry_template(self) -> None:
        state = {"entry_form_generation": 3, "entry_protein": "old draft"}
        template = {
            "paper": {"id": "paper-1", "doi": "10.1002/example", "title": "Example paper"},
            "entry": {
                "id": "entry-1",
                "logger_id": "user-1",
                "protein": "Protein A",
                "ionisation_mode": "Negative",
                "instrument_family": "Custom instrument",
                "native": False,
                "ims_type": "TWIMS",
                "subunits": 2,
                "oligomer_type": "Hetero",
                "drift_gas_calibration": "Helium",
                "drift_gas_measurement": "Custom gas",
                "measurement_conditions": "condition text",
                "sample_description": "sample text",
                "supplier_details": "supplier text",
                "supplier_details_provided": True,
                "uniprot_id": "P12345",
                "uniprot_id_provided": True,
                "pdb_id": "1ABC",
                "pdb_id_provided": True,
                "sequence": "PEPTIDE",
                "sequence_provided": True,
                "sequence_mass": 1000.25,
                "sequence_mass_provided": True,
                "measured_mass": 1001.5,
                "measured_mass_provided": True,
            },
            "measurements": [
                {
                    "measurement_type": "charge_state",
                    "charge_state": 7,
                    "charge_state_min": None,
                    "charge_state_max": None,
                    "ccs_value": 1800.0,
                    "error": 10.0,
                    "provided": True,
                    "from_graph": False,
                },
                {
                    "measurement_type": "global",
                    "charge_state": None,
                    "charge_state_min": 6,
                    "charge_state_max": 9,
                    "ccs_value": 1850.0,
                    "error": 12.0,
                    "provided": False,
                    "from_graph": True,
                },
            ],
        }

        with patch.object(pages.st, "session_state", state):
            pages._use_entry_as_template(template)

        self.assertEqual(state["navigation"], "Add entry")
        self.assertEqual(state["entry_doi"], "10.1002/example")
        self.assertEqual(state["entry_protein"], "Protein A")
        self.assertEqual(state["entry_instrument_choice"], "Other")
        self.assertEqual(state["entry_instrument_other"], "Custom instrument")
        self.assertEqual(state["entry_measurement_gas_choice"], "Other")
        self.assertEqual(state["entry_measurement_gas_other"], "Custom gas")
        self.assertEqual(state["entry_global_ccs_value"], 1850.0)
        self.assertEqual(state["entry_global_charge_min"], 6)
        self.assertEqual(state["entry_measurement_seed"].iloc[0]["charge_state"], 7)
        self.assertEqual(state["entry_form_generation"], 4)
        self.assertEqual(state["entry_form_mode"], "new")
        self.assertNotIn("entry_edit_id", state)

    def test_complete_entry_is_loaded_for_editing_with_its_identity(self) -> None:
        state = {"entry_form_generation": 1}
        template = {
            "paper": {"id": "paper-1", "doi": "10.1002/example", "title": "Example paper"},
            "entry": {
                "id": "entry-1",
                "logger_id": "user-1",
                "protein": "Protein A",
                "instrument_family": "Synapt",
                "drift_gas_calibration": "Helium",
                "drift_gas_measurement": "Nitrogen",
            },
            "measurements": [
                {
                    "measurement_type": "charge_state",
                    "charge_state": 7,
                    "ccs_value": 1800.0,
                }
            ],
        }

        with patch.object(pages.st, "session_state", state):
            pages._edit_entry(template)

        self.assertEqual(state["navigation"], "Add entry")
        self.assertEqual(state["entry_form_mode"], "edit")
        self.assertEqual(state["entry_edit_id"], "entry-1")
        self.assertNotIn("entry_template_source", state)
        self.assertEqual(state["entry_protein"], "Protein A")


class DataTableTests(unittest.TestCase):
    def test_background_columns_are_hidden_without_changing_download_data(self) -> None:
        data = pd.DataFrame(
            [
                {
                    "entry_id": "entry-1",
                    "paper_id": "paper-1",
                    "paper_source": "catalogue.csv",
                    "entry_status": "submitted",
                    "entry_created_at": "2026-09-11",
                    "entry_updated_at": "2026-09-11",
                    "measurement_id": "measurement-1",
                    "measurement_created_at": "2026-09-11",
                    "protein": "Protein A",
                    "ccs_value": 1800.0,
                }
            ],
            index=[7],
        )

        visible = pages._table_data(data)

        self.assertEqual(list(visible.columns), ["protein", "ccs_value"])
        self.assertEqual(list(visible.index), [7])
        self.assertIn("entry_id", data.columns)
        self.assertEqual(data.loc[7, "entry_id"], "entry-1")


if __name__ == "__main__":
    unittest.main()
