IL_nutrient_network = {
    'project' : 'Illinois Nutrient Monitoring Network',

    'sites': [
        {'id':'03339000',
         'name':'Vermillion',
         'location':'Danville',
         'start':'2015-02-24'},

        {'id':'03346500',
         'name':'Embarras',
         'start':'2015-11-01'},

        {'id':'03381495',
         'name':'LittleWabash',
         'start':'2015-11-01',
        'proxies':{'00060':'03381500'}},

        {'id':'05446500',
         'name':'Rock',
         'start':'2015-08-20'},

        {'id':'05447500', 'name':'Green', 'start':'2015-08-19'},

        {'id':'05586300', 'name':'Illinois', 'start':'2012-06-02',
        'proxies':{'00060':'05586100'}},

        {'id':'05595000', 'name':'Kaskaskia', 'start':'2015-09-17'},

        {'id':'05599490', 'name':'BigMuddy', 'start':'2015-10-01'},#Murphysboro
    ],

    'proxy_sites' : [

        {'id': '03381500',
         'name':'LittleWabashQ',
         'start':'2015-11-01'},

        {'id':'05586100',
         'name':'IllinoisQ',
         'start':'2012-06-02'},
    ]
}


said_files = {
    'Surrogate': { 
        #'00065' : 'Gage Height',
        '00060' : 'Discharge',
        '00095' : 'Spec Cond',
        '63680' : 'Turb',
        '99133' : 'NitrateSurr',
        '51289' : 'OrthoP'
    },

    'DailyQ' : {
        '00060' : 'Discharge',
    }
}

nwis_to_said = {
    'site_no' : 'Site',
    'datetime':'DateTime',
    '00065':'Gage Height',
    '00095':'Spec Cond',
    '63680_ysi' : 'Turb_YSI',
    '63680_hach': 'Turb_HACH',
    '99133': 'NitrateSurr',
    '51289': 'OrthoP',
    '00060': 'Discharge',
    'p80154': 'SSC',
    'p00665': 'TP',
    'p00631': 'Nitrate',
    'p70331': '<62'
}

# dictionary of parameter names same as nwis_to_said
pn = {
    'site_no' : 'Site',
    'datetime':'DateTime',
    '00065':'Gage Height',
    '00095':'Spec Cond',
    '63680_ysi' : 'Turb_YSI',
    '63680_hach': 'Turb_HACH',
    '99133': 'NitrateSurr',
    '51289': 'OrthoP',
    '00060': 'Discharge',
    'p80154': 'SSC',
    'p00665': 'TP',
    'p00631': 'Nitrate',
    'p70331': '<62'
}

pc = {
    'SSC':'p80154',
    'Turb_YSI':'63680_ysi',
    
}
