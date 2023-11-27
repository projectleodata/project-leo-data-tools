# -*- coding: utf-8 -*-
import io
import dash
import base64
import yagmail
import pandas as pd
import plotly.graph_objs as go
from dash import html, dash_table, dcc
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
from dash.dependencies import Input, Output
from scripts.dash_timeseriesClean import load_df, Formatting, Errors, Solutions

app = dash.Dash(__name__, meta_tags=[{"name": "viewport", "content": "width=device-width"}],
                suppress_callback_exceptions=True)
server = app.server


def Header(app):
    return html.Div([get_header(app), html.Br([])])


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
                        [html.P("Data Cleaning Tool")],
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


def parse_contents(contents):
    # This function will only run once the right file type has been uploaded
    # Split the binary string by decoding type and the encoded string
    content_type, content_string = contents.split(',')

    # Decode the data
    decoded = base64.b64decode(content_string)

    # Assumes that the user uploaded a CSV or TXT file
    df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))

    return df

    #     return html.Div(
    #         [
    #             dcc.Store(id='stored-data', data=df.to_dict('records'), storage_type='memory')
    #         ]
    #     )
    # else:
    #     return html.Div(
    #         [
    #             dcc.Store(id='stored-data', data=[{}], storage_type='memory')
    #         ]
    #     )


def error_solutions_processing(data_cols, date_cols, contents):
    """
    This function contains the sequence used to detect errors and clean the data based on various 'solutions'.

    :param data_cols: User selected data columns for data to clean
    :param date_cols: User selected date columns
    :param contents: Binary data uploaded by user

    :return:
    """
    # Initialize the Formatting and Errors classes
    fmt = Formatting()
    data_errors = Errors()

    # Reupload the data. This needs to be done because the serialisation of data into JSON affects how pandas
    # reads in the datetime columns. This is not efficient and should be improved
    full_df = parse_contents(contents)

    # Establish the cols to clean and the date/time cols
    cols_toclean = data_cols['props']['children']['props']['value']
    date_cols = date_cols['props']['children']['props']['value']

    # This section will add the "Errors" and "Solutions" columns
    # into the df as well as columns where the cleaned data will be entered. The label ord is important for
    # later cleaning stages.
    df = load_df(full_df, date_cols)
    label_ord, binlabel_df = fmt.bin_labels(df, cols_toclean)

    # Now that the df has been formatted, the following section will use the `error_detect` function to scan
    # for errors as per the cleaning documentation, and comments found within the subfunctions.
    updated_binlabel_df, nan_blocks, out_blocks, fmt_blocks, totals = data_errors. \
        err_detect(binlabel_df, cols_toclean)

    # Determine the stats for each column (not the most efficient as it is done in the `error_detect` subfunctions)
    # Only report for missing data and outliers
    # TODO: Remove totals from the error_detect subfunctions
    error_totals = {}

    for i, key in enumerate(nan_blocks.keys()):
        sin_tot, mul_tot, lrg_tot, out_tot = 0, 0, 0, 0
        size_idx = nan_blocks[key][1]

        # TODO: will need to have something similar for all in case there is no missing data
        if out_blocks:
            if key in out_blocks.keys():
                out_tot = len(out_blocks[key][1])

        for s, sze in enumerate(size_idx):
            # Single/Two Missing/Nan values
            if sze == 1:
                sin_tot += 1
            elif sze == 2:
                sin_tot += 1
            # Multiple Missing/Nan Values
            elif 2 < sze <= 10:
                mul_tot += 1
            # Large Gap in the data
            else:
                lrg_tot += 1
        error_totals[key] = [sin_tot, mul_tot, lrg_tot, out_tot]

    error_report = html.Div(
        [
            html.P(
                "Error checking on your dataset has just been performed based on the columns parsed \
                parsed above. The following information summarizes the results:",
                className='stats_card_nobar',
                style={'color': 'white'}
            ),
            html.P(
                "Total columns with errors: {}".format(len(nan_blocks.keys())),
                className='stats_card_nobar',
                style={'color': 'white'}
            ),
            html.P(
                "Total blocks of Single/Two Missing Values: {}".format(totals[0][0]),
                className='stats_card_nobar',
                style={'color': 'white'}
            ),
            html.P(
                "Total blocks of Multiple Missing Values: {}".format(totals[0][1]),
                className='stats_card_nobar',
                style={'color': 'white'}
            ),
            html.P(
                "Total blocks of Large Gaps: {}".format(totals[0][2]),
                className='stats_card_nobar',
                style={'color': 'white'}
            ),
            html.P(
                "Total blocks of Outlier Values: {}".format(totals[1]),
                className='stats_card_nobar',
                style={'color': 'white'}
            )
        ],
        style={
            'padding-top': '15px',
            'padding-bottom': '15px'
        }
    )

    # Setup the data for plotting
    plot_df = pd.DataFrame(columns=cols_toclean, index=['Single', 'Multiple', 'Large Gap', 'Outlier'])
    for col in cols_toclean:
        plot_df[col] = error_totals[col]

    # Define the colour palette, 5 maximum
    colours = ['#fab81e', '#f7e1bc', '#f7c143', '#f7c877', '#fcd695']

    # Create bar plots for each of the columns cleaned
    error_plot = html.Div(
        dcc.Graph(
            id="error-bar-plot",
            figure={
                "data": [
                    go.Bar(
                        x=plot_df.index.to_list(),
                        y=plot_df[col].to_list(),
                        marker={"color": colours[i]},
                        name=col
                    ) for i, col in enumerate(cols_toclean)
                ],
                "layout": go.Layout(
                    margin=dict(t=0, b=160, l=10, r=10),
                    autosize=True,
                    legend=dict(orientation='h', font=dict(size=10)),
                    bargap=0.4,
                    font={'family': 'avenir'},
                    hovermode="closest",
                    showlegend=True,
                    title="",
                    xaxis={
                        "autorange": True,
                        "showline": True,
                        "tickfont": {
                            "family": "Avenir",
                            "size": 8,
                        },
                        # "title": "Type of Error (Missing & Outliers)"
                    },
                    yaxis={
                        "autorange": True,
                        "showgrid": False,
                        "showline": False,
                        "tickfont": {
                            "family": "Avenir",
                            "size": 10,
                        },
                        "title": ""
                    },
                ),
            },
            config={"displayModeBar": False},
        )
    )

    # This callback will also process the solutions implementation within the data. The Errors and Solutions
    # processing was merged into one callback owing to how the JSON serialisation affects the binary labels.
    # If the JSON dataset (updated-binlabel-df) is ingested into another callback and converted to a Pandas
    # dataframe, the labels like "00000" become an integer 0. Labels of "00100" for instance, become an 'integer'
    # This can be optimized by explicitly (possibly) changing the data types in the dataframe before conversion
    # to JSON

    # Initialize the Solutions class
    data_sols = Solutions(updated_binlabel_df, cols_toclean, label_ord, nan_blocks, out_blocks, fmt_blocks)

    # First need to organize the dataset so that the timestamp column becomes the index. This step also determines the
    # frequency of the data, even if time is already set as the dataframe's index. The default state assumes that
    # the timestamp data are in a single column and not the index (usually the case with uploaded data)
    # NB: This should only be performed on datasets with a timestamp column/index
    time_idx = False
    updated_binlabel_df, freq = data_sols.time_freq(time_idx)

    # The next part of the script will perform data filling on columns that contain power data.
    # Outliers will first be removed from the data (raw data columns will be left untouched), and then the
    # location of these outliers will be combined with information on other missing
    # data which will be used to fill the data and update the 'Solutions' labels.
    if len(out_blocks.keys()) > 0:
        updated_binlabel_df, out_nan_blocks = data_sols.rvm_outliers(updated_binlabel_df)
    else:
        out_nan_blocks = {}

    # The dataframe is now ready for the filling of missing data. Please see the 'power_fill' function in the
    # 'dash_timeseriesClean.py' library for more information. The output variables, 'fill_blocks' and
    # 'interp_blocks' will give more information on how parts of the dataset were cleaned and what
    # methods were applied
    if out_nan_blocks:
        updated_binlabel_df, fill_blocks, interp_blocks = data_sols.power_fill(updated_binlabel_df, out_nan_blocks,
                                                                               freq, offset=1, interp='linear')
    else:
        fill_blocks, interp_blocks = {}, {}

    return updated_binlabel_df, out_blocks, out_nan_blocks, fill_blocks, interp_blocks, error_report, error_plot


