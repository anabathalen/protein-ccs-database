"""Streamlit page renderers."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from .database import Database
from .doi import normalize_doi, validate_doi
from .plotting import PLOT_CONFIG, build_plot, standalone_html

LABELS = {
    "entry_id": "Entry ID",
    "paper_id": "Paper ID",
    "doi": "DOI",
    "pmid": "PMID",
    "paper_title": "Paper title",
    "authors": "Authors",
    "journal": "Journal",
    "publication_date": "Publication date",
    "publication_type": "Publication type",
    "paper_source": "Paper source",
    "protein": "Protein",
    "logged_by": "Logged by",
    "ionisation_mode": "Ionisation mode",
    "instrument_family": "Instrument family",
    "native": "Native",
    "ims_type": "IMS type",
    "subunits": "Subunits",
    "oligomer_type": "Oligomer type",
    "drift_gas_calibration": "Drift gas (calibration)",
    "drift_gas_measurement": "Drift gas (measurement)",
    "measurement_conditions": "Measurement conditions",
    "sample_description": "Sample description",
    "supplier_details": "Supplier details",
    "supplier_details_provided": "Supplier details provided",
    "uniprot_id": "UniProt ID",
    "uniprot_id_provided": "UniProt ID provided",
    "pdb_id": "PDB ID",
    "pdb_id_provided": "PDB ID provided",
    "sequence": "Sequence",
    "sequence_provided": "Sequence provided",
    "sequence_mass": "Sequence mass (Da)",
    "sequence_mass_provided": "Sequence mass provided",
    "measured_mass": "Measured mass (Da)",
    "measured_mass_provided": "Measured mass provided",
    "entry_created_at": "Entry created",
    "entry_updated_at": "Entry updated",
    "entry_status": "Entry status",
    "measurement_id": "Measurement ID",
    "measurement_type": "Measurement type",
    "charge_state": "Charge state",
    "charge_state_min": "Minimum charge state",
    "charge_state_max": "Maximum charge state",
    "ccs_value": "CCS (Å²)",
    "error": "CCS error (Å²)",
    "provided": "CCS provided",
    "from_graph": "CCS read from graph",
    "measurement_created_at": "Measurement created",
    "logger_id": "Logger ID",
    "logger_email": "Logger email",
    "abstract": "Abstract",
}

PLOT_AXES = {
    "charge_state": "Charge state",
    "ccs_value": "CCS (Å²)",
    "error": "CCS error (Å²)",
    "measured_mass": "Measured mass (Da)",
    "sequence_mass": "Sequence mass (Da)",
    "subunits": "Subunits",
    "charge_state_min": "Minimum charge state",
    "charge_state_max": "Maximum charge state",
}

COLOUR_FIELDS = {
    "protein": "Protein",
    "ims_type": "IMS type",
    "instrument_family": "Instrument family",
    "drift_gas_measurement": "Drift gas",
    "native": "Native",
    "ionisation_mode": "Ionisation mode",
    "oligomer_type": "Oligomer type",
    "measurement_type": "Measurement type",
    "logged_by": "Logged by",
}

INSTRUMENT_FAMILIES = ["", "Synapt", "Cyclic", "Agilent6560", "Vion", "timsTOF", "Other"]
DRIFT_GASES = ["", "Helium", "Nitrogen", "Argon", "Other"]
IMS_TYPES = ["DTIMS", "TWIMS", "TIMS"]
INDIVIDUAL_MEASUREMENT_COLUMNS = ["charge_state", "ccs_value", "error", "provided", "from_graph"]

# Retain these fields in the complete CSV export and internal row-selection
# logic, but leave them out of the user-facing data table and its filters.
TABLE_BACKGROUND_COLUMNS = {
    "entry_id",
    "paper_id",
    "paper_source",
    "entry_status",
    "entry_created_at",
    "entry_updated_at",
    "measurement_id",
    "measurement_created_at",
}

ENTRY_FORM_KEYS = [
    "entry_doi",
    "entry_protein",
    "entry_ionisation_mode",
    "entry_instrument_choice",
    "entry_instrument_other",
    "entry_native",
    "entry_ims_type",
    "entry_subunits",
    "entry_oligomer_type",
    "entry_calibration_gas_choice",
    "entry_calibration_gas_other",
    "entry_measurement_gas_choice",
    "entry_measurement_gas_other",
    "entry_measurement_conditions",
    "entry_sample_description",
    "entry_supplier_details",
    "entry_supplier_details_provided",
    "entry_uniprot_id",
    "entry_uniprot_id_provided",
    "entry_pdb_id",
    "entry_pdb_id_provided",
    "entry_sequence",
    "entry_sequence_provided",
    "entry_sequence_mass",
    "entry_sequence_mass_provided",
    "entry_measured_mass",
    "entry_measured_mass_provided",
    "entry_global_ccs_value",
    "entry_global_ccs_error",
    "entry_global_ccs_provided",
    "entry_global_ccs_from_graph",
    "entry_global_charge_min",
    "entry_global_charge_max",
]


def _text(value: Any) -> str:
    return "" if value is None else str(value)


def _choice_with_other(value: Any, choices: list[str]) -> tuple[str, str]:
    clean = _text(value)
    return (clean, "") if clean in choices[:-1] else ("Other", clean)


def _blank_individual_measurements() -> pd.DataFrame:
    return pd.DataFrame(
        [{"charge_state": None, "ccs_value": None, "error": None, "provided": False, "from_graph": False}],
        columns=INDIVIDUAL_MEASUREMENT_COLUMNS,
    )


def _clear_entry_form_state() -> None:
    for key in ENTRY_FORM_KEYS:
        st.session_state.pop(key, None)
    st.session_state.pop("entry_measurement_seed", None)
    st.session_state.pop("entry_template_source", None)
    st.session_state.pop("entry_form_mode", None)
    st.session_state.pop("entry_edit_id", None)
    for key in list(st.session_state):
        if key.startswith("entry_individual_measurements_"):
            st.session_state.pop(key, None)
    st.session_state["entry_form_generation"] = int(st.session_state.get("entry_form_generation", 0)) + 1


def _ensure_entry_defaults(default_doi: str = "") -> None:
    defaults = {
        "entry_doi": default_doi,
        "entry_protein": "",
        "entry_ionisation_mode": "Positive",
        "entry_instrument_choice": "",
        "entry_instrument_other": "",
        "entry_native": "Yes",
        "entry_ims_type": "DTIMS",
        "entry_subunits": 0,
        "entry_oligomer_type": "Homo",
        "entry_calibration_gas_choice": "",
        "entry_calibration_gas_other": "",
        "entry_measurement_gas_choice": "",
        "entry_measurement_gas_other": "",
        "entry_measurement_conditions": "",
        "entry_sample_description": "",
        "entry_supplier_details": "",
        "entry_supplier_details_provided": False,
        "entry_uniprot_id": "",
        "entry_uniprot_id_provided": False,
        "entry_pdb_id": "",
        "entry_pdb_id_provided": False,
        "entry_sequence": "",
        "entry_sequence_provided": False,
        "entry_sequence_mass": None,
        "entry_sequence_mass_provided": False,
        "entry_measured_mass": None,
        "entry_measured_mass_provided": False,
        "entry_global_ccs_value": None,
        "entry_global_ccs_error": None,
        "entry_global_ccs_provided": False,
        "entry_global_ccs_from_graph": False,
        "entry_global_charge_min": None,
        "entry_global_charge_max": None,
        "entry_measurement_seed": _blank_individual_measurements(),
        "entry_form_generation": 0,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _use_entry_as_template(template: dict[str, Any]) -> None:
    """Deep-copy a stored entry into a new-entry draft, as in the desktop app."""

    _clear_entry_form_state()
    entry = template["entry"]
    paper = template["paper"]
    measurements = template["measurements"]
    instrument_choice, instrument_other = _choice_with_other(entry.get("instrument_family"), INSTRUMENT_FAMILIES)
    calibration_choice, calibration_other = _choice_with_other(entry.get("drift_gas_calibration"), DRIFT_GASES)
    measurement_choice, measurement_other = _choice_with_other(entry.get("drift_gas_measurement"), DRIFT_GASES)
    global_row = next((row for row in measurements if row["measurement_type"] == "global"), None)
    individual_rows = [
        {column: row.get(column) for column in INDIVIDUAL_MEASUREMENT_COLUMNS}
        for row in measurements
        if row["measurement_type"] == "charge_state"
    ]

    st.session_state.update(
        {
            "selected_paper": paper,
            "entry_doi": paper.get("doi") or "",
            "entry_protein": _text(entry.get("protein")),
            "entry_ionisation_mode": _text(entry.get("ionisation_mode")) or "Positive",
            "entry_instrument_choice": instrument_choice,
            "entry_instrument_other": instrument_other,
            "entry_native": "Yes" if entry.get("native") else "No",
            "entry_ims_type": _text(entry.get("ims_type")) or "DTIMS",
            "entry_subunits": int(entry.get("subunits") or 0),
            "entry_oligomer_type": _text(entry.get("oligomer_type")) or "Homo",
            "entry_calibration_gas_choice": calibration_choice,
            "entry_calibration_gas_other": calibration_other,
            "entry_measurement_gas_choice": measurement_choice,
            "entry_measurement_gas_other": measurement_other,
            "entry_measurement_conditions": _text(entry.get("measurement_conditions")),
            "entry_sample_description": _text(entry.get("sample_description")),
            "entry_supplier_details": _text(entry.get("supplier_details")),
            "entry_supplier_details_provided": bool(entry.get("supplier_details_provided")),
            "entry_uniprot_id": _text(entry.get("uniprot_id")),
            "entry_uniprot_id_provided": bool(entry.get("uniprot_id_provided")),
            "entry_pdb_id": _text(entry.get("pdb_id")),
            "entry_pdb_id_provided": bool(entry.get("pdb_id_provided")),
            "entry_sequence": _text(entry.get("sequence")),
            "entry_sequence_provided": bool(entry.get("sequence_provided")),
            "entry_sequence_mass": entry.get("sequence_mass"),
            "entry_sequence_mass_provided": bool(entry.get("sequence_mass_provided")),
            "entry_measured_mass": entry.get("measured_mass"),
            "entry_measured_mass_provided": bool(entry.get("measured_mass_provided")),
            "entry_global_ccs_value": global_row.get("ccs_value") if global_row else None,
            "entry_global_ccs_error": global_row.get("error") if global_row else None,
            "entry_global_ccs_provided": bool(global_row and global_row.get("provided")),
            "entry_global_ccs_from_graph": bool(global_row and global_row.get("from_graph")),
            "entry_global_charge_min": global_row.get("charge_state_min") if global_row else None,
            "entry_global_charge_max": global_row.get("charge_state_max") if global_row else None,
            "entry_measurement_seed": pd.DataFrame(individual_rows, columns=INDIVIDUAL_MEASUREMENT_COLUMNS)
            if individual_rows
            else _blank_individual_measurements(),
            "entry_template_source": _text(entry.get("protein")),
            "entry_form_mode": "new",
            "navigation": "Add entry",
        }
    )


def _edit_entry(template: dict[str, Any]) -> None:
    """Load an existing entry into the form while retaining its identity."""

    _use_entry_as_template(template)
    st.session_state.pop("entry_template_source", None)
    st.session_state["entry_form_mode"] = "edit"
    st.session_state["entry_edit_id"] = template["entry"]["id"]


def _cancel_editing() -> None:
    _clear_entry_form_state()
    st.session_state.pop("selected_paper", None)
    st.session_state["navigation"] = "Data"


def _start_blank_entry() -> None:
    _clear_entry_form_state()
    st.session_state.pop("selected_paper", None)
    st.session_state["navigation"] = "Add entry"


def _display(data: pd.DataFrame) -> pd.DataFrame:
    return data.rename(columns=LABELS)


def _table_data(data: pd.DataFrame) -> pd.DataFrame:
    """Return the scientific/user-facing columns shown in the Streamlit table."""

    return data.drop(columns=TABLE_BACKGROUND_COLUMNS, errors="ignore")


def filter_dataframe(data: pd.DataFrame, key_prefix: str) -> pd.DataFrame:
    """Allow users to filter on any selected column."""

    if data.empty:
        return data
    selected = st.multiselect(
        "Filter by",
        options=list(data.columns),
        format_func=lambda column: LABELS.get(column, column.replace("_", " ").title()),
        key=f"{key_prefix}_filter_columns",
    )
    filtered = data.copy()
    for column in selected:
        series = filtered[column]
        label = LABELS.get(column, column.replace("_", " ").title())
        non_null = series.dropna()
        if pd.api.types.is_bool_dtype(series):
            chosen = st.multiselect(label, [True, False], key=f"{key_prefix}_{column}")
            if chosen:
                filtered = filtered[series.isin(chosen)]
        elif pd.api.types.is_numeric_dtype(series) and not non_null.empty:
            minimum = float(non_null.min())
            maximum = float(non_null.max())
            if minimum == maximum:
                st.caption(f"{label}: {minimum:g}")
                continue
            chosen = st.slider(
                label,
                min_value=minimum,
                max_value=maximum,
                value=(minimum, maximum),
                key=f"{key_prefix}_{column}",
            )
            filtered = filtered[series.between(chosen[0], chosen[1])]
        else:
            values = sorted({str(value) for value in non_null})
            if len(values) <= 50:
                chosen = st.multiselect(label, values, key=f"{key_prefix}_{column}")
                if chosen:
                    filtered = filtered[series.astype(str).isin(chosen)]
            else:
                term = st.text_input(f"{label} contains", key=f"{key_prefix}_{column}")
                if term:
                    filtered = filtered[series.astype(str).str.contains(term, case=False, na=False)]
    return filtered


def render_data(database: Database, user: dict[str, Any]) -> None:
    st.title("Logged CCS data")
    if st.session_state.pop("clear_entry_after_save", False):
        _clear_entry_form_state()
        st.session_state.pop("selected_paper", None)
    if message := st.session_state.pop("data_success_message", None):
        st.success(message)
    data = database.measurement_data()
    if data.empty:
        st.info("No CCS entries have been logged yet.")
    else:
        table_data = _table_data(data)
        with st.expander("Filters", expanded=False):
            filtered = filter_dataframe(table_data, "table")
        st.caption(f"{len(filtered)} of {len(data)} CCS values shown")
        st.caption("Select any measurement row to edit its complete protein entry or reuse it as a template.")
        table_event = st.dataframe(
            _display(filtered),
            width="stretch",
            hide_index=True,
            key="logged_ccs_table",
            on_select="rerun",
            selection_mode="single-row",
        )
        selected_rows = table_event.selection.rows
        if selected_rows and selected_rows[0] < len(filtered):
            selected = data.loc[filtered.index[selected_rows[0]]]
            template = database.get_entry_template(str(selected["entry_id"]))
            if template:
                st.caption(
                    f"Selected: {template['entry']['protein']} · "
                    f"{template['paper'].get('doi') or template['paper'].get('pmid')}"
                )
                edit_control, template_control = st.columns(2)
                with edit_control:
                    if template["entry"]["logger_id"] == user["id"]:
                        st.button(
                            "Edit selected entry",
                            type="primary",
                            on_click=_edit_entry,
                            args=(template,),
                        )
                    else:
                        st.caption("Only the original contributor can edit this entry.")
                with template_control:
                    st.button(
                        "Use selected entry as template for new entry",
                        on_click=_use_entry_as_template,
                        args=(template,),
                    )

    export = database.export_data()
    st.download_button(
        "Download complete dataset",
        data=export.to_csv(index=False).encode("utf-8"),
        file_name="protein-ccs-database.csv",
        mime="text/csv",
        disabled=export.empty,
    )


def render_papers(database: Database, user: dict[str, Any]) -> None:
    st.title("Find a paper")
    st.write("Search by DOI to see whether a paper has already been logged, or add a paper that is not yet in the database.")
    with st.form("doi_search"):
        doi = st.text_input("DOI", placeholder="10.xxxx/...")
        searched = st.form_submit_button("Search", type="primary")
    if searched:
        try:
            normalised_doi = validate_doi(doi)
        except ValueError as error:
            st.session_state.pop("paper_result", None)
            st.session_state.pop("paper_search_doi", None)
            st.error(str(error))
        else:
            st.session_state["paper_result"] = database.find_paper(normalised_doi)
            st.session_state["paper_search_doi"] = normalised_doi

    result = st.session_state.get("paper_result")
    searched_doi = st.session_state.get("paper_search_doi")
    if searched_doi and result is None:
        st.warning("That DOI is not yet in the database. Add the paper details below to log data from it.")
        new_paper = _new_paper_form(database, searched_doi, "paper_search")
        if new_paper:
            st.session_state["paper_result"] = new_paper
            _select_paper(new_paper, defer_navigation=True)
            st.rerun()
    elif result:
        _paper_card(result)
        if result["entry_count"]:
            st.success(f"Logged: {result['entry_count']} protein entr{'y' if result['entry_count'] == 1 else 'ies'}")
        else:
            st.info("This paper has not been logged.")
        st.button(
            "Log data from this paper",
            key="log_search_result",
            on_click=_select_paper,
            args=(result,),
        )

    st.divider()
    st.subheader("Choose an unlogged paper")
    if st.button("Choose a paper for me"):
        st.session_state["random_paper"] = database.choose_unlogged_paper(user["id"])
    random_paper = st.session_state.get("random_paper")
    if random_paper:
        _paper_card(random_paper)
        st.button(
            "Log this paper",
            key="log_random_result",
            on_click=_select_paper,
            args=(random_paper,),
        )
    elif "random_paper" in st.session_state:
        st.info("Every available paper is already logged or assigned.")


def _paper_card(paper: dict[str, Any]) -> None:
    st.markdown(f"**{paper['title']}**")
    details = [paper.get("authors"), paper.get("journal"), paper.get("publication_date")]
    st.write(" · ".join(str(value) for value in details if value))
    st.code(paper.get("doi") or paper.get("pmid") or "No identifier", language=None)


def _new_paper_form(
    database: Database,
    normalised_doi: str,
    key_prefix: str,
) -> dict[str, Any] | None:
    """Collect the minimum metadata needed for a paper outside the catalogue."""

    st.code(normalised_doi, language=None)
    with st.form(f"{key_prefix}_new_paper"):
        title = st.text_input("Paper title:*", key=f"{key_prefix}_paper_title")
        authors = st.text_input("Authors:", key=f"{key_prefix}_paper_authors")
        journal = st.text_input("Journal:", key=f"{key_prefix}_paper_journal")
        publication_date = st.text_input(
            "Publication date:",
            placeholder="YYYY, YYYY-MM or YYYY-MM-DD",
            key=f"{key_prefix}_paper_publication_date",
        )
        add_paper = st.form_submit_button("Add paper and continue", type="primary")

    if not add_paper:
        return None
    try:
        return database.create_paper(
            normalised_doi,
            title,
            authors,
            journal,
            publication_date,
        )
    except ValueError as error:
        st.error(str(error))
        return None


def _select_paper(paper: dict[str, Any], defer_navigation: bool = False) -> None:
    _clear_entry_form_state()
    st.session_state["selected_paper"] = paper
    st.session_state["entry_doi"] = paper.get("doi") or ""
    navigation_key = "navigation_pending" if defer_navigation else "navigation"
    st.session_state[navigation_key] = "Add entry"


def render_add_entry(database: Database, user: dict[str, Any]) -> None:
    editing = bool(
        st.session_state.get("entry_form_mode") == "edit"
        and st.session_state.get("entry_edit_id")
    )
    st.title("Edit a CCS entry" if editing else "Add a CCS entry")
    _, clear_control = st.columns([5, 1])
    with clear_control:
        if editing:
            st.button("Cancel editing", on_click=_cancel_editing)
        else:
            st.button("Start blank entry", on_click=_start_blank_entry)

    selected = st.session_state.get("selected_paper")
    default_doi = selected.get("doi", "") if selected else ""
    _ensure_entry_defaults(default_doi)

    if editing:
        st.info("Editing this entry. Saving will replace its stored details and CCS measurements.")
    elif source := st.session_state.get("entry_template_source"):
        st.info(f"Using **{source}** as a template. Change the protein-specific details before saving.")

    basic_tab, conditions_tab, sample_tab, measurements_tab = st.tabs(
        ["Basic Info", "Detailed Measurement Conditions", "Sample Details", "Measurements"]
    )

    with basic_tab:
        doi = st.text_input("DOI:*", placeholder="10.xxxx/...", key="entry_doi")
        protein = st.text_input("Protein:*", key="entry_protein")
        ionisation_options = ["Positive", "Negative"]
        if st.session_state["entry_ionisation_mode"] not in ionisation_options:
            ionisation_options.append(st.session_state["entry_ionisation_mode"])
        ionisation_mode = st.selectbox(
            "Ionisation Mode:", ionisation_options, key="entry_ionisation_mode"
        )
        instrument_choice = st.selectbox(
            "Instrument Family:", INSTRUMENT_FAMILIES, key="entry_instrument_choice"
        )
        instrument_other = ""
        if instrument_choice == "Other":
            instrument_other = st.text_input(
                "Please specify instrument family", key="entry_instrument_other"
            )
        native_choice = st.selectbox("Native?", ["Yes", "No"], key="entry_native")
        ims_options = list(IMS_TYPES)
        if st.session_state["entry_ims_type"] not in ims_options:
            ims_options.append(st.session_state["entry_ims_type"])
        ims_type = st.selectbox("IMS Type:", ims_options, key="entry_ims_type")
        subunits = st.number_input(
            "Subunits:", min_value=0, max_value=100, step=1, key="entry_subunits",
            help="Leave at 0 when the number of subunits is not provided.",
        )
        oligomer_type = st.session_state.get("entry_oligomer_type", "Homo")
        if subunits > 1:
            oligomer_options = ["Homo", "Hetero"]
            if oligomer_type not in oligomer_options:
                oligomer_options.append(oligomer_type)
            oligomer_type = st.selectbox(
                "Oligomer Type:", oligomer_options, key="entry_oligomer_type"
            )

    with conditions_tab:
        calibration_choice = st.selectbox(
            "Drift Gas (calibration):",
            DRIFT_GASES,
            key="entry_calibration_gas_choice",
            disabled=ims_type == "DTIMS",
        )
        calibration_other = ""
        if calibration_choice == "Other":
            calibration_other = st.text_input(
                "Please specify calibration gas", key="entry_calibration_gas_other"
            )
        st.caption("Note: Drift gas for calibration is only required when IMS is NOT DTIMS.")
        measurement_choice = st.selectbox(
            "Drift Gas (measurement):*", DRIFT_GASES, key="entry_measurement_gas_choice"
        )
        measurement_other = ""
        if measurement_choice == "Other":
            measurement_other = st.text_input(
                "Please specify measurement gas", key="entry_measurement_gas_other"
            )
        measurement_conditions = st.text_area(
            "Measurement Conditions:", key="entry_measurement_conditions", height=120
        )
        sample_description = st.text_area(
            "Sample Description:", key="entry_sample_description", height=120
        )

    with sample_tab:
        supplier_details = st.text_input("Supplier Details:", key="entry_supplier_details")
        supplier_details_provided = st.checkbox(
            "Paper provided this", key="entry_supplier_details_provided"
        )
        st.divider()
        uniprot_id = st.text_input("UniProt ID:", key="entry_uniprot_id")
        uniprot_id_provided = st.checkbox("Paper provided this", key="entry_uniprot_id_provided")
        st.divider()
        pdb_id = st.text_input("PDB ID:", key="entry_pdb_id")
        pdb_id_provided = st.checkbox("Paper provided this", key="entry_pdb_id_provided")
        st.divider()
        sequence = st.text_area("Sequence:", key="entry_sequence", height=100)
        sequence_provided = st.checkbox("Paper provided this", key="entry_sequence_provided")
        st.divider()
        sequence_mass = st.number_input(
            "Sequence Mass:", min_value=0.0, value=None, key="entry_sequence_mass", format="%.6f"
        )
        sequence_mass_provided = st.checkbox(
            "Paper provided this", key="entry_sequence_mass_provided"
        )
        st.divider()
        measured_mass = st.number_input(
            "Measured Mass:", min_value=0.0, value=None, key="entry_measured_mass", format="%.6f"
        )
        measured_mass_provided = st.checkbox(
            "Paper provided this", key="entry_measured_mass_provided"
        )

    with measurements_tab:
        st.subheader("CCS Measurements")
        with st.container(border=True):
            st.markdown("**Global CCS Value (applies to all charge states)**")
            global_left, global_right = st.columns(2)
            with global_left:
                global_ccs_value = st.number_input(
                    "Global CCS Value:", min_value=0.0, value=None,
                    key="entry_global_ccs_value", format="%.6f"
                )
                global_ccs_provided = st.checkbox(
                    "Value provided in paper", key="entry_global_ccs_provided"
                )
            with global_right:
                global_ccs_error = st.number_input(
                    "Error (±):", min_value=0.0, value=None,
                    key="entry_global_ccs_error", format="%.6f"
                )
                global_ccs_from_graph = st.checkbox(
                    "Value read from graph", key="entry_global_ccs_from_graph"
                )

        with st.container(border=True):
            st.markdown("**Charge State Range (for global CCS)**")
            range_left, range_right = st.columns(2)
            with range_left:
                global_charge_min = st.number_input(
                    "Min Charge State:", min_value=1, max_value=100, value=None,
                    step=1, key="entry_global_charge_min"
                )
            with range_right:
                global_charge_max = st.number_input(
                    "Max Charge State:", min_value=1, max_value=100, value=None,
                    step=1, key="entry_global_charge_max"
                )

        st.markdown("**Individual CCS Measurements (per charge state)**")
        st.caption("Use the + control to add another charge state. Select a row and press Delete to remove it.")
        measurement_table = st.data_editor(
            st.session_state["entry_measurement_seed"],
            num_rows="dynamic",
            hide_index=True,
            width="stretch",
            key=f"entry_individual_measurements_{st.session_state['entry_form_generation']}",
            column_config={
                "charge_state": st.column_config.NumberColumn(
                    "Charge State", min_value=1, max_value=100, step=1
                ),
                "ccs_value": st.column_config.NumberColumn(
                    "CCS Value", min_value=0.0, format="%.6f"
                ),
                "error": st.column_config.NumberColumn(
                    "Error (±)", min_value=0.0, format="%.6f"
                ),
                "provided": st.column_config.CheckboxColumn("Value provided in paper"),
                "from_graph": st.column_config.CheckboxColumn("Value read from graph"),
            },
        )

    paper = None
    normalised_doi = None
    doi_error = None
    if doi:
        try:
            normalised_doi = validate_doi(doi)
            paper = database.find_paper(normalised_doi)
        except ValueError as error:
            doi_error = str(error)

    if paper:
        with st.expander("Selected paper", expanded=False):
            _paper_card(paper)
    elif doi_error:
        st.warning(doi_error)
    elif normalised_doi:
        st.warning("That DOI is not yet in the database. Add the paper details below before saving this entry.")
        new_paper = _new_paper_form(database, normalised_doi, "entry")
        if new_paper:
            st.session_state["selected_paper"] = new_paper
            st.session_state["entry_doi"] = new_paper["doi"]
            st.rerun()
    else:
        st.info("Enter a DOI, or select a paper on the Papers page.")

    submitted = st.button("Save changes" if editing else "Save entry", type="primary")

    if submitted:
        if not paper:
            st.error(doi_error or "Select or add a paper before submitting.")
            return
        instrument_family = instrument_other if instrument_choice == "Other" else instrument_choice
        drift_gas_calibration = (
            calibration_other if calibration_choice == "Other" else calibration_choice
        )
        drift_gas_measurement = measurement_other if measurement_choice == "Other" else measurement_choice
        payload = {
            "protein": protein,
            "ionisation_mode": ionisation_mode,
            "instrument_family": instrument_family,
            "native": native_choice == "Yes",
            "ims_type": ims_type,
            "subunits": subunits or None,
            "oligomer_type": oligomer_type,
            "drift_gas_calibration": drift_gas_calibration,
            "drift_gas_measurement": drift_gas_measurement,
            "measurement_conditions": measurement_conditions,
            "sample_description": sample_description,
            "supplier_details": supplier_details,
            "supplier_details_provided": supplier_details_provided,
            "uniprot_id": uniprot_id,
            "uniprot_id_provided": uniprot_id_provided,
            "pdb_id": pdb_id,
            "pdb_id_provided": pdb_id_provided,
            "sequence": sequence,
            "sequence_provided": sequence_provided,
            "sequence_mass": sequence_mass,
            "sequence_mass_provided": sequence_mass_provided,
            "measured_mass": measured_mass,
            "measured_mass_provided": measured_mass_provided,
        }
        measurement_rows = [
            {"measurement_type": "charge_state", **row}
            for row in measurement_table.to_dict("records")
        ]
        if global_ccs_value is not None:
            measurement_rows.append(
                {
                    "measurement_type": "global",
                    "charge_state": None,
                    "charge_state_min": global_charge_min,
                    "charge_state_max": global_charge_max,
                    "ccs_value": global_ccs_value,
                    "error": global_ccs_error,
                    "provided": global_ccs_provided,
                    "from_graph": global_ccs_from_graph,
                }
            )
        try:
            if editing:
                database.update_entry(
                    user["id"],
                    str(st.session_state["entry_edit_id"]),
                    paper["id"],
                    payload,
                    measurement_rows,
                )
            else:
                database.create_entry(user["id"], paper["id"], payload, measurement_rows)
        except (ValueError, PermissionError) as error:
            st.error(str(error))
        else:
            st.session_state["clear_entry_after_save"] = True
            st.session_state["data_success_message"] = (
                "Entry updated successfully."
                if editing
                else "Entry saved. Select any row below to edit it or use it as a template for another protein."
            )
            st.session_state["navigation_pending"] = "Data"
            st.rerun()


def render_visualize(database: Database) -> None:
    st.title("Visualise CCS data")
    data = database.measurement_data()
    if data.empty:
        st.info("There are no CCS measurements to plot yet.")
        return
    with st.expander("Filters", expanded=False):
        filtered = filter_dataframe(data, "plot")
    control_1, control_2, control_3, control_4 = st.columns([1, 1, 1, 0.7])
    available_axes = [column for column in PLOT_AXES if column in filtered.columns]
    with control_1:
        x_axis = st.selectbox("X-axis", available_axes, format_func=PLOT_AXES.get, index=available_axes.index("charge_state") if "charge_state" in available_axes else 0)
    with control_2:
        y_axis = st.selectbox("Y-axis", available_axes, format_func=PLOT_AXES.get, index=available_axes.index("ccs_value") if "ccs_value" in available_axes else 0)
    with control_3:
        colour_options = ["None", *[column for column in COLOUR_FIELDS if column in filtered.columns]]
        colour = st.selectbox("Colour by", colour_options, format_func=lambda value: COLOUR_FIELDS.get(value, value))
    with control_4:
        show_key = st.checkbox("Show key", value=False)
    colour_column = None if colour == "None" else colour
    figure = build_plot(filtered, x_axis, y_axis, colour_column, {**LABELS, **PLOT_AXES}, show_key)
    st.plotly_chart(figure, width="stretch", config=PLOT_CONFIG)
    first, second = st.columns(2)
    with first:
        st.download_button(
            "Download plotted data",
            filtered.to_csv(index=False).encode("utf-8"),
            file_name="protein-ccs-plotted-data.csv",
            mime="text/csv",
        )
    with second:
        st.download_button(
            "Download interactive plot",
            standalone_html(figure).encode("utf-8"),
            file_name="protein-ccs-interactive-plot.html",
            mime="text/html",
        )


def render_leaderboard(database: Database) -> None:
    st.title("Leaderboard")
    leaderboard = database.leaderboard()
    if leaderboard.empty:
        st.info("No contributors have logged data yet.")
        return
    leaderboard.index = range(1, len(leaderboard) + 1)
    leaderboard.index.name = "Rank"
    st.dataframe(
        leaderboard.rename(
            columns={
                "nickname": "Contributor",
                "papers_logged": "Papers logged",
                "protein_entries": "Protein entries",
                "ccs_values": "CCS values",
            }
        ),
        width="stretch",
    )
