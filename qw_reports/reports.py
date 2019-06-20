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
from io import StringIO

#XXX write out each import
from qw_reports.plot import *
from qw_reports.model import HierarchicalModel

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

def update_table(store, path, df):
    """
    """
    if path in store.keys():
        old_df = store.get(path)
        old_df = update_merge(old_df, df)
        store.put(path, old_df)

    else:
        store.put(path, df)


def process_nitrate(store, site):
    """Process an in situ measurement like nitrate or orthoP
    """
    constituent = 'NitrateSurr'
    db_path = '/said/{}/'.format(site['id'])
    iv_path = db_path + 'iv'
    df = store.get(iv_path)

    n_error = np.maximum(0.5, df[constituent]*.1)
    df[constituent+'_U90.0'] = df[constituent] + n_error
    df['NitrateSurr_L90.0'] = df.NitrateSurr - n_error
    #clip values below 0
    df['NitrateSurr_L90.0'] = np.maximum(0, df['NitrateSurr_L90.0'])

    update_table(store, iv_path, df)

def un_model(store, site, model_list, constituent):
    db_path = '/said/{}/'.format(site['id'])
    iv_path = db_path + 'iv'
    qwdata_path = db_path + 'qwdata'

    try:
        sur_df = store.get(iv_path)
        con_df = store.get(qwdata_path)

    except KeyError:
        print('site {} not found'.format(site['name']))

    model = HierarchicalModel(con_df, sur_df, model_list)

    predictions = model.get_prediction()
    sur_df = update_merge(sur_df, predictions)
    store.put(iv_path, sur_df)

    print(model.summary())
    #summary.to_csv('report/{}_{}_summary.csv'.format(site['name'],constituent))

class Report:
    def __init__(self, store, site, min_samples=10):
        self.store = store
        self.site = site
        self.summary_table = pd.DataFrame(columns=SUMMARY_COLS)
        self.min_samples = min_samples
        import pdb; pdb.set_trace()


    def run_model(self,model_list, constituent, match_time=30, min_samples=None):
        db_path = '/said/{}/'.format(self.site['id'])
        iv_path = db_path + 'iv'
        qwdata_path = db_path + 'qwdata'

        try:
            sur_df = self.store.get(iv_path)
            con_df = self.store.get(qwdata_path)

        except KeyError:
            print('site {} not found'.format(self.site['name']))
       
        if min_samples is None:
            min_samples = self.min_samples

        import pdb; pdb.set_trace()
        model = HierarchicalModel(con_df, sur_df, model_list, match_time, min_samples)
        predictions = model.get_prediction()
        sur_df = update_merge(sur_df, predictions)
        self.store.put(iv_path, sur_df)

        temp_csv = StringIO(model.summary().as_csv())
        model_summary = pd.read_csv(temp_csv, sep=',')
        model_summary.columns=['model','# obs','adjusted r^2','p-value']
        self.summary_table = self.summary_table.append(model_summary)
        #XXX update with class
        #print(model.summary())
        #summary.to_csv('report/{}_{}_summary.csv'.format(site['name'],constituent))


    def process_nitrate(self):
        """Process an in situ measurement like nitrate or orthoP
        """
        constituent = 'NitrateSurr'
        db_path = '/said/{}/'.format(self.site['id'])
        iv_path = db_path + 'iv'
        df = self.store.get(iv_path)

        n_error = np.maximum(0.5, df[constituent]*.1)
        df[constituent+'_U90.0'] = df[constituent] + n_error
        df['NitrateSurr_L90.0'] = df.NitrateSurr - n_error
        #clip values below 0
        df['NitrateSurr_L90.0'] = np.maximum(0, df['NitrateSurr_L90.0'])

        update_table(self.store, iv_path, df)

    def generate_plots(self):
        try:
            sur_df = self.store.get('/said/{}/iv'.format(self.site['id']))
            con_df = self.store.get('/said/{}/qwdata'.format(self.site['id']))

        except KeyError:
            print('site {} not found'.format(site['name']))

        plot_nitrate(con_df, sur_df, filename='plots/{}_nitrate.png'.format(self.site['name']))
        plot_ssc(con_df, sur_df, filename='plots/{}_ssc.png'.format(self.site['name']))
        plot_tp(con_df, sur_df, filename='plots/{}_tp.png'.format(self.site['name']))

    def run_all_models(self):
        """Generates a plots and model data for a given site
        """
        #self.process_nitrate()
        try:
            sur_df = self.store.get('/said/{}/iv'.format(self.site['id']))
            con_df = self.store.get('/said/{}/qwdata'.format(self.site['id']))

        except KeyError:
            print('site {} not found'.format(site['name']))


        #determine start and end for plots
        start_date, end_date = get_time_limit(sur_df, con_df)

        #update start and end according to user
        user_start = self.site.get('start')
        user_end   = self.site.get('end')

        if user_start:
            start_date = pd.to_datetime(user_start)

        if user_end:
            end_date = pd.to_datetime(user_end)


        #plot_ssc(ssc_model, filename='plots/{}_ssc.png'.format(site['name']),
        #         start_date=start_date, end_date=end_date)

        #append the model results to summary
        #summary_table= summary_table.append(model_row_summary(ssc_model))

        for directory in ['model_data','report']:
            try:
                os.stat(directory)
            except:
                os.mkdir(directory)

        #pp_model_list = import pdb; pdb.set_trace()[
        #    ['log(PP)',['log(Turb_HACH)']],
        #    ['log(PP)',['log(Turb_YSI)']]
        #]

        #self.run_model(pp_model_list, 'PP')

        no3_model_list = [
            ['Nitrate',['NitrateSurr']],
        ]
        self.run_model(no3_model_list, 'Nitrate')

        ssc_model_list = [
            ['log(SSC)',['log(Turb_HACH)']],
            ['log(SSC)',['log(Turb_YSI)']]
        ]
        self.run_model(ssc_model_list, 'SSC')

        tp_model_list = [
            ['log(TP)',['log(OrthoP)','log(Turb_HACH)']],
            ['log(TP)',['log(OrthoP)','log(Turb_YSI)']],
            ['log(TP)',['log(Turb_HACH)']],
            ['log(TP)',['log(Turb_YSI)']]
        ]
        self.run_model(tp_model_list, 'TP')

        #write ssc model report
        #reportfile = 'report/{}_ssc_report.txt'.format(site['name'])
        #with open(reportfile, 'w') as f:
        #    f.write(ssc_model.get_model_report().as_text())
        #summary_table= summary_table.append(model_row_summary(p_model1))
        #summary_table= summary_table.append(model_row_summary(p_model2))
        #plot_model(ssc_model, filename='plots/{}_ssc_model.png'.format(site['name']))
        #plot_phos(p_model1, p_model2, filename='plots/{}_tp.png'.format(site['name']),
        #          start_date=start_date, end_date=end_date)
        #plot_model(p_model1, filename='plots/{}_orthoP_model.png'.format(site['name']))
        #
        ## try to plot phosphate
        #try:
        #    phos_plot(con_data, sur_data, filename='plots/{}_p.png'.format(site['name']), title=site['name'],
        #             return_model=True)
        #except:
        #    print('phospate plot didnt work')
        #
        self.summary_table.to_csv('report/{}_model_summary.csv'.format(self.site['name']),
                            index=False)


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
