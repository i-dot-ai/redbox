import plotly.express as px
from dash import dcc, html
from dash.dependencies import Input, Output
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from plotly.graph_objects import Figure

# ----------------------------------#
# App setup and conditional imports #
# ----------------------------------#


if __name__ == "__main__":
    # Enables standalone running for developers outside of full Django app
    import os

    import django
    from dash import Dash

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "redbox_app.settings")

    # Django still needs some setup in order to access database
    django.setup()

    app = Dash("RedboxReport")
else:
    from django_plotly_dash import DjangoDash

    app = DjangoDash("RedboxReport")

from redbox_app.redbox_core import models  # Must be imported after django.setup()

# -----------#
# App layout #
# -----------#


app.layout = html.Div(
    [
        dcc.Graph(id="line-chart"),
        html.P("Select metric"),
        dcc.Dropdown(
            id="metric",
            options=[
                {"label": "message count", "value": "message_count"},
                {"label": "unique users", "value": "unique_users"},
                {"label": "tokens used", "value": "token_count"},
            ],
            value="message_count",
        ),
        html.P("Select breakdown"),
        dcc.Dropdown(
            id="breakdown",
            options=[
                {"label": "route", "value": "route"},
                {"label": "model", "value": "chat__chat_backend"},
                {"label": "none", "value": None},
            ],
            value="route",
        ),
    ]
)

# ----------#
# Callbacks #
# ----------#


@app.callback(Output("line-chart", "figure"), [Input("metric", "value"), Input("breakdown", "value")])
def update_graph(metric: str, breakdown: str | None, **kwargs) -> Figure:  # noqa: ARG001
    """A standard plotly callback.

    Note **kwargs must be used for compatibility across both Dash and DjangoDash.
    """
    breakdown_args = [breakdown] if breakdown else []
    queryset = (
        models.ChatMessage.objects.annotate(day=TruncDate("created_at"))
        .values("day", *breakdown_args)
        .annotate(
            message_count=Count("id", distinct=True),
            unique_users=Count("chat__user", distinct=True),
            token_count=Sum("chatmessagetokenuse__token_count"),
        )
        .order_by("day")
        .values("day", "message_count", "unique_users", "token_count", *breakdown_args)
    )

    breakdown_colours = {"color": breakdown} if breakdown else {}
    return px.bar(queryset, x="day", y=metric, title="use per day", **breakdown_colours)


if __name__ == "__main__":
    app.run(debug=True)
