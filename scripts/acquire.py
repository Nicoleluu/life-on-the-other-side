"""Download public source snapshots. Run from any directory; cached files are preserved."""
from pathlib import Path
import json, urllib.request, hashlib, concurrent.futures, time
ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'data/raw'
RAW.mkdir(parents=True,exist_ok=True)
INDICATORS=['SL.TLF.CACT.FE.ZS','SL.TLF.CACT.MA.ZS','SE.TER.ENRR','SE.TER.ENRR.FE','SE.TER.ENRR.MA','PA.NUS.PPPC.RF','PA.NUS.PRVT.PP','PA.NUS.FCRF','NY.GDP.PCAP.PP.KD','SM.POP.TOTL.ZS','SP.DYN.TFRT.IN','SP.POP.65UP.TO.ZS','SI.POV.GINI','SP.POP.TOTL.FE.ZS']
def fetch(name,url,accept=None):
    p=RAW/name
    if not p.exists():
        req=urllib.request.Request(url,headers={'User-Agent':'Academic data visualization project / public data download',**({'Accept':accept} if accept else {})})
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req,timeout=60) as r: data=r.read()
                p.write_bytes(data); break
            except Exception:
                if attempt==2: raise
                time.sleep(2)
    data=p.read_bytes()
    return dict(file=str(p.relative_to(ROOT)),url=url,accessed='2026-10-28',bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
def main():
    jobs=[]
    for code in INDICATORS:
        jobs.append((f'wdi_{code}.json',f'https://api.worldbank.org/v2/country/CHN;JPN;KOR;USA;CAN;GBR/indicator/{code}?format=json&date=2000:2025&per_page=20000'))
        jobs.append((f'metadata_{code}.json',f'https://api.worldbank.org/v2/indicator/{code}?format=json'))
    jobs.append(('oecd_time_use.csv','https://sdmx.oecd.org/public/rest/v1/data/OECD.WISE.INE,DSD_TIME_USE@DF_TIME_USE,1.0/all?format=csvfile'))
    jobs.append(('gsni2023.xlsx','https://hdr.undp.org/sites/default/files/publications/additional-files/2023-06/GSNI2023_AnnexTables2.xlsx'))
    jobs.append(('oecd_wages.csv','https://sdmx.oecd.org/public/rest/v1/data/OECD.ELS.SAE,DSD_EARNINGS@AV_AN_WAGE,1.0/all?startPeriod=2000&endPeriod=2025&format=csvfile'))
    jobs.append(('oecd_time_structure.xml','https://sdmx.oecd.org/public/rest/v1/dataflow/OECD.WISE.INE/DSD_TIME_USE@DF_TIME_USE/1.0?references=all'))
    jobs.append(('oecd_time_details.xlsx','https://www.oecd.org/content/dam/oecd/en/data/datasets/time-use-database/OECD-time-use-database-updates.xlsx'))
    results=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures={pool.submit(fetch,*j):j[0] for j in jobs}
        for f in concurrent.futures.as_completed(futures):
            try:
                r=f.result(); results.append(r); print(r['file'],r['bytes'],flush=True)
            except Exception as e: print('FAILED',futures[f],str(e),flush=True)
    (ROOT/'data/download_manifest.json').write_text(json.dumps(sorted(results,key=lambda x:x['file']),indent=2))
if __name__=='__main__':main()
