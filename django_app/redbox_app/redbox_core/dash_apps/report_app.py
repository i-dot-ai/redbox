import pandas as pd
import plotly.express as px
from dash import dcc, html
from dash.dependencies import Input, Output
from django.db.models import Count
from django.db.models.functions import TruncDate
from plotly.graph_objects import Figure

if __name__ == "__main__":
    # Enables standalone running for developers outside of full Django app
    import os

    import django
    from dash import Dash

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "redbox_app.settings")

    # Django still needs some setup in order to access database
    django.setup()
else:
    from django_plotly_dash import DjangoDash

from redbox_app.redbox_core import models

if __name__ == "__main__":  # noqa: SIM108
    # Enables standalone running for developers outside of Django
    app = Dash("RedboxReport")
else:
    app = DjangoDash("RedboxReport")

# ------------#
# App layout #
# ------------#


app.layout = html.Div(
    [
        dcc.Graph(id="line-chart"),
        dcc.Dropdown(
            id="dropdown",
            options=[
                {"label": "Daily count", "value": "Count"},
            ],
            value="Count",
        ),
    ]
)

# -----------#
# Callbacks #
# -----------#


@app.callback(Output("line-chart", "figure"), [Input("dropdown", "value")])
def update_graph(selected_metric: str, **kwargs) -> Figure:  # noqa: ARG001
    """A standard plotly callback.

    Note **kwargs must be used for compatibility across both Dash and DjangoDash.
    """
    queryset = (
        models.ChatMessage.objects.annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(count=Count("id"))
        .order_by("day")
    )

    data = (
        pd.DataFrame.from_records(queryset.values())
        .filter(["created_at", "count"])
        .assign(created_at=lambda x: pd.to_datetime(x["created_at"].dt.strftime("%Y-%m-%d")))
        .rename(columns={"created_at": "Date", "count": "Count"})
        .groupby(["Date"], as_index=False)
        .sum()
    )

    return px.line(data, x="Date", y=selected_metric, title="Messages per day")


if __name__ == "__main__":
    app.run(debug=True)
