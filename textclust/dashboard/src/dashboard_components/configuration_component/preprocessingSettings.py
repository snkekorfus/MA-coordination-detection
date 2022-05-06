import dash_html_components as html
import dash_core_components as dcc
import dash_daq as daq


def preprocessing_layout():
    return dcc.Tab(label='Preprocessing', children=[
        html.Div(id="preConfigContainer", children=[
            html.Div(id="preLanguageWrapper", children=[
                html.Span(children="language:"),
                dcc.Dropdown(
                    id="preLanguage",
                    options=[
                        {'label': 'English',
                         'value': 'english'},
                        {'label': 'German',
                         'value': 'german'},
                        {'label': 'French',
                         'value': 'french'},
                        {'label': 'Spanish',
                         'value': 'spanish'},
                        {'label': 'Italian',
                         'value': 'italian'},
                        {'label': 'Russian',
                         'value': 'russian'}
                    ],
                    value="english"
                ),
            ]),
            # various kinds of preprocessing paramters: stopwords, stemming, hashtag removal,...
            html.Div(id="preSwitchesWrapper", children=[
                daq.NumericInput(
                    className="preSwitch",
                    id="ngramInput",
                    label='n-grams',
                    labelPosition='bottom',
                    value=1
                ),
                daq.BooleanSwitch(
                    className="preSwitch",
                    id="stopwordInput",
                    on=True,
                    label="stopword removal",
                    labelPosition="bottom",
                    color="#090088"
                ),
                daq.BooleanSwitch(
                    className="preSwitch",
                    id="stemminInput",
                    on=False,
                    label="stemming",
                    labelPosition="bottom",
                    color="#090088"
                ),
                daq.BooleanSwitch(
                    className="preSwitch",
                    id="punctuationInput",
                    on=True,
                    label="punctuation removal",
                    labelPosition="bottom",
                    color="#090088"
                ),
                daq.BooleanSwitch(
                    className="preSwitch",
                    id="hashtagInput",
                    on=True,
                    label="hashtag removal",
                    labelPosition="bottom",
                    color="#090088"
                ),
                daq.BooleanSwitch(
                    className="preSwitch",
                    id="urlInput",
                    on=True,
                    label="URLS removal",
                    labelPosition="bottom",
                    color="#090088"
                ),
                daq.BooleanSwitch(
                    className="preSwitch",
                    id="userInput",
                    on=True,
                    label="usernames removal",
                    labelPosition="bottom",
                    color="#090088"
                )
            ])
        ])
    ])
