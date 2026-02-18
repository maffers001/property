import numpy as np
import pandas as pd
import os.path
import shutil
import datetime
from dateutil.rrule import rrule, MONTHLY

#generated_path = 'E:\\dtuklaptop\\e\\Users\\Mat\\python\\data\\property\\checked\\'
#tcy_path=r'E:\\dtuklaptop\\e\Users\\Mat\\python\\data\\property\\bank-download\\'
generated_path = 'J://My Drive//NAS//My Documents//Business//Property//Statements//working//python//data//property//checked//'
tcy_path = 'J://My Drive//NAS//My Documents//Business//Property//Statements//working//python//data//property//bank-download//'

class Property:
    def __init__(self, pid):
        self.pid = pid
        
class Tenant:
    def __init__(self, pid, pty, tcy_name, start_date, end_date, rent, agent):
        self.pid = pid
        self.pty = pty
        self.tcy_name = tcy_name
        self.start_date = start_date
        self.end_date = end_date
        self.rent = rent
        self.agent = agent
        
property_map = {
'321 London Rd': Property('321LON'),
'Flat 1 - 321 London Rd': Property('F1321LON'),
'Flat 2 - 321 London Rd': Property('F2321LON'),
'Flat 3 - 321 London Rd': Property('F3321LON'),
'Flat 4 - 321 London Rd': Property('F4321LON'),
'169 Fawcett Rd': Property('169FAW'),
'Flat 1 - 169 Fawcett Rd': Property('F1169FAW'),
'Flat 2 - 169 Fawcett Rd': Property('F2169FAW'),
'Flat 3 - 169 Fawcett Rd': Property('F3169FAW'),
'171 Fawcett Rd': Property('171FAW'),
'Flat 1 - 171 Fawcett Rd': Property('F1171FAW'),
'Flat 2 - 171 Fawcett Rd': Property('F2171FAW'),
'Flat 3 - 171 Fawcett Rd': Property('F3171FAW'),
'163 Fratton Rd': Property('163FRA'),
#'Flat 2 - 163 Fratton Rd': Property('F2163FRA'),
'Flat 3 - 163 Fratton Rd': Property('F3163FRA'),
'Flat 4 - 163 Fratton Rd': Property('F4163FRA'),
'Shop - 196 Kingston Rd': Property('SHOP196KIN'),
'GFF - 196 Kingston Rd': Property('196AKIN'),
'FFF - 196 Kingston Rd': Property('196BKIN'),
'Flat B - 23 Hampshire Terrace': Property('23BHAM'),
'Flat C - 23 Hampshire Terrace': Property('23CHAM'),
'Flat 5 - 4-8 Alhambra Rd': Property('F58ALH'),
'Flat 6 - 4-8 Alhambra Rd': Property('F68ALH'),
'Flat 7 - 4-8 Alhambra Rd': Property('F78ALH'),
'Flat 8 - 4-8 Alhambra Rd': Property('F88ALH'),
'Flat 17 - 4-8 Alhambra Rd': Property('F1746ALH'),    
'Flat 18 - 4-8 Alhambra Rd': Property('F1846ALH'),    
'Flat 19 - 4-8 Alhambra Rd': Property('F1946ALH'),    
'Flat 20 - 4-8 Alhambra Rd': Property('F2046ALH'),    
'Flat 21 - 4-8 Alhambra Rd': Property('F2146ALH'),    
'Flat 22 - 4-8 Alhambra Rd': Property('F2246ALH'),    
'Flat 23 - 4-8 Alhambra Rd': Property('F2346ALH'),    
'Flat 3 - 12-14 Alhambra Rd': Property('F31214ALH'),
'Flat 4 - 12-14 Alhambra Rd': Property('F41214ALH'),
'Flat 5 - 12-14 Alhambra Rd': Property('F51214ALH'),
'Flat 7 - 12-14 Alhambra Rd': Property('F71214ALH'),
'Flat 11 - 12-14 Alhambra Rd': Property('F111214ALH'),
'Flat 10 - 12-14 Alhambra Rd': Property('F101214ALH'),    
'Flat 14 - 12-14 Alhambra Rd': Property('F141214ALH'),
'Flat 16 - 12-14 Alhambra Rd': Property('F161214ALH'),
'Flat 1 - 16-18 Alhambra Rd': Property('F11618ALH'),  
'Flat 3 - 16-18 Alhambra Rd': Property('F31618ALH'),  
'Flat 6 - 16-18 Alhambra Rd': Property('F61618ALH'),  
'Flat 7 - 16-18 Alhambra Rd': Property('F71618ALH'),  
'Flat 11 - 16-18 Alhambra Rd': Property('F111618ALH'),  
'Flat 12 - 16-18 Alhambra Rd': Property('F121618ALH'),  
'Flat 13 - 16-18 Alhambra Rd': Property('F131618ALH'),  
'Flat 16 - 16-18 Alhambra Rd': Property('F161618ALH'),
'RSA': Property('RSA')    
}

