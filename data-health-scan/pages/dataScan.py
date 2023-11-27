import dash_core_components as dcc
import dash_html_components as html
import dash_uploader as du
import dash_daq as daq
from utils import Header
import pathlib

# get relative data folder
PATH = pathlib.Path(__file__).parent
DATA_PATH = PATH.joinpath("../data").resolve()


def get_upload_button(id):
    return du.Upload(
        text='Upload Dataset',
        id=id,
        max_file_size=50,  # 50 MB
        filetypes=['csv'],
        upload_id=None,
        default_style={
            'width': '80%',
            'border': 'none',
            'textAlign': 'center',
            'margin': '0px',
            'background': "#ea8f32",
            'color': 'white',
            'outlineColor': '#ea8f32',
            'font-family': 'Avenir',
            'font-size': '10px',
            'font-weight': '200',
            'border-radius': '10px',
            'minHeight': 1,
            'lineHeight': 0.8
        },
    )


def create_layout(app):
    # Page layouts
    return html.Div(
        [
            html.Div([Header(app)]),
            # page 1
            html.Div(
                [
                    # Row 1
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.H5("Before You Start",
                                            style={"color": "#ffffff",
                                                   "font-family": "Avenir",
                                                   "font-size": "18px"},
                                            ),
                                    html.Br([]),
                                    html.P(
                                        "\
                                    Within LEO, data are collected from many different sources and partners and this \
                                    tool has been developed to provide a user-friendly interface for both internal \
                                    and external LEO stakeholders. The scripts running the data processing behind \
                                    this tool can be found using the 'Source Code' link above this page, and further \
                                    information can be explored through the 'Supplementary Documentation' tab above. \
                                    Please note that with greater use, this dashboard will highlight some bugs, \
                                    a common experience in the development process. If you discover an error or \
                                    'break' this tool, please use the 'Debugging' tab to submit your issue.",
                                        style={"color": "#ffffff",
                                               "font-family": "Avenir",
                                               "font-size": "12px"},
                                        className="row",
                                    ),
                                ],
                                className="summary",
                            )
                        ],
                        className="row",
                    ),
                    # Row 2
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.H6(
                                        ["The 'Why'"],
                                        className="subtitle padded"
                                    ),
                                    html.P(
                                        [
                                            "\
                                            With the wide array of data types, plug-in projects, MVS (Minimum Viable \
                                            System) trials, and Foreground data coming in and out of Project LEO, \
                                            data are inherently bound to come in a diverse range of formats and \
                                            quality.",
                                            html.Br(),
                                            html.Br(),
                                            "This brings many challenges but sometimes, the biggest issues lie with \
                                            how the data are submitted in the first place. No headers, extra skipped \
                                            lines of data, poorly formatted and inconsistent units and labels ... \
                                            these will also affect how well data can be cleaned and the first step \
                                            lies with you. However, we do recognise that some of these issues are not \
                                            easily identifiable and thus we have created this tool to scan the \
                                            'health' of your datasets."
                                        ],
                                        className="paratext"
                                    ),
                                ],
                                className="six columns",
                                style={
                                    'padding-right': '35px'
                                }
                            ),
                            html.Div(
                                [
                                    html.H6(
                                        "The 'How'",
                                        className="subtitle padded",
                                    ),
                                    html.P(
                                        [
                                            "\
                                            Before cleaning your data with the ",
                                            dcc.Link("Data Cleaning Tool",
                                                     href="/data-cleaning/overview",
                                                     style={"color": "#ea8f32"},
                                                     className="link"
                                                     ),
                                            " or before submitting timeseries datasets to the Project LEO Data \
                                            Sharing Log, you should consider using the Data Health Scan to better \
                                            understand how your data may be affected by errors and/or poor formatting.",
                                            html.Br(),
                                            html.Br(),
                                            "When your dataset is uploaded, our algorithms will be working behind \
                                            the scenes to determine where and how you can improve the data quality \
                                            of your data. In particular, they will assess the level of missing data \
                                            and formatting errors, some of which are easily fixed through basic data \
                                            editing. These recommendations are all in line with standard data practices."
                                        ],
                                        className="paratext"
                                    ),
                                ],
                                className="six columns",
                                style={
                                    'padding-left': '35px'
                                }
                            ),
                        ],
                        className="row",
                        style={"margin-bottom": "15px"},
                    ),
                    # Row 3
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Img(
                                        src=app.get_asset_url("one.png"),
                                        style=
                                        {
                                            'height': '30px',
                                            'width': 'auto',
                                            'margin': '0px 0px',
                                            'padding-bottom': '10px',
                                        },
                                    ),
                                ],
                                className="four columns",
                                style={
                                    "textAlign": "center",
                                    "padding-left": "20px"
                                }
                            ),
                            html.Div(
                                [
                                    html.Img(
                                        src=app.get_asset_url("two.png"),
                                        style=
                                        {
                                            'height': '30px',
                                            'width': 'auto',
                                            'margin': '0px 0px',
                                            'padding-bottom': '10px',
                                        },
                                    ),
                                ],
                                className="four columns",
                                style={
                                    "textAlign": "center",
                                    "padding-left": "40px"
                                }
                            ),
                            html.Div(
                                [
                                    html.Img(
                                        src=app.get_asset_url("three.png"),
                                        style=
                                        {
                                            'height': '30px',
                                            'width': 'auto',
                                            'margin': '0px 0px',
                                            'padding-bottom': '10px',
                                        },
                                    ),
                                ],
                                className="four columns",
                                style={
                                    "textAlign": "center",
                                    "padding-left": "50px"
                                }
                            )
                        ]
                    ),
                    # Row 4
                    html.Div(
                        [
                            html.Div(
                                [
                                    get_upload_button(id='data-uploader'),
                                    html.Div(id='upload-status')
                                ],
                                className="four columns",
                                style={
                                    "textAlign": "center",
                                    "padding-left": "50px"
                                }
                            ),
                            html.Div(
                                [
                                    dcc.Dropdown(
                                        id="config-scan1",
                                        options=[
                                            {'label': 'Yes', 'value': 'yes'},
                                            {'label': 'No', 'value': 'no'}
                                        ],
                                        placeholder="Timeseries Power Data?",
                                        style={
                                            'width': '200px',
                                            'font-family': 'avenir',
                                            'font-size': '11px',
                                            'align-items': 'center',
                                            'justify-content': 'center'
                                        }
                                    ),
                                    dcc.Dropdown(
                                        id="config-scan2",
                                        options=[
                                            {'label': 'Yes, Data other than headers is numeric', 'value': 'yes'},
                                            {'label': 'No, Data other than headers can be nonnumeric', 'value': 'no'}
                                        ],
                                        placeholder="Only Numeric Data",
                                        style={
                                            'width': '200px',
                                            'font-family': 'avenir',
                                            'font-size': '11px',
                                            'align-items': 'center',
                                            'margin-top': '10px',
                                            'justify-content': 'center'
                                        }
                                    ),
                                ],
                                className="four columns",
                                style={
                                    "textAlign": "center",
                                    "padding-left": "35px"
                                }
                            ),
                            html.Div(
                                [
                                    html.Button(
                                        'Scan Data',
                                        id='scan-data',
                                        n_clicks=0,
                                        className="clean-data-button",
                                        style={
                                            'border-left': '5px solid #ea8f32',
                                            'font-family': 'avenir',
                                            'width': '80%'
                                        }
                                    ),
                                ],
                                className="four columns",
                                style={
                                    "textAlign": "center",
                                    "padding-left": "50px",
                                    "padding-right": "0px"
                                }
                            )
                        ],
                        className="row",
                        style={
                            "margin-top": "50px",
                            "margin-bottom": "50px"
                        }
                    ),
                    # Row 3
                    html.Div(
                        [
                            html.Div(
                                id="gauge1",
                                children=[
                                    html.P("Missing Data"),
                                    daq.Gauge(
                                        id="missing-gauge",
                                        max=100,
                                        min=0,
                                        value=0,
                                        units='%',
                                        showCurrentValue=True,  # default size 200 pixel
                                        color='#EA8F32',
                                    ),
                                ],
                                className="four columns"
                            ),
                            html.Div(
                                id="gauge2",
                                children=[
                                    html.P("Outliers"),
                                    daq.Gauge(
                                        id="outlier-gauge",
                                        max=100,
                                        min=0,
                                        value=0,
                                        units='%',
                                        showCurrentValue=True,  # default size 200 pixel
                                        color='#EA8F32',
                                    ),
                                ],
                                className="four columns",
                            ),
                            html.Div(
                                id="gauge3",
                                children=[
                                    html.P("Time Gaps"),
                                    daq.Gauge(
                                        id="timegaps-gauge",
                                        max=100,
                                        min=0,
                                        value=10,
                                        units='%',
                                        showCurrentValue=True,  # default size 200 pixel
                                        color='#EA8F32',
                                    ),
                                ],
                                className="four columns"
                            ),
                        ],
                        className="row"
                    ),
                    # Final row
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.H6(
                                        "Developers",
                                        className="subtitle padded",
                                    ),
                                    html.Div(
                                        [
                                            html.Div(
                                                html.Img(
                                                    src=app.get_asset_url("ScotW.png"),
                                                    className="headshot",
                                                    style={
                                                        'margin-left': '10px'
                                                    }
                                                ),
                                            ),
                                            html.Div(
                                                [
                                                    html.Div(
                                                        html.P(
                                                            "Dr. Scot Wheeler",
                                                            className="paratext",
                                                            style={
                                                                'margin-left': '15px',
                                                                'padding-top': '0px'
                                                            }
                                                        ),
                                                    ),
                                                    html.Div(
                                                        html.A(
                                                            html.Img(
                                                                src=app.get_asset_url("email_icon.png"),
                                                                className="email-icon"
                                                            ), href='mailto:scot.wheeler@eng.ox.ac.uk',
                                                            target="_blank"
                                                        )
                                                    )
                                                ]
                                            )
                                        ],
                                        style={'display': 'inline-block'}
                                    ),
                                    html.Div(
                                        [
                                            html.Div(
                                                html.Img(
                                                    src=app.get_asset_url("MasaoA.png"),
                                                    className="headshot",
                                                    style={
                                                        'margin-left': '10px'
                                                    }
                                                ),
                                            ),
                                            html.Div(
                                                [
                                                    html.Div(
                                                        html.P(
                                                            "Dr. Masaō Ashtine",
                                                            className="paratext",
                                                            style={
                                                                'margin-left': '15px',
                                                                'padding-top': '0px'
                                                            }
                                                        ),
                                                    ),
                                                    html.Div(
                                                        html.A(
                                                            html.Img(
                                                                src=app.get_asset_url("email_icon.png"),
                                                                className="email-icon"
                                                            ), href='mailto:masao.ashtine@eng.ox.ac.uk',
                                                            target="_blank"
                                                        )
                                                    )
                                                ]
                                            )

                                        ],
                                        style={'display': 'inline-block'}
                                    )
                                ],
                                className="six columns",
                                style={
                                    'padding-left': '35px'
                                }
                            ),
                        ],
                        className="row ",
                    ),
                ],
                className="sub_page",
            ),
        ],
        className="page",
    )
