"""Use existing independent semantics; add audit of pair warmup disclosures."""
from pathlib import Path
import importlib.util,json,sys,hashlib
ROOT=Path(__file__).resolve().parent
OUT=ROOT.parent
V6=OUT/'dataset_compact_graph_20261022_v6'
sys.dont_write_bytecode=True
sys.path.insert(0,str(OUT/'dataset_balanced_graph_20261022_v5'))

def dump(path,obj):Path(path).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def main():
    code=(V6/'audit_compact.py').read_text(encoding='utf-8')
    needle="return {(axis, base.token(value))}"
    assert code.count(needle)==1
    code=code.replace(needle,"return {(axis, base.token(value))} | ({('action_camera', base.token([t['action'], t['camera']]))} if axis in ('action','camera') else set())")
    # Snapshot changes only the explicit new warmup token's verification.
    path=ROOT/'audit_compact_v9_snapshot.py';path.write_text(code,encoding='utf-8')
    spec=importlib.util.spec_from_file_location('v9_structural_audit',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    m.write_diagnostic=dump
    # Test content budget modestly raised for user-requested camera expansion.
    m.base.LIMITS={'train':(5000,12000,43800),'test':(825,2400,8760)}
    report=m.audit_compact(ROOT/'structural_candidate',ROOT/'structural_audit.json')
    report['v9_scope']={'history_decay':.4,'mean_used_edge_reuse_soft_target':2.5,'legacy_v5_soft_target_fields_still_describe_2':True,'test_node_budget_override':825,'new_action_camera_token_disclosure_checked':True,'audit_snapshot_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'immutable_source_sha256':hashlib.sha256((V6/'audit_compact.py').read_bytes()).hexdigest()}
    dump(ROOT/'structural_audit.json',report)
    print(json.dumps({'passed_hard_checks':report['passed_hard_checks'],'splits':{s:{'counts':report[s]['counts'],'error_counts':report[s]['error_counts'],'errors':report[s]['errors_first_100'][:5]} for s in ('train','test')}},ensure_ascii=False),flush=True)
    if not report['passed_hard_checks']:raise SystemExit(1)
if __name__=='__main__':main()
