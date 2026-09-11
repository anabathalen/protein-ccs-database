"""Plotly figures shared by the page and standalone HTML download."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

SEABORN_COLORBLIND = [
    "#0173B2",
    "#DE8F05",
    "#029E73",
    "#D55E00",
    "#CC78BC",
    "#CA9161",
    "#FBAFE4",
    "#949494",
    "#ECE133",
    "#56B4E9",
]

PLOT_CONFIG = {
    "displayModeBar": True,
    "displaylogo": False,
    "scrollZoom": True,
    "responsive": True,
    "modeBarButtonsToRemove": ["select2d", "lasso2d"],
    "toImageButtonOptions": {
        "format": "png",
        "filename": "protein-ccs-plot",
        "height": 700,
        "width": 1100,
        "scale": 2,
    },
}


def build_plot(
    data: pd.DataFrame,
    x_column: str,
    y_column: str,
    colour_column: str | None,
    labels: dict[str, str],
    show_key: bool,
) -> go.Figure:
    plotting_data = data.dropna(subset=[x_column, y_column]).copy()
    hover_columns = [
        column
        for column in (
            "protein",
            "doi",
            "measurement_type",
            "charge_state",
            "charge_state_min",
            "charge_state_max",
            "ccs_value",
            "error",
            "ims_type",
            "instrument_family",
            "drift_gas_measurement",
            "native",
            "ionisation_mode",
            "measured_mass",
            "subunits",
            "oligomer_type",
            "logged_by",
        )
        if column in plotting_data.columns and column not in {x_column, y_column, colour_column}
    ]
    figure = px.scatter(
        plotting_data,
        x=x_column,
        y=y_column,
        color=colour_column,
        color_discrete_sequence=SEABORN_COLORBLIND,
        hover_data=hover_columns,
        labels=labels,
    )
    figure.update_traces(marker={"size": 9, "opacity": 0.78, "line": {"color": "white", "width": 1}})
    figure.update_layout(
        dragmode="pan",
        font={"family": "Helvetica, Arial, sans-serif", "color": "#222222", "size": 12},
        height=580,
        hovermode="closest",
        legend={
            "bgcolor": "rgba(255,255,255,0.9)",
            "bordercolor": "#d7d7d7",
            "borderwidth": 1,
            "title": None,
        },
        margin={"b": 70, "l": 75, "r": 25, "t": 25},
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        showlegend=show_key and colour_column is not None,
    )
    figure.update_xaxes(
        automargin=True,
        gridcolor="#e5e5e5",
        linecolor="#222222",
        linewidth=1,
        showgrid=True,
        showline=True,
        ticks="outside",
        tickcolor="#222222",
        zeroline=False,
    )
    figure.update_yaxes(
        automargin=True,
        gridcolor="#e5e5e5",
        linecolor="#222222",
        linewidth=1,
        showgrid=True,
        showline=True,
        ticks="outside",
        tickcolor="#222222",
        zeroline=False,
    )
    return figure


def standalone_html(figure: go.Figure) -> str:
    """Create a self-contained interactive file with the standard Plotly toolbar."""

    return figure.to_html(
        full_html=True,
        include_plotlyjs=True,
        config=PLOT_CONFIG,
        default_height="700px",
        default_width="100%",
    )
