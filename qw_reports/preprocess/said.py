from hygnd.store import Station, HGStore, Table, NWISStore
from hygnd.project import Project
from hygnd.munge import fill_iv_w_dv, filter_param_cd, interp_to_freq, update_merge, update_merge

#import table to lookup field names
from qw_reports.codes import pn

class SaidProject(NWISStore):


    def stage_sites(self,project_template):
        """
        Args:
            sites (list): list of dicts, each containing an id field

        XXX UPDATER THIS
        """
        self.template = Project(project_template)

        for site in self.template.sites:
            station = self.get_station(site['id'])
            proxy_id = site.get('proxy')

            if proxy_id:
                proxy = self.get_station(proxy_id)

            else:
                proxy = None

            station = SaidStation(station, proxy)
            station.stage()


    def cleanup(self):
        """Delete said files
        """
        pass


class SaidStation(Table):

    def __init__(self, Station, Proxy=None):
        """Fills data in with station first, then proxy
        """
        self._id = Station.id()
        self._store_path = Station.store_path
        self._root = 'said'
        self.station = Station
        self.proxy = Proxy



    def stage(self, verbose=True):
        """Prepare and store dataframes for input to SAID
        """
        if verbose:
            print(self._id)


        iv = self._apply_proxy('iv')
        dv = self._apply_proxy('dv')
        qwdata = self._apply_proxy('qwdata')


        #clean iv
        iv = iv.replace('P,e','A').replace('P:e','A')

        iv = filter_param_cd(iv, 'A')#.replace(-999999, np.NaN)
        dv = filter_param_cd(dv, 'A')#.replace(-999999, np.NaN)

        iv = interp_to_freq(iv, freq=15, interp_limit=120)

        if '00060' in iv.columns:
            iv = fill_iv_w_dv(iv, dv, freq='15min', col='00060')

        #interpolate the OrthoPhosphate down to 15min intervals
        if '51289' in iv.columns:
            iv['51289'] = interp_to_freq(iv['51289'], freq=15,
                                        interp_limit=480)

        iv = format_surrogate_df(iv)
        qwdata = format_constituent_df(qwdata)

        #what is being put
        self.put('iv', iv)
        self.put('qwdata',qwdata)

    def _apply_proxy(self, service):
        #import pdb; pdb.set_trace()

        if not self.proxy:
            return self.station.get(service)

        # check if the station even has a service
        try:
            df = self.station.get(service)

        except:
            return self.proxy.get(service)

        # if it does, check for the proxy
        try:
            proxy_df = self.proxy.get(service)
            #import pdb; pdb.set_trace()
            #return update_merge(df, proxy_df)
            return update_merge(df, proxy_df, na_only=True)

        except:
            return self.station.get(service)



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
    check_params = ['00060','00095','63680_ysi','63680_hach','99133', '51289']
    sur_params = []
    for i in check_params:
        if i in df.columns:
            sur_params.append(i)

    #only get params in the df
    out_df = df[sur_params]
    out_cols = {param: pn[param] for param in sur_params}
    return out_df.rename(columns=out_cols)
