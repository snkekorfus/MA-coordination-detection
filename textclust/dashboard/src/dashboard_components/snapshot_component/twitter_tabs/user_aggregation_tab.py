import dash_html_components as html
import dash_core_components as dcc
import dash_bootstrap_components as dbc


def user_aggregation_tab_layout():
    return dcc.Tab(label="Nutzer Statistiken", children=[
             dbc.Row(
            [
                # follower boxplot
                        dbc.Col(dcc.Graph(
                            id="followerBoxPlot",
                            style={"height": "250px"},
                            config={"displayModeBar":False,"staticPlot":True},
                        ),width=3)
                   ,
                # likes boxplot
                        dbc.Col(dcc.Graph(
                            id="likedBoxPlot",
                            style={"height": "250px"},
                             config={"displayModeBar":False,"staticPlot":True},
                        ),width=3)
                    ,
                # statuses boxplot
                        dbc.Col(dcc.Graph(
                            id="userTweetsBoxPlot",
                            style={"height": "250px"},
                             config={"displayModeBar":False,"staticPlot":True},
                        ),width=3)
                    ,
                # friends boxplot
                        dbc.Col(dcc.Graph(
                            id="friendsBoxPlot",
                            style={"height": "250px"},
                             config={"displayModeBar":False,"staticPlot":True},
                        ),width=3)
                ]),
                dbc.Tooltip("Statistik über die Follower der Accounts (= Nutzer die den betrachteten Accounts folgen), die an dem ausgewählten Thema / Cluster beteiligt sind.", target="followerBoxPlot", ),
                dbc.Tooltip("Statistik über die Likes der Accounts, die an dem ausgewählten Thema / Cluster beteiligt sind.", target="likedBoxPlot", ),
                dbc.Tooltip("Statistik über die Gesamt-Tweet-Anzahl der Accounts, die an dem ausgewählten Thema / Cluster beteiligt sind.", target="userTweetsBoxPlot", ),
                dbc.Tooltip("Statistik über die Anzahl der Freunde der Accounts (= Anzahl der Nutzer denen jeder betrachtete Account folgt), die an dem ausgewählten Thema / Cluster beteiligt sind.", target="friendsBoxPlot", ),

                dbc.Row([
                # friends historam
                        dbc.Col(dcc.Graph(
                            id="accountnAgeBar",
                            style={"height": "200px"} ,
                             config={"displayModeBar":False,"staticPlot":True},
                    ),width=6),
                    dbc.Col(dcc.Graph(
                            id="mcStatusesBar",
                            style={"height": "200px"} ,
                             config={"displayModeBar":False,"staticPlot":True},
                    ),width=6)
                ]
            ),
            dbc.Tooltip("Empirische Verteilung des Alters der Accounts. Auf der x-Achse ist die Erstellungszeit der Accounts abgetragen. Auf der y-Achse die Häufigkeit in der Menge der betrachteten Accounts.", target="accountnAgeBar", ),
            dbc.Tooltip("Aktivität (Häufigkeit von Posts, Direktnachrichten, Replies) der aktivsten Nutzer.", target="mcStatusesBar", )
    ])