property_id_map = {
'321LON':2,
'F1321LON':1,
'F2321LON':14,
'F3321LON':3,
'F4321LON':4,
'169FAW':7,
'F1169FAW':5,
'F2169FAW':6,
'F3169FAW':8,
'171FAW':7,    
'F1171FAW':73,
'F2171FAW':74,
'F3171FAW':75,
'163FRA':12,
'F2163FRA':9,
'F3163FRA':10,
'F4163FRA':11,
'SHOP196KIN':17,
'196AKIN':15,
'196AKIN':44,
'196BKIN':16,
'23BHAM':19,
'23CHAM':34,
'23HAM':18,
'F58ALH':31,
'F68ALH':30,
'F78ALH':33,
'F88ALH':32,
'F1746ALH':26,
'F1846ALH':22,
'F1946ALH':21,
'F2046ALH':25,
'F2146ALH':28,
'F2246ALH':23,
'F2346ALH':27,
'F31214ALH':46,
'F41214ALH':52,
'F51214ALH':47,
'F71214ALH':48,
'F111214ALH':49,
'F101214ALH':53,
'F141214ALH':54,
'F161214ALH':55,
'F11618ALH':66,
'F31618ALH':67,
'F61618ALH':63,
'F71618ALH':68,
'F111618ALH':64,
'F121618ALH':71,
'F131618ALH':70,
'F161618ALH':65,
'RSA':81
}

def load_tenancies(tenancy_datafile):
    input_file = tcy_path + tenancy_datafile
    dfT = pd.read_excel(input_file,index_col=0,header=None,sheet_name='Sheet 1',names=['PROPERTY_ID','PROPERTY_NAME','TENANCY_ID','TENANT','START_DATE','END_DATE','RENT_AMOUNT','RENT_FREQ','AGENT_NAME','FEE_AMOUNT','FEE_TYPE','VAT'])
    return dfT

def load_data(start, end):
    csvext='.csv'
    xlsext='.xlsx'
    start_date=datetime.datetime.strptime(start, '%Y-%m-%d')
    end_date=datetime.datetime.strptime(end, '%Y-%m-%d')  
    dates = [dt for dt in rrule(MONTHLY, dtstart=start_date, until=end_date)]

    dfAll=pd.DataFrame()
    dfAll=pd.DataFrame(columns=['Account','Amount','Subcategory','Memo','Property','Description','Cat','Subcat'])

    for date in dates:
        dateStr= date.strftime("%b").upper() + date.strftime("%Y")
        input_file=generated_path + dateStr + '_codedAndCategorised'
        csvExist=os.path.isfile(input_file + csvext)
        xlsExist=os.path.isfile(input_file + xlsext)
        if((not csvExist)&(not xlsExist)):
            print('Warning missing file: ' + input_file)
            continue
        # Load excel file if both types exist
        if xlsExist:
            print('Reading file: ' + input_file + xlsext)
            dfTemp=pd.read_excel(input_file + xlsext, index_col=0, parse_dates=True, engine='openpyxl')
        else:
            print('Reading file: ' + input_file + csvext)
            dfTemp=pd.read_csv(input_file + csvext, index_col=0, parse_dates=True)
        dfAll=pd.concat([dfAll,dfTemp])
        dfAll=dfAll[['Account','Amount','Subcategory','Memo','Property','Description','Cat','Subcat']]
        dfAll

    return dfAll

