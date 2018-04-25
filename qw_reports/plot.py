"""
Plotting tools
"""

def plot_nitrate(con_data, sur_data, filename=None, title=None):
    """
    Note: this function should use a regression, based on the error of current nitrate sensors
    Args:
        df: df containing nitrate and discharge
        df2: df containing nitrate samples
    """
    df2 = con_data.get_data()
    df = sur_data.get_data()
    fig, (ax1, ax2, ax3) = plt.subplots(3, sharex=True, figsize=HP_FIGSIZE, dpi=DPI)
    fig.subplots_adjust(hspace=0)

    ax1.plot(df.index, df.Discharge, color='cornflowerblue', label='Discharge')
    ax2.plot(df.index,df.NitrateSurr, color='green', label='Nitrate probe observation')
    ax2.plot(df2.index,df2.Nitrate, marker='o', markerfacecolor='yellow', linewidth=0, label='Nitrate sample', ms=4)

    #error is the greater of 0.5mg/L or 10% of the measurement 
    n_error = np.maximum(0.5, df['NitrateSurr']*.1)
    df['NitrateSurr_u90'] = df.NitrateSurr + n_error
    df['NitrateSurr_l90'] = df.NitrateSurr - n_error
    #clip values below 0
    df['NitrateSurr_l90'] = np.maximum(0, df['NitrateSurr_l90'])

    ax2.fill_between(df.index, df.NitrateSurr_l90, df.NitrateSurr_u90, facecolor='gray',
                    edgecolor='gray', alpha=0.5, #interpolate=True,
                    label='90% Prediction Interval')

    load = df.Discharge * df.NitrateSurr * 0.00269688566 #XXX check this,
    load_u90 = df.Discharge * df.NitrateSurr_u90 * 0.00269688566 #XXX check this,
    load_l90 = df.Discharge * df.NitrateSurr_l90 * 0.00269688566 #XXX check this,

    ax3.plot(load.index, load.values, color='black', label='Load')
    ax3.fill_between(load.index, load_l90, load_u90, facecolor='gray',
                    edgecolor='gray', alpha=0.5, #interpolate=True,
                    label='90% Prediction Interval')

    if title:
        fig.suptitle(title)
    #set labels
    ax2.yaxis.tick_right()
    ax2.yaxis.set_label_position('right')
    ax1.set_ylabel('Streamflow, in cfs')
    ax2.set_ylabel('Nitrate, in mg/L')
    ax3.set_ylabel('Nitrate, in tons/day')

    #set grid
    for ax in (ax1, ax2, ax3):
        ax.grid(which='major',axis='x',linestyle='--')

    #format y-axis tick labels to include commas for thousands
    ax1.get_yaxis().set_major_formatter(tkr.FuncFormatter(lambda x, p: format(int(x),',')))
    ax2.yaxis.set_major_formatter(tkr.FormatStrFormatter('%.1f'))
    ax3.get_yaxis().set_major_formatter(tkr.FuncFormatter(lambda x, p: format(int(x),',')))


    #align yaxis labels
    #ax1.get_yaxis().set_label_coords(-.05, .5)
    #ax2.get_yaxis().set_label_coords(-.05, .5)
    #ax3.get_yaxis().set_label_coords(-.05, .5)

    #create legend(s), set figure size, save figure
    ax2.legend(loc='best', numpoints=1)
    #fig.set_size_inches(15,10)
    fig.autofmt_xdate()

    if filename:

        plt.savefig(filename, bbox_inches = 'tight')


