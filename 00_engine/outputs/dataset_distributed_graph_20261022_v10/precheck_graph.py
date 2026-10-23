from pathlib import Path
import argparse,json,sys
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'audit_work'))
from audit_distributed import Rules,exposure
def main():
    p=argparse.ArgumentParser();p.add_argument('trial');p.add_argument('--split',default='train');a=p.parse_args()
    nodes=json.loads((ROOT/a.trial/'graph'/a.split/'nodes.json').read_text(encoding='utf-8'))
    result=exposure(Rules(),[(n['state'],1) for n in nodes],a.split=='train')
    (ROOT/a.trial/f'node_frequency_{a.split}.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'nodes':len(nodes),'global':{k:{'min_ratio':min(v['ratios_to_own_mean'].values()),'max_ratio':max(v['ratios_to_own_mean'].values()),'below':len(v['below_half_mean']),'above':len(v['above_one_and_half_mean'])} for k,v in result['distributions'].items()},'failed_action_camera':{k:{'mean':v['mean'],'below':v['below_half_mean'],'above':v['above_one_and_half_mean']} for k,v in result['each_action_internal_camera_frequency'].items() if not v['passed']},'garment_context_pass':result['all_represented_garments_min3_actions_and_cameras']},ensure_ascii=False))
if __name__=='__main__':main()