def get_tenancy(dfT, property_id, start, end):
    tenancy=dfT.loc[(dfT.index==property_id)&(dfT.START_DATE<=end)&((dfT.END_DATE.isnull())|(dfT.END_DATE>=start))].sort_values(['START_DATE'], ascending=False).head(1)
    if(not tenancy.empty):
        return Tenant(tenancy.index, tenancy.PROPERTY_NAME, tenancy.TENANT, tenancy.START_DATE, tenancy.END_DATE, tenancy.RENT_AMOUNT, tenancy.AGENT_NAME)
    return None

def get_rent_statement(dfAll, dfT, start, end, inarrearslist, paidinadvancelist):
    excludelist = ['321 London Rd','169 Fawcett Rd','171 Fawcett Rd','163 Fratton Rd','RSA']
    
    dfRs=pd.DataFrame(columns=['Property','Tenant','Agent','Received','Bills','Mortgage','Net'])
    # Need to do this to set column types - workaround for what seems to be a bug
    dfRs = pd.DataFrame({'Property': {0: 'PropertyTest'}, 'Tenant': {0: 'PropertyTest'}, 'Agent': {0: 'AgentTest'},\
                       'Received': {0: 0.0},'Bills': {0: 0.0},'Mortgage': {0: 0.0},'Net': {0: 0.0} \
                      })
    index=0
    for key in property_map:
        tcy_start_date=None
        tcy_end_date=None
        prop=property_map[key]
        dfRs.at[index,'Property']=key
        if prop.pid != 'RSA' and prop.pid in property_id_map:
            tenancy=get_tenancy(dfT, property_id_map[prop.pid], start, end)
            dfRs.at[index,'Tenant']=''
            if(tenancy is not None):
                tenant=tenancy.tcy_name.values[0]
                agent=tenancy.agent.values[0]
                tcy_start_date=pd.to_datetime(str(tenancy.start_date.values[0]))
                if(not pd.isnull(tenancy.end_date.values[0])):
                    tcy_end_date=pd.to_datetime(str(tenancy.end_date.values[0]))
                    dfRs.at[index,'Tenant']=tenant + ' (' + tcy_start_date.strftime('%d/%m/%Y') + '-' + tcy_end_date.strftime('%d/%m/%Y') +')'
                else:
                    dfRs.at[index,'Tenant']=tenant + ' (' + tcy_start_date.strftime('%d/%m/%Y') + ')'
                dfRs.at[index,'Agent']=agent
            else:
                dfRs.at[index,'Tenant']=''
                dfRs.at[index,'Agent']=''
        dfRs.at[index,'Received']=dfAll.loc[(dfAll.Property==prop.pid)&((dfAll.Cat=='BealsRent')|(dfAll.Cat=='OurRent')),'Amount'][start:end].sum()
        dfRs.at[index,'Bills']=dfAll.loc[(dfAll.Property==prop.pid)&((dfAll.Cat=='PropertyExpense')),'Amount'][start:end].sum()
        dfRs.at[index,'Mortgage']=dfAll.loc[(dfAll.Property==prop.pid)&((dfAll.Cat=='Mortgage')),'Amount'][start:end].sum()
        dfRs=dfRs.fillna(0)
        dfRs.at[index,'Net']=dfRs.at[index,'Received']+dfRs.at[index,'Bills']+dfRs.at[index,'Mortgage']

        # Calc statuses
        dfRs.at[index,'Status']=''
        if(key not in excludelist):
            if(dfRs.at[index,'Tenant'] in paidinadvancelist):
               dfRs.at[index,'Status']='PaidInAdvance'
            elif(dfRs.at[index,'Tenant'] in inarrearslist):
               dfRs.at[index,'Status']='InArrears'
            elif(dfRs.at[index,'Received'] == 0):
               dfRs.at[index,'Status']='NotPaid'
            elif(dfRs.at[index,'Received'] <= 300):
               dfRs.at[index,'Status']='Underpayment'        
            else:
               dfRs.at[index,'Status']='Paid'

            if(tenancy is not None):
                if(tcy_start_date>=pd.to_datetime(start)):
                    dfRs.at[index,'Status']='New'
                elif((tcy_end_date is not None)):
                    if(tcy_end_date>=pd.to_datetime(start))&(tcy_end_date<=pd.to_datetime(end)):
                        dfRs.at[index,'Status']='Ending'
            else:
                dfRs.at[index,'Status']='Empty'

        index=index+1

    # Add service charges paid in total for all properties
    dfRs.at[index,'Property']='Service Charges'
    dfRs.at[index,'Tenant']=''
    dfRs.at[index,'Agent']=''
    dfRs.at[index,'Received']=0
    dfRs.at[index,'Bills']=dfAll.loc[(dfAll.Cat=='ServiceCharge'),'Amount'][start:end].sum()
    dfRs.at[index,'Mortgage']=0
    dfRs.at[index,'Net']=dfRs.at[index,'Received']+dfRs.at[index,'Bills']
    dfRs.at[index,'Status']=''
    index=index+1

    # Add totals
    dfRs.at[index,'Property']='Totals'
    dfRs.at[index,'Tenant']=''
    dfRs.at[index,'Agent']=''
    dfRs.at[index,'Received']=dfRs['Received'].sum()
    dfRs.at[index,'Bills']=dfRs['Bills'].sum()
    dfRs.at[index,'Mortgage']=dfRs['Mortgage'].sum()
    dfRs.at[index,'Net']=dfRs['Net'].sum()        
    dfRs.at[index,'Status']=''

    dfRs=dfRs.set_index('Property')
    return dfRs

