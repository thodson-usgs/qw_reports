import matplotlib.ticker as tkr
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib as mpl

from said.surrogatemodel import SurrogateRatingModel
from linearmodel.datamanager import DataManager
from hygnd.munge import update_merge

import os
import numpy as np
import pandas as pd

#XXX write out each import
from qw_reports.plot import *

#MARK_SIZE = 3 # not used
SUMMARY_COLS = ['model','# obs','adjusted r^2','p-value']
HP_FIGSIZE = (7.5,5) #Half page figsize
DPI = 150
MODEL_FIGSIZE = (7.5,9)

mpl.rcParams.update({'font.size':8})
mpl.rcParams['lines.linewidth'] = 1

#FLUX_CONV = 0.00269688566

# Conversions
mg2lbs = 2.20462e-6
l2cf = 1/0.0353137
min2sec = 60
lbs2ton = 0.0005
interval = 15 * min2sec

FLUX_CONV = mg2lbs * l2cf * interval
def get_time_limit(df1, df2):
    start = min(df1.dropna(how='all').index[0], df2.dropna(how='all').index[0])
    end = max(df1.dropna(how='all').index[-1], df2.dropna(how='all').index[-1])
    return start, end

def gen_report(store, site):
    """Generates a plots and model data for a given site
    """
    try:
        sur_df = store.get('/said/{}/iv'.format(site['id']))
        con_df = store.get('/said/{}/qwdata'.format(site['id']))

    except KeyError:
        print('site {} not found'.format(site['name']))

    sur_data = DataManager(sur_df)
    con_data = DataManager(con_df)

    summary_table = pd.DataFrame(columns=SUMMARY_COLS)

    #determine start and end for plots
    start_date, end_date = get_time_limit(sur_df, con_df)

    plot_nitrate(con_data, sur_data, filename='plots/{}_nitrate.png'.format(site['name']),
                start_date=start_date, end_date=end_date)

    ssc_model = make_ssc_model(con_data, sur_data)

    plot_ssc(ssc_model, filename='plots/{}_ssc.png'.format(site['name']),
             start_date=start_date, end_date=end_date)

    #append the model results to summary
    summary_table= summary_table.append(model_row_summary(ssc_model))

    for directory in ['model_data','report']:
        try:
            os.stat(directory)
        except:
            os.mkdir(directory)

    #output model input data
    df = ssc_model.get_model_dataset()
    df.to_csv('model_data/{}_ssc.csv'.format(site['name']))

    #output prediction

    #write ssc model report
    reportfile = 'report/{}_ssc_report.txt'.format(site['name'])
    with open(reportfile, 'w') as f:
        f.write(ssc_model.get_model_report().as_text())

    p_model1, p_model2 = make_phos_model(con_data, sur_data)

    #df_p1 = p_model1.get_model_dataset()
    predicted_p = p_model1._model.predict_response_variable(explanatory_data=p_model1._surrogate_data,
                                                            raw_response=True,
                                                            bias_correction=True,
                                                            prediction_interval=True)

    predicted_p.to_csv('model_data/{}_tp.csv'.format(site['name']))

    summary_table= summary_table.append(model_row_summary(p_model1))
    summary_table= summary_table.append(model_row_summary(p_model2))


    plot_model(ssc_model, filename='plots/{}_ssc_model.png'.format(site['name']))

    plot_phos(p_model1, p_model2, filename='plots/{}_tp.png'.format(site['name']),
              start_date=start_date, end_date=end_date)

    plot_model(p_model1, filename='plots/{}_orthoP_model.png'.format(site['name']))
    #
    ## try to plot phosphate
    #try:
    #    phos_plot(con_data, sur_data, filename='plots/{}_p.png'.format(site['name']), title=site['name'],
    #             return_model=True)
    #except:
    #    print('phospate plot didnt work')
    #
    summary_table.to_csv('report/{}_model_summary.csv'.format(site['name']),
                        index=False)


    #write loads to file



def make_phos_model(con_data, sur_data):

    rating_model_1 = SurrogateRatingModel(con_data,
                                          sur_data,
                                          constituent_variable='TP',
                                          surrogate_variables=['Turb_YSI'],#,'Discharge'],
                                          match_method='nearest',
                                          match_time=30)

    rating_model_1.set_surrogate_transform(['log10'], surrogate_variable='Turb_YSI')
    rating_model_1.set_constituent_transform('log10')


    try:
        rating_model_2 = SurrogateRatingModel(con_data,
                                          sur_data,
                                          constituent_variable='TP',
                                          surrogate_variables=['OrthoP','Turb_YSI'],
                                          match_method='nearest',
                                          match_time=30)

        rating_model_2.set_surrogate_transform(['log10'], surrogate_variable='Turb_YSI')
        #rating_model_2.set_surrogate_transform(['log10'], surrogate_variable='OrthoP')
        rating_model_2.set_constituent_transform('log10')



        pvalue = rating_model_2._model._model.fit().f_pvalue
        #reject insignificant models
        #import pdb; pdb.set_trace()
        # move rejection elsewhere
        #if pvalue > 0.05 or pvalue < 0 or np.isnan(pvalue):
        #    rating_model_2 = None
    except:#
        rating_model_2 = None

    return rating_model_1, rating_model_2


#XXX: procedure for creating fixed interval record
def make_ssc_model(con_data, sur_data):

    rating_model = SurrogateRatingModel(con_data,
                                        sur_data,
                                        constituent_variable= 'SSC',
                                        surrogate_variables= ['Turb_YSI'],
                                        match_method='nearest', match_time=30)

    rating_model.set_surrogate_transform(['log10'], surrogate_variable='Turb_YSI')
    rating_model.set_constituent_transform('log10')
    return rating_model

def model_row_summary(model):
    if not model:
        return None

    res = model._model._model.fit()
    columns = SUMMARY_COLS
    row = [[
        model._model.get_model_formula(),
        res.nobs,
        res.rsquared_adj,
        res.f_pvalue
    ]]

    return pd.DataFrame(row, columns=columns)


def predictions_to_txt(model, site):
    predicted_data = model._model.predict_response_variable(explanatory_data=model._surrogate_data,
                                                           raw_response=True,
                                                           bias_correction=True,
                                                           prediction_interval=True)
    constituent = model2.get_constituent_variable()
    predicted_data.to_csv('model_data/{}_{}.csv',format('site',constituent))

