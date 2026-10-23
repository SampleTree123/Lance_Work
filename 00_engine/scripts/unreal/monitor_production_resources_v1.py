"""Read-only resource sampler for root's serial render; stop through a file."""
from pathlib import Path
import datetime,json,subprocess,time,shutil
import psutil

RUN=Path(__file__).resolve().parents[2]/'outputs/production_workflow_20261017_v1'

def sample():
    mem=psutil.virtual_memory()
    row={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
         'available_ram_gib':round(mem.available/2**30,3),'ram_used_percent':mem.percent,
         'disk_free_gib':round(shutil.disk_usage('D:/').free/2**30,3)}
    try:
        result=subprocess.run(['nvidia-smi','--query-gpu=memory.used,memory.total,utilization.gpu','--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=8)
        row['gpu_used_mib'],row['gpu_total_mib'],row['gpu_util_percent']=map(int,result.stdout.strip().split(',')[:3])
    except Exception as e:row['gpu_error']=str(e)
    row['unreal_rss_gib']=round(sum(p.info['memory_info'].rss for p in psutil.process_iter(['name','memory_info']) if (p.info['name'] or '').lower().startswith('unrealeditor')),0)/2**30
    return row

def main():
    RUN.mkdir(parents=True,exist_ok=True)
    stop=RUN/'resource_monitor.stop'
    if stop.exists():raise RuntimeError('Remove previous stop file explicitly before starting')
    rows=[]
    with (RUN/'resource_samples.jsonl').open('a',encoding='utf-8') as stream:
        while not stop.exists():
            row=sample();rows.append(row);stream.write(json.dumps(row)+'\n');stream.flush()
            (RUN/'resource_latest.json').write_text(json.dumps(row,indent=2),encoding='utf-8')
            time.sleep(5)
    report={'samples':len(rows),'minimum_available_ram_gib':min(r['available_ram_gib'] for r in rows),
            'maximum_gpu_used_mib':max(r.get('gpu_used_mib',0) for r in rows),
            'minimum_disk_free_gib':min(r['disk_free_gib'] for r in rows),'rows_file':str(RUN/'resource_samples.jsonl')}
    (RUN/'resource_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(report)

if __name__=='__main__':main()
