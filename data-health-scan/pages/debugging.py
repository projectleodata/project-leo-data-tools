from dash.dependencies import Input, Output, State
import dash_core_components as dcc
import dash_html_components as html
from utils import Header
import pandas as pd
import pathlib
import dash

# get relative data folder
PATH = pathlib.Path(__file__).parent
DATA_PATH = PATH.joinpath("../data").resolve()

INPUTS = ("name", "email", "issue_page", "issue_descrip", "ease_of_use")


def create_layout(app):
    return html.Div(
        [
            Header(app),
            # page 2
            html.Div(
                [
                    # Row 1
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.H6(
                                        "The 'Let's Fix That' Section",
                                        className="subtitle padded",
                                    ),
                                    html.P(
                                        [
                                            "Error detection is no easy task and as datasets will come in various \
                                            sizes, formats, and types, we expect the Data Cleaning Tool to 'break' \
                                            from time to time as we iron out its development. But breaking things \
                                            isn't always bad! If you do experience an error, as simple as it may be, \
                                            you will help us a lot by submitting it here so that we can improve the \
                                            functionality of this tool. Use the fields below to submit a \
                                            troubleshooting request and we will try to solve it as soon as we can."
                                        ],
                                        className="paratext"
                                    ),
                                ],
                                className="eight columns",
                            ),
                            html.Div(
                                [
                                    html.Img(
                                        src=app.get_asset_url("debugging.gif"),
                                        style=
                                        {
                                            'height': '200px',
                                            'width': 'auto',
                                            'margin': '0px 0px',
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
                            html.Div(
                                [
                                    dcc.Input(
                                        id="input-name",
                                        type='text',
                                        placeholder="Full Name",
                                        style={
                                            'height': '25px'
                                        }
                                    ),
                                    dcc.Input(
                                        id="input-email",
                                        type='email',
                                        placeholder="Email",
                                        style={
                                            'margin-left': '25px',
                                            'height': '25px'
                                        }
                                    ),
                                    dcc.Dropdown(
                                        id="input-issue-page",
                                        options=[
                                            {'label': 'Errors Report', 'value': 'Errors Report'},
                                            {'label': 'Solutions Report', 'value': 'Solutions Report'},
                                            {'label': 'Cleaned Data', 'value': 'Cleaned Data'}
                                        ],
                                        placeholder="Select the page with the issue",
                                        style={
                                            'width': '350px',
                                            'font-family': 'avenir',
                                            'vertical-align': 'top'
                                        }
                                    ),
                                ]
                            ),
                        ]
                    ),
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Br(),
                                    dcc.Input(
                                        id="input-issue-descrip",
                                        type='text',
                                        placeholder="Briefly tell us the issue",
                                        style={
                                            'height': '200px',
                                            'width': '650px',
                                            'justify-content': 'top'
                                        }
                                    ),
                                ],
                                className="eight columns"
                            ),
                            html.Div(
                                [
                                    dcc.Slider(
                                        id='input-rating',
                                        min=0,
                                        max=10,
                                        step=None,
                                        marks={
                                            0: 'Difficult',
                                            3: '',
                                            6: '',
                                            10: 'Useful!'
                                        },
                                        value=0,
                                        vertical=True,
                                        verticalHeight=230
                                    )
                                ],
                                className="four columns",
                                style={
                                    'padding-left': '200px',
                                    'height': '200px',
                                    'font-family': 'avenir'
                                }
                            ),
                        ],
                        className="row"
                    ),
                    # Row 3
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Button(
                                        'Submit',
                                        id='submit-debug',
                                        n_clicks=0,
                                        className="clean-data-button",
                                        style={
                                            'border-left': '5px solid #ea8f32',
                                            'font-family': 'avenir',
                                            'width': '50%'
                                        }
                                    ),
                                    html.Div(id='debug-submission')
                                ],
                                className="four columns",
                            )
                        ],
                        className="row",
                    ),
                    html.Div(
                        [
                            html.P(
                                [
                                    "Animation ('500error') by ",
                                    dcc.Link("Kokolv",
                                             href="https://dribbble.com/kokolv",
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
