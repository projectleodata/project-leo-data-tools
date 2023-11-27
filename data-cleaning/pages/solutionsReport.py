from dash import html, dcc
from utils import Header
import pathlib

# get relative data folder
PATH = pathlib.Path(__file__).parent
DATA_PATH = PATH.joinpath("../data").resolve()


def create_layout(app):
    return html.Div(
        [
            Header(app),
            # page 4
            html.Div(
                [
                    # Row 1
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.H6(
                                        "Applied Solutions",
                                        className="subtitle padded",
                                    ),
                                    html.P(
                                        [
                                            "\
                                            The error detection stage of the data cleaning process may highlight certain \
                                            issues in the uploaded dataset. If certain errors were observed, missing data \
                                            outliers etc., the page will show how the errors were cleaning and the methods \
                                            applied to improve the data quality. To allow for a transparent data cleaning \
                                            process, the solutions stage will also apply binary labels to the dataset \
                                            effectively allowing you to understand where and how the data were treated. \
                                            Use each of the sections below to see how your data were treated for the \
                                            selected parameters to clean."
                                        ],
                                        className="paratext"
                                    ),
                                ],
                                className="eight columns",
                            ),
                            html.Div(
                                [
                                    html.Img(
                                        src=app.get_asset_url("cleaning.gif"),
                                        style=
                                        {
                                            'height': '180px',
                                            'width': 'auto',
                                            'margin': '0px 20px',
                                            'padding-bottom': '10px'
                                        },
                                    ),
                                ],
                                className="four columns"
                            ),
                        ],
                        className="row"
                    ),
                    # Row 2
                    html.Div(
                        [
                            html.H6(
                                "Missing Data (Small Gaps)",
                                className="subtitle padded",
                            )
                        ],
                        className="row ",
                    ),
                    # Row 3
                    html.Div(
                        [
                            html.H6(
                                "Missing Data (Large Gaps)",
                                className="subtitle padded",
                            ),
                        ],
                        className="row ",
                    ),
                    # Row 4
                    html.Div(
                        [
                            html.H6(
                                "Outliers",
                                className="subtitle padded",
                            ),
                        ],
                        className="row ",
                    ),
                    # Final Row
                    html.Div(
                        [
                            html.P(
                                [
                                    "Animation ('A Look Inside') by ",
                                    dcc.Link("Lula",
                                             href="https://dribbble.com/lulachristman",
                                             style={"color": "#ea8f32"},
                                             className="link"
                                             ),
                                ],
                                className="footnote"
                            ),
                        ],
                        className="four columns"
                    ),
                ],
                className="sub_page",
            ),
        ],
        className="page",
    )
