"""Small normal multi-axis test graph; independent forbidden state set."""
from pathlib import Path
from collections import Counter
import argparse,copy,importlib.util,json,random,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent;OUT=ROOT.parent
code=(HERE/'builder_snapshot.py').read_text(encoding='utf-8')
code=code.replace('ROOT=Path(__file__).resolve().parent;OUT=ROOT.parent','ROOT=Path(__file__).resolve().parent.parent;OUT=ROOT.parent')
code=code.replace('if len(clones)>=260:break','if len(clones)>=96:break')
code=code.replace("core_mean=sum(count['core'].values())/239","core_mean=sum(count['core'].values())/max(1,len(count['core']))")
code=code.replace("solver_temp=OUT.parent/'temp/dataset_distributed_graph_20261022_v10'","solver_temp=Path(__file__).resolve().parent/'solver_temp'")
code=code.replace('PULP_CBC_CMD(msg=True','PULP_CBC_CMD(msg=False')
code=code.replace('status=problem.solve(solver);milp_status=pulp.LpStatus[status]','status=0;milp_status="bounded_local_search_snapshot"')
code=code.replace('pools=[uppers,full,full] if bid%4!=0 and not finish_core and upper_complete>=2 else [full,full,full]','pools=[uppers,full,full]')
code=code.replace('lows=np.flatnonzero(ratios<.56)','lows=np.array([p for p in np.flatnonzero(ratios<.56) if options_for_pair[p]])')
code=code.replace("if any(wardrobe_key(row)==wardrobe_key(w) for w in chosen):return -1e9","if any(wardrobe_key(row)==wardrobe_key(w) for w in chosen) or sum(w['family']==row['family'] for w in chosen)>=2:return -1e9")
snapshot=HERE/'builder_test_impl.py';snapshot.write_text(code,encoding='utf-8')
spec=importlib.util.spec_from_file_location('test_builder_impl',snapshot);b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
from build_compact import closed_wardrobes
OriginalDomain=b.Domain
class TestDomain(OriginalDomain):
    def __init__(self):
        super().__init__()
        self.ids={sex:vals[6:10] for sex,vals in self.ids.items()}
        self.hairs={sex:vals[3:7] for sex,vals in self.hairs.items()}
        self.actions=self.actions[3:9]
        self.sites=self.sites[4:10]
b.Domain=TestDomain
def main():
    p=argparse.ArgumentParser();p.add_argument('--output',default='trial1');p.add_argument('--seed',type=int,default=2026102231);p.add_argument('--repeat',type=int,default=2);p.add_argument('--extra',type=int,default=0);a=p.parse_args()
    dest=HERE/a.output
    if dest.exists():raise FileExistsError(dest)
    dest.mkdir();d=TestDomain();rules=b.Rules();rng=random.Random(a.seed)
    looks=[]
    for bid in (0,1,2,4):
        sex='male' if bid==1 else 'female'
        # Alternate sex equally by using two blocks of each sex.
        if bid==4:bid=5;sex='male'
        ws=closed_wardrobes(d,sex,bid,rng)
        for w in ws:
            looks.append({'sex':sex,'family':w['family_id'],'group':w['group_id'],'visibility':'full','choice':w,'visible_core':list(d.nc.core_asset_ids(sex,w))})
    extra=([r for r in looks if len(r['visible_core'])==1]*4)[:a.extra]
    looks=looks*a.repeat+extra
    train=ROOT/'trial12/graph/train';trainrows=b.read(train/'nodes.json');forbidden={d.canonical(n['state']) for n in trainrows}
    b.write(dest/'look_selection.json',{'looks':looks,'selected_pools':{'identities':d.ids,'hairs':d.hairs,'actions':d.actions,'sites':d.sites},'policy':'four complete ordinary wardrobe groups repeated in independent contexts; no coverage padding'})
    g,meta=b.make_graph(looks,a.seed,forbidden)
    meta.update(test_selected_pools={'identities':d.ids,'hairs':d.hairs,'actions':d.actions,'sites':d.sites},forbidden_train=b.pin(train/'nodes.json'))
    b.save_empty_graph(dest/'graph/test',g,meta)
    sys.path.insert(0,str(ROOT/'audit_work'));from audit_distributed import exposure
    e=exposure(rules,[(s,1) for s in g.nodes],False);b.write(dest/'node_frequency_test.json',e)
    print(json.dumps({'nodes':len(g.nodes),'edges':meta['axis_edges'],'global':e['all_requested_global_frequencies_in_range'],'camera':e['all_action_internal_camera_frequencies_in_range'],'dist':{k:[v['minimum'],v['maximum'],v['mean'],v['passed']] for k,v in e['distributions'].items()},'failed_camera':{k:[v['minimum'],v['maximum'],v['mean']] for k,v in e['each_action_internal_camera_frequency'].items() if not v['passed']}}),flush=True)
if __name__=='__main__':main()
