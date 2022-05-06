import dash_html_components as html


def header_layout(app):
    return html.Header([
        html.Div([
            html.Div([
                html.Img(className="textClustLogo",
                         src=app.get_asset_url("textClustLogo.png")),
                html.Img(className="wwuLogo",
                         src=app.get_asset_url("wwu_logo.png")),
                html.Img(className="wwuLogo",
                         src=app.get_asset_url("logo_cc_sma.jpg")),
                html.Img(className="wwuLogo",
                         src=app.get_asset_url("algo.jpg")),
                #html.H1("DASHBOARD", className="dashbooardHeader")
            ], className="headerWrapper"),
            html.A([html.Img(className="textClustLogo", src=app.get_asset_url("githubLogo.png"))],
                   className="githubLogo", href="https://github.com/Dennis1989/textClustPy", target="_blank")],
            className="headerOuterWrapper")],
        className="header")
