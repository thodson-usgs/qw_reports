import pandas as pd

from linearmodel.datamanager import DataManager
from qw_reports.analysis.loads import mean_annual_load
#from qw_reports.reports import make_phos_model

class ReportTable():
    """All children must contain a data object
    """

    def __init__(self, df):
        self.data = df

    def write(self, filename, fileformat):
        if fileformat=='string':
            self.data.to_string()
        else:
            pass

class SampleTable(ReportTable):
    def __init__(self, store_path, project_template):
        """
        """
        #import pdb; pdb.set_trace()
        #super.__init__
        self.store_path = store_path
        self.template = project_template
        self.columns = ['No. Obs.', 'Mean', 'Median']
        #self.columns = ['No. Obs.', 'No. Uncen. Obs', 'Mean', 'Median']

        self.data = pd.DataFrame(data=None, columns=self.columns)
        self.data.index.name = 'Site ID'


    def generate(self, constituent):
        for site in self.template.sites:
            df = self.get_samples(site['id'])
            series = df[constituent].dropna()

            self.data.loc[site['id'], 'Mean'] = series.mean()
            self.data.loc[site['id'], 'No. Obs.'] = series.count()
            self.data.loc[site['id'], 'Median'] = series.median()
        

    def get_samples(self, site_id):
        try:
            with pd.HDFStore(self.store_path, mode='r') as store:
                df = store.get('/said/{}/qwdata'.format(site_id))

        except KeyError:
            print('site {} not found'.format(site_id) )

        return df
 
class LoadTable(ReportTable):
    """
    """
    def __init__(self, store, project_template):
        """
        """
        #import pdb; pdb.set_trace()
        #super.__init__
        self.store = store
        self.template = project_template
        self.columns = ['Nitrate (lbs-N)','Phosphorous (lbs)', 'SSC (tons)']

        self.data = pd.DataFrame(data=None, columns=self.columns)
        self.data.index.name = 'Site ID'


    def generate(self, water_years=None):
        """
        water_years : list

        TODO: make this a method of a another class
        """

        if water_years:
            water_year_columns = water_years + ['mean']
            #water_years.append('mean')
            column_names = [self.columns, water_year_columns]
            columns = pd.MultiIndex.from_product(column_names)

        else:
            columns = self.columns

        data = pd.DataFrame(data=None, columns=columns)

        for site in self.template.sites:

            if water_years:
                entry = pd.Series(index=columns, name=site['id'])
                # Not working yet
                for year in water_years:
                    annual_entry = self.calculate_site_load(site['id'], wy=year)
                    for constituent in annual_entry.index:
                        entry.loc[constituent, year] = annual_entry.loc[constituent]

                mean_entry = self.calculate_site_load(site['id'], year_range=[water_years[0], water_years[-1]])
                for constituent in mean_entry.index:
                    entry.loc[constituent, 'mean'] = mean_entry.loc[constituent]

            else:
                entry = self.calculate_site_load(site['id'])

            data = data.append(entry)

        return data


    def calculate_site_load(self, site_id, wy=None, year_range=None):
        """
        TODO: make this a method of the station object
        """
        try:
            sur_df = self.store.get('/said/{}/iv'.format(site_id))
            con_df = self.store.get('/said/{}/qwdata'.format(site_id))

        except KeyError:
            print('site {} not found'.format(site_id))


        N = mean_annual_load(sur_df['Discharge'], sur_df['Nitrate'], wy=wy, year_range=year_range)
        SSC = mean_annual_load(sur_df['Discharge'],sur_df['SSC'], wy=wy, year_range=year_range, units='tons')
        TP = mean_annual_load(sur_df['Discharge'], sur_df['TP'], year_range=year_range, wy=wy)

        entry = pd.Series(data = [N, TP, SSC], index = self.columns, name= site_id)
        return entry

def discrete_data_table(df):
    """
    Create a data table summarizing discrete water quality data.

    Parameters
    ----------
    df : DataFrame
        Nwis dataframe of discrete water samples
    """
    cols = [col for col in df.columns if col.startswith('p')]
    cols = [col for col in cols if len(col)==6]
    out = df[cols]
    table = pd.DataFrame()
    
    table['n'] = out.count()
    table['min'] = out.min()
    table['max'] = out.max()
    table['median'] = out.median()
    table['25p'] = out.quantile(.25)
    table['75p'] = out.quantile(.75)
    
    return table

def data_range_table(iv, qwdata):
    """
    Create a data table summarizing the range of continous data
    """
    cols = iv.columns.tolist()
    cols.remove('site_no')
    iv = iv[cols]
    temp = pd.merge_asof(qwdata, iv, left_index=True, right_index=True,
                         tolerance=pd.Timedelta('120 min'))
    
    temp = temp[cols]
    

    out = pd.DataFrame()
    out.index.name = 'USGS parameter code'
    out['Min during discrete sample collection'] = temp.min()
    out['Max during discrete sample collection'] = temp.max()
    out['Min continuous data'] = iv.min()
    out['Max continuous data'] = iv.max()

    
    return out