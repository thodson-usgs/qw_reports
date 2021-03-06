import numpy as np

from hygnd.store import Station, HGStore, Collection, NWISStore
from hygnd.project import Project
from hygnd.munge import fill_iv_w_dv, filter_param_cd, interp_to_freq, update_merge, update_merge

#import table to lookup field names
from qw_reports.codes import pn
from qw_reports.model import HierarchicalModel

class SAIDProject(NWISStore):
    """Rename to ModelProject
    """
    def get_surrogatemodel(self, site_id):
        return SurrogateModel(site_id, self._path)

    def stage_sites(self,project_template,
                    approved_only=True):
        """
        Args:
            sites (list): list of dicts, each containing an id field

        XXX UPDATER THIS
        """
        self.template = Project(project_template)

        for site in self.template.sites:
            station_id = site['id']
            proxy_id = site.get('proxy')
            start = site.get('start')
            end = site.get('end')

            model = self.get_surrogatemodel(station_id)
            model.stage(proxy_id, start=start, end=end, approved_only=approved_only)


    def cleanup(self):
        """Delete said filesan
        """
        pass

class SurrogateModel(Collection):
    """
    XXX Note this is not a  table
    """
    def __init__(self, site_id, store_path):
        super().__init__(site_id, store_path, 'said')

    def run_model(self, constituent, model_list):
        model = HierachicalModel(con_df, sur_df, model_list)

        predictions = model.get_predictions()

        iv = self.get('iv')

        iv = update_merge(iv, predictions)
        self.put('iv')



    def stage(self, proxy_id=None,
              verbose=True,
              start=None,
              end=None,
              approved_only=True):
        """Prepare and store dataframes for input to SAID
        """
        if verbose:
            print(self._id)


        iv = self._apply_proxy('iv', proxy_id)
        dv = self._apply_proxy('dv', proxy_id)
        qwdata = self._apply_proxy('qwdata', proxy_id)

        #clean iv
        iv = iv.replace(-999999, np.NaN)
        dv = dv.replace(-999999, np.NaN)

        if approved_only == True:
            #iv = iv.replace('P,e','A').replace('P:e','A')
            iv = filter_param_cd(iv, 'A')#.replace(-999999, np.NaN)
            dv = filter_param_cd(dv, 'A')#.replace(-999999, np.NaN)

        if not iv.empty:
            # clip data to time interval
            iv = iv[start:end]
            dv = dv[start:end]
            qwdata = qwdata[start:end]

            iv = iv.drop_duplicates()
            iv = interp_to_freq(iv, freq=15, interp_limit=120)

            # fill in gaps in instantaneous discharge with daily estimates
            if '00060' in dv.columns:
                iv = fill_iv_w_dv(iv, dv, freq='15min', col='00060')

            # interpolate the OrthoPhosphate down to 15min intervals
            if '51289' in iv.columns:
                iv['51289'] = interp_to_freq(iv['51289'], freq=15,
                                            interp_limit=480)

        iv = format_surrogate_df(iv)
        qwdata = format_constituent_df(qwdata)
        # can't use grap sample for estimating DP, fix
        #qwdata['PP'] = qwdata['TP'] - qwdata['OrthoP']
        #what is being put
        self.put('iv', iv)
        self.put('qwdata',qwdata)

    def _apply_proxy(self, service, proxy_id):
        #import pdb; pdb.set_trace()
        with NWISStore(self._store_path) as store:

            #import pdb; pdb.set_trace()
            station = store.get_station(self.id())
            #try::w

            #    station = store.get_station(self.site_id)
##
            #except:
            #    print('station not found')



        if not proxy_id:
            return station.get(service)

        else:
            proxy = store.get_station(proxy_id)

        # check if the station even has a service
        try:
            df = station.get(service)

        except:
            return proxy.get(service)

        # if it does, check for the proxy
        try:
            proxy_df = proxy.get(service)
           #import pdb; pdb.set_trace()
            #return update_merge(df, proxy_df)
            return update_merge(df, proxy_df, na_only=True)

        except:
            return station.get(service)

#XXX these can be class methods
def format_constituent_df(df):
    check_params = ['p00665','p80154','p00631','p70331']
    con_params = []
    for i in check_params:
        if i in df.columns:
            con_params.append(i)

    out_df = df[con_params]
    out_cols = {param: pn[param] for param in con_params}
    return out_df.rename(columns=out_cols)

#duplicates previous function
def format_surrogate_df(df):
    check_params = ['00060','00095','63680_ysi','63680_hach','99133', '51289',
                    '00301','00400','00010']
    sur_params = []
    renamed_cols = rename_params(df.columns.to_list())
    df.columns = renamed_cols

    for i in check_params:
        if i in df.columns:
            sur_params.append(i)

    #import pdb; pdb.set_trace()
    #only get params in the df
    out_df = df[sur_params]
    out_cols = {param: pn[param] for param in sur_params}
    return out_df.rename(columns=out_cols)

def rename_params(param_list):
    check_params = ['00060','00095','63680_ysi','63680_hach','99133', '51289',
                    '00301','00400','00010']
    out_list = param_list.copy()
    #import pdb; pdb.set_trace()
    for param in check_params:
        i = index_containing_substring(param_list, param)
        if i is not None:
            out_list[i] = param
    return out_list
            

def index_containing_substring(the_list, substring):
    for i, s in enumerate(the_list):
        if substring in s and '_cd' not in s:
            return i
    return None

