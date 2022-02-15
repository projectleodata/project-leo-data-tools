# -*- coding: utf-8 -*-
import dash
import yagmail
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import html, dash_table, dcc
import dash_bootstrap_components as dbc
from plotly.subplots import make_subplots
from dash.exceptions import PreventUpdate
from dash.dependencies import Input, Output

app = dash.Dash(__name__, meta_tags=[{"name": "viewport", "content": "width=device-width"}],
                suppress_callback_exceptions=True)
server = app.server


# TODO: Finalise docstring for formulae
# TODO: Streamline function input for dash callback usage (disconnect in needs from SW python code)
# TODO: Correct for util/avail bid vs ceil
# TODO: Properly comment all code
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
                        [html.P("Bid Analysis Tool")],
                        className="seven columns main-title",
                    ),
                    html.Div(
                        [
                            html.A(
                                "Source Code (Restricted)",
                                href="https://github.com/projectleodata/project-leo-data-tools",
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


# TODO: Does not include 'Other Fixed' at the moment
def tot_marg_cost(asset_effic, asset_cap, energy_cost, duos_nonevent,
                  duos_event, lcos, person_rate, util_person_hrs):
    """
    Simple function to determine the total marginal cost

    :param asset_effic:
    :param asset_cap:
    :param energy_cost:
    :param duos_nonevent:
    :param duos_event:
    :param lcos:
    :param person_rate:
    :param util_person_hrs:

    :return: tot_SRMC

    """
    # TODO: Does not include hrs_per_util variable as this is assumed to be 1.0
    energy_SRMC = (1. / asset_effic) * energy_cost + (duos_nonevent - duos_event) + lcos
    hrly_util = person_rate * (util_person_hrs / 60)
    person_SRMC = hrly_util / asset_cap
    tot_SRMC = energy_SRMC + person_SRMC

    return tot_SRMC


def calc_avail_bid(tcv, exp_util_hrs, tot_avail_hrs, util_bid, avail_ceil, asset_cap):
    """
    Given a utilisation bid, calculate max availability bid and be equal to TCV
    Returns
    """
    remaining_tcv = tcv - util_bid
    weight = util_bid / tcv
    avail_max = ((remaining_tcv * exp_util_hrs * asset_cap)
                 / asset_cap
                 / tot_avail_hrs)
    avail = np.min([avail_ceil, avail_max])

    return avail, weight


def calc_util_bid(tcv, exp_util_hrs, tot_avail_hrs, avail_bid, util_ceil, asset_cap):
    """
    Given an availability bid, calculate max utilisation bid and be equal to TCV
    Returns
    """
    util_max = (((tcv * exp_util_hrs * asset_cap) - (avail_bid * tot_avail_hrs * asset_cap))
                / (exp_util_hrs * asset_cap))
    util = np.min([util_ceil, util_max])
    weight = util / tcv

    return util, weight


def maxout_tcv(tcv, exp_util_hrs, tot_avail_hrs, util_ceil, avail_ceil, asset_cap, bid_weight):
    """
    This calculates the availability and utilisation bids to max out the tcv
    for a given expected number of hours of delivery. This can be used to
    replicate Harry Orchards original analysis with bid_weight 0 for
    all availability and 1 for all utilisaton.
    """
    util_max = bid_weight * tcv
    avail_max = ((((1 - bid_weight) * tcv) * exp_util_hrs * asset_cap)
                 / asset_cap
                 / tot_avail_hrs)

    util = np.min([util_max, util_ceil])
    avail = np.min([avail_ceil, avail_max])

    return avail, util


def calc_costs(asset_cap, avail_bid, util_bid, person_rate, fixed_person_hrs, tot_SRMC, tot_avail_hrs):
    """
    Calculates the costs of participation, revenue and profit
    """
    # Create starting lists This is adapted from the original function to remove the isinstance and list checks and
    # this can be constrained at point of user input. List input avoided for simplification of tool in v1.0
    util_hours = np.arange(0, (tot_avail_hrs + 1), 1.0)
    avail_bids = [avail_bid] * len(util_hours)
    util_bids = [util_bid] * len(util_hours)

    # Creating data for the data table columns
    energy = util_hours * asset_cap
    tot_SRMC = [tot_SRMC] * len(util_hours)
    marginal_cost = tot_SRMC * energy
    fixed_cost = (fixed_person_hrs / 60) * person_rate
    fixed_cost = np.ones(util_hours.shape) * fixed_cost
    tot_cost = marginal_cost + fixed_cost
    revenue = (util_bids * energy) + (avail_bid * asset_cap * tot_avail_hrs)
    profit = revenue - tot_cost
    tcv = revenue / energy

    # Full data matrix and dataframe creation
    cost_matrix = np.array([util_hours, energy, avail_bids, util_bids, marginal_cost,
                            fixed_cost, tot_cost, revenue, profit, tcv])

    # TODO: Need to ensure column headers are consistently named throughout tables
    cost_df = pd.DataFrame(cost_matrix.T,
                           columns=["Utilisation Hours",
                                    "Energy (kWh)",
                                    "Availability Bid (£/kW/h)",
                                    "Utilisation Bid (£/kWh)",
                                    "Marginal Cost (£)",
                                    "Auction Fixed Cost (£)",
                                    "Total Service Cost (£)",
                                    "Revenue (£)",
                                    "Profit (£)",
                                    "TCV (£/kWh)"])

    return cost_matrix, cost_df


def profit_vs_expected_util(tcv, exp_util_hrs, tot_avail_hrs, util_ceil, avail_ceil, asset_cap, fixed_person_hrs,
                            person_rate, tot_SRMC):
    """
    Calculate 3D matrix of profit for expected utilisation vs actual
    utilisation for a particular set of bids and strategy weight.
    """

    exp_util_range = np.arange(0.0, tot_avail_hrs + 1, 1.0)
    weight_range = np.linspace(0.0, 1.0, 11)

    profits = np.zeros((len(exp_util_range), len(weight_range), len(exp_util_range)))
    revenues = np.zeros((len(exp_util_range), len(weight_range), len(exp_util_range)))
    for i, exp_util in enumerate(exp_util_range):
        for j, weight in enumerate(weight_range):
            bids = maxout_tcv(tcv, exp_util_hrs, tot_avail_hrs, util_ceil, avail_ceil, asset_cap, weight)
            costs = \
                calc_costs(asset_cap, bids[0], bids[1], fixed_person_hrs / 60, person_rate, tot_SRMC, tot_avail_hrs)[
                    0]
            profits[i][j] = costs[8]
            revenues[i][j] = costs[7]

    return profits


def plot_exp_vs_act_heatmap(tot_avail_hrs, exp_util_hrs, profits, weight):
    weight_range = np.round(np.linspace(0.0, 1.0, profits.shape[1]), decimals=4)
    weight_index = np.where(weight_range == weight)

    data = profits[:, weight_index[0][0], :]

    # using graph_objects, i can't work out how to add annotations in squares
    # think it shoud be the text argument tbut thtat doesn't work.
    fig = make_subplots()
    fig.add_trace(go.Heatmap(x=np.arange(0.0, tot_avail_hrs + 1, 1.0),
                             y=np.arange(0.0, tot_avail_hrs + 1, 1.0),
                             z=data,
                             colorscale='RdBu',
                             zmid=0,
                             text=data,
                             colorbar={"title": 'Profit (£)'}))

    fig.add_shape(
        type='rect',
        x0=exp_util_hrs - 0.5, x1=exp_util_hrs + 0.5, y0=exp_util_hrs - 0.5, y1=exp_util_hrs + 0.5,
        xref='x', yref='y',
        line_color='black'
    )

    fig.update_yaxes(title_text="Expected Utilisation Hours",
                     nticks=int(tot_avail_hrs + 1),
                     range=[-0.5, tot_avail_hrs + 0.5])
    fig.update_xaxes(title_text="Actual Utilisation Hours",
                     nticks=int(tot_avail_hrs + 1),
                     range=[-0.5, tot_avail_hrs + 0.5])
    return fig


def plot_weight_vs_act_heatmap_plotly(profits, exp_util_hrs, tot_avail_hrs, util_ceil):
    exp_range = np.round(np.arange(0.0, tot_avail_hrs + 1, 1.0), decimals=1)
    exp_index = np.where(exp_range == exp_util_hrs)

    data = profits[exp_index[0][0], :, :]

    # using graph_objects, i can't work out how to add annotations in squares
    # think it shoud be the text argument but that doesn't work.

    # also want to add secondary axis which uses different 'unit'.
    # e.g. weight 0 - 1 can also be expressed as utilisation bid 0 - util_max.
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # this first one just makes the secondary y axis appear
    fig.add_trace(go.Heatmap(x=np.arange(0.0, tot_avail_hrs + 1, 1.0),
                             y=np.linspace(0.0, util_ceil, profits.shape[1]),
                             z=data,
                             colorscale='RdBu',
                             zmid=0,
                             text=data,
                             colorbar={"title": 'Profit (£)'},
                             ), secondary_y=True)

    fig.add_trace(go.Heatmap(x=np.arange(0.0, tot_avail_hrs + 1, 1.0),
                             y=np.linspace(0.0, 1.0, profits.shape[1]),
                             z=data,
                             colorscale='RdBu',
                             zmid=0,
                             text=data,
                             colorbar={"title": 'Profit (£)'}))
    fig.add_vrect(x0=exp_util_hrs - 0.5, x1=exp_util_hrs + 0.5, line_width=1)

    fig.update_yaxes(title_text="Bid weighting")
    fig.update_xaxes(title_text="Actual Utilisation Hours",
                     nticks=int(tot_avail_hrs + 1),
                     range=[0, tot_avail_hrs])
    fig.update_yaxes(title_text="Utilisation Bid", secondary_y=True)

    return fig


def profit_vs_actual_plotly(tcv, exp_util_hrs, tot_avail_hrs, asset_effic, asset_cap, energy_cost, duos_nonevent,
                            duos_event, lcos, util_bid, util_ceil, avail_bid, avail_ceil, person_rate,
                            fixed_person_hrs, util_person_hrs):
    tot_SRMC = tot_marg_cost(asset_effic, asset_cap, energy_cost, duos_nonevent,
                             duos_event, lcos, person_rate, util_person_hrs)

    bids = maxout_tcv(tcv, exp_util_hrs, tot_avail_hrs, util_ceil, avail_ceil, asset_cap, 0.0)
    max_avail_profit = calc_costs(asset_cap, bids[0], bids[1], person_rate,
                                  fixed_person_hrs, tot_SRMC, tot_avail_hrs)[1]["Profit (£)"]

    bids = maxout_tcv(tcv, exp_util_hrs, tot_avail_hrs, util_ceil, avail_ceil, asset_cap, 1.0)
    max_util_profit = calc_costs(asset_cap, bids[0], bids[1], person_rate,
                                 fixed_person_hrs, tot_SRMC, tot_avail_hrs)[1]["Profit (£)"]

    user_def_prof = calc_costs(asset_cap, avail_bid, util_bid, person_rate,
                               fixed_person_hrs, tot_SRMC, tot_avail_hrs)[1]["Profit (£)"]

    data = pd.DataFrame({"max availability": max_avail_profit,
                         "max utilisation": max_util_profit,
                         "user defined": user_def_prof},
                        index=np.arange(0.0, tot_avail_hrs + 1, 1.0))

    fig = px.line(data, x=data.index, y=["max availability",
                                         "max utilisation",
                                         "user defined"],
                  width=1150, height=800)

    fig.update_yaxes(title_text="Profit (£)")
    fig.update_xaxes(title_text="Actual Utilisation Hours",
                     nticks=int(tot_avail_hrs + 1),
                     range=[0, tot_avail_hrs])
    fig.add_vline(x=exp_util_hrs, fillcolor='black')
    fig.add_vrect(x0=0, x1=exp_util_hrs,
                  annotation_text="""
              If expecting to be under-utilised, <br> 
              weight bid towards availability to <br>
              increase profit""",
                  annotation_position="top right",
                  annotation_font_size=10,
                  fillcolor="blue", opacity=0.1, line_width=0)
    fig.add_vrect(x0=exp_util_hrs, x1=tot_avail_hrs,
                  annotation_text="""
              If expecting to be over-utilised, <br> 
              weight bid towards utilisation to <br>
              increase profit""",
                  annotation_position="top left",
                  annotation_font_size=10,
                  fillcolor="red", opacity=0.1, line_width=0)
    fig.update_layout(legend_title_text='Bid Weighting Scenario')
    fig.update_layout(legend_title_font_size=12)
    fig.update_layout(legend=dict(
        orientation="h",
        yanchor="bottom",
        y=-0.15,
        xanchor="right",
        x=0.76
    ))

    return fig


overview = dbc.Card(
    dbc.CardBody(
        [
            html.Div(
                [
                    html.Div([Header(app)]),
                    html.Div(
                        [
                            # Preamble
                            html.Div(
                                [
                                    html.H6(
                                        ["Before you start"],
                                        className="subtitle padded"
                                    ),
                                    html.Br([]),
                                    html.P(
                                        "This tool is based on continued work from a previous \
                                        calculator that has been developed by the Low Carbon \
                                        Hub and with support from SSEN and Origami. This \
                                        online version of the Bid Analysis Calculator provides \
                                        improved interaction and visulation for partners to \
                                        explore the effect of different pricing strategies and \
                                        number of asset utilisation hours on potential revenue \
                                        and Total Contract Value (TCV) where Sustained Peak \
                                        Management (SPM) markets are concerned in Project LEO.",
                                        className="paratext",
                                    ),
                                    html.P(
                                        [
                                            "Please Note: This tool is simply for analysis and "
                                            "the developers can not be held responsible for "
                                            "any subsequent issues with the use of this tool within "
                                            "the market trials. If you have any queries around the license "
                                            "used for this tool, please contact us ",
                                            dcc.Link("here",
                                                     href="mailto:scot.wheeler@eng.ox.ac.uk",
                                                     style={"color": "#ea8f32"},
                                                     className="link"
                                                     ),
                                        ],
                                        className="paratext",
                                        style={
                                            "font-style": "italic"
                                        }
                                    ),
                                ],
                                className="row",
                                style={
                                    "padding-bottom": "50px"
                                }
                            ),
                            # Asset config. information
                            html.Div(
                                [
                                    html.Div(
                                        [
                                            html.H6(
                                                "Asset Configuration",
                                                className="subtitle padded",
                                            ),
                                            html.P(
                                                [
                                                    "In order to allow you to explore how Availability \
                                                    and Utilisation affect your operational profit margins \
                                                    for your asset based on the selected TCV, we need some \
                                                    more information. Go ahead an fill in the respective \
                                                    fields to describe your asset and operational costs as \
                                                    accurately as possible. Given the current market design, \
                                                    fields in the LEO ",
                                                    html.Span("orange ", style={"color": "#ea8f32"}),
                                                    "are set at default values to help you assess your \
                                                    asset in accordance to what you will most likely \
                                                    experience in the NMF. For instance, a total of 20 \
                                                    Availability hours are used in calculations owing \
                                                    to SSEN be able to request availability for 4 hour \
                                                    windows for each working day in a given week. \
                                                    Once you have completed this configuration, head over to the ",
                                                    html.Span("Bid Analysis ", style={"color": "#ea8f32"}),
                                                    "tab to explore your best pricing model. \
                                                    The current values represent a hypothetical \
                                                    battery operation as a starting point for your \
                                                    reference. You can use these values to first \
                                                    understand how the tool works. Hover over fields with \
                                                    '*' for more guidance."
                                                ],
                                                className="paratext"
                                            ),
                                        ],
                                        className="eight columns",
                                    ),
                                    html.Div(
                                        [
                                            html.Img(
                                                src=app.get_asset_url("config.gif"),
                                                style=
                                                {
                                                    'height': '300px',
                                                    'width': 'auto',
                                                },
                                            ),
                                        ],
                                        className="four columns",
                                    )
                                ],
                                className="row",
                                style={
                                    "padding-bottom": "50px",
                                    "padding-top": "50px"
                                }
                            ),
                            # Default Header
                            html.Div(
                                [
                                    html.B(
                                        [
                                            "High-level Assumptions"
                                        ],
                                        className="paratextital",
                                    ),
                                ],
                                style={
                                    'padding-bottom': '30px'
                                }
                            ),
                            # TCV and Avail. Ceil
                            html.Div(
                                [
                                    # TCV
                                    html.Div(
                                        [
                                            html.P(
                                                [
                                                    html.Span(
                                                        "Total Contract Value (TCV £/kWh) *", id="tcv-tooltip"
                                                    ),
                                                ],
                                                className='paratext'
                                            ),
                                            # TODO: Get to work in styles sheet
                                            dbc.Tooltip(
                                                "As determined by DSO",
                                                target="tcv-tooltip",
                                                placement="top",
                                                className="paratext",
                                                style={
                                                    "background-color": "#3D4E68",
                                                    "color": "white",
                                                    'width': '200px',
                                                    'height': '30px',
                                                    'text-align': 'center',
                                                    'align-items': 'center',
                                                    'border-radius': '30px',
                                                    'padding-top': '5px',
                                                }
                                            ),
                                        ],
                                        className="three columns"
                                    ),
                                    html.Div(
                                        [
                                            dcc.Input(
                                                id="tcv",
                                                type="number",
                                                value=0.30,
                                                min=0,
                                                step=0.01,
                                                style={
                                                    'fontFamily': "avenir",
                                                    'fontSize': '16px',
                                                    'color': 'white',
                                                    'background-color': '#ea8f32',
                                                    'width': '100px',
                                                    'text-align': 'center'
                                                }
                                            ),
                                        ],
                                        className="three columns"
                                    ),
                                    # Avail Bid
                                    html.Div(
                                        [
                                            html.P(
                                                [
                                                    html.Span(
                                                        "Availability Ceiling (£/kW/h)"
                                                    ),
                                                ],
                                                className='paratext'
                                            ),
                                        ],
                                        className="four columns",
                                        style={
                                            'padding-left': '60px',
                                        }
                                    ),
                                    html.Div(
                                        [
                                            dcc.Input(
                                                id="avail-ceil",
                                                type="number",
                                                value=0.045,
                                                min=0,
                                                step=0.001,
                                                style={
                                                    'fontFamily': "avenir",
                                                    'fontSize': '16px',
                                                    'color': 'white',
                                                    'background-color': '#ea8f32',
                                                    'width': '100px',
                                                    'text-align': 'center'
                                                }
                                            ),
                                        ],
                                        className="two columns"
                                    ),
                                ],
                                className="row ",
                            ),
                            # Total Hours and Util. Ceil
                            html.Div(
                                [
                                    html.Div(
                                        [
                                            html.P(
                                                [
                                                    html.Span(
                                                        "Available Hours *", id="hrs-tooltip"
                                                    ),
                                                ],
                                                className='paratext'
                                            ),
                                            # TODO: Get to work in styles sheet
                                            dbc.Tooltip(
                                                "Based on 5 days of 15:00-19:00.",
                                                target="hrs-tooltip",
                                                placement="top",
                                                className="paratext",
                                                style={
                                                    "background-color": "#3D4E68",
                                                    "color": "white",
                                                    'width': '300px',
                                                    'text-align': 'center',
                                                    'align-items': 'center',
                                                    'border-radius': '30px',
                                                    'padding-top': '5px',
                                                    'padding-left': '15px',
                                                    'padding-right': '15px',
                                                    'padding-bottom': '5px',
                                                }
                                            ),
                                        ],
                                        className="three columns"
                                    ),
                                    html.Div(
                                        [
                                            dcc.Input(
                                                id="tot-avail-hrs",
                                                type="number",
                                                value=20,
                                                min=0,
                                                step=1,
                                                style={
                                                    'fontFamily': "avenir",
                                                    'fontSize': '16px',
                                                    'color': 'white',
                                                    'background-color': '#ea8f32',
                                                    'width': '100px',
                                                    'text-align': 'center'
                                                }
                                            ),
                                        ],
                                        className="three columns"
                                    ),
                                    # Util Bid
                                    html.Div(
                                        [
                                            html.P(
                                                [
                                                    html.Span(
                                                        "Utilisation Ceiling (£/kWh)"
                                                    ),
                                                ],
                                                className='paratext'
                                            ),
                                        ],
                                        className="four columns",
                                        style={
                                            'padding-left': '60px',
                                        }
                                    ),
                                    html.Div(
                                        [
                                            dcc.Input(
                                                id="util-ceil",
                                                type="number",
                                                value=0.30,
                                                min=0,
                                                step=0.01,
                                                style={
                                                    'fontFamily': "avenir",
                                                    'fontSize': '16px',
                                                    'color': 'white',
                                                    'background-color': '#ea8f32',
                                                    'width': '100px',
                                                    'text-align': 'center'
                                                }
                                            ),
                                        ],
                                        className="two columns"
                                    ),
                                ],
                                className="row ",
                            ),
                            # Asset Config. Header
                            html.Div(
                                [
                                    html.B(
                                        [
                                            "Asset Specific"
                                        ],
                                        className="paratextital",
                                    ),
                                ],
                                style={
                                    'padding-bottom': '30px',
                                    'padding-top': '30px'
                                }
                            ),
                            # Asset Capacity and Cost of Elec.
                            html.Div(
                                [
                                    # Asset Capacity
                                    html.Div(
                                        [
                                            html.P(
                                                [
                                                    "Installed Capacity (kW)"
                                                ],
                                                className="paratext"
                                            ),
                                        ],
                                        className="three columns"
                                    ),
                                    html.Div(
                                        [
                                            # TODO: Check FSA to confirm limits on installed capacity entries
                                            dcc.Input(
                                                id="asset-cap",
                                                type="number",
                                                min=0,
                                                step=0.1,
                                                value=16,
                                                style={
                                                    'fontFamily': "avenir",
                                                    'fontSize': '16px',
                                                    'color': '#1A2542',
                                                    'width': '100px',
                                                    'text-align': 'center'
                                                }
                                            ),
                                        ],
                                        className="three columns"
                                    ),
                                    # Cost of Elec.
                                    html.Div(
                                        [
                                            html.P(
                                                [
                                                    "Cost of Energy (£/kWh)"
                                                ],
                                                className="paratext"
                                            ),
                                        ],
                                        className="four columns",
                                        style={
                                            'padding-left': '60px',
                                        }
                                    ),
                                    html.Div(
                                        [
                                            dcc.Input(
                                                id="energy-cost",
                                                type="number",
                                                min=0,
                                                max=1,
                                                step=0.001,
                                                value=0.120,
                                                style={
                                                    'fontFamily': "avenir",
                                                    'fontSize': '16px',
                                                    'color': '#1A2542',
                                                    'width': '100px',
                                                    'text-align': 'center'
                                                }
                                            ),
                                        ],
                                        className="two columns"
                                    ),
                                ],
                                className="row ",
                            ),
                            # DUoS (red and green) and LCOS
                            html.Div(
                                [
                                    # DUoS
                                    html.Div(
                                        [
                                            html.P(
                                                [
                                                    html.Span(
                                                        "DUoS (£/kWh) *", id="duos-tooltip"
                                                    ),
                                                ],
                                                className='paratext'
                                            ),
                                            # TODO: Get to work in styles sheet
                                            dbc.Tooltip(
                                                "Event: DUoS rate during flexibility event. "
                                                "Non-event: DUoS rate during recharging of asset",
                                                target="duos-tooltip",
                                                placement="top",
                                                className="paratext",
                                                style={
                                                    "background-color": "#3D4E68",
                                                    "color": "white",
                                                    'text-align': 'center',
                                                    'align-items': 'center',
                                                    'border-radius': '30px',
                                                    'padding-top': '5px',
                                                    'padding-left': '15px',
                                                    'padding-right': '15px',
                                                    'padding-bottom': '5px',

                                                }
                                            ),
                                        ],
                                        className="three columns"
                                    ),
                                    html.Div(
                                        [
                                            dcc.Input(
                                                id="duos-event",
                                                type="number",
                                                min=0,
                                                max=1,
                                                step=0.001,
                                                value=0.055,
                                                style={
                                                    'fontFamily': "avenir",
                                                    'fontSize': '16px',
                                                    'color': '#1A2542',
                                                    'width': '100px',
                                                    'text-align': 'center'
                                                }
                                            ),
                                            dcc.Input(
                                                id="duos-nonevent",
                                                type="number",
                                                min=0,
                                                max=1,
                                                step=0.0001,
                                                value=0.0064,
                                                style={
                                                    'fontFamily': "avenir",
                                                    'fontSize': '16px',
                                                    'color': '#1A2542',
                                                    'width': '100px',
                                                    'text-align': 'center',
                                                }
                                            ),
                                        ],
                                        className="three columns",
                                    ),
                                    # LCOS
                                    html.Div(
                                        [
                                            html.P(
                                                [
                                                    html.Span(
                                                        "LCOS (£/kWh) *", id="lcos-tooltip"
                                                    ),
                                                ],
                                                className='paratext'
                                            ),
                                            # TODO: Get to work in styles sheet
                                            dbc.Tooltip(
                                                "Levelised cost of storage proportioned to flexibility market",
                                                target="lcos-tooltip",
                                                placement="top",
                                                className="paratext",
                                                style={
                                                    "background-color": "#3D4E68",
                                                    "color": "white",
                                                    'width': '200px',
                                                    'height': '30px',
                                                    'text-align': 'center',
                                                    'align-items': 'center',
                                                    'border-radius': '30px',
                                                    'padding-top': '5px',
                                                }
                                            ),
                                        ],
                                        className="three columns"
                                    ),
                                    html.Div(
                                        [
                                            dcc.Input(
                                                id="lcos",
                                                type="number",
                                                min=0,
                                                max=1,
                                                step=0.01,
                                                value=0.03,
                                                style={
                                                    'fontFamily': "avenir",
                                                    'fontSize': '16px',
                                                    'color': '#1A2542',
                                                    'width': '100px',
                                                    'text-align': 'center'
                                                }
                                            ),
                                        ],
                                        className="two columns"
                                    ),
                                ],
                                className="row ",
                            ),
                            # Asset Efficiency
                            html.Div(
                                [
                                    html.Div(
                                        [
                                            html.P(
                                                [
                                                    "Asset Efficiency"
                                                ],
                                                className="paratext"
                                            ),
                                        ],
                                        className="three columns"
                                    ),
                                    html.Div(
                                        [
                                            dcc.Input(
                                                id="asset-effic",
                                                type="number",
                                                min=0,
                                                max=1,
                                                step=0.01,
                                                value=0.90,
                                                style={
                                                    'fontFamily': "avenir",
                                                    'fontSize': '16px',
                                                    'color': '#1A2542',
                                                    'width': '100px',
                                                    'text-align': 'center'
                                                }
                                            ),
                                        ],
                                        className="three columns"
                                    ),
                                ],
                                className="row ",
                            ),
                            # Personnel costs
                            html.Div(
                                [
                                    html.Div(
                                        [
                                            html.P(
                                                [
                                                    html.Span(
                                                        "Personnel Costs *", id="persn-tooltip"
                                                    ),
                                                ],
                                                className='paratext'
                                            ),
                                            # TODO: Get to work in styles sheet
                                            dbc.Tooltip(
                                                "Enter your hourly rate for personnel, the fixed number of \
                                                minutes to take part in an auction, and minutes used to \
                                                schedule/dispatch a flex event",
                                                target="persn-tooltip",
                                                placement="top",
                                                className="paratext",
                                                style={
                                                    "background-color": "#3D4E68",
                                                    "color": "white",
                                                    'width': '300px',
                                                    'text-align': 'center',
                                                    'align-items': 'center',
                                                    'border-radius': '30px',
                                                    'padding-top': '5px',
                                                    'padding-left': '15px',
                                                    'padding-right': '15px',
                                                    'padding-bottom': '5px',

                                                }
                                            ),
                                        ],
                                        className="three columns"
                                    ),
                                    html.Div(
                                        [
                                            dcc.Input(
                                                id="person-rate",
                                                type="number",
                                                min=0,
                                                max=100,
                                                step=0.5,
                                                value=15,
                                                style={
                                                    'fontFamily': "avenir",
                                                    'fontSize': '16px',
                                                    'color': '#1A2542',
                                                    'width': '100px',
                                                    'text-align': 'center'
                                                }
                                            ),
                                            dcc.Input(
                                                id="fixed-person-hrs",
                                                type="number",
                                                min=0,
                                                max=120,
                                                step=1,
                                                value=10,
                                                style={
                                                    'fontFamily': "avenir",
                                                    'fontSize': '16px',
                                                    'color': '#1A2542',
                                                    'width': '100px',
                                                    'text-align': 'center'
                                                }
                                            ),
                                            dcc.Input(
                                                id="util-person-hrs",
                                                type="number",
                                                min=0,
                                                max=120,
                                                step=1,
                                                value=5,
                                                style={
                                                    'fontFamily': "avenir",
                                                    'fontSize': '16px',
                                                    'color': '#1A2542',
                                                    'width': '100px',
                                                    'text-align': 'center'
                                                }
                                            ),
                                        ],
                                        className="four columns"
                                    ),
                                ],
                                className="row ",
                            ),
                            # Marginal costs and developer info
                            html.Div(
                                [
                                    # Marginal costs printouts
                                    html.Div(
                                        [
                                            # Marginal Costs Header
                                            html.Div(
                                                [
                                                    html.B(
                                                        [
                                                            "Marginal Costs"
                                                        ],
                                                        className="paratextital",
                                                    ),
                                                ],
                                                style={
                                                    'padding-bottom': '30px',
                                                    'padding-top': '30px'
                                                }
                                            ),
                                            # Marginal energy costs (utilisation)
                                            # Energy util costs
                                            html.Div(
                                                [
                                                    html.Div(
                                                        [
                                                            html.P(
                                                                [
                                                                    html.Span(
                                                                        "Energy Cost of Utilisation (£/kWh) *",
                                                                        id="marg-util-tooltip"
                                                                    ),
                                                                ],
                                                                className='paratext'
                                                            ),
                                                            dbc.Tooltip(
                                                                "Includes arbitrage between high and low DUOS. \
                                                                Also assumes that the site never exports.",
                                                                target="marg-util-tooltip",
                                                                placement="top",
                                                                className="paratext",
                                                                style={
                                                                    "background-color": "#3D4E68",
                                                                    "color": "white",
                                                                    'width': '300px',
                                                                    'text-align': 'center',
                                                                    'align-items': 'center',
                                                                    'border-radius': '30px',
                                                                    'padding-top': '5px',
                                                                    'padding-left': '15px',
                                                                    'padding-right': '15px',
                                                                    'padding-bottom': '5px',

                                                                }
                                                            ),
                                                        ],
                                                        className="six columns"
                                                    ),
                                                    html.Div(
                                                        [
                                                            html.Div(id='marg-energy-util-cost')
                                                        ],
                                                        className="six columns"
                                                    ),
                                                ],
                                                className="row ",
                                            ),
                                            # Hrly util cost
                                            html.Div(
                                                [
                                                    html.Div(
                                                        [
                                                            html.P(
                                                                [
                                                                    "Hourly Cost of Utilisation (£/h)"
                                                                ],
                                                                className='paratext'
                                                            ),
                                                        ],
                                                        className="six columns"
                                                    ),
                                                    html.Div(
                                                        [
                                                            html.Div(id='marg-hrly-util-cost'),
                                                        ],
                                                        className="six columns"
                                                    ),
                                                ],
                                                className="row ",
                                            ),
                                            # Personnel cost
                                            html.Div(
                                                [
                                                    html.Div(
                                                        [
                                                            html.P(
                                                                [
                                                                    "Personnel Cost of Utilisation (£/kWh)"
                                                                ],
                                                                className='paratext'
                                                            ),
                                                        ],
                                                        className="six columns"
                                                    ),
                                                    html.Div(
                                                        [
                                                            html.Div(id='marg-persn-cost'),
                                                        ],
                                                        className="six columns"
                                                    ),
                                                ],
                                                className="row ",
                                            ),
                                            # Total marg util cost
                                            html.Div(
                                                [
                                                    html.Div(
                                                        [
                                                            html.P(
                                                                [
                                                                    html.Span(
                                                                        "Total Marginal Costs (£/kWh) *",
                                                                        id="marg-tot-tooltip"
                                                                    ),
                                                                ],
                                                                className='paratext'
                                                            ),
                                                            dbc.Tooltip(
                                                                "This needs to be lower than TCV if any profit is to be made \
                                                                through utilisation stratgey, or, it represents the \
                                                                minimum utilisation part of a bid",
                                                                target="marg-tot-tooltip",
                                                                placement="top",
                                                                className="paratext",
                                                                style={
                                                                    "background-color": "#3D4E68",
                                                                    "color": "white",
                                                                    'width': '300px',
                                                                    'text-align': 'center',
                                                                    'align-items': 'center',
                                                                    'border-radius': '30px',
                                                                    'padding-top': '5px',
                                                                    'padding-left': '15px',
                                                                    'padding-right': '15px',
                                                                    'padding-bottom': '5px',
                                                                }
                                                            ),
                                                        ],
                                                        className="six columns"
                                                    ),
                                                    html.Div(
                                                        [
                                                            html.Div(id='tot-marg-cost'),
                                                        ],
                                                        className="six columns"
                                                    ),
                                                ],
                                                className="row ",
                                            ),
                                        ],
                                        className="six columns"
                                    ),
                                    # Developer Info
                                    html.Div(
                                        [
                                            html.Div(
                                                [
                                                    html.H6(
                                                        "Developers",
                                                        className="paratext",
                                                        style={
                                                            'color': '#ea8f32',
                                                            'padding-bottom': '20px'
                                                        }
                                                    ),
                                                    html.Div(
                                                        [
                                                            html.Div(
                                                                html.Img(
                                                                    src=app.get_asset_url("ScotW.png"),
                                                                    className="headshot",
                                                                    style={
                                                                        'margin-left': '15px'
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
                                                                        'margin-left': '15px'
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
                                                    "padding-bottom": "50px",
                                                    "padding-top": "50px"
                                                }
                                            ),
                                        ],
                                        className="six columns",
                                        style={
                                            'text-align': 'center'
                                        }
                                    ),
                                ],
                                className="row"
                            ),
                            # Credits
                            html.Div(
                                [
                                    html.P(
                                        [
                                            "Animation ('Animated Icon Pack') by ",
                                            dcc.Link("Aslan Almukhambetov",
                                                     href="https://dribbble.com/reggid",
                                                     style={"color": "#ea8f32"},
                                                     className="link"
                                                     ),
                                        ],
                                        className="footnote"
                                    ),
                                ]
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

bidAnalysis = dbc.Card(
    dbc.CardBody(
        [
            html.Div(
                [
                    Header(app),
                    html.Div(
                        [
                            # Bid Options preamble
                            html.Div(
                                [
                                    html.Div(
                                        [
                                            html.H6(
                                                "Bid Options",
                                                className="subtitle padded",
                                            ),
                                            html.P(
                                                [
                                                    "Understanding your Availability and Utilisation bids in the "
                                                    "competitive market, while remaining below the TCV, will give you "
                                                    "the best strategy to maximise profits. Use the fields below to "
                                                    "determine how varying Availability and Utilisation affect your "
                                                    "options (default values are the ceiling for "
                                                    "Availability and £0 for Utilisation)."
                                                ],
                                                className="paratext"
                                            ),
                                        ],
                                        className="twelve columns",
                                        style={
                                            'padding-bottom': '50px'
                                        }
                                    ),
                                ],
                                className="row ",
                            ),
                            # Expected hours (expt hrs) label
                            html.Div(
                                [
                                    html.P(
                                        [
                                            html.Span(
                                                "Expected Hours *", id="expt-tooltip"
                                            ),
                                        ],
                                        className='paratext'
                                    ),
                                    dbc.Tooltip(
                                        "Enter the expected number of hours that your asset will \
                                        be called on for delivering a flex service",
                                        target="expt-tooltip",
                                        placement="top",
                                        className="paratext",
                                        style={
                                            "background-color": "#3D4E68",
                                            "color": "white",
                                            'width': '300px',
                                            'text-align': 'center',
                                            'align-items': 'center',
                                            'border-radius': '30px',
                                            'padding-top': '5px',
                                            'padding-left': '15px',
                                            'padding-right': '15px',
                                            'padding-bottom': '5px',
                                        }
                                    ),
                                ],
                                className="row",
                                style={
                                    'text-align': 'center',
                                    'padding-right': '70px'
                                }
                            ),
                            # Expt hrs input field
                            html.Div(
                                [
                                    dcc.Input(
                                        id="exp-util-hrs",
                                        type="number",
                                        value=3,
                                        min=0,
                                        max=20,
                                        step=1,
                                        style={
                                            'fontFamily': "avenir",
                                            'fontSize': '16px',
                                            'color': 'white',
                                            'background-color': '#ea8f32',
                                            'width': '100px',
                                            'text-align': 'center'
                                        }
                                    ),
                                ],
                                className="row",
                                style={
                                    'text-align': 'center',
                                    'padding-right': '70px'
                                }
                            ),
                            # Bid entry and max. calculations
                            html.Div(
                                [
                                    # Availability Bid
                                    html.Div(
                                        [
                                            html.Div(
                                                [
                                                    html.P(
                                                        [
                                                            "Availability Bid"
                                                        ],
                                                        className="paratext"
                                                    ),
                                                ],
                                                className="eight columns",
                                                style={
                                                    'text-align': 'right',
                                                    'padding-right': '10px'
                                                }
                                            ),
                                            html.Div(
                                                [
                                                    dcc.Input(
                                                        id="avail-bid",
                                                        type="number",
                                                        min=0,
                                                        step=0.001,
                                                        value=0.045,
                                                        style={
                                                            'fontFamily': "avenir",
                                                            'fontSize': '16px',
                                                            'color': '#1A2542',
                                                            'width': '100px',
                                                            'text-align': 'center'
                                                        }
                                                    ),
                                                ],
                                                className="four columns",
                                                style={
                                                    'text-align': 'right',
                                                    'padding-right': '10px'
                                                }
                                            ),
                                        ],
                                        className="six columns",
                                    ),
                                    # Utilisation Bid
                                    html.Div(
                                        [
                                            html.Div(
                                                [
                                                    dcc.Input(
                                                        id="util-bid",
                                                        type="number",
                                                        min=0,
                                                        step=0.001,
                                                        value=0.0,
                                                        style={
                                                            'fontFamily': "avenir",
                                                            'fontSize': '16px',
                                                            'color': '#1A2542',
                                                            'width': '100px',
                                                            'text-align': 'center'
                                                        }
                                                    ),
                                                ],
                                                className="four columns"
                                            ),
                                            html.Div(
                                                [
                                                    html.P(
                                                        [
                                                            "Utilisation Bid"
                                                        ],
                                                        className="paratext"
                                                    ),
                                                ],
                                                className="eight columns"
                                            ),
                                        ],
                                        className="six columns",
                                        style={
                                            'text-align': 'left',
                                            'padding-left': '10px'
                                        }
                                    ),
                                ],
                                className="row"
                            ),
                            # Max Bid readout
                            html.Div(id='max-bids'),
                            html.Div(id='exceed-warning'),

                            # Plot of Profit vs Actual Hours
                            # TODO: We need a right up (small) of how to read this plot
                            html.Div(id='profit-vs-actual-plot'),

                            # Data table Preample
                            html.Div(
                                [
                                    html.Div(
                                        [
                                            html.H6(
                                                "The Deeper Dive",
                                                className="subtitle padded",
                                            ),
                                            html.P(
                                                [
                                                    "\
                                                    Use this section to explore the numbers more closely. \
                                                    We have laid out the data tables in neat and collapsible \
                                                    forms so that you can see how costs vary by operational \
                                                    costs for various Availability, Utilisation strategies \
                                                    across a range of service \
                                                    hours. There is also the functionality to weight your \
                                                    bids by maximising Availability versus Utilisation to \
                                                    see how your profit margins are affected based on your \
                                                    asset input on the previous tab. Use the menu below to \
                                                    see the details and note that your expected number of hours \
                                                    is highlighted for your reference."
                                                ],
                                                className="paratext"
                                            ),
                                        ],
                                        className="twelve columns",
                                    ),
                                ],
                                className="row ",
                                style={
                                    'padding-bottom': '30px',
                                    'padding-top': '50px'
                                }
                            ),
                            # Data table dropdown
                            html.Div(
                                [
                                    dcc.Dropdown(
                                        id='show-datatbl',
                                        options=[
                                            {
                                                'label': i, 'value': i
                                            } for i in
                                            ['Hide Data Tables', 'S1: Utilisation vs Costs',
                                             'S2: Maximising Availability', 'S3: Maximising Utilisation',
                                             'S4: Break Even Costs', 'S5: User-Defined Bids']
                                        ],
                                        placeholder="Select a data table",
                                        multi=False,
                                        className="paratext"
                                    ),
                                ],
                                className="four columns",
                                style={
                                    'padding-bottom': '50px'
                                }
                            ),
                            # Visible data table
                            html.Div(
                                [
                                    html.Div(className="paratext", id="visible-datatbl")
                                ],
                                className="row",
                                style={
                                    "padding-top": "30px",
                                }
                            ),
                            # Blank row for page padding
                            html.Div([], style={"padding-bottom": "100px"}),
                            # Maximising bid options preamble
                            html.Div(
                                [
                                    html.Div(
                                        [
                                            html.H6(
                                                "Maximising Your Bid Options",
                                                className="subtitle padded",
                                            ),
                                            html.P(
                                                [
                                                    "The following input fields will allow you to \
                                                    enter your Availablity and Utilisation bids, \
                                                    while exploring what limits in an aution may \
                                                    exist. For example, entering Availability and \
                                                    Utilisation bids will show you the maximum \
                                                    respective bids that can be used within the \
                                                    predefined (DSO) TCV limit. Use the slider below to \
                                                    adjust your bid weighting between \
                                                    0 and 1 where 0 means you are bidding 'all Availability' \
                                                    and 1 means you are bidding 'all Utilisation' with values \
                                                    in between being a mixture of both depending on how you \
                                                    prioritise your bidding strategy."
                                                ],
                                                className="paratext"
                                            ),
                                        ],
                                        className="twelve columns",
                                        style={
                                            'padding-bottom': '50px'
                                        }
                                    ),
                                ],
                                className="row ",
                                style={
                                    'padding-top': '50px'
                                }
                            ),
                            # Weighting slider
                            html.Div(
                                [
                                    dcc.Slider(
                                        min=0, max=1, step=0.1,
                                        id='weight-slider',
                                        value=0.50,
                                        marks={
                                            0: {'label': 'Availability', 'style': {'font-family': 'avenir'}},
                                            1: {'label': 'Utilisation', 'style': {'font-family': 'avenir'}}
                                        },
                                        tooltip={
                                            "placement": "bottom",
                                            "always_visible": False
                                        },
                                    )
                                ],
                                style={
                                    'padding-top': '30px'
                                }
                            ),
                            # Output of Maxout TCV bid calculations
                            html.Div(id='maxout_tcv_bids'),

                            # Heatmap of expected vs actual hours and profit
                            # TODO: Need a write-up (small) on how to read these plots
                            html.Details(
                                [
                                    html.Summary('Explore: Heatmap of Expected vs Actual Utilisation Hours '
                                                 'with Profit (£)'),
                                    html.Div(id='expt-vs-actual-heatmap'),
                                ],
                                className="paratext",
                                style={
                                    'color': '#ea8f32',
                                    'text-align': 'center'
                                }
                            ),
                            # Heatmap of weight vs actual hours and profit
                            html.Details(
                                [
                                    html.Summary('Explore: Heatmap of Bid Weight vs Actual Utilisation Hours '
                                                 'with Profit (£)'),
                                    html.Div(id='weight-vs-actual-heatmap'),
                                ],
                                className="paratext",
                                style={
                                    'color': '#ea8f32',
                                    'text-align': 'center',
                                    'padding-top': '30px',
                                    'padding-bottom': '100px'
                                }
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
                                                    src=app.get_asset_url("LEOGitHub_comp.png"),
                                                    className="supp_reports_large",
                                                    style={
                                                        'margin-top': '80px',
                                                        'padding-top': '0px',
                                                        'height': '50%',
                                                        'width': '50%'
                                                    }
                                                ),
                                                href='https://github.com/projectleodata/project-leo-data-tools',
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
                                                    to head over to the LEO GitHub Repository (Restricted Access)'
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
                                                    "We expect the Bid Analysis Tool to 'break' \
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
            dcc.Tab(label="Overview & Configuration", style=tab_style,
                    selected_style=tab_selected_style, children=[overview]),
            dcc.Tab(label="Bid Analysis", style=tab_style,
                    selected_style=tab_selected_style, children=[bidAnalysis]),
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


@app.callback([Output('marg-energy-util-cost', 'children'),
               Output('marg-hrly-util-cost', 'children'),
               Output('marg-persn-cost', 'children'),
               Output('tot-marg-cost', 'children')],
              [Input('duos-event', 'value'),
               Input('duos-nonevent', 'value'),
               Input('energy-cost', 'value'),
               Input('asset-effic', 'value'),
               Input('asset-cap', 'value'),
               Input('lcos', 'value'),
               Input('person-rate', 'value'),
               Input('util-person-hrs', 'value')])
def calc_marg_energy_util_cost(duos_event, duos_nonevent, energy_cost, asset_effic, asset_cap,
                               lcos, person_rate, util_person_hrs):
    """
    Function for calculating the main asset marginal costs from user input

    :param duos_event:
    :param duos_nonevent:
    :param energy_cost:
    :param asset_effic:
    :param asset_cap:
    :param lcos:
    :param person_rate:
    :param util_person_hrs:

    :return: marginal costs
    """

    # Calculate the marginal energy cost of utilisation (£/kWh)
    energy_SRMC = (1. / asset_effic) * energy_cost + (duos_nonevent - duos_event) + lcos
    marg_energy_util_cost = html.P(
        [
            " {:10.3f}".format(energy_SRMC)
        ],
        className='paratext'
    )

    # Calculate the marginal hourly cost of utilisation (£/hr)
    hrly_util = person_rate * (util_person_hrs / 60)
    marg_hrly_util_cost = html.P(
        [
            " {:10.3f}".format(hrly_util)
        ],
        className='paratext'
    )

    # Calculate the marginal personnel cost of utilisation (£/kWh)
    person_SRMC = hrly_util / asset_cap
    marg_person_SRMC = html.P(
        [
            " {:10.3f}".format(person_SRMC)
        ],
        className='paratext'
    )

    tot_SRMC = energy_SRMC + person_SRMC
    tot_SRMC_cost = html.P(
        [
            " {:10.3f}".format(tot_SRMC)
        ],
        className='paratext'
    )

    return marg_energy_util_cost, marg_hrly_util_cost, marg_person_SRMC, tot_SRMC_cost


@app.callback(Output('visible-datatbl', 'children'),
              [Input('tot-avail-hrs', 'value'),
               Input('tcv', 'value'),
               Input('exp-util-hrs', 'value'),
               Input('avail-bid', 'value'),
               Input('avail-ceil', 'value'),
               Input('util-bid', 'value'),
               Input('util-ceil', 'value'),
               Input('duos-event', 'value'),
               Input('duos-nonevent', 'value'),
               Input('energy-cost', 'value'),
               Input('asset-effic', 'value'),
               Input('asset-cap', 'value'),
               Input('lcos', 'value'),
               Input('person-rate', 'value'),
               Input('fixed-person-hrs', 'value'),
               Input('util-person-hrs', 'value'),
               Input('show-datatbl', 'value')])
def datatables(tot_avail_hrs, tcv, exp_util_hrs, avail_bid, avail_ceil, util_bid, util_ceil, duos_event,
               duos_nonevent, energy_cost, asset_effic, asset_cap, lcos, person_rate,
               fixed_person_hrs, util_person_hrs, datatbl):
    """
    Function for producing three main data tables for costs from user input

    :param tot_avail_hrs:
    :param tcv:
    :param exp_util_hrs:
    :param util_ceil:
    :param avail_ceil:
    :param duos_event:
    :param duos_nonevent:
    :param energy_cost:
    :param asset_effic:
    :param asset_cap:
    :param lcos:
    :param person_rate:
    :param fixed_person_hrs:
    :param util_person_hrs:
    :param value: user selected table

    :return: costing table
    """

    """
    S1: Utilisation versus costs
    """
    util_costs_df = pd.DataFrame(np.arange(0, tot_avail_hrs + 1), columns=['Actual Utilisation Hours'])
    util_costs_df['Energy (kWh)'] = util_costs_df['Actual Utilisation Hours'] * asset_cap

    # Calculate the marginal energy cost of utilisation (£/kWh) and the marginal hourly cost of utilisation (£/hr)
    energy_SRMC_calc_tmp = (1. / asset_effic) * energy_cost + (duos_nonevent - duos_event) + lcos
    hrly_util_calc_tmp = person_rate * (util_person_hrs / 60)

    util_costs_df['Marginal Cost of Utilisation (£)'] = (util_costs_df['Energy (kWh)'] * energy_SRMC_calc_tmp) + \
                                                        (util_costs_df['Actual Utilisation Hours'] * hrly_util_calc_tmp)

    # TODO: Does not include an option for 'Other Fixed Costs' at the moment to reduce complexity as
    #  there doesn't seem to be much of a case for it for an intial version
    util_costs_df['Fixed Participation Cost (£)'] = person_rate * (fixed_person_hrs / 60)
    util_costs_df['Operational Cost (£)'] = util_costs_df['Marginal Cost of Utilisation (£)'] + \
                                            util_costs_df['Fixed Participation Cost (£)']

    # Set index for datatable
    util_costs_df.set_index('Actual Utilisation Hours')

    """
    S2: Maximising Availability
    """
    max_avail_costs_df = pd.DataFrame(np.arange(0, tot_avail_hrs + 1), columns=['Actual Utilisation Hours'])

    # Enter the user submitted bid and calc. Revenue and Profit
    max_avail_costs_df['Availability Bid (£)'] = avail_ceil
    max_avail_costs_df['Revenue (£)'] = avail_ceil * tot_avail_hrs * asset_cap
    max_avail_costs_df['Operational Profit (£)'] = max_avail_costs_df['Revenue (£)'] - util_costs_df[
        'Operational Cost (£)']
    max_avail_costs_df['TCV (£/kWh)'] = max_avail_costs_df['Revenue (£)'] / util_costs_df['Energy (kWh)']

    """
    S3: Maximising Utilisation
    """
    max_util_costs_df = pd.DataFrame(np.arange(0, tot_avail_hrs + 1), columns=['Actual Utilisation Hours'])

    # Enter the user submitted bid and calc. Revenue and Profit
    max_util_costs_df['Utilisation Bid (£)'] = util_ceil
    max_util_costs_df['Revenue (£)'] = util_costs_df['Energy (kWh)'] * util_ceil
    max_util_costs_df['Operational Profit (£)'] = max_util_costs_df['Revenue (£)'] - util_costs_df[
        'Operational Cost (£)']
    max_util_costs_df['TCV (£/kWh)'] = max_util_costs_df['Revenue (£)'] / util_costs_df['Energy (kWh)']

    """
    S4: Break Even
    """
    break_even_costs_df = pd.DataFrame(np.arange(0, tot_avail_hrs + 1), columns=['Actual Utilisation Hours'])

    # Calculate the Break Even params. based on user input
    break_even_costs_df['Availability Bid (£)'] = (person_rate * (fixed_person_hrs / 60)) / asset_cap / tot_avail_hrs
    break_even_costs_df['Utilisatin Bid (£)'] = tot_marg_cost(asset_effic, asset_cap, energy_cost, duos_nonevent, duos_event,
                                                              lcos, person_rate, util_person_hrs)
    break_even_costs_df['Revenue (£)'] = (break_even_costs_df['Availability Bid (£)'] * tot_avail_hrs * asset_cap) + \
                                         (break_even_costs_df['Utilisatin Bid (£)'] * util_costs_df['Energy (kWh)'])
    break_even_costs_df['Operational Profit (£)'] = break_even_costs_df['Revenue (£)'] - util_costs_df[
        'Operational Cost (£)']
    break_even_costs_df['TCV (£/kWh)'] = break_even_costs_df['Revenue (£)'] / util_costs_df['Energy (kWh)']

    """
    S5: User-Defined Bids and Costs
    """
    tot_SRMC = tot_marg_cost(asset_effic, asset_cap, energy_cost, duos_nonevent,
                             duos_event, lcos, person_rate, util_person_hrs)

    user_bid_df = calc_costs(asset_cap, avail_bid, util_bid, person_rate,
                             fixed_person_hrs, tot_SRMC, tot_avail_hrs)[1]

    # Produce data tables for reporting in thr Bid Analysis tab
    # TODO: Need to fix the unexpected left margins in the columns
    util_costs_datatbl = dash_table.DataTable(
        data=util_costs_df[:21].round(2).to_dict("records"),
        columns=[{"id": x, "name": x} for x in util_costs_df.columns],
        style_cell={'textAlign': 'center',
                    'textOverflow': 'ellipsis',
                    'padding-left': '0px'
                    },
        style_header={
            'backgroundColor': 'white',
            'fontWeight': 'bold',
            'fontFamily': 'Avenir',
            'border': 'none',
            'textAlign': 'left',
            'margin-left': '0px'
        },
        style_data_conditional=[
            {
                'if': {'row_index': 'odd'},
                'backgroundColor': '#FBF2E6'
            },
            {
                'if': {
                    'filter_query': '{{Actual Utilisation Hours}} = {}'.format(exp_util_hrs)
                },
                'backgroundColor': '#3D4E68',
                'color': 'white'
            },
        ],
        style_as_list_view=True,
        style_table={'overflowX': 'auto'},
        fill_width=False
    ),

    max_avail_datatbl = dash_table.DataTable(
        data=max_avail_costs_df[:21].round(2).to_dict("records"),
        columns=[{"id": x, "name": x} for x in max_avail_costs_df.columns],
        style_cell={'textAlign': 'center',
                    'textOverflow': 'ellipsis',
                    'padding-left': '0px'
                    },
        style_header={
            'backgroundColor': 'white',
            'fontWeight': 'bold',
            'fontFamily': 'Avenir',
            'border': 'none',
            'textAlign': 'left',
            'margin': '0px 0px 0px 0px'
        },
        style_data_conditional=[
            {
                'if': {'row_index': 'odd'},
                'backgroundColor': '#FBF2E6'
            },
            {
                'if': {
                    'filter_query': '{{Actual Utilisation Hours}} = {}'.format(exp_util_hrs)
                },
                'backgroundColor': '#3D4E68',
                'color': 'white'
            },
        ],
        style_as_list_view=True,
        style_table={'overflowX': 'auto'},
        fill_width=False
    ),

    max_util_databl = dash_table.DataTable(
        data=max_util_costs_df[:21].round(2).to_dict("records"),
        columns=[{"id": x, "name": x} for x in max_util_costs_df.columns],
        style_cell={'textAlign': 'center',
                    'textOverflow': 'ellipsis',
                    'padding-left': '0px'
                    },
        style_header={
            'backgroundColor': 'white',
            'fontWeight': 'bold',
            'fontFamily': 'Avenir',
            'border': 'none',
            'textAlign': 'left',
        },
        style_data_conditional=[
            {
                'if': {'row_index': 'odd'},
                'backgroundColor': '#FBF2E6'
            },
            {
                'if': {
                    'filter_query': '{{Actual Utilisation Hours}} = {}'.format(exp_util_hrs)
                },
                'backgroundColor': '#3D4E68',
                'color': 'white'
            },
        ],
        style_as_list_view=True,
        style_table={'overflowX': 'auto'},
        fill_width=False
    ),

    break_even_datatbl = dash_table.DataTable(
        data=break_even_costs_df[:21].round(2).to_dict("records"),
        columns=[{"id": x, "name": x} for x in break_even_costs_df.columns],
        style_cell={'textAlign': 'center',
                    'textOverflow': 'ellipsis',
                    'padding-left': '0px'
                    },
        style_header={
            'backgroundColor': 'white',
            'fontWeight': 'bold',
            'fontFamily': 'Avenir',
            'border': 'none',
            'textAlign': 'left',
        },
        style_data_conditional=[
            {
                'if': {'row_index': 'odd'},
                'backgroundColor': '#FBF2E6'
            },
            {
                'if': {
                    'filter_query': '{{Actual Utilisation Hours}} = {}'.format(exp_util_hrs)
                },
                'backgroundColor': '#3D4E68',
                'color': 'white'
            },
            {
                'if': {
                    'filter_query': '{{TCV (£/kWh)}} > {}'.format(tcv),
                    'column_id': 'TCV (£/kWh)'
                },
                'backgroundColor': '#f55442',
                'color': 'white'
            },
        ],
        style_as_list_view=True,
        style_table={'overflowX': 'auto'},
        fill_width=False
    ),

    usr_bids_databl = dash_table.DataTable(
        data=user_bid_df[:21].round(2).to_dict("records"),
        columns=[{"id": x, "name": x} for x in user_bid_df.columns],
        style_cell={'textAlign': 'center',
                    'textOverflow': 'ellipsis',
                    'padding-left': '0px',
                    'minWidth': '200px', 'width': '200px', 'maxWidth': '200px',
                    },
        style_header={
            'backgroundColor': 'white',
            'fontWeight': 'bold',
            'fontFamily': 'Avenir',
            'border': 'none',
            'textAlign': 'left',
        },
        style_data_conditional=[
            {
                'if': {'row_index': 'odd'},
                'backgroundColor': '#FBF2E6'
            },
            {
                'if': {
                    'filter_query': '{{Utilisation Hours}} = {}'.format(exp_util_hrs)
                },
                'backgroundColor': '#3D4E68',
                'color': 'white'
            },
            {
                'if': {
                    'filter_query': '{{TCV (£/kWh)}} > {}'.format(tcv),
                    'column_id': 'TCV (£/kWh)'
                },
                'backgroundColor': '#f55442',
                'color': 'white'
            },
        ],
        style_as_list_view=True,
        style_table={'overflowX': 'auto'},
        fill_width=False
    ),

    if datatbl == "S1: Utilisation vs Costs":
        return util_costs_datatbl
    elif datatbl == "S2: Maximising Availability":
        return max_avail_datatbl
    elif datatbl == "S3: Maximising Utilisation":
        return max_util_databl
    elif datatbl == "S4: Break Even Costs":
        return break_even_datatbl
    elif datatbl == "S5: User-Defined Bids":
        return usr_bids_databl
    else:
        return html.Div([])


@app.callback(Output('maxout_tcv_bids', 'children'),
              [Input('tot-avail-hrs', 'value'),
               Input('tcv', 'value'),
               Input('exp-util-hrs', 'value'),
               Input('avail-ceil', 'value'),
               Input('util-ceil', 'value'),
               Input('asset-cap', 'value'),
               Input('weight-slider', 'value')])
def maxout_tcv_display(tot_avail_hrs, tcv, exp_util_hrs, avail_ceil, util_ceil, asset_cap, bid_weight):
    """
    Calculates and updates the Availability and Utilisation bids (to maxout the TCV)
    depnding on the user weighting input from slider

    :param tot_avail_hrs:
    :param tcv:
    :param exp_util_hrs:
    :param avail_ceil:
    :param util_ceil:
    :param asset_cap:
    :param bid_weight:
    :return:
    """
    avail, util = maxout_tcv(tcv, exp_util_hrs, tot_avail_hrs, util_ceil, avail_ceil, asset_cap, bid_weight)

    maxout_tcv_bids = html.Div(
        [
            html.Div(
                [
                    html.P(
                        [
                            "Availability Bid: ",
                            html.Span("£{:.3f}".format(avail), style={"color": "#ea8f32"})
                        ],
                        className="paratext"
                    )
                ],
                className="six columns",
                style={
                    'textAlign': 'right'
                }
            ),
            html.Div(
                [
                    html.P(
                        [
                            "Utilisation Bid: ",
                            html.Span("£{:.3f}".format(util), style={"color": "#ea8f32"})
                        ],
                        className="paratext"
                    )
                ],
                className="six columns"
            ),
        ],
        className="row",
        style={
            'padding-top': '30px',
            'padding-bottom': '50px'
        }
    )

    return maxout_tcv_bids


@app.callback([Output('max-bids', 'children'),
               Output('exceed-warning', 'children')],
              [Input('tot-avail-hrs', 'value'),
               Input('tcv', 'value'),
               Input('exp-util-hrs', 'value'),
               Input('avail-bid', 'value'),
               Input('avail-ceil', 'value'),
               Input('util-bid', 'value'),
               Input('util-ceil', 'value'),
               Input('asset-cap', 'value')])
def max_bid_calcs(tot_avail_hrs, tcv, exp_util_hrs, avail_bid, avail_ceil, util_bid, util_ceil, asset_cap):
    avail_max = calc_avail_bid(tcv, exp_util_hrs, tot_avail_hrs, util_bid, avail_ceil, asset_cap)[0]
    util_max = calc_util_bid(tcv, exp_util_hrs, tot_avail_hrs, avail_bid, util_ceil, asset_cap)[0]

    max_bids = html.Div(
        [
            html.P(
                [
                    "To stay under the TCV, your maximum Availability Bid can be ",
                    html.Span("£{:.3f} ".format(avail_max), style={"color": "#ea8f32"}),
                    "and your maximum Utilisation Bid can be ",
                    html.Span("£{:.3f} ".format(util_max), style={"color": "#ea8f32"})
                ],
                className="paratext"
            )
        ],
        className="row",
        style={
            'text-align': 'center',
        }
    )

    # Warning row if any of the ceilings are exceed. If they aren't, nothing is shown
    exceed_warning = html.Div()

    if util_bid > util_ceil:
        bid = "Utilisation Bid"
        ceil = util_ceil

        exceed_warning = html.Div(
            [
                html.P(
                    [
                        html.Span("Whoops! Your entered {} has exceeded the ceiling of £{:.3f}".format(bid, ceil),
                                  style={"color": "#ffffff"})
                    ],
                    className="paratext"
                )
            ],
            className="row",
            style={
                'text-align': 'center',
                'background-color': '#f55442'
            }
        )

    if avail_bid > avail_ceil:
        bid = "Availability Bid"
        ceil = avail_ceil

        exceed_warning = html.Div(
            [
                html.P(
                    [
                        html.Span("Whoops! Your entered {} has exceeded the ceiling of £{:.3f}".format(bid, ceil),
                                  style={"color": "#ffffff"})
                    ],
                    className="paratext"
                )
            ],
            className="row",
            style={
                'text-align': 'center',
                'background-color': '#f55442'
            }
        )

    return max_bids, exceed_warning


@app.callback([Output('expt-vs-actual-heatmap', 'children'),
               Output('weight-vs-actual-heatmap', 'children'),
               Output('profit-vs-actual-plot', 'children')],
              [Input('tot-avail-hrs', 'value'),
               Input('tcv', 'value'),
               Input('exp-util-hrs', 'value'),
               Input('avail-ceil', 'value'),
               Input('avail-bid', 'value'),
               Input('util-ceil', 'value'),
               Input('util-bid', 'value'),
               Input('duos-event', 'value'),
               Input('duos-nonevent', 'value'),
               Input('energy-cost', 'value'),
               Input('asset-effic', 'value'),
               Input('asset-cap', 'value'),
               Input('lcos', 'value'),
               Input('person-rate', 'value'),
               Input('fixed-person-hrs', 'value'),
               Input('util-person-hrs', 'value'),
               Input('weight-slider', 'value')])
def heatmaps_plots(tot_avail_hrs, tcv, exp_util_hrs, avail_ceil, avail_bid, util_ceil, util_bid, duos_event,
             duos_nonevent, energy_cost, asset_effic, asset_cap, lcos, person_rate,
             fixed_person_hrs, util_person_hrs, weight):

    # TODO: Plotting colours need to be more consistent in all plots.
    tot_SRMC = tot_marg_cost(asset_effic, asset_cap, energy_cost, duos_nonevent,
                             duos_event, lcos, person_rate, util_person_hrs)

    profits = profit_vs_expected_util(tcv, exp_util_hrs, tot_avail_hrs, util_ceil, avail_ceil, asset_cap, fixed_person_hrs,
                                      person_rate, tot_SRMC)

    # Various figures for visualisation
    expt_vs_actual_heatmap = plot_exp_vs_act_heatmap(tot_avail_hrs, exp_util_hrs, profits, weight)
    weight_vs_actual_heatmap = plot_weight_vs_act_heatmap_plotly(profits, exp_util_hrs, tot_avail_hrs, util_ceil)

    # TODO: Yes, I know, this is messy and certainly not efficent! Well be corrected with module pairing
    profit_vs_actual_plot = profit_vs_actual_plotly(tcv, exp_util_hrs, tot_avail_hrs, asset_effic, asset_cap,
                                                    energy_cost, duos_nonevent, duos_event, lcos, util_bid,
                                                    util_ceil, avail_bid, avail_ceil, person_rate,
                                                    fixed_person_hrs, util_person_hrs)

    return dcc.Graph(figure=expt_vs_actual_heatmap), \
           dcc.Graph(figure=weight_vs_actual_heatmap), \
           dcc.Graph(figure=profit_vs_actual_plot)


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
