import dash_html_components as html
import dash_core_components as dcc


def Header(app):
    return html.Div([get_header(app), html.Br([]), get_menu()])


def get_header(app):
    header = html.Div(
        [
            html.Div(
                [
                    html.Img(
                        src=app.get_asset_url("project-leo-logo.png"),
                        className="logo",
                    ),
                ],
                className="row",
            ),
            html.Div(
                [
                    html.Div(
                        [html.P("Data Health Scan")],
                        className="seven columns main-title",
                    ),
                    html.Div(
                        [
                            html.A(
                                "Source Code",
                                href="https://www.bitbucket.org/projectleodata/project-leo-database/src",
                                target="_blank",
                                className="source-code-link",
                            )
                        ],
                        className="five columns",
                    ),
                ],
                className="twelve columns",
                style={"padding-left": "0"},
            ),
            html.Div(
                [
                    html.H2(
                        "version 1.0",
                        className="version",
                        style={"padding-left": 50,
                               "font-size": "14px",
                               "font-family": "Avenir"},
                    )
                ],
                className="row",
            ),
        ],
        className="row",
    )
    return header


def get_menu():
    menu = html.Div(
        [
            dcc.Link(
                "Data Scan",
                href="/data-health-scan/data-scan",
                className="tab first",
            ),
            dcc.Link(
                "Supporting Documentation",
                href="/data-health-scan/supporting-documentation",
                className="tab",
            ),
            dcc.Link(
                "Debugging",
                href="/data-health-scan/debugging",
                className="tab",
            ),
        ],
        className="row all-tabs",
    )
    return menu


def make_dash_table(df):
    """ Return a dash definition of an HTML table for a Pandas dataframe """
    table = []
    for index, row in df.iterrows():
        html_row = []
        for i in range(len(row)):
            html_row.append(html.Td([row[i]]))
        table.append(html.Tr(html_row))
    return table
