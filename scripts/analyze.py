"""Reproduce cleaned data and descriptive statistics from the retained snapshots."""
from pathlib import Path
import json, math
import pandas as pd
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'data/raw'; OUT=ROOT/'data/processed'; RESULTS=ROOT/'analysis'
OUT.mkdir(exist_ok=True);RESULTS.mkdir(exist_ok=True)
COUNTRIES={'CHN':'China','JPN':'Japan','KOR':'South Korea','USA':'United States','CAN':'Canada'}
stats=[]; validations=[]; inventories=[]
def save(df,name,key):
    df.to_csv(OUT/name,index=False)
    inventories.append(dict(file=name,rows=len(df),columns=len(df.columns),column_names=list(df.columns)))
    validations.append(dict(dataset=name,check='duplicate primary keys',count=int(df.duplicated(key).sum())))
    assert not df.duplicated(key).any(),(name,'duplicate keys')
def summary(label,values,unit,population):
    a=pd.to_numeric(pd.Series(values),errors='coerce').dropna()
    q1,q3=a.quantile([.25,.75]);iqr=q3-q1
    stats.append(dict(variable=label,unit=unit,population=population,n=len(a),minimum=a.min(),maximum=a.max(),mean=a.mean(),median=a.median(),range=a.max()-a.min(),sample_sd=a.std(ddof=1),p25=q1,p75=q3,skewness=a.skew(),iqr_outliers=int(((a<q1-1.5*iqr)|(a>q3+1.5*iqr)).sum())))

rows=[]; metadata=[]; rejected=[]
for p in sorted(RAW.glob('wdi_*.json')):
    code=p.stem[4:]; j=json.loads(p.read_text())
    if len(j)!=2 or not isinstance(j[1],list):
        rejected.append(dict(file=p.name,reason=j));continue
    assert j[0]['pages']==1
    meta=json.loads((RAW/f'metadata_{code}.json').read_text())[1][0]
    metadata.append(dict(indicator=code,name=meta['name'],definition=meta['sourceNote'],producer=meta['sourceOrganization'],last_updated=j[0].get('lastupdated'),unit=meta.get('unit',''),source_url=f'https://data.worldbank.org/indicator/{code}'))
    for r in j[1]:
        if r['countryiso3code'] not in COUNTRIES: continue
        rows.append(dict(iso3=r['countryiso3code'],country=COUNTRIES[r['countryiso3code']],year=int(r['date']),indicator=code,indicator_name=r['indicator']['value'],value=r['value'],unit=r.get('unit',''),obs_status=r.get('obs_status',''),source_id=j[0]['sourceid'],source_updated=j[0].get('lastupdated'),accessed='2026-10-28'))
wdi=pd.DataFrame(rows).sort_values(['indicator','iso3','year'])
save(wdi,'wdi_country_year.csv',['iso3','year','indicator'])
pd.DataFrame(metadata).to_csv(OUT/'wdi_indicator_dictionary.csv',index=False)
coverage=wdi.groupby(['indicator','iso3']).agg(rows=('value','size'),nonmissing=('value','count'),first_observed_year=('year',lambda x: int(x[wdi.loc[x.index,'value'].notna()].min()) if wdi.loc[x.index,'value'].notna().any() else None),last_observed_year=('year',lambda x:int(x[wdi.loc[x.index,'value'].notna()].max()) if wdi.loc[x.index,'value'].notna().any() else None)).reset_index()
coverage['missing']=coverage.rows-coverage.nonmissing
coverage.to_csv(RESULTS/'wdi_coverage.csv',index=False)
wdi.groupby(['year','indicator']).value.count().unstack().to_csv(RESULTS/'wdi_year_counts.csv')
snap=[]
for code,g in wdi.groupby('indicator'):
    valid=g.dropna(subset=['value'])
    counts=valid.groupby('year').iso3.nunique()
    shared=counts[counts==5]
    if len(shared):
        year=int(shared.index.max());s=valid[valid.year==year].copy();s['comparison_year']=year;snap.append(s)
        if code not in ['PA.NUS.FCRF','PA.NUS.PRVT.PP']:
            summary(code,s.value,'see indicator dictionary',f'5 country values in {year}; equal country weights')
    validations.append(dict(dataset=code,check='missing values in requested 2000–2025 panel',count=int(g.value.isna().sum())))