def plot_model_ts(model, filename=None, title=None, color='blue',
                 constituent_name=None, units='mg/L'):
    """ Generate plots of discharge, predicted concentration and predicted load.

    Parameters
    ----------
    model : SurrogateRatingModel:

    constituent_name : string
        name of constituent (and units of measure) for plot labels.

    units : string
        units of measure for plot labels
    """

    #rating_model = make_ssc_model(con_data, sur_data)
    #need to get discharge
    response_var = model.get_constituent_variable_names()

    if not constituent_name:
        constituent_name = response_var

    df = sur_data.get_data() #FIXME where can i find discharge
    obs = model.get_model_dataset()

    predicted_data = model._model.predict_response_variable(explanatory_data=rating_model._surrogate_data,
                                                            raw_response=True,
                                                            bias_correction=True,
                                                            prediction_interval=True)


    fig, (ax1, ax2, ax3) = plt.subplots(3, sharex=True, figsize=HP_FIGSIZE, dpi=DPI)
    fig.subplots_adjust(hspace=0)

    # make plots
    ax1.plot(df.index, df['Discharge'])
    plot_predicted_ts(predicted_data, obs, response_var, ax2, color=color)
    plot_load_ts(predicted_data, df.Discharge, response_var, ax3)

    ax2.yaxis.tick_right()
    ax2.yaxis.set_label_position('right')
    ax1.set_ylabel('Streamflow, in cfs')
    ax2.set_ylabel('{}, in {}'.format(constituent_name, units)
    ax3.set_ylabel('{}, in tons/day'.format(constituent_name)

    #set grid
    for ax in (ax1, ax2, ax3):
        ax.grid(which='major',axis='x',linestyle='--')
        #/ax.xaxis.grid() # vertical lines

    ax1.get_yaxis().set_major_formatter(tkr.FuncFormatter(lambda x, p: format(int(x),',')))
    ax2.get_yaxis().set_major_formatter(tkr.FuncFormatter(lambda x, p: format(int(x),',')))
    ax3.get_yaxis().set_major_formatter(tkr.FuncFormatter(lambda x, p: format(int(x),',')))
    fig.autofmt_xdate()

    if title:
        fig.suptitle(title)

    if filename:

        fig.savefig(filename, bbox_inches='tight')

    else:
        fig.show()


def plot_model(model, filename=None, title=None):
    """Make plots to assess model fit.

    Parameters
    ----------
    model : SurrogateRatingModel

    filename : string
        path to save the file
    """

    plt.figure(figsize=MODEL_FIGSIZE)
    G = gridspec.GridSpec(3,2)
    ax1 = plt.subplot(G[0,0])
    ax2 = plt.subplot(G[0,1])
    ax3 = plt.subplot(G[1,0])
    ax4 = plt.subplot(G[1,1])
    ax5 = plt.subplot(G[-1, :])
    #fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2,2, figsize=(15,8))

    model.plot(plot_type='model_pred_vs_obs', ax=ax1)
    model.plot(plot_type='resid_probability', ax=ax2)
    model.plot(plot_type='resid_vs_fitted', ax=ax3)
    model.plot(plot_type='quantile', ax=ax4)
    model.plot(plot_type='resid_vs_time', ax=ax5)

    #plt.tight_layout()

    if title:
        plt.suptitle(title)

    if filename:
        plt.savefig(filename, bbox_inches = 'tight')


def plot_load_ts(data, discharge, response_var, ax, color='black'):
    """
    TODO: include discharge in same plot
    """

    LOAD_CONV = 0.00269688566 #XXX check
    L90 = '{}_L90.0'.format(response_var)
    U90 = '{}_U90.0'.format(response_var)

    load = discharge * data[response_var] * LOAD_CONV
    ax.plot(data.index, load, color=color)


def plot_predicted_ts(data, obs, response_var, ax, color='blue'):
    """
    """
    L90 = '{}_L90.0'.format(response_var)
    U90 = '{}_U90.0'.format(response_var)
    #obs = rating_model.get_model_dataset()

    ax.plot(data.index, data[response_var], color=color, 
            label='Predicted {}'.format(response_var))

    ax.fill_between(data.index, data[L90], data[U90], facecolor='gray',
                    edgecolor='gray', alpha=0.5, #interpolate=True,
                    label='90% Prediction Interval')

    #get observations
    included = obs[~obs['Missing'] & ~obs['Excluded']][response_var]
    missing  = obs[obs['Missing']][response_var]
    #con_obs = model_dataset[response_var]

    ax.plot(missing.index, missing.values, marker='o', label='Missing',
            markeredgecolor='black', markerfacecolor='None', linestyle='None',ms=4)
    ax.plot(included.index, included.values, marker='o', label='Included',
            markerfacecolor='yellow', markeredgecolor='black',linestyle='None',ms=4)

    ax.legend(loc='best') 
    #ax.set_ylabel('TP')

