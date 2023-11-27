# -*- coding: utf-8 -*-
import base64
import csv
import io
import os

import dash
import dash_bootstrap_components as dbc
import dash_daq as daq
import dash_uploader as du
import pandas as pd
import plotly.graph_objs as go
import yagmail
from dash import dcc
from dash import html
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

from scripts.dash_timeseriesClean import load_df, Formatting, Errors, Solutions

app = dash.Dash(__name__, meta_tags=[{"name": "viewport", "content": "width=device-width"}],
                suppress_callback_exceptions=True)
server = app.server

UPLOAD_FOLDER_ROOT = r"/Users/mashtine/PycharmProjects/ProjectLEO_Data/" \
                     r"LEODashTools/Cleaning/data-cleaning/data/tmp"
du.configure_upload(app, UPLOAD_FOLDER_ROOT, use_upload_id=True)


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


def parse_contents(contents):
    # This function will only run once the right file type has been uploaded
    # Split the binary string by decoding type and the encoded string
    content_type, content_string = contents.split(',')

    # Decode the data
    decoded = base64.b64decode(content_string)

    # Assumes that the user uploaded a CSV or TXT file
    df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))

    return df


def get_menu():
    menu = html.Div(
        [
            dcc.Link(
                "Data Scan",
                href="/data-health-scan-test/data-scan",
                className="tab first",
            ),
            dcc.Link(
                "Supporting Documentation",
                href="/data-health-scan-test/supporting-documentation",
                className="tab",
            ),
            dcc.Link(
                "Debugging",
                href="/data-health-scan-test/debugging",
                className="tab",
            ),
        ],
        className="row all-tabs",
    )
    return menu


def error_solutions_processing(data_cols, date_cols, filename, usr_id):
    """
    This function contains the sequence used to detect errors and clean the data based on various 'solutions'.

    :param data_cols: User selected data columns for data to clean
    :param date_cols: User selected date columns
    :param start: Flag for button selection to begin cleaning process
    :param filename: Name of the uploaded file
    :param usr_id: Unique usr session ID

    :return:
    """
    # Initialize the Formatting and Errors classes
    fmt = Formatting()
    data_errors = Errors()

    # Reupload the data. This needs to be done because the serialisation of data into JSON affects how pandas
    # reads in the datetime columns. This is not efficient and should be improved
    os.chdir(os.path.join(UPLOAD_FOLDER_ROOT, usr_id))

    if filename[0].split('.')[-1] == 'txt':
        with open(filename[0], 'r') as csvfile:
            dialect = csv.Sniffer().sniff(csvfile.read(1024))
        full_df = pd.read_csv(filename[0], index_col=False, delimiter=dialect.delimiter)
    else:
        full_df = pd.read_csv(filename[0], index_col=False)

    # Establish the cols to clean and the date/time cols
    cols_toclean = data_cols['props']['children']['props']['value']
    date_cols = date_cols['props']['children']['props']['value']

    # Import the data from JSON and put into pd df. This section will add the "Errors" and "Solutions" columns
    # into the df as well as columns where the cleaned data will be entered. The label ord is important for
    # later cleaning stages.
    df = load_df(full_df, date_cols)
    label_ord, binlabel_df = fmt.bin_labels(df, cols_toclean)
    # binlabel_df = binlabel_df.to_json(orient='records')

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
            'padding-top': '15px'
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


