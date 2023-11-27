from dash import html, dcc
from utils import Header
import pathlib

# get relative data folder
PATH = pathlib.Path(__file__).parent
DATA_PATH = PATH.joinpath("../data").resolve()


def create_layout(app):
    # Page layouts
    return html.Div(
        [
            html.Div([Header(app)]),
            # page 1
            html.Div(
                [
                    # Row 3
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
                    # Row 4
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.H6(
                                        ["Cleaning Steps"],
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
                                            "Before any Project LEO data are analysed, the datasets should be \
                                            preprocessed and cleaned through the use of this tool to ensure that they \
                                            meet the necessary criteria as outlined in the ",
                                            dcc.Link("Data Cleaning and Processing (v1)",
                                                     href="/data-cleaning/overview",
                                                     style={"color": "#ea8f32"},
                                                     className="link"
                                                     ),
                                            " report. When datasets are uploaded to this tool, they are automatically \
                                            processed for various errors as shown in the table below and reported on \
                                            in the following tabs. Data are primarily treated for missing and outlier \
                                            values, where various solutions are then applied to fill and clean the \
                                            data."
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
                                        "Multi-Label Classification",
                                        className="subtitle padded",
                                    ),
                                    html.P(
                                        [
                                            "\
                                            Within LEO we have begun developing a ‘multi-label classification’ \
                                            methodology to clean the data as well as provide proper metadata on the \
                                            cleaning techniques applied. This technique involves the use of various \
                                            algorithms which scan through each ‘row’ in a time series dataset, \
                                            applying the multi-label classification method which mimics an ‘on/off’ \
                                            status depending on the errors listed in the table below.",
                                            html.Br(),
                                            html.Br(),
                                            "An 'Error' and 'Solution' Bit labelling system is applied within \
                                            LEO’s data cleaning. For instance, a row of data can have a label of \
                                            “00000” which means that the data will not be altered from its raw state, \
                                            or a label of “01100” which means that two categories of error have been \
                                            flagged in the data."
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
                    # Row 5
                    html.Div(
                        [
                            html.Img(
                                src=app.get_asset_url("binary-labels.png"),
                                className="binary_labels",
                            ),
                        ],
                        className="row"
                    ),
                    # Row 6
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.H6(
                                        "Data Upload",
                                        className="subtitle padded",
                                    ),
                                    html.P(
                                        [
                                            "\
                                            On the following tab, ",
                                            dcc.Link("Errors Report",
                                                     href="/data-cleaning/errors-report",
                                                     style={"color": "#ea8f32"},
                                                     className="link"
                                                     ),
                                            ", you will have the opportunity \
                                            to upload your dataset (1) for cleaning. It is strongly \
                                            advised that you ensure datasets are well prepared and you can use the ",
                                            dcc.Link("LEO Data Health",
                                                     href="/data-cleaning/errors-report",
                                                     style={"color": "#ea8f32"},
                                                     className="link"
                                                     ),
                                            " tool to see where your dataset can be improved. Once done, you can \
                                            progress through this online tool, using the next tab to begin.",
                                        ],
                                        className="paratext"
                                    ),
                                    # get_upload_button(id='data-uploader'),
                                    # html.Div(id='upload-status'),
                                    # html.Div(id='load-dataset', style={'display': 'none'}),
                                    # html.Div(id='data-upload-preview')
                                ],
                                className="six columns",
                                style={
                                    'padding-right': '35px'
                                }
                            ),
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
