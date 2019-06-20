import matplotlib.ticker as tkr
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib as mpl

from math import ceil


from said.surrogatemodel import SurrogateRatingModel
from linearmodel.datamanager import DataManager

from statsmodels.iolib.summary import Summary
from statsmodels.iolib.table import SimpleTable

from linearmodel import stats, model as saidmodel


from hygnd.munge import update_merge

import os
import numpy as np
import pandas as pd

#XXX write out each import
from qw_reports.plot import *

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


class HierarchicalModel:
    """Class combines mulitple surrogate models and uses the best among
    them to generate predicitons.

    Examples
    --------
    Given DataManagers containg constituent (con_data) and surrogates (sur_data),
    and columns: 'SSC', 'Turb', 'Discharge', initialize a HierarchicalModel as follows.

    >>> model_list = [
        ['SSC', ['log(Turb)', 'log(Discharge']],
        ['SSC', ['log(Turb)']]

    >>> model = HierarchicalModl(con_data, sur_data,
                                 model_list=model_list)

    >>> model.summary()

    TODO
    ----
    -model skill is currently assessed by r^2. Include alternative metrics
    like tightest prediction interval.
    -improve interface with linearmodel to a avoid reliance on
    private methods.

   """

    def __init__(self, constituent_df, surrogate_df, model_list,
                 min_samples=10, max_extrapolation=0.1, match_time=30,
                 p_thres=0.05):
        """ Initialize a HierarchicalModel


        :param constituent_data:
        :type constituent_data: DataManager
        :param surrogate_data:
        :type surrogate_data: DataManger
        :param model_list:
        """
        #HierarchicalModel.pad_data(surrogate_df) 
        self._surrogate_data = DataManager(surrogate_df)
        self._constituent_data = DataManager(constituent_df)

        self._model_list = model_list

        self.match_time=match_time
        self.max_extrapolation= max_extrapolation
        self.min_samples = min_samples
        self.p_thres = p_thres


        self._create_models()

    @staticmethod
    def pad_data(sur_df):
        """ Makes surrogates non negative and > 0
        TOOD: only pad data subject to log transformation
        TODO: only use positive data in mean
        """
        for col in sur_df:
            sur_df.loc[sur_df[col] <= 0, col] = sur_df[col].mean() * 0.001

    
    def _create_models(self):
        """Populate a HierarchicalModel with SurrogateRatingModel objects.

        Called by __init__.

        """
        self._set_variables_and_transforms()
        #specify (n) the number of models managed within the instance
        n = len(self._model_list)
        self._models = [None for i in range(n)]

        #initialize arrays to store p values, nobs and rsquared of each model
        self._pvalues = np.zeros(n)
        self._nobs = np.zeros(n)
        self._rsquared = np.zeros(n)
        #import pdb; pdb.set_trace()
        for i in range(n):
            #FIXME try to fix this by taking a the set of surrogate_variables
            surrogate_set = list(set(self._surrogates[i])) #removes duplicates
            try: 
                self._models[i] = SurrogateRatingModel(self._constituent_data,
                                                       self._surrogate_data,
                                                       constituent_variable = self._constituent,
                                                       surrogate_variables = surrogate_set,
                                                       match_method = 'nearest',
                                                       #should set match in init
                                                       match_time = self.match_time)
                for surrogate in surrogate_set:
                    #ceate an index of each occurance of the surrogate
                    surrogate_transforms = [self._surrogate_transforms[i][j] for j,v in enumerate(self._surrogates[i]) if v == surrogate]
                    #set the surrogate transforms based on the surrogate index
                    #XXX testing if else
                    #if len(surrogate_transforms) != 1: #XXX consider using >
                    #    raise ValueError('Only works with single surrogate transform')
                    #else:
                    #    surrogate_transforms = surrogate_transforms[0]
                    self._models[i].set_surrogate_transform(surrogate_transforms, surrogate_variable=surrogate)
    
                #set transforms for each surrogate
                #for surrogate in self._surrogates[i]:
                #    self._models[i].set_surrogate_transform(self._surrogate_transforms[i], surrogate_variable=surrogate)
                self._models[i].set_constituent_transform(self._constituent_transforms[i])
    
                #FIXME depends on private methods
                res = self._models[i]._model._model.fit()
                self._pvalues[i] = res.f_pvalue
                self._rsquared[i] = res.rsquared_adj
                self._nobs[i] = res.nobs
                #TODO check transforms
    
            #XXX added this as well as try except 2019/02/07
            #while None in self._models:
            #    self._models.remove(None)
            except ValueError:
                self._models[i] = None

        good_i = [i for i, x in enumerate(self._models) if x is not None]
        while None in self._models:
            self._models.remove(None)

        self._pvalues = self._pvalues[good_i]
        self._nobs = self._nobs[good_i]
        self._rsquared = self._rsquared[good_i]



    def _set_variables_and_transforms(self):
        """Parses surrogates, constituent, and their transforms.

        This function is a part of HierarchicalModel's init.
        """
        self._constituent = None
        self._constituent_transforms = []

        self._surrogates = []
        self._surrogate_transforms = []

        temp_constituents = []

        for constituent, surrogates in self._model_list:

            constituent_transform, raw_constituent = saidmodel.find_raw_variable(constituent)
            temp_constituents.append(raw_constituent)
            self._constituent_transforms.append(constituent_transform)

            # make temporary list to store surrogates before appending them
            sur_temp = []
            sur_trans_temp = []
            for surrogate in surrogates:
                surrogate_transform, raw_surrogate = saidmodel.find_raw_variable(surrogate)
                sur_temp.append(raw_surrogate)
                sur_trans_temp.append(surrogate_transform)

            self._surrogates.append(sur_temp)
            self._surrogate_transforms.append(sur_trans_temp)

        # check that there is one and only one constituent

        temp_constituents =  list(set(temp_constituents))

        if len(temp_constituents) != 1:
            raise Exception('Only one raw constituent allowed')

        self._constituent = temp_constituents[0]


    def get_prediction(self, explanatory_data=None):
        """Use the HierarchicalModel to make a prediction based on explanatory_data.

        If no explanatory data is given, the prediction is based on the data uses to initialize
        the HierarchicalModel

        :param explanatory_data:
        :return:
        """
        #rank models by r2, starting with the lowest (worst)
        model_ranks = self._rsquared.argsort()
        #model_ranks = range(len(model_list))

        for i in model_ranks:
            #skip models that aren't robust
            #TODO replace hard nobs thresh with thres * (surrogatecount + 1)
            if self._nobs[i] < self.min_samples or self._pvalues[i] > self.p_thres:
                pass #continue
            elif self._rsquared[i] == 0: #skip models that had no data
                continue

            elif type(explanatory_data) is type(None):
                explanatory_data = self._models[i]._surrogate_data
            
            prediction = self._models[i]._model.predict_response_variable(
                explanatory_data = explanatory_data,
                raw_response=True,
                bias_correction=True,
                prediction_interval=True)
            try:
                hierarchical_prediction.update(prediction)

            except:
                hierarchical_prediction = prediction

        return hierarchical_prediction
        

    def plot_model_pred_vs_obs(self, axes=None):
        n = len(self._models)
        cols = min(n, 2)
        rows = ceil(n/cols)

        if axes is None:
            fig, axes = plt.subplots(rows, cols, sharex=True, sharey=True)
        for ax, model in zip(axes.flatten(), self._models):
            model._model._plot_model_pred_vs_obs(ax)
            ax.set_title('+'.join(model._model.get_explanatory_variables()))
            if not ax.is_last_row():
                ax.set_xlabel('')

            if not ax.is_first_col():
                ax.set_ylabel('')


    def summary(self):
        """Generates a summary table with basic statistics for each submodel.

        TODO: immprove interface with linearmodel, so that this doesn't rely on
        private methods.
        """
        summary = Summary()
        headers = ['Model form', 'Observations', 'Adjusted r^2',
                   'P value']
        table_data = []
        # for each model
        for model in self._models:
            row = []
            # populate row with model statistics
            res = model._model._model.fit()
            row.append(model._model.get_model_formula())
            row.append( round(res.nobs) )
            row.append( round(res.rsquared_adj, 2))
            row.append( format(res.f_pvalue, '.1E'))
            # append the row to the data
            table_data.append(row)

        # create table with data and headers:w
        table = SimpleTable(data=table_data, headers=headers)
        # add table to summary
        summary.tables.append(table)

        return summary

    
def predictions_to_txt(model, site):
    predicted_data = model._model.predict_response_variable(explanatory_data=model._surrogate_data,
                                                           raw_response=True,
                                                           bias_correction=True,
                                                           prediction_interval=True)
    constituent = model2.get_constituent_variable()
    predicted_data.to_csv('model_data/{}_{}.csv',format('site',constituent))

