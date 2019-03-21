import matplotlib.ticker as tkr
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib as mpl

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

def model_TP(con_data, sur_data):

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
        #pdb; pdb.set_trace()
        # move rejection elsewhere
        #if pvalue > 0.05 or pvalue < 0 or np.isnan(pvalue):
        #    rating_model_2 = None
    except:#
        rating_model_2 = None

    return rating_model_1, rating_model_2


def model_pp(con_df, sur_df):
    con_data = DataManager(sur_df)
    sur_data = DataManager(con_df)

    con_data['PP'] = con_data['TP']-con_data['OrthoP']

    rating_model = SurrogateRatingModel(con_data,
                                        sur_data,
                                        constituent_variable= 'PP',
                                        surrogate_variables= ['Turb_YSI'],
                                        match_method='nearest', match_time=30)

    rating_model.set_surrogate_transform(['log10'], surrogate_variable='Turb_YSI')
    rating_model.set_constituent_transform('log10')

    predicted_data = rating_model._model.predict_response_variable(explanatory_data=rating_model._surrogate_data,
                                                            raw_response=True,
                                                            bias_correction=True,
                                                            prediction_interval=True)


    return predicted_data


#XXX: procedure for creating fixed interval record
def model_ssc(con_df, sur_df, site=None, summary=False):
    con_data = DataManager(sur_df)
    sur_data = DataManager(con_df)

    rating_model = SurrogateRatingModel(con_data,
                                        sur_data,
                                        constituent_variable= 'SSC',
                                        surrogate_variables= ['Turb_YSI'],
                                        match_method='nearest', match_time=30)

    rating_model.set_surrogate_transform(['log10'], surrogate_variable='Turb_YSI')
    rating_model.set_constituent_transform('log10')

    predicted_data = rating_model._model.predict_response_variable(explanatory_data=rating_model._surrogate_data,
                                                            raw_response=True,
                                                            bias_correction=True,
                                                            prediction_interval=True)


    if summary and site:
        predictions_to_txt(rating_model, site)

    return predicted_data

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
        self._surrogate_data = DataManager(surrogate_df)
        self._constituent_data = DataManager(constituent_df)

        self._model_list = model_list

        self.match_time=match_time
        self.max_extrapolation= max_extrapolation
        self.min_samples = min_samples
        self.p_thres = p_thres



        self._create_models()


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
            except:
                pass

        #XXX added this as well as try except 2019/02/07
        #while None in self._models:
        #    self._models.remove(None)



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
            if self._nobs[i] < 10 or self._pvalues[i] > self.p_thres:
                continue
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



class TurbiditySurrogateModel:
    """
    TODO expand to include other turbidity data sources
    """
    def __init__(self, con_data, sur_data):
        rating_model = SurrogateRatingModel(con_data,
                                            sur_data,
                                            constituent_variable= 'SSC',
                                            surrogate_variables= ['Turb_YSI'],
                                            match_method='nearest', match_time=30)

        rating_model.set_surrogate_transform(['log10'], surrogate_variable='Turb_YSI')
        rating_model.set_constituent_transform('log10')

    def predict(explanatory_data=None):
        if explanatory_data is None:
            explanatory_data = self.rating_model._surrogate_data

        predicted_data = rating_model._model.predict_response_variable(explanatory_data=explanatory_data,
                                                            raw_response=True,
                                                            bias_correction=True,
                                                            prediction_interval=True)



    

def predictions_to_txt(model, site):
    predicted_data = model._model.predict_response_variable(explanatory_data=model._surrogate_data,
                                                           raw_response=True,
                                                           bias_correction=True,
                                                           prediction_interval=True)
    constituent = model2.get_constituent_variable()
    predicted_data.to_csv('model_data/{}_{}.csv',format('site',constituent))