overview = dbc.Card(
    dbc.CardBody(
        [
            html.Div(
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
                                                       "font-size": "16px"},
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
                                                             href="https://project-leo.co.uk/reports/data-"
                                                                  "cleaning-and-processing-march-2021/",
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
                                                    On the following tab, ""Errors Report",
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
                className="page"
            )
        ]
    )
)

errorsReport = dbc.Card(
    dbc.CardBody(
        [
            html.Div(
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
                                                    LEO Data Health tool to see where your datasets can be improved. It is \
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
                                                    html.Button(
                                                        dcc.Upload(
                                                            id="uploaded-data",
                                                            children=html.Div(['Upload File']),
                                                            multiple=False
                                                        ),
                                                        id='upload-btn',
                                                        n_clicks=0,
                                                        style={
                                                            'width': '100%',
                                                            'height': '60px',
                                                            'border': 'none',
                                                            'lineHeight': '60px',
                                                            'textAlign': 'center',
                                                            'margin-top': '60px',
                                                            'background': "#ea8f32",
                                                            'color': 'white',
                                                            'outlineColor': '#ea8f32',
                                                            'font-family': 'Avenir',
                                                            'font-size': '10px',
                                                            'font-weight': '150',
                                                            'border-radius': '30px',
                                                        },
                                                    ),
                                                    html.Div(id='upload-status'),
                                                    html.Div(id='output-data-upload')
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
                                                style={
                                                    'color': 'white',
                                                    'font-size': '14px'
                                                }
                                            ),
                                            # html.Div(id='updated-binlabel-df', style={'display': 'none'}),
                                            # html.Div(id='nan-blocks', style={'display': 'none'}),
                                            # html.Div(id='out-blocks', style={'display': 'none'}),
                                            # html.Div(id='fmt-blocks', style={'display': 'none'}),
                                            # html.Div(id='label-ord', style={'display': 'none'}),
                                            html.Div(id='error-report')
                                        ],
                                        className="four columns",
                                        style={
                                            'background-color': '#ea8f32',
                                            'height': '350px',
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
        ]
    )
)

