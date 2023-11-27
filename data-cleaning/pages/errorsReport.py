from dash import html, dcc
import dash_uploader as du
from utils import Header
import pathlib

# get relative data folder
PATH = pathlib.Path(__file__).parent
DATA_PATH = PATH.joinpath("../data").resolve()


def get_upload_button(id):
    return du.Upload(
        text='Drag and Drop, or Select Files',
        id=id,
        max_file_size=50,  # 50 MB
        filetypes=['csv', 'txt'],
        upload_id=None,
        default_style={
            'width': '80%',
            'border': 'none',
            'textAlign': 'center',
            'margin-top': '60px',
            'background': "#ea8f32",
            'color': 'white',
            'outlineColor': '#ea8f32',
            'font-family': 'Avenir',
            'font-size': '10px',
            'font-weight': '150',
            'border-radius': '10px',
            'minHeight': 1.5,
            'lineHeight': 1
        },
    )


def create_layout(app):
    return html.Div(
        [
            Header(app),
            # page 3
            html.Div(
                [
                    # Row 1
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
                                            Use this section to upload your dataset for cleaning. It is strongly \
                                            advised that you ensure datasets are well prepared and you can use the \
                                            LEO Data Health tool to see where your dataset can be improved. It is, \
                                            important that you read the ",
                                            dcc.Link("LEO Data Cleaning and Processing",
                                                     href="/data-cleaning/errors-report",
                                                     style={"color": "#ea8f32"},
                                                     className="link"
                                                     ),
                                            " report in the Supplementary Documentation tab before performing the \
                                            data cleaning process."
                                        ],
                                        className="paratext"
                                    ),
                                ],
                                className="eight columns",
                            ),
                            html.Div(
                                [
                                    html.Div(
                                        [
                                            get_upload_button(id='data-uploader'),
                                            # html.Div(id='data-cols'),
                                            html.Div(id='upload-status')
                                        ]
                                    ),
                                ],
                                className="four columns",
                            ),
                        ],
                        className="row ",
                    ),
                    # Row 2
                    html.Br([]),
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.H6(
                                        ["Data Preview"],
                                        className="subtitle padded",
                                    ),
                                    html.P(
                                        [
                                            "Below are the first 5 rows of your dataset. Please ensure that the \
                                            data are properly formatted whereby the column names are \
                                            appropriately formatted. You may need to format your dataset \
                                            before cleaning.",
                                            html.Br(),
                                            html.Br(),
                                            html.Div(id='load-dataset', style={'display': 'none'}),
                                            html.Div(id='data-cols', style={'display': 'none'}),
                                            html.Div(id='data-upload-preview')
                                        ],
                                        className="paratext"
                                    ),
                                ],
                                className=" twelve columns",
                            )
                        ],
                        className="row ",
                    ),
                    # Row 3
                    html.Br([]),
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.H6(
                                        ["Configuration"],
                                        className="subtitle padded",
                                    ),
                                    html.P(
                                        "This section is used to configure the cleaning algorithms so that operations \
                                        are best suited to the dataset that you have uploaded. This process is \
                                        automated as much as possible, but for efficiency, please use the following \
                                        fields to specify certain aspects of the data.",
                                        className='paratext'
                                    ),
                                    html.P(
                                        "If date/time fields are found in separate columns in your dataset, \
                                        they will be concatenated before cleaning begins. Please select the detected \
                                        data/time columns below (max. 2). If the timestamp is represented by one \
                                        column, select that one.",
                                        className="paratext"
                                    ),
                                ],
                                className=" twelve columns",
                            )
                        ],
                        className="row ",
                    ),
                    # Row 4
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Div(id='date-cols-dropdown')
                                ],
                                className="four columns",
                            ),
                            html.Div(
                                [
                                    html.Div(id='data-cols-dropdown')
                                ],
                                className="eight columns",
                            )
                        ],
                        className="row ",
                    ),
                    # Row 5
                    html.Br([]),
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Button(
                                        'Clean Data',
                                        id='start-clean',
                                        n_clicks=0,
                                        className="clean-data-button",
                                        style={
                                            'border-left': '5px solid #ea8f32',
                                            'font-family': 'avenir',
                                            'width': '100%'
                                        }
                                    ),
                                ],
                                className="four columns",
                            ),
                        ],
                        className="row ",
                        style={
                            'margin-bottom': '50px'
                        }
                    ),
                    # Row 6
                    html.Br([]),
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.P(
                                        "Error Summary",
                                        className='stats_card',
                                        style={'color': 'white'}
                                    ),
                                    html.Div(id='updated-binlabel-df', style={'display': 'none'}),
                                    html.Div(id='nan-blocks', style={'display': 'none'}),
                                    html.Div(id='out-blocks', style={'display': 'none'}),
                                    html.Div(id='fmt-blocks', style={'display': 'none'}),
                                    html.Div(id='label-ord', style={'display': 'none'}),
                                    html.Div(id='error-report')
                                ],
                                className="four columns",
                                style={
                                    'background-color': '#ea8f32',
                                    'height': '300px',
                                    'padding': '10px',
                                    'margin-right': '10px',
                                    'border-radius': '10px'
                                }
                            ),
                            html.Div(
                                [
                                    html.Div(id='error-plot'),
                                ],
                                className="eight columns",
                                style={
                                    'padding-top': '0px'
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
