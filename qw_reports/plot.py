"""
Plotting tools
"""

import matplotlib.ticker as tkr
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib as mpl

import numpy as np

from hygnd.munge import update_merge

DPI = 150
HP_FIGSIZE = (7.5,5) #Half page figsize
MODEL_FIGSIZE = (7.5,9)

LOAD_FACTOR = 0.00269688566 #XXX check this, 

MARKER_SIZE = 3

mpl.rcParams['lines.markeredgewidth'] = 0.5
mpl.rcParams['lines.markersize'] = MARKER_SIZE
mpl.rcParams['lines.linewidth'] = 1
mpl.rcParams['font.size'] = 8
mpl.rcParams.update({'font.size':8})


def plot_dp(con_data, sur_data, filename=None, title=None,
           legend=None,
           start_date=None,
           end_date=None):
    """TODO: needs updating
    """

    df2 = con_data.get_data()
    df = sur_data.get_data()
    fig, (ax1, ax2, ax3) = plt.subplots(3, sharex=True, figsize=HP_FIGSIZE, dpi=DPI)
    fig.subplots_adjust(hspace=0)

    ax1.plot(df.index, df.Discharge, color='cornflowerblue', label='Discharge')
    ax2.plot(df.index,df.OrthoP, color='maroon', label='In-situ PO_4-P')
    ax2.plot(df2.index,df2.OrthoP, marker='o', markerfacecolor='Yellow',
             markeredgecolor='black', linewidth=0, label='Sample')

    plot_load_ts(df, df.Discharge, 'OrthoP', ax=ax3)
    format_load_plot(fig, 'DP (mg/L-P)', 'DP (tons/day)',
                     start_date=start_date,
                     end_date=end_date,
                     title=title, legend=None, filename=filename)

def format_load_plot(fig,
                     concentration_label,
                     load_label,
                     start_date=None,
                     end_date=None,
                     title=None, legend=False, filename=None):
    if title:
        fig.suptitle(title)
    #set labels
    ax1, ax2, ax3 = fig.axes
    ax2.yaxis.tick_right()
    ax2.yaxis.set_label_position('right')
    ax1.set_ylabel('Streamflow (cfs)')
    ax2.set_ylabel(concentration_label)
    ax3.set_ylabel(load_label)

    #set grid
    for ax in fig.axes:
        ax.grid(which='major',axis='x',linestyle='--')
        ax.set_xlim([start_date, end_date])

    #format y-axis tick labels to include commas for thousands
    ax1.get_yaxis().set_major_formatter(tkr.FuncFormatter(lambda x, p: format(int(x),',')))
    ax2.yaxis.set_major_formatter(tkr.FormatStrFormatter('%.1f'))
    ax3.get_yaxis().set_major_formatter(tkr.FuncFormatter(lambda x, p: format(int(x),',')))


    #create legend(s), set figure size, save figure
    if legend:
        ax2.legend(loc='best', numpoints=1)
    #fig.set_size_inches(15,10)
    fig.autofmt_xdate()

    if filename:
        plt.savefig(filename, bbox_inches = 'tight')


def plot_discharge_ts(discharge, ax, color='cornflowerblue'):
    ax.plot(discharge.index, discharge.values, color=color)


def plot_load_ts(df, constituent_col, discharge_col, ax, color='black'):
    """
    TODO: include discharge in same plot
    """

    LOAD_CONV = LOAD_FACTOR #XXX check
    #L90 = '{}_L90.0'.format(response_var)
    #U90 = '{}_U90.0'.format(response_var)

    load = df[discharge_col] * df[constituent_col] * LOAD_CONV
    ax.plot(df.index, load, color=color)


def plot_concentration_ts(df, constituent_col, ax, obs=None, color='blue',
                     missing=False, excluded=False, legend=False,
                     highlight_gaps=False):
    """
    """
    L90 = '{}_L90.0'.format(constituent_col)
    U90 = '{}_U90.0'.format(constituent_col)
    #obs = rating_model.get_model_dataset()

    ax.plot(df.index, df[constituent_col], color=color,
            label='Predicted {}'.format(constituent_col))

    ax.fill_between(df.index, df[L90], df[U90], facecolor='gray',
                    edgecolor='gray', alpha=0.5, #interpolate=True,
                    label='90% Prediction Interval')
    ylim = ax.get_ylim()

    if highlight_gaps:
        ax.fill_between(df.index, ylim[0], ylim[1],
                        where= df[constituent_col].isna(),
                        facecolor='red', alpha=0.1)


    #plot included observations
    if obs is not None:
        ax.plot(obs.index, obs.values, marker='o', label='Sample',
                markerfacecolor='Yellow', markeredgecolor='black', linestyle='None')

    if legend:
        ax.legend(loc='best')
    #ax.set_ylabel('TP')

def plot_tp(con_df, sur_df, filename=None, title=None,
             start_date=None, end_date=None):


    fig, (ax1, ax2, ax3) = plt.subplots(3, sharex=True, figsize=HP_FIGSIZE, dpi=DPI)
    fig.subplots_adjust(hspace=0)

    plot_discharge_ts(sur_df['Discharge'], ax=ax1)

    plot_concentration_ts(sur_df, 'TP', ax2, obs=con_df['TP'], color='maroon')

    plot_load_ts(sur_df, 'TP','Discharge', ax3)

    format_load_plot(fig, 'TP (mg/L-P)', 'TP (tons/day)',
                     start_date=start_date, end_date=end_date,
                     title=title, legend=None, filename=filename)

def plot_ssc(con_df, sur_df, filename=None, title=None, start_date=None, end_date=None):
    fig, (ax1, ax2, ax3) = plt.subplots(3, sharex=True, figsize=HP_FIGSIZE, dpi=DPI)
    fig.subplots_adjust(hspace=0)

    plot_discharge_ts(sur_df['Discharge'], ax=ax1)

    plot_concentration_ts(sur_df, 'SSC', ax2, obs=con_df['SSC'], color='olive')

    plot_load_ts(sur_df, 'SSC','Discharge', ax3)

    format_load_plot(fig, 'SSC (mg/L)', 'SSC (tons/day)',
                     start_date=start_date, end_date=end_date,
                     title=title, legend=None, filename=filename)

def plot_nitrate(con_df, sur_df, filename=None, title=None, start_date=None, end_date=None):
    fig, (ax1, ax2, ax3) = plt.subplots(3, sharex=True, figsize=HP_FIGSIZE, dpi=DPI)
    fig.subplots_adjust(hspace=0)

    plot_discharge_ts(sur_df['Discharge'], ax=ax1)

    plot_concentration_ts(sur_df, 'Nitrate', ax2, obs=con_df['Nitrate'], color='green')

    plot_load_ts(sur_df, 'Nitrate','Discharge', ax3)

    format_load_plot(fig, 'Nitrate (mg/L-N)', 'Nitrate (tons/day)',
                     start_date=start_date, end_date=end_date,
                     title=title, legend=None, filename=filename)
