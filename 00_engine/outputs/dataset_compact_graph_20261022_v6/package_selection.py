"""Assemble a concrete train/test delivery without changing experiment records."""
import argparse, hashlib, json, shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def pin(p):return {'path':str(p.resolve()),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--selection',required=True);a=ap.parse_args()
    selection=read(ROOT/a.selection)
    for row in selection['sampling_seeds']:
        target=ROOT/row['assembled_candidate']
        if target.exists():raise RuntimeError(f'Refusing to overwrite {target}')
        provenance={'scope':'offline data manifests; not rendered videos','sources':{},
                    'sampling_configuration':selection['sampling_configuration']}
        for split in ('train','test'):
            src=ROOT/row[split];dst=target/split
            shutil.copytree(src,dst)
            provenance['sources'][split]={'source_split':str(src),'files':[pin(p) for p in src.iterdir() if p.is_file()]}
            sampler=src.parent/'sampler_source.py'
            shutil.copyfile(sampler,dst/'sampler_source.py')
            provenance['sources'][split]['sampler_source']=pin(sampler)
        hashes=[v['sampler_source']['sha256'] for v in provenance['sources'].values()]
        if len(set(hashes))!=1:raise RuntimeError('Train/test sampler differs; disclose or fix before selecting')
        write(target/'ASSEMBLY.json',provenance)
    print('Assembled',len(selection['sampling_seeds']),'alternative candidates; never combine them as more data.')

if __name__=='__main__':main()
