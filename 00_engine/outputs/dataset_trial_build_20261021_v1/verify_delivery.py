"""Scoped trial delivery checks; deliberately not the repository-wide audit."""
import ast,hashlib,json,re
from pathlib import Path
from verify_trial import Verification
from build_trial import HERE,read,write

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    errors=[];counts={'json':0,'python':0,'jsonl_records':0,'links':0}; files=[]
    for p in sorted(HERE.rglob('*')):
        if not p.is_file() or '__pycache__' in p.parts or p.name in ('delivery_verification.json','DELIVERY_MANIFEST.json'):continue
        rel=p.relative_to(HERE).as_posix()
        try:
            if p.suffix=='.json':read(p);counts['json']+=1
            elif p.suffix=='.py':ast.parse(p.read_text(encoding='utf-8-sig'));counts['python']+=1
            elif p.suffix=='.jsonl':
                for line in p.read_text(encoding='utf-8').splitlines():json.loads(line);counts['jsonl_records']+=1
            elif p.suffix=='.md':
                for dest in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf-8-sig')):
                    dest=dest.split('#')[0]
                    if not dest or '://' in dest or '%' in dest:continue
                    counts['links']+=1
                    if not (p.parent/dest).exists():errors.append('missing link: '+rel+' -> '+dest)
        except Exception as e:errors.append(rel+': '+str(e))
        files.append({'path':rel,'bytes':p.stat().st_size,'sha256':sha(p)})
    v=read(HERE/'verification_full_squares_uniform_nodes.json')
    for k,h in v['inputs_sha256'].items():
        p=HERE/'full_squares_uniform_nodes'/k if k.startswith(('train/','test/')) else HERE/k
        if sha(p)!=h:errors.append('verification input changed: '+str(p))
    pinned=0
    for pin in read(HERE/'catalog.json')['source_pins']:
        p=Path(pin['path']);pinned+=1
        if not p.is_file() or sha(p)!=pin['sha256']:errors.append('catalog input changed: '+str(p))
    probe=HERE/'requested_sampling_probe'; verifier=Verification();nodes=read(probe/'nodes.json'); states={n['id']:n['state'] for n in nodes}
    for n in nodes:verifier.check_node(n,'diagnostic_probe')
    for e in read(probe/'edges.json'):verifier.check_edge(e,states,'diagnostic_probe')
    sessions=[json.loads(x) for x in (probe/'sessions.jsonl').read_text(encoding='utf-8').splitlines()]
    seen=set()
    for s in sessions:
        h=s['history']; forks=0
        for t,e in enumerate(s['steps'],1):
            p=e['source_position'];assert 0<=p<t and e['source']==h[p] and e['target']==h[t]
            forks+=p!=t-1;verifier.check_edge(e,states,'diagnostic_probe','used')
        assert forks==(s['kind']=='fork') and 2<=len(s['steps'])<=5
        signature=(h[0],tuple((e['source_position'],e['target']) for e in s['steps']));assert signature not in seen;seen.add(signature)
    if verifier.errors:errors.append('probe independent semantic checks failed: '+str(dict(verifier.errors)))
    manifest={'schema':'experimental_trial_manifest_v1','rendered':False,'files':files,'owner':'TECH-DATASET-EXPLORE-20261021','retention':'unclassified_protected'}
    write(HERE/'DELIVERY_MANIFEST.json',manifest)
    result={'scope':'trial syntax, relative links, selected integrity input hashes, current catalog pins, independent full-domain probe semantic validation',
            'success':not errors,'counts':counts,'manifest_files':len(files),'catalog_pins_checked':pinned,'probe_nodes':len(nodes),'probe_sessions':len(sessions),
            'probe_independent_checks':dict(verifier.counts),'errors':errors,'production_sampling_accepted':False,'no_ue_or_media_validation':True}
    write(HERE/'delivery_verification.json',result);print(json.dumps(result,ensure_ascii=False))
    if errors:raise SystemExit(1)
if __name__=='__main__':main()
