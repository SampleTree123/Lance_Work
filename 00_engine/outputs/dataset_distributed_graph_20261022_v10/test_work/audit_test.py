from pathlib import Path
import argparse,json,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
sys.path.insert(0,str(ROOT/'audit_work'))
from audit_distributed import Rules,audit_split,read,content_key,pin
from audit_inherited_contract import audit_split as inherited_split,legacy_semantics
def main():
    p=argparse.ArgumentParser();p.add_argument('--candidate',required=True);a=p.parse_args();candidate=HERE/a.candidate;rules=Rules()
    r,keys,sigs=audit_split(rules,candidate,'test');r['inherited']=inherited_split(candidate,'test',rules);r['legacy_semantics']=legacy_semantics(candidate,'test',rules)
    train=ROOT/'trial12/graph/train/nodes.json';trainkeys={content_key(rules,row['state']) for row in read(train)}
    r['train_disjoint']={'train_nodes':pin(train),'canonical_overlap':len(keys&trainkeys),'passed':not keys&trainkeys}
    r['passed']=all((r['passed_hard_semantics'],r['all_node_and_chain_frequency_ranges_passed'],r['inherited']['passed_inherited_required_checks'],r['legacy_semantics']['passed_current_inherited_semantics'],r['train_disjoint']['passed']))
    (candidate/'audit_test.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'passed':r['passed'],'counts':r['counts'],'hard':r['passed_hard_semantics'],'inherited':r['inherited']['passed_inherited_required_checks'],'disjoint':r['train_disjoint']['passed'],'global_frequency':{unit:{k:[v['minimum'],v['maximum'],v['mean']] for k,v in r[unit]['distributions'].items() if not v['passed']} for unit in ('unique_content_node_frequency','chain_history_occurrence_frequency')},'camera_frequency':{unit:{act:{k:v for k,v in d['ratios_to_own_mean'].items() if v<.5 or v>1.5} for act,d in r[unit]['each_action_internal_camera_frequency'].items() if not d['passed']} for unit in ('unique_content_node_frequency','chain_history_occurrence_frequency')},'reuse':r['semantic_directed_edge_reuse'],'conditional_single_fraction':r['inherited']['wardrobe_formal_opportunity']['conditional_single_fraction']},ensure_ascii=False),flush=True)
if __name__=='__main__':main()
