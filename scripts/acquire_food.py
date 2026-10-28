"""Six small exploratory restaurant extracts. OSM data and derivatives: ODbL 1.0."""
from acquire import ROOT,fetch
import urllib.parse,json,time
SAMPLES=[('Beijing','CHN',39.9042,116.4074),('Tokyo','JPN',35.6812,139.7671),('Seoul','KOR',37.5665,126.9780),('New York','USA',40.7306,-73.9866),('Toronto','CAN',43.6532,-79.3832),('London','GBR',51.5074,-0.1278)]
results=[]
for city,iso,lat,lon in SAMPLES:
    query=f'[out:json][timeout:60];nwr["amenity"="restaurant"](around:2000,{lat},{lon});out center tags;'
    url='https://overpass-api.de/api/interpreter?data='+urllib.parse.quote(query)
    try:
        r=fetch('osm_'+iso+'.json',url)
        r.update(city=city,iso3=iso,center_lat=lat,center_lon=lon,radius_m=2000,query=query)
        results.append(r);print(city,r['bytes'],flush=True)
    except Exception as e:print('FAILED',city,str(e),flush=True)
    time.sleep(1)
(ROOT/'data/osm_manifest.json').write_text(json.dumps(results,indent=2))