snapshot=pd.concat(snap,ignore_index=True)
save(snapshot,'wdi_latest_common_year.csv',['iso3','indicator'])
wide=wdi.pivot(index=['iso3','country','year'],columns='indicator',values='value').reset_index()
prices=wide[['iso3','country','year','PA.NUS.PRVT.PP','PA.NUS.FCRF']].rename(columns={'PA.NUS.PRVT.PP':'consumption_ppp_lcu_per_int_dollar','PA.NUS.FCRF':'exchange_lcu_per_usd'})
prices['ppp_exchange_ratio']=prices.consumption_ppp_lcu_per_int_dollar/prices.exchange_lcu_per_usd
us=prices[prices.iso3=='USA'].set_index('year').ppp_exchange_ratio
prices['relative_price_level_us_100']=prices.ppp_exchange_ratio/prices.year.map(us)*100
save(prices,'consumption_price_levels.csv',['iso3','year'])
py=prices.dropna(subset=['relative_price_level_us_100']).groupby('year').iso3.nunique();price_year=int(py[py==5].index.max())
summary('Consumption price level',prices.loc[prices.year==price_year,'relative_price_level_us_100'],'US=100',f'5 country values in {price_year}; macro consumption PPP proxy')

measures=['at_least_one_bias_pct','at_least_two_biases_pct','no_bias_pct','political_bias_pct','educational_bias_pct','economic_bias_pct','physical_integrity_bias_pct']
gs=[]
for sheet,groups in [('Table A1',[('Total',None)]),('Table A2',[('Women',0),('Men',1)])]:
    d=pd.read_excel(RAW/'gsni2023.xlsx',sheet_name=sheet,header=None)
    for _,r in d[d[0].isin(COUNTRIES)].iterrows():
        for sex,offset in groups:
            z=dict(iso3=r[0],country=COUNTRIES[r[0]],sex=sex,survey_period=r[3])
            for k,m in enumerate(measures):z[m]=float(r[4+k if offset is None else 4+2*k+offset])
            gs.append(z)
gsni=pd.DataFrame(gs)
save(gsni,'gender_social_norms.csv',['iso3','sex'])
assert gsni[measures].ge(0).all().all() and gsni[measures].le(100).all().all()
assert np.allclose(gsni.at_least_one_bias_pct+gsni.no_bias_pct,100,atol=.00001)
for m in ['educational_bias_pct','economic_bias_pct']:
    summary('GSNI '+m,gsni[gsni.sex=='Total'][m],'percent', '5 country estimates; WVS wave 2017–2022')

time=pd.read_csv(RAW/'oecd_time_use.csv');time=time[time.REF_AREA.isin(COUNTRIES)].copy()
details=pd.read_excel(RAW/'oecd_time_details.xlsx',sheet_name='Total',header=None,usecols='A:AL')
headers={str(details.iloc[0,c]).replace('*','').strip():c for c in range(2,len(details.columns))}
namemap={'CHN':'China','JPN':'Japan','KOR':'Korea','USA':'United States','CAN':'Canada'}
time['country']=time.REF_AREA.map(COUNTRIES)
time['survey_period']=time.REF_AREA.map({k:str(details.iloc[1,headers[v]]) for k,v in namemap.items()})
time['age_reference']=time.REF_AREA.map({k:str(details.iloc[2,headers[v]]) for k,v in namemap.items()})
time['activity']=time.MEASURE.map({'LEI':'Leisure','PCA':'Personal care','UPW':'Unpaid work','PAW':'Paid work or study','OTH':'Other'})
time['sex_label']=time.SEX.map({'F':'Women','M':'Men','_T':'Total'})
save(time,'time_use.csv',['REF_AREA','MEASURE','SEX'])
totals=time.groupby(['REF_AREA','SEX']).OBS_VALUE.sum().reset_index(name='minutes_sum')
totals['deviation_from_1440']=totals.minutes_sum-1440
totals.to_csv(RESULTS/'time_budget_checks.csv',index=False)
assert time.OBS_VALUE.between(0,1440).all()
assert (totals.deviation_from_1440.abs()<=2).all()
up=time[time.MEASURE=='UPW'].pivot(index='REF_AREA',columns='SEX',values='OBS_VALUE')
up['female_minus_male_minutes']=up.F-up.M
up.to_csv(RESULTS/'unpaid_work_gap.csv')
for m in ['UPW','LEI','PAW']:
    summary('Time use '+m,time[(time.MEASURE==m)&(time.SEX=='_T')].OBS_VALUE,'minutes/day','5 country averages; mixed years and China age exception')
