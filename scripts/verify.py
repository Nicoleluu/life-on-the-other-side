"""Validate frozen files, report links, coverage and selected source transformations."""
from pathlib import Path
import hashlib,json,re
import pandas as pd
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
manifest=json.loads((ROOT/'data/download_manifest.json').read_text())+json.loads((ROOT/'data/osm_manifest.json').read_text())
for row in manifest:
    p=ROOT/row['file'];assert p.is_file(),p
    assert hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256'],p
for filename in ['README.md','DATA_DOCUMENT.md','DATA_RIGHTS.md']:
    s=(ROOT/filename).read_text()
    for target in re.findall(r'\]\(([^)]+)\)',s):
        if not target.startswith(('https://','http://','#')):
            assert (ROOT/target.split('#')[0]).exists(),(filename,target)
w=pd.read_csv(ROOT/'data/processed/wdi_country_year.csv')
assert len(w)==1690
assert set(w.iso3)=={'CHN','JPN','KOR','USA','CAN'}
for code,g in w.groupby('indicator'):
    assert len(g)==130
    if code not in ['SE.TER.ENRR','SE.TER.ENRR.FE','SE.TER.ENRR.MA','NY.GDP.PCAP.PP.KD','PA.NUS.PRVT.PP','PA.NUS.FCRF','SP.DYN.TFRT.IN']:
        assert g.value.dropna().between(0,100).all(),code
    assert g.value.dropna().ge(0).all(),code
price=pd.read_csv(ROOT/'data/processed/consumption_price_levels.csv')
assert np.allclose(price[price.iso3=='USA'].relative_price_level_us_100,100)
raw=pd.read_excel(ROOT/'data/raw/gsni2023.xlsx',sheet_name='Table A1',header=None)
clean=pd.read_csv(ROOT/'data/processed/gender_social_norms.csv')
for iso in w.iso3.unique():
    assert np.isclose(float(raw.loc[raw[0]==iso,8].iloc[0]),float(clean.loc[(clean.iso3==iso)&(clean.sex=='Total'),'educational_bias_pct'].iloc[0]))
food=pd.read_csv(ROOT/'data/processed/restaurant_pilot.csv')
assert len(food)==8998 and food.city.nunique()==5
assert food.lat.between(-90,90).all() and food.lon.between(-180,180).all()
assert not (ROOT/'data/raw/marriage.csv').exists()
stat=pd.read_csv(ROOT/'analysis/descriptive_statistics.csv')
assert stat[['minimum','maximum','mean','median','range','sample_sd','p25','p75']].notna().all().all()
assert (stat.minimum<=stat.p25).all() and (stat.p25<=stat['median']).all() and (stat['median']<=stat.p75).all() and (stat.p75<=stat.maximum).all()
print(f'Validated {len(manifest)} source checksums, all local document links, numeric ranges, five-country coverage, price normalization and GSNI source matches.')
