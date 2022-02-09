#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jan 26 09:33:39 2022

@author: scotwheeler

Things to do/check
 - use correct language for profit, cost, revenue etc
 - something slightly different in the energy_SRMC between excel and python (something to do with python internal float representation maybe?)
 - use of global variables, and those in functions is messy
 - should probably wrap everything in a class (called Service?) This would help with the above point, and all global variables can be changed to self.
 - Current assumes 100% utilisation. How does the settlement rules for utilisation and availability impact the outcome.
 - add functionality to undercut tcv max. Can probably be done manualy by changing the tcv limit. Otherwise, add scaler to any function that uses tcv
"""

__version__ = '0.2.0'

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import seaborn as sns

import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio
#pio.renderers.default = 'svg'
pio.renderers.default = 'browser'

np.seterr(divide='ignore') 

# =============================================================================
# Inputs
# =============================================================================
#%% asset parameters
asset_type = 'storage'  # storage/gen/dsr
cap = 16.0              # kW
person_rate = 15.0   # £/hour


#%% costs
# fixed costs
fixed_person_hrs = 10/60 # number of hrs for a person to enter an auction (inc. forecasting of availability)

# other fixed costs to be inc. e.g. metering, data storage, installation etc
other_fixed = 0.0

# SRMC - marginal costs

# not sure how to generalise DUOS charges as it depends on when the service is delivered vs when the asset recharges
DUOS_event = 0.055        # £/kWh - DUOS during event
DUOS_recharge = 0.006      # £/kWh - DUOS outside of event when 'recharge' scheduled
energy_cost = 0.120     # £/kWh
LCOS_battery = 0.03     # £/kWh - based on $400 / MWh and 10% of battery associated with flex.
roundtrip_eff = 0.9
util_person_hrs = 5/60  # number of hrs for a person to respond to a utilisation instruction (inc. asset dispatch, delivery and data upload)  
other_SRMC = 0.0        # £/kWh

#%% market parameters
tot_avail_hrs = 20.0
service_type = 'turn-up'
tcv = 0.30              # £/kWh
avail_ceil = 0.045      # £/kW
util_ceil = 0.30        # £/kWh
exp_util_hrs = 3.0        # hrs - expected utilisation hours
hrs_per_service_win = 4.0 # hrs per service window e.g. 4 if window is 3-7pm every day
hrs_per_util = 1.0        # number of hrs in a single utilisation - this is hard to know and could vary between 1 and service window

# =============================================================================
# Calculations
# =============================================================================
## fixed
tot_fixed = ((fixed_person_hrs * person_rate)
            + other_fixed)

## marginal
# marginal energy (kWh) - slightly different between excel and python?
if (asset_type == 'storage') and (service_type == "turn-up"):
    energy_SRMC = (((1/roundtrip_eff) * energy_cost)    # additional energy due to roundtrip eff
                   + (DUOS_recharge - DUOS_event)            # difference between DUOS rates  
                   + LCOS_battery)                      # battery deg cost
else:
    raise Exception("Only 'storage' asset for 'turn_up' service programmed so far")

# marginal person (£/kWh)
person_SRMC = ((util_person_hrs * person_rate) / (cap * hrs_per_util))

# tot marginal
tot_SRMC = (energy_SRMC
            + person_SRMC
            + other_SRMC)


def break_even():
    """
    Calculates the availability and utilisation bids such that an asset
    breaks even (i.e 0 profit) for any number of actual utilisation hours.
    
    Fixed costs inform availability price
    SRMC inform utilisation price
    
    This does not guarentee that the TCV will be low than the TCV limit, or
    that availability or utilisation bids will be under the respective
    ceiling prices.

    Returns
    -------
    avail: float
        The availability bid
        
    util: float
        The utilisation bid

    """
    util = tot_SRMC
    avail = tot_fixed / cap / tot_avail_hrs
    
    return avail, util

def inde_maxTCV(exp_util_hrs):
    """
    Determines the availability and utilisation bid that maximises the TCV for
    the expected number of hours, but ensures profit is independent of actual
    utilisation hours. This does not guarentee bids will be under the
    individual ceiling prices.
    
    Parameters
    ----------
    exp_util_hrs : float
        The expected number of utilisation hours.

    Returns
    -------
    Returns
    -------
    avail_bid : float
        Availability bid.
    util_bid : float
        Utilisation bid.
    weight : float
        Corresponding bid weighting.

    """
    util_bid = tot_SRMC
    remaining_tcv = tcv - util_bid
    weight = util_bid / tcv
    avail_bid = ((remaining_tcv * exp_util_hrs * cap) 
                 / cap 
                 / tot_avail_hrs)
    
    # don't think it's possible to ensure bids stay within ceiling price
    # as util is defined by the marginal cost of delivery. If this is
    # higher than the ceiling price, I don't think you can achieve what 
    # this function sets out to achieve. Might look something like this:
    
    # util = np.min(tot_SRMC, util_max)
    # avail, weight = calc_avail_bid(exp_util_hrs, util)
    
    
    return avail_bid, util_bid, weight

def calc_costs(cap, avail_bid, util_bid, fixed_cost, marginal_cost,
               tot_hrs = tot_avail_hrs):
    """
    Calculates the costs matrix of participation, revenue and profit as a
    function 

    Parameters
    ----------
    cap : float
        Capacity of the asset.
    avail_bid : float
        Availability bid to calculate costs.
    util_bid : float
        Utilisation bid to calculate costs.
    fixed_cost : float
        The fixed costs of market participation
    marginal_cost : float
        The marginal (per kWh) cost of utilisation.
    tot_hrs : float, optional
        The total possible hours in the auctioned service. 
        The default is the global parameter tot_avail_hrs.

    Returns
    -------
    cost_matrix : np.array
        Numpy array used for plotting
    
    cost_df : pd.DataFrame
        A dataframe version of the cost_matrix array

    """
    # create lists
    util_hours = np.arange(0, (tot_hrs+1), 1.0)
    #marginal_cost = [0] * len(util_hours)
    #fixed_cost = [0] * len(util_hours)
    #tot_cost = [0] * len(util_hours)
    if isinstance(avail_bid, float):
       avail_bids = [avail_bid] * len(util_hours)
    elif isinstance(avail_bid,list): # if different bids can be entered into 1 auction in future
        # should also check length is correct
       avail_bids = avail_bid
    else: raise Exception("Wrong avail bid format")
    if isinstance(util_bid, float):
       util_bids = [util_bid] * len(util_hours)
    elif isinstance(avail_bid,list):
        # should also check length is correct
       util_bids = util_bid
    else: raise Exception("Wrong util bid format")
    #revenue = [0] * len(util_hours)
    #profit = [0] * len(util_hours)
    #tcv = [0] * len(util_hours)
    
    # calculations - actually, probably didn't need to define them all above
    energy = util_hours * cap
    marginal_cost = marginal_cost * energy
    fixed_cost = np.ones(util_hours.shape) * fixed_cost
    tot_cost = marginal_cost + fixed_cost
    revenue = (util_bids * energy) + (avail_bid * cap * tot_avail_hrs)
    profit = revenue - tot_cost
    tcv = revenue / energy
    
    cost_matrix = np.array([util_hours, energy, avail_bids, util_bids,
                            marginal_cost, fixed_cost, tot_cost, revenue,
                            profit, tcv])
    cost_df = pd.DataFrame(cost_matrix.T,
                           columns=["Utilisation hrs",
                                    "energy (kWh)",
                                    "Availability bid (£/kW/h)",
                                    "Utilisation bid (£/kWh)",
                                    "Marginal cost (£/kWh)",
                                    "Auction fixed cost (£)",
                                    "Total service cost (£)",
                                    "Revenue (£)",
                                    "Profit (£)",
                                    "TCV (£/kWh)"])
    return cost_matrix, cost_df

def maxout_tcv(exp_util_hrs, bid_weight):
    """
    This calculates the availability and utilisation bids to max out the tcv
    for a given expected number of hours of delivery and chosen weighting
    between availability and utilisation. This can be used to 
    replicate Harry Orchards (HO) original analysis with bid_weight 0 for 
    all availability and 1 for all utilisaton.

    Parameters
    ----------
    exp_util_hrs : float
        The expected number of utilisation hours.
    bid_weight : float
        A value between 0 and 1. The weighting of the tcv between availability
        and utilisation.

    Returns
    -------
    avail : float
        Availability bid.
    util : float
        Utilisation bid.

    """
        
    util_max = bid_weight * tcv
    avail_max = ((((1 - bid_weight)* tcv) * exp_util_hrs * cap) 
                 / cap 
                 / tot_avail_hrs)
    
    util = np.min([util_max, util_ceil])
    avail = np.min([avail_ceil, avail_max])
    
    return avail, util

def calc_avail_bid(exp_util_hrs, util_bid):
    """
    Given a chosen utilisation bid, calculate max availability bid that 
    ensures the TCV is not exceeded.

    Parameters
    ----------
    exp_util_hrs : float
        The expected number of utilisation hours.
    util_bid : float
        The user defined utilisation bid.

    Returns
    -------
    avail : float
        The max possible availability bid.
    weight : float
        The corresponding weighting assuming this combination of utilisation
        and availability bid.

    """
    remaining_tcv = tcv - util_bid
    weight = util_bid / tcv
    avail_max = ((remaining_tcv * exp_util_hrs * cap) 
                 / cap 
                 / tot_avail_hrs)
    avail = np.min([avail_ceil, avail_max])
    return avail, weight

def calc_util_bid(exp_util_hrs, avail_bid):
    """
    Given a chosen availability bid, calculate max utilisation bid that 
    ensures the TCV is not exceeded.

    Parameters
    ----------
    exp_util_hrs : float
        The expected number of utilisation hours.
    avail_bid : float
        The user defined availability bid.

    Returns
    -------
    util : float
        The max possible utilisation bid.
    weight : float
        The corresponding weighting assuming this comibination of availability
        and utilisation bid.

    """
    util_max = (((tcv * exp_util_hrs * cap) - (avail_bid * tot_avail_hrs * cap))
               / (exp_util_hrs * cap))
    util = np.min([util_ceil, util_max])
    weight = util / tcv
    return util, weight

def profit_vs_expected_util_vs_weight(avail_bid=None, util_bid=None, weight=None):
    """
    Calculate 3D matrix of profit for expected utilisation vs actual
    utilisation for a particular set of bids and strategy weight. 
    
    Parameters
    ----------
    avail_bid : Float
        Availability bid to use for the analysis. If supplied, util_bid must
        also be supplied and None for weight.
        
    util_bid : Float
        Utilisation bid to use for the analysis. If supplied, avail_bid must
        also be supplied and None for weight.
        
    weight : float
        Decimal between 0 and 1. If supplied, avail_bid and util_bid should
        be left blank.

    Returns
    -------
    3d  array with axis [expected utilisation, weight, actual utilisation]
    To get test scenario back where expected utilisation = 3, and weight = 0.5
    use ndarray[3][5]
    
    To get profit as a function of bid weight for a given expected utilisation and actual utilisation
    use profits[exp,:,act]
    
    
    To do: add error checking for input parameter rules

    """
    
    
    exp_util_range = np.arange(0.0, tot_avail_hrs+1, 1.0)
    weight_range = np.linspace(0.0,1.0,11)
    profits = np.zeros((len(exp_util_range), len(weight_range),
                        len(exp_util_range)))
    revenues = np.zeros((len(exp_util_range), len(weight_range),
                         len(exp_util_range)))
    for i, exp_util in enumerate(exp_util_range):
        for j, weight in enumerate(weight_range):
            bids = maxout_tcv(exp_util, weight)
            costs = calc_costs(cap, bids[0], bids[1],
                                  tot_fixed, tot_SRMC)[0]
            profits[i][j] = costs[8]
            revenues[i][j] = costs[7]

    return profits

def profit_vs_expected_util(avail_bid=None, util_bid=None):
    exp_util_range = np.arange(0.0, tot_avail_hrs+1, 1.0)
    #weight_range = np.linspace(0.0,1.0,11)
    profits = np.zeros((len(exp_util_range), len(exp_util_range)))
    revenues = np.zeros((len(exp_util_range), len(exp_util_range)))
    for i, exp_util in enumerate(exp_util_range):
        costs = calc_costs(cap, avail_bid, util_bid, tot_fixed, tot_SRMC)[0]
        profits[i] = costs[8]
        revenues[i] = costs[7]

    return profits
    

def plot_weight_vs_actual(profits, exp_util):
    
    # make x axis utilisation factor = ratio of actual / expected. Add line indicating flat profile.
    
    fig, ax = plt.subplots(figsize=(15,6))
    sns.heatmap(profits[exp_util], ax=ax, annot=profits[exp_util], fmt='.2f', annot_kws={"fontsize":6})
    ax.set_xticklabels(['{:,.0f}'.format(x) for x in np.arange(0.0, tot_avail_hrs+1, 1.0)], rotation=45, ha='right', rotation_mode='anchor')
    # ax.set_yticklabels(np.linspace(0.0,1.0,11), rotation=0, ha='right', rotation_mode='anchor')
    plt.gca().set_yticklabels(['{:,.1f}'.format(x) for x in np.linspace(0.0,1.0,11)], rotation=0, ha='right', rotation_mode='anchor')
    # ax.yaxis.set_major_formatter(ticker.FormatStrFormatter('%0.1f'))
    ax.set_xlabel("Actual Utilisation Hours")
    ax.set_ylabel("Utilisation bid weighting")
    plt.show()
    
def plot_exp_vs_actual(profits, weight):
    fig, ax = plt.subplots(figsize=(15,6))
    sns.heatmap(profits[:,int(weight*10),:], ax=ax, annot=profits[:,int(weight*10),:], fmt='.2f', annot_kws={"fontsize":6})
    ax.set_xticklabels(['{:,.0f}'.format(x) for x in np.arange(0.0, tot_avail_hrs+1, 1.0)], rotation=45, ha='right', rotation_mode='anchor')
    ax.set_yticklabels(['{:,.0f}'.format(x) for x in np.arange(0.0, tot_avail_hrs+1, 1.0)], rotation=0, ha='right', rotation_mode='anchor')
    
    ax.set_xlabel("Actual Utilisation Hours")
    ax.set_ylabel("Expected Utilisation Hours")
    plt.show()
    
def plot_exp_vs_act_heatmap_plotly(profits, weight):
    
    weight_range = np.linspace(0.0, 1.0, profits.shape[1])
    weight_index = np.where(weight_range == weight)

    data = profits[:,weight_index[0][0],:]
    
    # lim = np.max(np.abs(profits))
    
    # using plotly express, i can't work out how to set 0 as midpoint of colorscale or how to annotate. 
    # fig = px.imshow(data,
    #             labels=dict(x="Actual Utilisation Hours", y="Expected Utilisation Hours", color="Profit (£)"),
    #             x = np.arange(0.0, tot_avail_hrs+1, 1.0),
    #             y = np.arange(0.0, tot_avail_hrs+1, 1.0),
    #             color_continuous_scale='RdBu',
    #               aspect="auto", 
    #             )
    
    # using graph_objects, i can't work out how to add annotations in squares
    # think it shoud be the text argument tbut thtat doesn't work.
    fig = make_subplots()
    fig.add_trace(go.Heatmap(x = np.arange(0.0, tot_avail_hrs+1, 1.0),
                              y = np.arange(0.0, tot_avail_hrs+1, 1.0),
                              z=data,
                              colorscale='RdBu',
                              zmid=0,
                              text=data))

    
    fig.add_shape(
        type='rect',
        x0=exp_util_hrs-0.5, x1=exp_util_hrs+0.5, y0=exp_util_hrs-0.5, y1=exp_util_hrs+0.5,
        xref='x', yref='y',
        line_color='black'
        )
    
    fig.update_yaxes(title_text="Expected Utilisation Hours")
    fig.update_xaxes(title_text="Actual Utilisation Hours")
    fig.show()
    return fig
    
def plot_weight_vs_act_heatmap_plotly(profits, exp_util_hrs):
    
    exp_range = np.arange(0.0, tot_avail_hrs+1, 1.0)
    exp_index = np.where(exp_range == exp_util_hrs)

    data = profits[exp_index[0][0],:,:]
    
    # using graph_objects, i can't work out how to add annotations in squares
    # think it shoud be the text argument but that doesn't work.
    
    # also want to add secondary axis which uses different 'unit'.
    # e.g. weight 0 - 1 can also be expressed as utilisation bid 0 - util_max.
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # this first one just makes the secondary y axis appear
    fig.add_trace(go.Heatmap(x = np.arange(0.0, tot_avail_hrs+1, 1.0),
                              y = np.linspace(0.0, util_ceil, profits.shape[1]),
                              z=data,
                              colorscale='RdBu',
                              zmid=0,
                              text=data,
                              colorbar={"title": 'Profit (£)'},
                              ), secondary_y=True)
    
    
    
    fig.add_trace(go.Heatmap(x = np.arange(0.0, tot_avail_hrs+1, 1.0),
                              y = np.linspace(0.0, 1.0, profits.shape[1]),
                              z=data,
                              colorscale='RdBu',
                              zmid=0,
                              text=data,
                              colorbar={"title": 'Profit (£)'}))
    fig.add_vrect(x0=exp_util_hrs-0.5, x1=exp_util_hrs+0.5, line_width=1)
    
    

    
    fig.update_yaxes(title_text="Bid weighting")
    fig.update_xaxes(title_text="Actual Utilisation Hours")
    fig.update_yaxes(title_text="Utilisation bid", secondary_y=True)
    fig.show()
    return fig
    
def profit_vs_actual_plotly(exp_util_hrs, avail_bid, util_bid):
    
    bids = maxout_tcv(exp_util_hrs, 0.0)
    max_avail_profit = calc_costs(cap, bids[0], bids[1],
                              tot_fixed, tot_SRMC)[1]["Profit (£)"]
    
    bids = maxout_tcv(exp_util_hrs, 1.0)
    max_util_profit = calc_costs(cap, bids[0], bids[1],
                              tot_fixed, tot_SRMC)[1]["Profit (£)"]
    
    user_def_prof = calc_costs(cap, avail_bid, util_bid,
                              tot_fixed, tot_SRMC)[1]["Profit (£)"]


    data = pd.DataFrame({"max availability": max_avail_profit,
                         "max utilisation": max_util_profit,
                         "user defined": user_def_prof},
                         index = np.arange(0.0, tot_avail_hrs+1, 1.0))
    
    fig = px.line(data, x=data.index, y=["max availability",
                                         "max utilisation",
                                         "user defined" ])
    
    fig.update_yaxes(title_text="Profit (£)")
    fig.update_xaxes(title_text="Actual Utilisation Hours",
                     nticks=int(tot_avail_hrs+1),
                     range=[0,tot_avail_hrs])
    fig.add_vline(x=exp_util_hrs, fillcolor='black')
    fig.add_vrect(x0=0, x1=exp_util_hrs, 
              annotation_text="""
              If expecting to be under-utilised, <br> 
              weight bid towards availability to <br>
              increase profit""", 
              annotation_position="top right",
              fillcolor="blue", opacity=0.1, line_width=0)
    fig.add_vrect(x0=exp_util_hrs, x1=tot_avail_hrs, 
              annotation_text="""
              If expecting to be over-utilised, <br> 
              weight bid towards utilisation to <br>
              increase profit""", 
              annotation_position="top left",
              fillcolor="red", opacity=0.1, line_width=0)
    fig.show()
    return fig
        

if __name__ == "__main__":
    
    #%% Scenarios
    ## Break even
    # this calculates the utilisation bid and availability bid such that an
    # asset breaks even (i.e. 0 profit) no matter what number the actual 
    # utilisation hours are. This does not guarentee a bid will be under the
    # TCV or utilisation or availability ceiling prices. The cost matrix is 
    # generated with calc_costs function. 
    break_even_df = calc_costs(cap, break_even()[0], break_even()[1],
                              tot_fixed, tot_SRMC)[1]
    exp_profit = break_even_df["Profit (£)"][break_even_df["Utilisation hrs"]==exp_util_hrs].values[0]
    print("Break even profit: £{:0.2f}".format(exp_profit))
    
    ## Maximum availability scenario
    # recreates HO's max availability scenario. This ensures TCV is equal to
    # the TCV limit.
    bids = maxout_tcv(exp_util_hrs, 0.0)
    max_avail_df = calc_costs(cap, bids[0], bids[1],
                              tot_fixed, tot_SRMC)[1]
    exp_profit = max_avail_df["Profit (£)"][max_avail_df["Utilisation hrs"]==exp_util_hrs].values[0]
    print("Max availability profit: £{:0.2f}".format(exp_profit))
    
    ## Maximum utilisation scenario
    # recreates HO's max utilisation scenario. This ensures TCV is equal to
    # the TCV limit.
    bids = maxout_tcv(exp_util_hrs, 1.0)
    max_util_df = calc_costs(cap, bids[0], bids[1],
                              tot_fixed, tot_SRMC)[1]
    exp_profit = max_util_df["Profit (£)"][max_util_df["Utilisation hrs"]==exp_util_hrs].values[0]
    print("Max utilisation profit: £{:0.2f}".format(exp_profit))
    
    ## Middle weighting
    # This splits the total contract equally between availability and 
    # utilisation. This ensures TCV is equal to the TCV limit.
    bids = maxout_tcv(exp_util_hrs, 0.5)
    middle_df = calc_costs(cap, bids[0], bids[1],
                              tot_fixed, tot_SRMC)[1]
    exp_profit = middle_df["Profit (£)"][middle_df["Utilisation hrs"]==exp_util_hrs].values[0]
    print("Middle profit: £{:0.2f}".format(exp_profit))
    
    ## independent scenario
    # this ensures profit is independent of actual hours vs expected utilisation.
    bids = inde_maxTCV(exp_util_hrs)
    inde_df = calc_costs(cap, bids[0], bids[1],
                              tot_fixed, tot_SRMC)[1]
    exp_profit = inde_df["Profit (£)"][inde_df["Utilisation hrs"]==exp_util_hrs].values[0]
    print("Middle profit: £{:0.2f}".format(exp_profit))
    
    
    analysis = profit_vs_expected_util_vs_weight(weight=0.5)
    plot_exp_vs_act_heatmap_plotly(analysis, 0.5)
    plot_weight_vs_act_heatmap_plotly(analysis ,exp_util_hrs)
    
    ## independent scenario
    bids = inde_maxTCV(exp_util_hrs)
    profit_vs_actual_plotly(exp_util_hrs, bids[0], bids[1])
