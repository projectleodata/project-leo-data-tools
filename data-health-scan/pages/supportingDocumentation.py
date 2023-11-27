import dash_html_components as html
from utils import Header


def create_layout(app):
    return html.Div(
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
                                        ), href='https://project-leo.co.uk/wp-content/uploads/2021/05/Project-LEO-'
                                                'Data-Cleaning-and-Processing-Mar-2021-1.pdf',
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
                                        ), href='https://project-leo.co.uk/wp-content/uploads/2021/01/Project-LEO-'
                                                'Data-Standards-and-Protocols.pdf',
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
                                        ), href='https://project-leo.co.uk/wp-content/uploads/2021/03/Project-LEO-'
                                                'Data-Collection-and-Access-Jan-2021-2.pdf',
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
                                                'margin-top': '0px',
                                                'padding-top': '0px'
                                            }
                                        ), href='https://project-leo.co.uk/wp-content/uploads/2021/03/Project-LEO-'
                                                'Data-Collection-and-Access-Jan-2021-2.pdf',
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
