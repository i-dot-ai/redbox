import plotly.express as px
from dash import dcc, html
from dash.dependencies import Input, Output
from django.db.models import Count
from django.db.models.functions import TruncDate
from django_plotly_dash import DjangoDash

from redbox_app.redbox_core import models

app = DjangoDash("RedboxReport")

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


@app.callback(Output("line-chart", "figure"), [Input("dropdown", "value")])
def update_graph(selected_metric):
    queryset = (
        models.ChatMessage.objects.annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(count=Count("id"))
        .order_by("day")
    )

    data = {
        "Date": [entry["day"].strftime("%Y-%m-%d") for entry in queryset],
        "Count": [entry["count"] for entry in queryset],
    }

    return px.line(data, x="Date", y=selected_metric, title="Messages per day")