dataScan = dbc.Card(
    dbc.CardBody(
        [
            html.Div(
                [
                    Header(app),
                    # page 1
                    html.Div(
                        [
                            # Preamble
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
                            # Further Information
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
                            # Numbers Header
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
                                        className="eight columns",
                                        style={
                                            "textAlign": "center",
                                            "padding-left": "40px"
                                        }
                                    ),
                                ]
                            ),
                            # Upload and configurations
                            html.Div(
                                [
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
                                                            'height': '40px',
                                                            'border': 'none',
                                                            'lineHeight': '10px',
                                                            'text-align': 'center',
                                                            'margin-top': '0px',
                                                            'background': "#ea8f32",
                                                            'color': 'white',
                                                            'outlineColor': '#ea8f32',
                                                            'font-family': 'Avenir',
                                                            'font-size': '10px',
                                                            'font-weight': '150',
                                                            'border-radius': '10px',
                                                        },
                                                    ),
                                                ],
                                                className="row"
                                            ),
                                            html.Div(
                                                [
                                                    html.Div(id='upload-status')
                                                ],
                                                className="row"
                                            ),
                                            html.Div(id='data-cols', style={'display': 'none'}),
                                            html.Div(id='load-dataset', style={'display': 'none'}),
                                            html.Div(id='error-totals', style={"display": "none"})
                                        ],
                                        className="four columns",
                                        style={
                                            "textAlign": "center",
                                            "padding-left": "30px"
                                        }
                                    ),
                                    # TODO: Need to integrate this functionalty into the tool for error checking.
                                    #  Currently is not used.
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
                                                    'justify-content': 'center',
                                                    'margin-top': '3px'
                                                }
                                            ),
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
                                                id="config-scan2",
                                                options=[
                                                    {'label': 'Yes, Data other than headers are numeric',
                                                     'value': 'yes'},
                                                    {'label': 'No, Data other than headers can be nonnumeric',
                                                     'value': 'no'}
                                                ],
                                                placeholder="Only Numeric Data",
                                                style={
                                                    'width': '200px',
                                                    'font-family': 'avenir',
                                                    'font-size': '11px',
                                                    'align-items': 'center',
                                                    'justify-content': 'center',
                                                    'margin-top': '3px'
                                                }
                                            ),
                                        ],
                                        className="four columns",
                                        style={
                                            "textAlign": "center",
                                            "padding-left": "20px"
                                        }
                                    ),
                                ],
                                className="row",
                                style={
                                    "margin-top": "50px",
                                    "margin-bottom": "50px"
                                }
                            ),
                            # Numbers Header
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
                                            'padding-right': '15px'
                                        },
                                    ),
                                ],
                                className="row",
                                style={
                                    "textAlign": "center",
                                }
                            ),
                            # Input dropdowns for data
                            html.Div(
                                [
                                    html.Div(
                                        [
                                            html.Div(id='date-cols-dropdown')
                                        ],
                                        className="six columns",
                                        style={
                                            "textAlign": "center",
                                        }
                                    ),
                                    html.Div(
                                        [
                                            html.Div(id='data-cols-dropdown')
                                        ],
                                        className="six columns",
                                        style={
                                            "textAlign": "center",
                                        }
                                    ),
                                ],
                                className="row",
                                style={
                                    "textAlign": "center",
                                    "margin-bottom": "50px"
                                }
                            ),
                            # Numbers Header
                            html.Div(
                                [
                                    html.Img(
                                        src=app.get_asset_url("four.png"),
                                        style=
                                        {
                                            'height': '30px',
                                            'width': 'auto',
                                            'margin': '0px 0px',
                                            'padding-bottom': '10px',
                                            'padding-right': '15px'
                                        },
                                    ),
                                ],
                                className="row",
                                style={
                                    "textAlign": "center",
                                }
                            ),
                            # Scan Button
                            html.Div(
                                [
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
                                        className="eight columns",
                                        style={
                                            "textAlign": "center",
                                            "padding-left": "240px",
                                            "padding-right": "0px"
                                        }
                                    )
                                ],
                                className="row ",
                            ),
                            # Scan Status
                            html.Div(
                                [
                                    html.Div(id='scan-status')
                                ],
                                className="row",
                                style={
                                    'padding-bottom': '30px',
                                    'text-align': 'center'
                                }
                            ),
                            # Stats info
                            html.Div(
                                [
                                    html.P(
                                        [
                                            "As missing values can represent a small percentage of your full dataset, "
                                            "the values below have been normalised by the total missing data "
                                            "points. Thus, a readout of 50% should be read as half of all missing "
                                            "values fall within the category shown by the gauges below. "
                                            "See explanation below for more details."
                                        ],
                                        className="paratext",
                                        style={
                                            'text-align': 'center',
                                            'padding-bottom': '30px'
                                        }
                                    )
                                ],
                                className="row"
                            ),
                            # Data Gauges
                            html.Div(
                                [
                                    html.Div(id='miss-gauges')
                                ],
                                style={
                                    'margin-bottom': '0px'
                                },
                                className="row"
                            ),
                            # Stats Report
                            html.Div(
                                [
                                    html.Div(id='stats-report')
                                ],
                                style={
                                    'margin-bottom': '50px',
                                    "textAlign": "center",
                                },
                                className="row"
                            ),
                            # Final row
                            html.Div(
                                [
                                    html.Div(
                                        [
                                            html.H6(
                                                "Developers",
                                                className="paratext",
                                                style={
                                                    'color': '#ea8f32'
                                                }
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
                                        className="row",
                                        style={
                                            "textAlign": "center",
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
    ),
    className="mt-3",
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
                                                    sizes, formats, and types, we expect the Data Health Scan Tool to 'break' \
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
                                                    {'label': 'Data Scan', 'value': 'Data Scan'},
                                                    {'label': 'Supporting Documentation',
                                                     'value': 'Supporting Documentation'}
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
        ]
    ),
    className="mt-3",
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
                                                ), href='https://project-leo.co.uk/reports/data-cleaning-and-'
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
                                                ), href='https://project-leo.co.uk/reports/'
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
                                                ), href='https://project-leo.co.uk/reports/'
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
                                                ), href='https://www.bitbucket.org/projectleodata/'
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
    ),
    className="mt-3",
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
                dcc.Tab(label="Data Scan", style=tab_style,
                        selected_style=tab_selected_style, children=[dataScan]),
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