# How to syle Rent Statement - this function is processed for each row, returns an array corresponding to style for each column
def custom_style(row):
    color = 'white'
    fontweight = 'normal'
    fontstyle = 'normal'
    if(row.Status=='NotPaid'):
       color = 'red'
    elif((row.Status=='Underpayment')|(row.Status=='InArrears')):
        color = 'pink'
    elif(row.Status=='PaidInAdvance'):
       color = 'grey'    
    elif(row.Status=='New'):
       color = 'lightgreen'         
    elif((row.Status=='Empty')|(row.Status=='Ending')):
       color = 'yellow'         
       
    if((row.name in ['Totals'])):
        color = 'lightblue'
        fontweight = 'bold'

    style = ['background-color: %s;' % color + 'font-weight: %s;' % fontweight+ 'font-style: %s;' % fontstyle]*len(row.values)
    return style

def plot_income_expenditure_per_property(dfRs):
    dfBar=pd.DataFrame()

    dfBar['Received'] = dfRs['Received']
    dfBar['Bills'] = abs(dfRs['Bills'])
    dfBar['Mortgage'] = abs(dfRs['Mortgage'])
    dfBar['Net'] = dfRs['Net']

    ax = dfBar[['Mortgage','Bills']].plot.bar(stacked=True, position=1, width=.3, color=['red','yellow'])
    ax.axhline(200, color="gray",linestyle='--')
    ax.axhline(400, color="gray",linestyle='--')
    ax.axhline(600, color="gray",linestyle='--')
    ax.axhline(800, color="gray",linestyle='--')
    ax.axhline(1000, color="gray",linestyle='--')

    dfBar[['Received']].plot.bar(stacked=True,ax=ax, position=2, width=.3, color=['green'],figsize=(30,15),fontsize=20).legend(loc=2, prop={'size': 20})

def plot_net_income(dfRs):
    dfBar=pd.DataFrame()

    dfBar['Net'] = dfRs['Net']
    ax = dfBar[['Net']].plot.bar(stacked=True, position=1, width=.3, color=['blue'],figsize=(30,15),fontsize=20)
    ax.axhline(0, color="gray",linestyle='-')
    ax.axhline(200, color="gray",linestyle='--')
    ax.axhline(400, color="gray",linestyle='--')
    ax.axhline(600, color="gray",linestyle='--')
    ax.axhline(800, color="gray",linestyle='--')
    ax.axhline(1000, color="gray",linestyle='--')
    ax.axhline(-200, color="gray",linestyle='--')
    ax.axhline(-400, color="gray",linestyle='--')
    ax.axhline(-600, color="gray",linestyle='--')
    ax.axhline(-800, color="gray",linestyle='--')
    ax.axhline(-1000, color="gray",linestyle='--')

    ax.legend(loc=2, prop={'size': 20})    

def custom_style_accounts_cat(row):
    color = 'white'
    fontweight = 'normal'
    fontstyle = 'normal'

    if((row.name[1]=='PersonalExpense')|(row.name[1]=='RegularPayment')):
        color = 'yellow'
    elif((row.name[1]=='Drawings')):
        color = 'pink'        

    style = ['background-color: %s;' % color + 'font-weight: %s;' % fontweight+ 'font-style: %s;' % fontstyle]*len(row.values)
    return style
        