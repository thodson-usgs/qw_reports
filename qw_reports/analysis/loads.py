#FLUX_CONV = 0.00269688566

# Conversions
mg2lbs = 2.20462e-6
l2cf = 1/0.0353137
min2sec = 60
lbs2ton = 0.0005
interval = 15 * min2sec

FLUX_CONV = mg2lbs * l2cf * interval

SAMPLES_PER_YEAR = 15 * 24 * 365.25 #min * hours * days

def load_ts(discharge, constituent, units='lbs'):
    """
    """
    df = discharge * constituent * FLUX_CONV

    if units = 'tons':
        df = df * lbs2ton

    return df

def mean_annual_load(discharge, constituent, units='lbs'):
    """
    Assumes a 15 minute interval
    """
    flux = load_ts(discharge, constituent, units)
    mean_15m_flux = flux.mean()

    return mean_15m_flux * SAMPLES_PER_YEAR

def wy_load(wy, discharge, constituent, units='lbs'):
    """
    """
    start = str(wy-1) + '-10-01'
    end   = str(wy) + '-09-30'

    flux = load_ts(discharge, constituent, units)
    return flux.loc[start:end].sum()

# OLD FUNCTIONS BELOW
def phos_load(model1, model2, wy=None):
    """
    """
    predicted_data_1 = model1._model.predict_response_variable(explanatory_data=model1._surrogate_data,
                                                            raw_response=True,
                                                            bias_correction=True,
                                                            prediction_interval=True)

    obs = model1.get_model_dataset()

    df = model1._surrogate_data.get_data()

    if model2:

        pvalue = model2._model._model.fit().f_pvalue

        if pvalue < 0.05:
            obs = obs[~obs['Missing']]
            obs2 = model2.get_model_dataset()
            obs2.drop(obs.index, axis=0) #drop anything thats in obs1 from obs2
            obs = obs.append(obs2).sort_index()


            predicted_data_2 = model2._model.predict_response_variable(explanatory_data=model2._surrogate_data,
                                                            raw_response=True,
                                                            bias_correction=True,
                                                            prediction_interval=True)

            predicted_data_1 = update_merge(predicted_data_2, predicted_data_1, na_only=True)

    discharge = df['Discharge']
    constituent = predicted_data_1['TP']

    if wy:
        return wy_load(wy, discharge, constituent)

    else:
        return mean_annual_load(discharge, constituent)


def nitrate_load(sur_data, wy=None):
    df = sur_data.get_data()
    discharge = df['Discharge']
    constituent = df['NitrateSurr']

    if wy:
        return wy_load(wy, discharge, constituent)

    else:
        return mean_annual_load(discharge, constituent)


def ssc_load(con_data, sur_data, wy=None):
    """calc ssc load for water year
    """
    df = sur_data.get_data()

    rating_model = make_ssc_model(con_data, sur_data)

    predicted_data = rating_model._model.predict_response_variable(explanatory_data=rating_model._surrogate_data,
                                                            raw_response=True,
                                                            bias_correction=True,
                                                            prediction_interval=True)
    discharge = df.Discharge
    constituent = predicted_data['SSC']

    if wy:
        return wy_load(wy, discharge, constituent, units='tons')

    else:
        return mean_annual_load(discharge, constituent, units='tons')
