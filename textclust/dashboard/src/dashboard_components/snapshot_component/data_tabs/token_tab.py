import dash_html_components as html
import dash_core_components as dcc
from dash.dependencies import Input, Output
import dash_table


def token_tab_layout():
    return dcc.Tab(id="token_tab", value="token-tab", label='Schlagwörter', children=[
        dcc.Store( id = "wordcloud-data"),
        html.Canvas(id="my_canvas", style =  {"width": "100%","object-fit": "contain"}),
        html.Div(className="dataTable", children=[
            dash_table.DataTable(
                id='termTable',
                columns=[
                    {
                        "name": "Schlagwort",
                        "id": "termcolumn"
                    },
                    {
                        "name": "Gewicht",
                        "id": "freqcolumn"
                    }
                ],
                style_cell={'textAlign': 'left',
                            'overflow': 'hidden',
                            'textOverflow': 'ellipsis',
                            'whiteSpace': 'normal'},
                style_table={'width': "100%"},
                style_header={
                    "width": "150px",
                    "color": "black"
                },
                page_action="native",
                page_current=0,
                page_size=8,
                sort_action="native",
                filter_action="native"
            )
        ])
    ])


def register_callback(app):
    # callback functions to reset termTable's pages if fitler query is applied or new data is coming in
    # otherwise, if users watch a table page, which new fetcehs metrics does not reach -> display bug
    # no content, pages must be reset to 0 ( on display page 1)
    # Done
    @app.callback(Output('termTable', 'page_current'),
                  [Input('termTable', 'filter_query'),
                   Input('termTable', 'data')])
    def reset_to_page_0_terms_single(filter_query, data_input):
        return 0

    # word clouds are drawn locally on client side.
    app.clientside_callback(
        """
        function wordlcloud(data, data2) {

              arr = [];
              if (JSON.stringify(data2)!=="{}"){
                  data2.forEach(function (item, index) {
                    arr.push([item["termcolumn"],Math.log(item["freqcolumn"])]);
                   });
              }
              if(data=="token-tab"){
                  var options = { }
                  var canvas = document.getElementById('my_canvas');
                  canvas.width = canvas.getBoundingClientRect().width;
                  canvas.height = canvas.getBoundingClientRect().height;
                  return WordCloud(document.getElementById('my_canvas'), { list: arr, weightFactor: 20,shrinkToFit:1});
              }

        }
        """,
        Output('my_canvas', 'children'),
        [Input('clusterDataTabs', 'value'),
         Input('wordcloud-data','data')]

    )
