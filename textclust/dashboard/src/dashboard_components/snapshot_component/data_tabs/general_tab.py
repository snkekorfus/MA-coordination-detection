import dash_html_components as html
import dash_core_components as dcc
import dash_bootstrap_components as dbc

def general_tab_layout():
    return dcc.Tab(label='Allgemein', children=[
        # microcluster weight
        html.Div(className="dataMetrics", children=[
            html.Div(className="dataMetric", id= "clust_weight", children=[
                html.Div(className="metricHeader", children=[
                    html.H6("Cluster Gewicht",style={"display": "inline-block"}),
                    html.Div(className="fa fa-weight fa-vc")
                ]),
                html.Div(
                    className="metricBody metricNumber",
                    id="selectedClusterWeight",
                    children=[0]
                ),
                dbc.Tooltip("Berechnetes Gewicht des Themas zum ausgewählten Zeitpunkt.", target="clust_weight", )
            ]),
            # microcluster weight change abs.
            html.Div(className="dataMetric", id = "abs_change", children=[
                html.Div(className="metricHeader", children=[
                    html.H6("abs. Gewichtsänd.")
                ]),
                html.Div(
                    className="metricBody metricNumber",
                    id="selectedClusterWeightChangeAbs",
                    children=[0]
                ),
                dbc.Tooltip("Änderung des Gewichteswertes zum vorher berechneten Gewichtswert eines Themas.", target="abs_change", )
            ]),
            # microcluster weight change rel.
            html.Div(className="dataMetric", id='rel_change', children=[
                html.Div(className="metricHeader",  children=[
                    html.H6("rel. Gewichtsänd.",style={"display": "inline-block"}),
                    html.Div(className="fa fa-weight fa-vc"),
                    html.Div(className="fa fa-arrows-alt-v fa-vc")
                ]),
                html.Div(
                    className="metricBody metricNumber",
                    id="selectedClusterWeightChangeRel",
                    children=["0.00%"]
                ),
                dbc.Tooltip("Relative Änderung des Gewichtes zu vorher berechnetem Gewicht.", target="rel_change", )
            ]),
            # microcluster number of texts inside abs.
            html.Div(className="dataMetric", id="num_tweets", children=[
                html.Div(className="metricHeader", children=[
                    html.H6("# Tweets")
                ]),
                html.Div(
                    className="metricBody metricNumber",
                    id="textNumber",
                    children=[0]
                ),
                dbc.Tooltip("Anzahl der Tweets im beobachteten Zeitfenster (max. 5 Stunden).", target="num_tweets", )
            ]),
            # microcluster number of texts inside abs.
            html.Div(className="dataMetric", id="abs_tweet_change", children=[
                html.Div(className="metricHeader", children=[
                    html.H6("Neue Tweets",style={"display": "inline-block"}),
                    html.Div(className="fa fa-plus fa-vc")
                ]),
                html.Div(
                    className="metricBody metricNumber",
                    id="selectedClusterNewTextsAbs",
                    children=[0]
                ),
                dbc.Tooltip("Anzahl der neuen Tweets seit letztem Zeitpunkt vor gewähltem Zeitpunkt.", target="abs_tweet_change", )
            ]),
            # microcluster number of texts inside rel.
            html.Div(className="dataMetric", id="rel_tweet_change", children=[
                html.Div(className="metricHeader", children=[
                    html.H6("Neue Tweets (Rel)")
                ]),
                html.Div(
                    className="metricBody metricNumber",
                    id="selectedClusterNewTextsRel",
                    children=["0.00%"]
                ),
                dbc.Tooltip("Relative Zunahme von neuen Tweets bezgl. vorheriger Gesamt-Tweet-Anzahl.", target="rel_tweet_change", )
            ]),
        ]),
    ])
