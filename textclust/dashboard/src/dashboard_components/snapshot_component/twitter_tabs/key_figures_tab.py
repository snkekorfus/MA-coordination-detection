import dash_html_components as html
import dash_core_components as dcc
import dash_bootstrap_components as dbc

def key_figures_tab_layout():
    return dcc.Tab(label="Nutzer Metriken", children=[
        html.Div(className="dataMetrics", children=[
            # number of accounts
            html.Div(className="dataMetric", id="account_num", children=[
                html.Div(className="metricHeader", children=[
                    html.H6("Twitter Accounts",style={"display": "inline-block"}),
                    html.Div(className="fab fa-twitter fa-vc"),
                ]),
                html.P(
                    className="metricBody metricNumber",
                    id="twtAccNumber",
                    children=[0]
                ),
                dbc.Tooltip("Gesamtanzahl von Twitter-Accounts, die im beobachteten Zeitfenster (max. 5h) bis zum gewählten Zeitpunkt an dem Thema beteilig waren.", target="account_num", )
            ]),


            # number of verified users abs.
            html.Div(className="dataMetric", id="ver_account_num", children=[
                html.Div(className="metricHeader", children=[
                    html.H6("Verifiziert",style={"display": "inline-block"}),
                    html.Div(className="fa fa-check fa-vc")
                ]),
                html.Div(
                    className="metricBody metricNumber",
                    id="twtVerifiedUsersAbs",
                    children=[0]
                ),
                dbc.Tooltip("Gesamtanzahl von verifizierten Twitter-Accounts, die im beobachteten Zeitfenster (max. 5h) bis zum gewählten Zeitpunkt an dem Thema beteilig waren.", target="ver_account_num", )
            ]),
            # number of tweets inside
            html.Div(className="dataMetric", id="tweet_count", children=[
                html.Div(className="metricHeader", children=[
                    html.H6("Tweets",style={"display": "inline-block"}),
                    html.Div(className="fa fa-hashtag fa-vc"),
                ]),
                html.Div(
                    className="metricBody metricNumber",
                    id="twtNumber",
                    children=[0]
                ),
                dbc.Tooltip("Anzahl der Tweets, im beobachteten Zeitfenster (max. 5h).", target="tweet_count", )
            ]),
            # number of users with default profile
            html.Div(className="dataMetric", id="standard_profile_count", children=[
                html.Div(className="metricHeader", children=[
                    html.H6("Standardprofil",style={"display": "inline-block"}),
                     html.Div(className="fa fa-user fa-vc")
                ]),
                html.Div(
                    className="metricBody metricNumber",
                    id="twtDefaultProfile",
                    children=[0]
                ),
                dbc.Tooltip("Anzahl der Accounts mit Standardprofil, im beobachteten Zeitfenster (max. 5h) bis zum gewählten Zeitpunkt.", target="standard_profile_count", )
            ]),
            # number of users with default image
            html.Div(className="dataMetric", id="standard_pic_count", children=[
                html.Div(className="metricHeader", children=[
                    html.H6("Standardbild",style={"display": "inline-block"}),
                    html.Div(className="fa fa-address-card fa-vc")
                ]),
                html.Div(
                    className="metricBody metricNumber",
                    id="twtDefaultImage",
                    children=[0]
                ),
                dbc.Tooltip("Anzahl der Accounts mit Standardbild, im beobachteten Zeitfenster (max. 5h) bis zum gewählten Zeitpunkt.", target="standard_pic_count", )
            ]),
            # number of verified users rel.
            html.Div(className="dataMetric", id="rel_verified_count", children=[
                html.Div(className="metricHeader", children=[
                    html.H6("Anteil verifizierter Accounts",style={"display": "inline-block"}),
                    html.Div(className="fa fa-check fa-vc"),
                    html.Div(className="fa fa-divide fa-vc")
                ]),
                html.Div(
                    className="metricBody metricNumber",
                    id="twtVerifiedUsersRel",
                    children=[0]
                ),
                dbc.Tooltip("Relativer Anteil der verifizierten Accounts bezpgen auf das beobachtete Zeitfenster (max. 5h) bis zum gewählten Zeitpunkt.", target="rel_verified_count", )
            ])
        ])
    ])