summary('Unpaid work gender gap',up.female_minus_male_minutes,'minutes/day','5 paired female-minus-male gaps; mixed years')

wages=pd.read_csv(RAW/'oecd_wages.csv')
wages=wages[wages.REF_AREA.isin(COUNTRIES)&(wages.UNIT_MEASURE=='USD_PPP')&(wages.PRICE_BASE=='Q')].copy()
wages['country']=wages.REF_AREA.map(COUNTRIES)
save(wages,'annual_wages_ppp.csv',['REF_AREA','TIME_PERIOD'])
assert wages.OBS_VALUE.gt(0).all()
wcounts=wages.groupby('TIME_PERIOD').REF_AREA.nunique();wyear=int(wcounts[wcounts==4].index.max())
summary('Average annual wages',wages[wages.TIME_PERIOD==wyear].OBS_VALUE,'USD PPP, constant base year in BASE_PER',f'4 country values in {wyear}; China absent; full-time equivalent employees')

food=[]
manifest=ROOT/'data/osm_manifest.json'
if manifest.exists():
    for m in json.loads(manifest.read_text()):
        if m['iso3'] not in COUNTRIES: continue
        j=json.loads((ROOT/m['file']).read_text())
        assert 'remark' not in j, (m['city'],j.get('remark'))
        for e in j['elements']:
            t=e.get('tags',{});point=e.get('center',e)
            food.append(dict(iso3=m['iso3'],city=m['city'],osm_type=e['type'],osm_id=e['id'],name=t.get('name',''),cuisine_raw=t.get('cuisine',''),lat=point.get('lat'),lon=point.get('lon'),radius_m=m['radius_m'],center_lat=m['center_lat'],center_lon=m['center_lon'],snapshot_utc=j['osm3s']['timestamp_osm_base']))
    foods=pd.DataFrame(food)
    save(foods,'restaurant_pilot.csv',['city','osm_type','osm_id'])
    fs=foods.groupby(['iso3','city']).agg(mapped_objects=('osm_id','size'),with_cuisine=('cuisine_raw',lambda s:s.ne('').sum()),unique_raw_cuisine_strings=('cuisine_raw',lambda s:s[s!=''].nunique())).reset_index()
    fs['missing_cuisine']=fs.mapped_objects-fs.with_cuisine
    fs['missing_cuisine_pct']=100*fs.missing_cuisine/fs.mapped_objects
    fs.to_csv(RESULTS/'restaurant_coverage.csv',index=False)
    cats=foods.assign(cuisine=foods.cuisine_raw.str.split(';')).explode('cuisine');cats['cuisine']=cats.cuisine.str.strip().str.lower()
    cats=cats[cats.cuisine!=''];cats.groupby(['city','cuisine']).size().rename('tag_occurrences').reset_index().to_csv(RESULTS/'cuisine_tag_counts.csv',index=False)
    summary('Missing cuisine tags',fs.missing_cuisine_pct,'percent of mapped restaurant objects','5 analyst-selected 2 km radius pilot areas; not country estimates')

pd.DataFrame(stats).to_csv(RESULTS/'descriptive_statistics.csv',index=False)
milestones=pd.read_csv(ROOT/'data/curated/marriage_milestones.csv')
dates=pd.to_datetime(milestones.event_date,errors='raise')
assert milestones.source_url.notna().all()
validations.append(dict(dataset='marriage_milestones.csv',check='duplicate jurisdiction and date',count=int(milestones.duplicated(['jurisdiction','event_date']).sum())))
inventories.append(dict(file='marriage_milestones.csv',rows=len(milestones),columns=len(milestones.columns),column_names=list(milestones.columns)))
pd.DataFrame(validations).to_csv(RESULTS/'validation_checks.csv',index=False)
(RESULTS/'inventory.json').write_text(json.dumps(inventories,indent=2))
(RESULTS/'rejected_sources.json').write_text(json.dumps(rejected,indent=2))
print(json.dumps({'files':inventories,'wdi_missing':int(wdi.value.isna().sum()),'common_years':snapshot.groupby('indicator').year.first().to_dict(),'wage_year':wyear,'price_year':price_year,'time_budget_max_error':float(totals.deviation_from_1440.abs().max())},indent=2))
