import pandas as pd

from linearmodel.datamanager import DataManager
from qw_reports.analysis.loads import nitrate_load, phos_load, ssc_load
from qw_reports.reports import make_phos_model

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
            water_years.append('mean')
            column_names = [self.columns, water_years]
            columns = pd.MultiIndex.from_product(column_names)

        else:
            columns = self.columns

        data = pd.DataFrame(data=None, columns=self.columns)

        for site in self.template.sites:

            if water_years:
                entry = pd.Series(index=self.columns, name=site['id'])
                # Not working yet
                for year in water_years:
                    annual_entry = self.calculate_site_load(site['id'])
                    for constituent in annual_entry.index:
                        entry.loc[constituent, year] = annual_entry.loc[constituent]

            else:
                entry = self.calculate_site_load(site['id'])

            data = data.append(entry)

        return data


    def calculate_site_load(self, site_id, wy=None):
        """
        TODO: make this a method of the station object
        """
        try:
            sur_df = self.store.get('/said/{}/iv'.format(site_id))
            con_df = self.store.get('/said/{}/qwdata'.format(site_id))

        except KeyError:
            print('site {} not found'.format(site['name']))


        sur_data = DataManager(sur_df)
        con_data = DataManager(con_df)

        N = nitrate_load(sur_data, wy)
        SSC = ssc_load(con_data, sur_data, wy)

        p_model1, p_model2 = make_phos_model(con_data, sur_data)
        TP = phos_load(p_model1, p_model2, wy)

        entry = pd.Series(data = [N, TP, SSC], index = self.columns, name= site_id)
        return entry