solutionsReport = dbc.Card(
    dbc.CardBody(
        [
            html.Div(
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
                                                    outliers etc., this page will show how the errors were cleaned and the methods \
                                                    applied to improve the data quality. To allow for a transparent data cleaning \
                                                    process, the solutions stage will also apply binary labels to the dataset \
                                                    effectively allowing you to understand where and how the data were treated. \
                                                    Use each of the sections below to see how your data were handled for the \
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
                                                    'height': '250px',
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
                            html.Div(
                                [
                                    html.Div(
                                        [
                                            html.P(
                                                [
                                                    "Quick Note"
                                                ],
                                                className="paratext",
                                                style={
                                                    "font-style": "italic",
                                                    "color": "#ea8f32"
                                                }
                                            ),
                                            html.P(
                                                [
                                                    "If errors exist, data filling has just been performed on the \
                                                    dataset based on the \
                                                    columns parsed to the function. It is important to remember that \
                                                    gaps listed as 'unfilled' have been left untouched owing to \
                                                    missing data in the surrounding time windows used to fill the \
                                                    data. This may be more common in high-resolution datasets \
                                                    (1s, 30s etc) \
                                                    that do not have a wide range of data where buffer times can be \
                                                    used to fill gaps for particular times of the day/week."
                                                ],
                                                className="paratext",
                                                style={
                                                    "font-style": "italic"
                                                }
                                            ),
                                            html.P(
                                                [
                                                    "The tables below will remain hidden if no errors were detected."
                                                ],
                                                className="paratext",
                                                style={
                                                    "font-style": "italic",
                                                    "color": "#ea8f32"
                                                }
                                            ),
                                            html.Br(),
                                            html.Br()
                                        ],
                                        className="twelve columns",
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
                                    ),
                                    html.P(
                                        [
                                            "Small Gaps constitute missing data of two (2) or less data points."
                                        ],
                                        className="paratext"
                                    ),
                                    html.Div(id='final-binlabel-df', style={"display": "none"}),
                                    html.Div(id='missing-sml'),
                                ],
                                style={
                                    'margin-bottom': '50px'
                                },
                                className="row ",
                            ),
                            # Row 3
                            html.Div(
                                [
                                    html.H6(
                                        "Missing Data (Large Gaps)",
                                        className="subtitle padded",
                                    ),
                                    html.P(
                                        [
                                            "Large Gaps constitute missing data of three (3) or more data points."
                                        ],
                                        className="paratext"
                                    ),
                                    html.Div(id='missing-lrg'),
                                ],
                                style={
                                    'margin-bottom': '50px'
                                },
                                className="row ",
                            ),
                            # Row 4
                            html.Div(
                                [
                                    html.H6(
                                        "Outliers",
                                        className="subtitle padded",
                                    ),
                                    html.P(
                                        [
                                            "If outliers were detected, they have been removed and treated as missing "
                                            "values and will be reported above if applicable."
                                        ],
                                        className="paratext"
                                    ),
                                ],
                                style={
                                    'margin-bottom': '50px'
                                },
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
        ]
    )
)

cleanedData = dbc.Card(
    dbc.CardBody(
        [
            html.Div(
                [
                    Header(app),
                    # page 5
                    html.Div(
                        [
                            # Row 1
                            html.Div(
                                [
                                    html.Div(
                                        [
                                            html.H6(
                                                ["Understanding How Data Were Cleaned"],
                                                style={
                                                    'margin-bottom': '10px'
                                                },
                                                className="subtitle padded"
                                            ),
                                            html.Div(
                                                [
                                                    html.P(
                                                        [
                                                            "When the cleaning process has been completed, "
                                                            "you will see some descriptive information to help "
                                                            "you better assess how your dataset has been cleaned. "
                                                            "Please remember that this section will only be populated "
                                                            "if errors have been detected in your dataset."
                                                        ],
                                                        className="paratext"
                                                    )
                                                ],
                                                className="row",
                                                style={
                                                    'margin-bottom': '30px',
                                                },
                                            ),
                                            html.Div(id='clean-report'),
                                            html.Div(id='clean-stats', style={'display': 'none'}),
                                            html.H6(
                                                ["Download Your Cleaned Data"],
                                                style={
                                                    'margin-bottom': '10px',
                                                    'margin-top': '50px'
                                                },
                                                className="subtitle padded"
                                            ),
                                            html.Div(id='download-msg'),
                                        ]
                                    ),
                                    html.Div(
                                        [
                                            dcc.Dropdown(
                                                id="raw-clean-opt",
                                                options=[
                                                    {'label': 'Cleaned Data Only', 'value': 'clean data'},
                                                    {'label': 'Cleaned and Raw Data', 'value': 'clean and raw'}
                                                ],
                                                placeholder="What data do you want?",
                                                style={
                                                    'width': '350px',
                                                    'font-family': 'avenir',
                                                    'vertical-align': 'top'
                                                }
                                            ),
                                        ],
                                        style={
                                            'margin-bottom': '20px'
                                        },
                                        className="row"
                                    ),
                                    html.Div(
                                        [
                                            html.Div(
                                                [
                                                    html.Button(
                                                        "Download CSV",
                                                        id="btn_csv",
                                                        n_clicks=0,
                                                        className="clean-data-button",
                                                        style={
                                                            'border-left': '5px solid #ea8f32',
                                                            'font-family': 'avenir',
                                                            'width': '100%'
                                                        }
                                                    ),
                                                    dcc.Download(id="download-clean-data")
                                                ],
                                                className="four columns"
                                            ),

                                        ],
                                        className="row"
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
        ]
    )
)

supportingDocumentation = dbc.Card(
    dbc.CardBody(
        [
            html.Div(
                [
                    Header(app),
                    # page 6
                    html.Div(
                        [
                            # Row 1
                            html.Div(
                                [
                                    html.Div(
                                        [
                                            html.H6("Important Links and Reports", className="subtitle padded"),
                                            html.P(
                                                [
                                                    "\
                                                    This data dashboard utilises various scripts and data analytical methods \
                                                    that are not all explained within these pages. How are Z-Scores used to \
                                                    detect outliers? Why are the various interpolation methods used to \
                                                    gap-fill the power data? These questions and more can be found through \
                                                    the various report links below. It is also important to note how data are \
                                                    generally handled in Project LEO, and thus, various reports that aid in \
                                                    this understanding have been referenced below."
                                                ],
                                                className="paratext"
                                            ),
                                        ],
                                        className="row",
                                    ),
                                ],
                                className="row ",
                            ),
                            # Row 2
                            html.Div(
                                [
                                    html.Div(
                                        [
                                            html.Br(),
                                            html.Br(),
                                            html.A(
                                                html.Img(
                                                    src=app.get_asset_url("data-cleaning-processing.png"),
                                                    className="supp_reports"
                                                ),
                                                href='https://project-leo.co.uk/reports/data-cleaning-and-'
                                                     'processing-march-2021/',
                                                target="_blank"
                                            ),
                                            html.P(
                                                [
                                                    'This report (and previous versions) is the basis of the Data \
                                                    Cleaning Tool and explains the data cleaning methods.'
                                                ],
                                                className='paratext',
                                                style={
                                                    "padding-right": "30px",
                                                    "padding-left": "30px",
                                                    "text-align": "center"
                                                }
                                            )
                                        ],
                                        className="four columns",
                                    ),
                                    html.Div(
                                        [
                                            html.Br(),
                                            html.Br(),
                                            html.A(
                                                html.Img(
                                                    src=app.get_asset_url("data-standards-protocols.png"),
                                                    className="supp_reports"
                                                ),
                                                href='https://project-leo.co.uk/reports/'
                                                     'project-leo-data-standards-and-protocol/',
                                                target="_blank"
                                            ),
                                            html.P(
                                                [
                                                    'This report is helpful in understanding the ways in which data are \
                                                    treated in LEO in terms of data standards.'
                                                ],
                                                className='paratext',
                                                style={
                                                    "padding-left": "35px",
                                                    "text-align": "center"
                                                }
                                            )
                                        ],
                                        className="four columns",
                                    ),
                                    html.Div(
                                        [
                                            html.Br(),
                                            html.Br(),
                                            html.A(
                                                html.Img(
                                                    src=app.get_asset_url("data-collection-access.png"),
                                                    className="supp_reports"
                                                ),
                                                href='https://project-leo.co.uk/reports/'
                                                     'data-collection-and-access-jan-2021/',
                                                target="_blank"
                                            ),
                                            html.P(
                                                [
                                                    'Use this report to better understand how LEO collects and handles data '
                                                    'coming in from project activities'
                                                ],
                                                className='paratext',
                                                style={
                                                    "padding-left": "35px",
                                                    "text-align": "center"
                                                }
                                            )
                                        ],
                                        className="four columns",
                                    ),
                                ],
                                className="row ",
                            ),
                            # Row 3
                            html.Div(
                                [
                                    html.Div(
                                        [
                                            html.A(
                                                html.Img(
                                                    src=app.get_asset_url("Bitbucket.png"),
                                                    className="supp_reports_large",
                                                    style={
                                                        'margin-top': '80px',
                                                        'padding-top': '0px',
                                                        'height': '50%',
                                                        'width': '50%'
                                                    }
                                                ),
                                                href='https://www.bitbucket.org/projectleodata/'
                                                     'project-leo-database/src',
                                                target="_blank",
                                                style={
                                                    'margin-top': '0px',
                                                    'padding-top': '0px'
                                                }
                                            ),
                                            html.P(
                                                [
                                                    'Want to dive deeper into the scripts behind this dashboard? You can click \
                                                    on the image above or the "Source Code" button at the top of the page \
                                                    to head over to the LEO BitBucket Repository (Restricted Access)'
                                                ],
                                                className='paratext',
                                                style={
                                                    "padding-left": "35px",
                                                    "padding-right": "35px",
                                                    "text-align": "center"
                                                }
                                            )
                                        ],
                                        className="twelve columns",
                                        style={
                                            'textAlign': 'center',
                                            'margin-top': '0px'
                                        }
                                    )
                                ],
                                className="row ",
                            )
                        ],
                        className="sub_page",
                    ),
                ],
                className="page",
            )
        ]
    )
)

debugging = dbc.Card(
    dbc.CardBody(
        [
            html.Div(
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
                                                    'height': '300px',
                                                    'width': 'auto',
                                                    'margin': '0px 0px',
                                                },
                                            ),
                                        ],
                                        className="four columns"
                                    ),
                                ],
                                className="row",
                                style={
                                    'margin-bottom': '0px'
                                }
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
                                                    'height': '25px',
                                                    'font-family': 'avenir',
                                                    'font-size': '14px',
                                                }
                                            ),
                                            dcc.Input(
                                                id="input-email",
                                                type='email',
                                                placeholder="Email",
                                                style={
                                                    'margin-left': '25px',
                                                    'height': '25px',
                                                    'font-family': 'avenir',
                                                    'font-size': '14px'
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
                                                    'vertical-align': 'top',
                                                    'font-size': '14px'
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
                                                    'width': '850px',
                                                    'justify-content': 'top',
                                                    'font-family': 'avenir',
                                                    'font-size': '14px'
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
                                            'font-family': 'avenir',
                                            'font-size': '14px'
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
                                                    'font-size': '14px',
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
                            # Final Row
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
        ]
    )
)

tabs_styles = {
    'align-items': 'center',
}

tab_style = {
    'borderBottom': '1px solid #d6d6d6',
    'background-color': 'white',
    'color': '#3D4E68'
}

tab_selected_style = {
    'borderTop': '4px solid #ea8f32',
    'borderBottom': '1px solid #d6d6d6',
    'background-color': 'white',
    'color': '#ea8f32',
}

app.layout = html.Div([
    dcc.Tabs(
        [
            dcc.Tab(label="Overview", style=tab_style,
                    selected_style=tab_selected_style, children=[overview]),
            dcc.Tab(label="Errors Report", style=tab_style,
                    selected_style=tab_selected_style, children=[errorsReport]),
            dcc.Tab(label="Solutions Report", style=tab_style,
                    selected_style=tab_selected_style, children=[solutionsReport]),
            dcc.Tab(label="Cleaned Data", style=tab_style,
                    selected_style=tab_selected_style, children=[cleanedData]),
            dcc.Tab(label="Supporting Documentation", style=tab_style,
                    selected_style=tab_selected_style, children=[supportingDocumentation]),
            dcc.Tab(label="Debugging", style=tab_style,
                    selected_style=tab_selected_style, children=[debugging]),
        ],
        id="tabs",
        style=tabs_styles
    )
]
)


@app.callback([Output('load-dataset', 'data'),
               Output('upload-status', 'children'),
               Output('data-cols', 'data')],
              [Input('uploaded-data', 'contents'),
              Input('uploaded-data', 'filename')])
def update_output(contents, name):
    # First determine if something was uploaded
    if contents is not None:
        # Determine if the right file type was uploaded
        ext = name.split('.')[-1]

        if ext == 'csv' or ext == 'txt':
            # Update the status message
            up_status = html.Div(
                [
                    "{} Upload Successful".format(name),
                ],
                className="status_msg",
                style={
                    "margin-top": "0px",
                    "padding-left": "10px",
                    "padding-right": "10px"
                }
            )

            # Parse the df and cols from the uploaded data
            df = parse_contents(contents)
            cols = []
            for col in df.columns:
                cols.append({'label': '{}'.format(col), 'value': col})

            # Need to use 'orient='records'' when exporting to JSON format for dash callbacks
            full_data = df.to_json(orient='records')

            return full_data, up_status, cols
    else:
        raise PreventUpdate


# @app.callback(Output('upload-status', 'children'),
#               Input('data-uploader', 'isCompleted'),
#               State('data-uploader', 'fileNames'), )
# def upload_status(iscompleted, filename):
#     """
#     Simple callback function to print the status of the uploaded database
#
#     :param
#     iscompleted: flag for data upload being successful
#     filename: filename
#
#     :return: HTML status
#     """
#     # Assumes that the user uploads only one file as instructed.
#     if iscompleted:
#         return html.Div(
#             [
#                 "{} Upload Successful".format(filename[0]),
#             ],
#             className="status_msg",
#             style={
#                 "margin-top": "0px",
#                 "padding-left": "10px",
#                 "padding-right": "10px"
#             }
#         )
#     return dash.no_update


# @app.callback([Output('load-dataset', 'data'),
#                Output('data-cols', 'data')],
#               [Input('data-uploader', 'isCompleted'),
#                Input('data-uploader', 'fileNames')],
#               State('data-uploader', 'upload_id'))
# def load_data(iscompleted, filename, upload_id):
#     """
#     Callback function to load the uploaded dataset from local storage
#
#     :param
#     iscompleted: flag for data upload being successful
#     filename: filename
#     upload_id: user session id
#
#     :return: Dataframe, column names
#     """
#     if iscompleted:
#         os.chdir(os.path.join(UPLOAD_FOLDER_ROOT, upload_id))
#
#         #TODO: Add automatic skiprow detection
#         if filename[0].split('.')[-1] == 'txt':
#             with open(filename[0], 'r') as csvfile:
#                 dialect = csv.Sniffer().sniff(csvfile.read(1024))
#             df = pd.read_csv(filename[0], index_col=False, delimiter=dialect.delimiter)
#         else:
#             df = pd.read_csv(filename[0], index_col=False)
#
#         cols = []
#         for col in df.columns:
#             cols.append({'label': '{}'.format(col), 'value': col})
#
#         # Need to use 'orient='records''
#         full_data = df.to_json(orient='records')
#
#         # TODO: add another return to return an empty JSON dict if 'not iscomplete'
#         return full_data, cols
#     else:
#         raise PreventUpdate


@app.callback(Output('data-upload-preview', 'children'),
              [Input('load-dataset', 'data'),
               Input('upload-btn','n_clicks')])
def upload_preview(full_data, clicks):
    """
    Callback function to load the uploaded dataset from local storage

    :param
    full_data: Binary dataset
    clicks: number of button clicks

    :return: Dash Data table
    """

    if full_data is not None:
        df = pd.read_json(full_data, orient='records')
        data_preview = html.Div([
            html.P(
                [
                    "Below are the first 5 rows of your dataset. Please ensure that the \
                    data are properly formatted whereby the column names are \
                    appropriately formatted. You may need to format your dataset \
                    before cleaning.",
                    html.Br(),
                    html.Br(),
                ],
                className="paratext"
            ),
            dash_table.DataTable(data=df[:5].to_dict("rows"),
                                 columns=[{"id": x, "name": x} for x in df.columns],
                                 style_cell={'textAlign': 'left',
                                             'minWidth': '180px', 'width': '180px', 'maxWidth': '180px',
                                             'overflow': 'hidden',
                                             'textOverflow': 'ellipsis',
                                             'fontFamily': 'Avenir'
                                             },
                                 tooltip_data=[
                                     {
                                         column: {'value': str(value), 'type': 'markdown'}
                                         for column, value in row.items()
                                     } for row in df.to_dict('records')
                                 ],
                                 tooltip_duration=None,
                                 style_header={
                                     'backgroundColor': 'white',
                                     'fontWeight': 'bold',
                                     'fontFamily': 'Avenir',
                                     'border': 'none'
                                 },
                                 style_data_conditional=[
                                     {
                                         'if': {'row_index': 'odd'},
                                         'backgroundColor': '#FBF2E6'
                                     }
                                 ],
                                 style_as_list_view=True,
                                 style_table={'overflowX': 'auto'},
                                 persistence=True
                                 ),
        ])
        return data_preview

    elif clicks == 0:
        dummy_data = [['', ''], ['', ''], ['', ''], ['', ''], ['', '']]
        dummy_df = pd.DataFrame(dummy_data, columns=['Your data preview will display here once '
                                                     'successfully uploaded', ''])
        data_preview = html.Div([
            dash_table.DataTable(data=dummy_df[:5].to_dict("rows"),
                                 columns=[{"id": x, "name": x} for x in dummy_df.columns],
                                 style_cell={'textAlign': 'left',
                                             'minWidth': '180px', 'width': '180px', 'maxWidth': '180px',
                                             'overflow': 'hidden',
                                             'textOverflow': 'ellipsis',
                                             },
                                 style_header={
                                     'backgroundColor': 'white',
                                     'fontWeight': 'bold',
                                     'fontFamily': 'Avenir',
                                     'border': 'none'
                                 },
                                 style_data_conditional=[
                                     {
                                         'if': {'row_index': 'odd'},
                                         'backgroundColor': '#FBF2E6'
                                     }
                                 ],
                                 style_as_list_view=True,
                                 style_table={'overflowX': 'auto'}
                                 ),
        ])

        return data_preview


@app.callback(Output('data-cols-dropdown', 'children'),
              [Input('data-cols', 'data'),
               Input('uploaded-data', 'filename')])
def update_cols_dropdown(data_cols, name):
    """
    Callback function to update the  data columns available for cleaning

    :param
    data_cols: df columns
    name: flag for data upload being successful

    :return: dropdown menu options
    """
    if not name:
        return html.Div(
            dcc.Dropdown(
                id='data-cols-update',
                options=[
                    {'label': '', 'value': 'nodata'}
                ],
                placeholder='Upload dataset',
                style={
                    'fontFamily': "avenir",
                    'fontSize': '16px'
                }
            )
        )
    else:
        # Remove any date or time value permutations from the columns for cleaning. Of course, this list
        # will not catch all possibilities.
        rem_list = ['date', 'time', 'timestamp', 'datetime']
        data_cols_nodate = [col for col in data_cols if col['label'].lower() not in rem_list]
        return html.Div(
            dcc.Dropdown(
                id='data-cols-update',
                options=data_cols_nodate,
                placeholder='Columns to clean (5 max)',
                style={
                    'fontFamily': "avenir",
                    'fontSize': '16px'
                },
                multi=True
            )
        )


@app.callback(Output('date-cols-dropdown', 'children'),
              [Input('data-cols', 'data'),
               Input('uploaded-data', 'filename')])
def update_date_cols_dropdown(date_cols, name):
    """
    Callback function to update the  data columns available for cleaning

    :param
    date_cols: df columns for date/time
    name: flag for data upload being successful

    :return: dropdown menu options
    """
    if not name:
        return html.Div(
            dcc.Dropdown(
                id='date-cols-update',
                options=[
                    {'label': '', 'value': 'nodata'}
                ],
                placeholder='Upload dataset',
                style={
                    'fontFamily': "avenir",
                    'fontSize': '16px'
                }
            )
        )
    else:
        # Only keep date or time value permutations from the columns. Of course, this list
        # will not catch all possibilities.
        keep_list = ['date', 'time', 'timestamp', 'datetime']
        date_cols = [col for col in date_cols if col['label'].lower() in keep_list]
        return html.Div(
            dcc.Dropdown(
                id='data-cols-update',
                options=date_cols,
                placeholder='Select date & time columns',
                style={
                    'fontFamily': "avenir",
                    'fontSize': '16px'
                },
                multi=True
            )
        )


@app.callback([Output('final-binlabel-df', 'children'),
               Output('missing-sml', 'children'),
               Output('missing-lrg', 'children'),
               Output('clean-stats', 'children'),
               Output('error-report', 'children'),
               Output('error-plot', 'children')],
              [Input('data-cols-dropdown', 'children'),
               Input('date-cols-dropdown', 'children'),
               Input('start-clean', 'n_clicks'),
               Input('uploaded-data', 'contents'),
               Input('uploaded-data', 'filename')])
def errors_solutions(data_cols, date_cols, start, contents, name):
    """
    Callback function to perform the error detection and visualizations, and data filling (solutions). As commenting
    has been summarized, please see the documentation in the "dash_dataCleaning.py" script for further information
    on what is being done below.

    :param
    data_cols: df columns
    date_cols: df columns for date/time
    start: flag for 'Clean data' button being clicked
    filename: filename of data to load
    iscompleted: flag for if data has been uploaded successfully to the dashboard
    usr_id: folder name where the data is stored

    :return
    updated_binlabel_df: JSON dataframe with the 'Errors' and 'Solutions column completed
    out_nan_blocks: dict of missing and outlier values
    fill_blocks: dict of filled data points
    interp_blocks: dict of filled data points with interpolation methods used
    error-report: hmtl Div of the errors
    error-plot: bar plot for the errors
    """
    # Begin processing once user has clicked clean data and it has been uploaded
    if start > 0 and name:

        # Perform error detection and solution application (if errors exist) on the dataset
        updated_binlabel_df, out_blocks, out_nan_blocks, fill_blocks, interp_blocks, error_report, error_plot = \
            error_solutions_processing(data_cols, date_cols, contents)

        # Create the data tables for reporting the various solutions that have been applied to the data
        df_cols = ['Parameter', 'Start Time', 'End Time', 'Gap Size', 'Solutions Method']
        missing_sml_df = pd.DataFrame(columns=df_cols)
        missing_lrg_df = pd.DataFrame(columns=df_cols)

        # Only produce the tables if missing data existed
        # NB: This currently does not include functionality for formatting errors
        if out_nan_blocks:

            # For each for the fill/interp errors, determine the size of the data gap and then add the corresponding
            # data into the relevant dataframe
            for col in fill_blocks.keys():
                data_gaps = fill_blocks[col][0]
                data_fill = fill_blocks[col][1]

                for gap, fill in zip(data_gaps, data_fill):
                    # Deal with larger gaps. Gaps below 3 values will be appended separately
                    if isinstance(gap, list):
                        gap_sze = gap[1] - gap[0] + 1
                        sols_data = pd.Series([col, updated_binlabel_df.index[gap[0]],
                                               updated_binlabel_df.index[gap[1]], gap_sze, fill], index=df_cols)
                        if gap_sze < 3:
                            missing_sml_df = missing_sml_df.append(sols_data, ignore_index=True)
                        else:
                            missing_lrg_df = missing_lrg_df.append(sols_data, ignore_index=True)
                    else:
                        # Deal with 'single' data points
                        sols_data = pd.Series([col, updated_binlabel_df.index[gap], updated_binlabel_df.index[gap],
                                               1, fill], index=df_cols)
                        missing_sml_df = missing_sml_df.append(sols_data, ignore_index=True)

            # Do the same for the interpolation blocks of data, appending to the same dataframes.
            for col in interp_blocks.keys():
                data_gaps = interp_blocks[col][0]
                data_fill = interp_blocks[col][1]

                for gap, fill in zip(data_gaps, data_fill):
                    # Deal with larger gaps. Gaps below 3 values will be appended separately
                    if isinstance(gap, list):
                        gap_sze = gap[1] - gap[0] + 1
                        sols_data = pd.Series([col, updated_binlabel_df.index[gap[0]],
                                               updated_binlabel_df.index[gap[1]], gap_sze, fill], index=df_cols)
                        if gap_sze < 3:
                            missing_sml_df = missing_sml_df.append(sols_data, ignore_index=True)
                        else:
                            missing_lrg_df = missing_lrg_df.append(sols_data, ignore_index=True)

                    else:
                        # Deal with 'single' data points
                        sols_data = pd.Series([col, updated_binlabel_df.index[gap], updated_binlabel_df.index[gap],
                                               1, fill], index=df_cols)
                        missing_sml_df = missing_sml_df.append(sols_data, ignore_index=True)

            # Calculate the stats of missing values for the summary table in the clean-report callback
            # The percentage of missing data points is based on the user selected columns only and not other parameters
            tot_cols = len(data_cols)
            tot_data_pts = len(updated_binlabel_df) * tot_cols
            tot_missing_sml = len(missing_sml_df)
            tot_missing_lrg = len(missing_lrg_df)
            tot_missing = missing_sml_df['Gap Size'].sum() + missing_lrg_df['Gap Size'].sum()
            per_data_pts = round((tot_missing / tot_data_pts) * 100, 1)

            # Count the cleaned data pts and find the total percent cleaned
            tot_clean = missing_sml_df['Gap Size'][missing_sml_df['Solutions Method'] != 'unfilled'].sum() \
                        + missing_lrg_df['Gap Size'][missing_lrg_df['Solutions Method'] != 'unfilled'].sum()
            per_clean = round((tot_clean / tot_missing) * 100, 1)
            clean_stats = pd.DataFrame([[tot_cols, tot_data_pts, tot_missing_sml, tot_missing_lrg, tot_missing,
                                         per_data_pts, per_clean]],
                                       columns=['tot_cols', 'tot_data_pts', 'tot_missing_sml', 'tot_missing_lrg',
                                                'tot_missing', 'per_data_pts', 'per_clean'])
            clean_stats = clean_stats.to_json(orient='records')

            # Produce the summary table for the small missing gaps in data
            missing_sml = html.Div([
                dash_table.DataTable(data=missing_sml_df.to_dict("rows"),
                                     columns=[{"id": x, "name": x} for x in missing_sml_df.columns],
                                     style_cell={'textAlign': 'left',
                                                 'minWidth': '180px', 'width': '180px', 'maxWidth': '180px',
                                                 'overflow': 'hidden',
                                                 'textOverflow': 'ellipsis',
                                                 'fontFamily': 'Avenir',
                                                 'fontSize': '16px'
                                                 },
                                     tooltip_data=[
                                         {
                                             column: {'value': str(value), 'type': 'markdown'}
                                             for column, value in row.items()
                                         } for row in missing_sml_df.to_dict('records')
                                     ],
                                     tooltip_duration=None,
                                     style_header={
                                         'backgroundColor': 'white',
                                         'fontWeight': 'bold',
                                         'fontFamily': 'Avenir',
                                         'fontSize': '16px',
                                         'border': 'none'
                                     },
                                     style_data_conditional=[
                                         {
                                             'if': {'row_index': 'odd'},
                                             'backgroundColor': '#FBF2E6'
                                         }
                                     ],
                                     style_as_list_view=True,
                                     style_table={'overflowX': 'auto'},
                                     persistence=True
                                     ),
            ])

            # Produce the summary table for the large missing gaps in data
            missing_lrg = html.Div([
                dash_table.DataTable(data=missing_lrg_df.to_dict("rows"),
                                     columns=[{"id": x, "name": x} for x in missing_lrg_df.columns],
                                     style_cell={'textAlign': 'left',
                                                 'minWidth': '180px', 'width': '180px', 'maxWidth': '180px',
                                                 'overflow': 'hidden',
                                                 'textOverflow': 'ellipsis',
                                                 'fontFamily': 'Avenir',
                                                 'fontSize': '16px'
                                                 },
                                     tooltip_data=[
                                         {
                                             column: {'value': str(value), 'type': 'markdown'}
                                             for column, value in row.items()
                                         } for row in missing_lrg_df.to_dict('records')
                                     ],
                                     tooltip_duration=None,
                                     style_header={
                                         'backgroundColor': 'white',
                                         'fontWeight': 'bold',
                                         'fontFamily': 'Avenir',
                                         'fontSize': '16px',
                                         'border': 'none'
                                     },
                                     style_data_conditional=[
                                         {
                                             'if': {'row_index': 'odd'},
                                             'backgroundColor': '#FBF2E6'
                                         }
                                     ],
                                     style_as_list_view=True,
                                     style_table={'overflowX': 'auto'},
                                     persistence=True
                                     ),
            ])

            # TODO: Possibly add functionality for an outlier table. Need to factor in for most
            #  errors not having outliers

            # Need to reset the index to be a column because the JSON conversion does not
            # preserve the index through orient
            updated_binlabel_df.reset_index(inplace=True)

            # Need to convert the Date/Time column into a string before converting into JSON as JSON does not
            # preserve the datetime format
            updated_binlabel_df = updated_binlabel_df.to_json(orient='records', date_format='iso')

            return updated_binlabel_df, missing_sml, missing_lrg, clean_stats, error_report, error_plot

        else:
            raise PreventUpdate

    else:
        raise PreventUpdate


@app.callback(Output('clean-report', 'children'),
              [Input('clean-stats', 'children'),
               Input('start-clean', 'n_clicks')])
def clean_report(clean_stats, start):
    """
    Callback function to produce a summary report of the cleaning that was performed. This callback function will also
    allow users to download the cleaned data (only cleaned data or with raw data included) if errors were detected.

    :param clean_stats: df with the summary stats of the missing data
    :param start: determine if the user clicked clean data

    :return: Div component with the summart report.
    """

    if start > 0:
        # Load in the stats data
        clean_stats = pd.read_json(clean_stats, orient='records')

        # Produce the display of the missing data summary stats as calculated above
        clean_summary = html.Div(
            [
                html.Div(
                    [
                        html.Div(
                            [
                                html.P(
                                    "{}".format(clean_stats["tot_missing"].iloc[0]),
                                    style={"color": "#ea8f32",
                                           "font-family": "Avenir",
                                           "font-size": "80px",
                                           "padding-left": "30px",
                                           "border-bottom": "3px solid #ea8f32"
                                           },
                                    className="four columns",
                                ),
                                html.P(
                                    "Error scanning found a total of {} missing "
                                    "data points and this also includes any data "
                                    "points that were identified as outliers. "
                                    "Out of this missing data, {} areas of your "
                                    "dataset were classified as small gaps in "
                                    "the data whereas {} areas are conseridered "
                                    "to be large gaps where 3 or more data points "
                                    "were missing or affected by outliers."
                                        .format(clean_stats["tot_missing"].iloc[0],
                                                clean_stats["tot_missing_sml"].iloc[0],
                                                clean_stats["tot_missing_lrg"].iloc[0]),
                                    style={
                                        'padding-top': '50px',
                                        'padding-left': '80px',
                                        "font-family": "Avenir",
                                        "font-size": "12px",
                                    },
                                    className="eight columns",
                                ),
                            ],
                            className="row"
                        ),
                        html.Div(
                            [
                                html.P(
                                    "The total number of errors found in "
                                    "your dataset, including outliers",
                                    style={
                                        "font-family": "Avenir",
                                        "font-size": "12px",
                                        "padding-left": "20px",
                                        "padding-top": "20px",
                                        "padding-bottom": "20px",
                                        "background": "#ea8f32",
                                        "color": "#ffffff"
                                    },
                                    className="four columns",
                                ),
                                html.P(
                                    "",
                                    className="eight columns",
                                ),
                            ],
                            className="row"
                        ),
                    ],
                    style={
                        'margin-bottom': '50px'
                    },
                    className="row"
                ),
                html.Div(
                    [
                        html.Div(
                            [
                                html.P(
                                    "{}%".format(clean_stats["per_data_pts"].iloc[0]),
                                    style={"color": "#ea8f32",
                                           "font-family": "Avenir",
                                           "font-size": "80px",
                                           "padding-left": "20px",
                                           "border-bottom": "3px solid #ea8f32"
                                           },
                                    className="four columns",
                                ),
                                html.P(
                                    "This is the percentage of the total data "
                                    "points in the columns that you chose to "
                                    "clean that have been indentified as "
                                    "missing or outlier data. This percentage "
                                    "is not for the entire dataset. There are a "
                                    "total of {} raw data points in the {} "
                                    "columns that you chose to clean."
                                        .format(clean_stats["tot_data_pts"].iloc[0],
                                                clean_stats["tot_cols"].iloc[0]),
                                    style={
                                        'padding-top': '50px',
                                        'padding-left': '80px',
                                        "font-family": "Avenir",
                                        "font-size": "12px",
                                    },
                                    className="eight columns",
                                ),
                            ],
                            className="row"
                        ),
                        html.Div(
                            [
                                html.P(
                                    "The % of your dataset that contains "
                                    "erroneous values based on the parameters scanned",
                                    style={
                                        "font-family": "Avenir",
                                        "font-size": "12px",
                                        "padding-top": "20px",
                                        "padding-left": "20px",
                                        "padding-right": "20px",
                                        "padding-bottom": "20px",
                                        "background": "#ea8f32",
                                        "color": "#ffffff"
                                    },
                                    className="four columns",
                                ),
                                html.P(
                                    "",
                                    className="eight columns",
                                ),
                            ],
                            className="row"
                        ),
                    ],
                    style={
                        'margin-bottom': '50px'
                    },
                    className="row",
                ),
                html.Div(
                    [
                        html.Div(
                            [
                                html.P(
                                    "{}%".format(clean_stats["per_clean"].iloc[0]),
                                    style={"color": "#ea8f32",
                                           "font-family": "Avenir",
                                           "font-size": "80px",
                                           "padding-left": "10px",
                                           "border-bottom": "3px solid #ea8f32"
                                           },
                                    className="four columns",
                                ),
                                html.P(
                                    "Not all data values can be cleaned. "
                                    "As stated in the introduction of this page, "
                                    "if your dataset contains low-resolution data "
                                    "over a short time period, gaps at the "
                                    "'edges' of the dataset can not be filled "
                                    "with more complex methods such as hour and "
                                    "day filling techniques.",
                                    style={
                                        'padding-top': '50px',
                                        'padding-left': '80px',
                                        "font-family": "Avenir",
                                        "font-size": "12px",
                                    },
                                    className="eight columns",
                                ),
                            ],
                            className="row"
                        ),
                        html.Div(
                            [
                                html.P(
                                    "The % of your erroneous data that we were "
                                    "able to clean",
                                    style={
                                        "font-family": "Avenir",
                                        "font-size": "12px",
                                        "padding-left": "20px",
                                        "padding-top": "20px",
                                        "padding-bottom": "20px",
                                        "padding-right": "20px",
                                        "background": "#ea8f32",
                                        "color": "#ffffff"
                                    },
                                    className="four columns",
                                ),
                                html.P(
                                    "",
                                    className="eight columns",
                                ),
                            ],
                            className="row"
                        )
                    ],
                    style={
                        'margin-bottom': '50px'
                    },
                    className="row",
                ),
            ],
            className="row",
        ),
        return clean_summary
    else:
        raise PreventUpdate


@app.callback(Output('download-clean-data', 'data'),
              [Input('final-binlabel-df', 'children'),
               Input('btn_csv', 'n_clicks'),
               Input('raw-clean-opt', 'value'),
               Input('data-cols-dropdown', 'children'),
               Input('uploaded-data', 'filename')])
def clean_data_dwn(final_df, n_clicks, raw_clean_opt, data_cols, fname):
    if n_clicks > 0:
        # Format filename
        dwn_fname = fname.split('.')[0] + "_cleaned." + fname.split('.')[-1]

        # Need to convert the binary labels in string to avoid errors in formatting in JSON and export.
        # If this is not done "00000", for instance, will become "0" in the exported file
        dtype_dic = {'Errors': str, 'Solutions': str}
        final_df = pd.read_json(final_df, orient='records', dtype=dtype_dic)
        #final_df[["Errors", "Solutions"]] = final_df[["Errors", "Solutions"]].astype(str)

        # Determine if the user wants both clean and raw data
        if raw_clean_opt == 'clean data':
            clean_cols = data_cols['props']['children']['props']['value']
            final_df.drop(clean_cols, inplace=True, axis=1)

        return dcc.send_data_frame(final_df.to_csv, dwn_fname, index=False)
    else:
        raise PreventUpdate


@app.callback(Output('download-msg', 'children'),
              Input('start-clean', 'n_clicks'))
def dwn_msg(stat_clean):
    if stat_clean > 0:
        return html.Div(
            [
                html.P(
                    [
                        "You are now able to download your cleaned data using the options below. "
                        "You can either choose between downloading the cleaned data only (raw data for the "
                        "columns you selected will be removed), or to have a file containing both "
                        "the raw and cleaned data."
                    ],
                    className="paratext"
                )
            ],
            className="row",
            style={
                'margin-bottom': '30px',
            },
        )
    else:
        return html.Div(
            [
                html.P(
                    [
                        'You will only be able to download data once you have clicked "Clean Data" on '
                        'the Errors Report page. Do not click any of the button below until the '
                        'cleaning process has finished.'
                    ],
                    className="paratext"
                )
            ],
            className="row",
            style={
                'margin-bottom': '30px',
            },
        )


@app.callback(Output('debug-submission', 'children'),
              [Input('input-name', 'value'),
               Input('input-email', 'value'),
               Input('input-issue-page', 'value'),
               Input('input-issue-descrip', 'value'),
               Input('input-rating', 'value'),
               Input('submit-debug', 'n_clicks')])
def debug_submission(name, email, issue_page, issue_descrip, rating, debug):
    if debug > 0:
        if name and email and issue_page and issue_descrip and rating:

            receiver = ['masao.ashtine@oerc.ox.ac.uk']

            body = "Dear Admin,\n\nA user, {}, has requested support with the Data Cleaning Tool based on the \
            following information submitted on the 'Debugging' page:\n\n\
            User Email: {}\n\
            Page with reported issue: {}\n\
            Description of issue: {}\n\
            Overall form ease-of-use: {}\n\nPlease investigate the issue and update the user as soon as possible \
            via their submitted email above. Please note that the rating value is out of a maximum of 10 points, \
            with '10' representing a submission of 'Useful' which should be read as the user viewing the tool as being \
            easy to use.\n\nBest wishes,\n\nMasao Ashtine,\nLEO Data Coordinator" \
                .format(name, email, issue_page, issue_descrip, rating)

            subject = "Data Cleaning Tool - Debug Submission from {}".format(name)

            # Needed for YAGMAIL service keychain credentials. NOT Secure but this email is simply for debugging
            # Need to determine how to access creds on the server to prevent hardcoding pwd
            yag_service = yagmail.SMTP("projectleodebug@gmail.com", "ProjecTLEODebuG2021")

            # Send emails to the app developers based on the user input
            yag_service.send(to=receiver, subject=subject, contents=body)

            print("Test Done")

            return html.Div(
                [
                    "A confirmation email has been sent to the App Developers. They will contact you shortly!",
                ],
                style={
                    "font-style": "italic",
                    "font-family": "avenir"
                }
            )
        else:
            return html.Div(
                [
                    html.P(
                        "Please complete all fields including the slider!",
                        style={
                            "font-style": "italic",
                            "font-family": "avenir"
                        }
                    )
                ]
            )
    else:
        raise PreventUpdate


if __name__ == "__main__":
    app.run_server(debug=True)