@app.callback(Output('data-cols-dropdown', 'children'),
              [Input('data-cols', 'data'),
               Input('uploaded-data', 'filename')])
def update_cols_dropdown(data_cols, name):
    """
    Callback function to update the  data columns available for cleaning

    :param
    data_cols: df columns
    iscompleted: flag for data upload being successful

    :return: dropdown menu options
    """
    if not name:
        return html.Div(
            dcc.Dropdown(
                id='data-cols-update',
                options=[
                    {'label': '', 'value': 'nodata'}
                ],
                placeholder='Upload dataset first',
                style={'fontFamily': "avenir"}
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
                style={'fontFamily': "avenir"},
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
    iscompleted: flag for data upload being successful

    :return: dropdown menu options
    """
    if not name:
        return html.Div(
            dcc.Dropdown(
                id='date-cols-update',
                options=[
                    {'label': '', 'value': 'nodata'}
                ],
                placeholder='Upload dataset first',
                style={'fontFamily': "avenir"}
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
                style={'fontFamily': "avenir"},
                multi=True
            )
        )


@app.callback(Output('scan-status', 'children'),
              Input('scan-data', 'n_clicks'))
def scan_status(n_clicks):

    if n_clicks > 0:
        return html.Div(
                    [
                        "Please wait while your data is being scanned. Results will appear below",
                    ],
                    className="status_msg",
                    style={
                        "margin-top": "0px",
                        "padding-left": "10px",
                        "padding-right": "10px"
                    }
                )
    else:
        raise PreventUpdate


@app.callback([Output('error-totals', 'children'),
               Output('miss-gauges', 'children'),
               Output('stats-report', 'children')],
              [Input('data-cols-dropdown', 'children'),
               Input('date-cols-dropdown', 'children'),
               Input('scan-data', 'n_clicks'),
               Input('uploaded-data', 'contents'),
               Input('uploaded-data', 'filename')])
def error_detection(data_cols, date_cols, scan, contents, name):
    """
    Callback function to update the  data columns available for cleaning

    :param
    data_cols: df columns
    date_cols: df columns for date/time
    scan: flag for 'Clean data' button being clicked
    filename: filename of data to load
    iscompleted: flag for if data has been uploaded successfully to the dashboard
    usr_id: folder name where the data is stored

    :return
    error-totals: dict of missing and outlier values
    miss-gauges: html of the stat gauges from the error scan

    """
    # Begin processing once user has clicked clean data and it has been uploaded
    if scan > 0 and name:

        # Initialize the formatting class
        fmt = Formatting()
        data_errors = Errors()

        # Reload the data. This needs to be done because the serialisation of data into JSON affects how pandas
        # reads in the datetime columns. This is not efficient and should be improved
        full_df = parse_contents(contents)

        # Establish the cols to clean and the date/time cols
        cols_toclean = data_cols['props']['children']['props']['value']
        date_cols = date_cols['props']['children']['props']['value']

        # Import the data from JSON and put into pd df. This section will add the "Errors" and "Solutions" columns
        # into the df as well as columns where the cleaned data will be entered. The label ord is important for
        # later cleaning stages.
        df = load_df(full_df, date_cols)
        label_ord, binlabel_df = fmt.bin_labels(df, cols_toclean)

        # Now that the df has been formatted, the following section will use the `error_detect` function to scan
        # for errors as per the cleaning documentation, and comments found within the subfunctions.
        updated_binlabel_df, nan_blocks, out_blocks, fmt_blocks, totals = data_errors.\
            err_detect(binlabel_df, cols_toclean)

        # Determine the stats for each column (not the most efficient as it is done in the `error_detect` subfunctions)
        # Only report for missing data and outliers
        #TODO: Remove totals from the error_detect subfunctions
        error_totals = {}
        tot_data_pts = len(updated_binlabel_df)*len(cols_toclean)

        # Unlike with the data cleaning scripts, this will report the total size of all data gaps and not the total
        # number of data gaps of various categories (single, large etc.)
        full_miss_tot, full_out_tot = 0, 0

        for i, key in enumerate(nan_blocks.keys()):
            # miss_tot does not include outlier values.
            #TODO: Include a count for missing time gaps
            miss_tot, out_tot = 0, 0
            size_idx = nan_blocks[key][1]

            #TODO: will need to have something similar for all in case there is no missing data
            if out_blocks:
                if key in out_blocks.keys():
                    out_tot = sum(out_blocks[key][1])
                    full_out_tot += sum(out_blocks[key][1])

            for s, sze in enumerate(size_idx):
                # Single/Two Missing/Nan values
                miss_tot += sze
                full_miss_tot += sze

        error_totals['miss_stats'] = [full_miss_tot, full_out_tot,
                                      round((full_miss_tot/(full_miss_tot + full_out_tot))*100, 2),
                                      round((full_out_tot/(full_miss_tot + full_out_tot))*100, 2)]

        # Produce the updated gauges for reporting the stats
        miss_gauges = html.Div(
            [
                html.Div(
                    id="gauge1",
                    children=[
                        html.P("Missing Data"),
                        daq.Gauge(
                            id="missing-gauge",
                            max=100,
                            min=0,
                            value=error_totals['miss_stats'][2],
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
                            value=error_totals['miss_stats'][3],
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
                            value=0,
                            units='%',
                            showCurrentValue=True,  # default size 200 pixel
                            color='#EA8F32',
                        ),
                    ],
                    className="four columns"
                )
            ]
        )

        # Produce a stats report depending on if errors were found
        if nan_blocks:
            stats_report = html.Div(
                [
                    html.P(
                        [
                            "These values represent the percentage of errors from the total errors detected. "
                            "As missing data tend to be a smaller percentage of the full dataset, statistics are "
                            "reported in this manner for greater insight. Your dataset had a total of ",
                            html.B("{} missing values".format(error_totals['miss_stats'][0] +
                                                              error_totals['miss_stats'][1])),
                            ", of which, ",
                            html.B("{} of them were outliers ".format(error_totals['miss_stats'][1])),
                            "and there were 0 data points ",
                            "where times were not accounted for. Please note that these values are only for the ",
                            html.B("{} column(s) ".format(len(cols_toclean))),
                            "that you have chosen to scan. You should consider using the ",
                            html.P(
                                [
                                    "LEO Data Cleaning Tool "
                                ],
                                style={
                                    "color": "#EA8F32"
                                },
                                className="paratext"
                            ),
                            "to address these issues and download a cleaned dataset."
                        ],
                        className="paratext"
                    )
                ]
            )
        else:
            stats_report = html.Div(
                [
                    html.P(
                        [
                            "These values represent the percentage of errors from the total errors detected. "
                            "As missing data tend to be a smaller percentage of the full dataset, statistics are "
                            "reported in this manner for greater insight. There were no known errors found in "
                            "your dataset! However, this tool is automated and may miss certain errors and the "
                            "output should not be seen as a definite result where data errors are concerned."
                        ],
                        className="paratext"
                    )
                ]
            )

        # Place information into JSON
        error_totals = pd.DataFrame(error_totals, index=['miss_tot', 'out_tot', 'per_miss', 'per_out'])
        error_totals = error_totals.to_json(orient='records')

        return error_totals, miss_gauges, stats_report
    else:

        # Return gauges with 0 values
        error_totals = {'miss_stats': [0, 0, 0, 0]}
        miss_gauges = html.Div(
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
                            value=0,
                            units='%',
                            showCurrentValue=True,  # default size 200 pixel
                            color='#EA8F32',
                        ),
                    ],
                    className="four columns"
                )
            ]
        )

        # Place information into JSON
        error_totals = pd.DataFrame(error_totals, index=['miss_tot', 'out_tot', 'per_miss', 'per_out'])
        error_totals = error_totals.to_json(orient='records')

        # Produce a message to guide the user
        stats_report = html.Div(
            [
                html.P(
                    [
                        "Once your dataset has been scanned, values will be displayed through the gauges above."
                    ],
                    className="paratext"
                )
            ]
        )

        return error_totals, miss_gauges, stats_report


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

            receiver = ['masao.ashtine@oerc.ox.ac.uk', 'scot.wheeler@eng.ox.ac.uk']

            body = "Dear Admin,\n\nA user, {}, has requested support with the Data Cleaning Tool based on the \
            following information submitted on the 'Debugging' page:\n\n\
            User Email: {}\n\
            Page with reported issue: {}\n\
            Description of issue: {}\n\
            Overall form ease-of-use: {}\n\nPlease investigate the issue and update the user as soon as possible \
            via their submitted email above. Please note that the rating value is out of a maximum of 10 points, \
            with '10' representing a submission of 'Useful' which should be read as the user viewing the tool as being \
            easy to use.\n\nBest wishes,\n\nMasao Ashtine,\nLEO Data Coordinator"\
                .format(name, email, issue_page, issue_descrip, rating)

            subject = "Data Cleaning Tool - Debug Submission from {}".format(name)

            # TODO: Make more secure by going through the oauth2 process
            # Needed for YAGMAIL service keychain credentials. NOT Secure but this email is simply for debugging
            # Need to determine how to access creds on the server to prevent hardcoding pwd
            yag_service = yagmail.SMTP("projectleodebug@gmail.com", "ProjecTLEODebuG2021")

            # Send emails to the app developers based on the user input
            yag_service.send(to=receiver, subject=subject, contents=body)

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
