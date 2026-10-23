"""Bounded GPU telemetry during corrected pilot."""
import subprocess,time
from pathlib import Path
r=Path(__file__).resolve().parent
with (r/'gpu_telemetry.csv').open('w',encoding='utf-8') as f:
    f.write('timestamp,memory_used_mib,memory_total_mib,utilization_percent\n')
    for i in range(180):
        row=subprocess.run(['nvidia-smi','--query-gpu=timestamp,memory.used,memory.total,utilization.gpu','--format=csv,noheader,nounits'],capture_output=True,text=True)
        if row.returncode:break
        f.write(row.stdout);f.flush();time.sleep(1)
