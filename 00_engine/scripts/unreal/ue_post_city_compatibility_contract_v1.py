"""Definitions only; prospective S/ue_post_city_compatibility_contract_v1.py.

Only PostCity has original four serialized imports; current AR resolves the exact new addresses.
Only a SHA-pinned pure finite construction module is loaded from this task.
No opaque UObject load, asset write or general class alias.
The actual fresh AFTER-cleanup receipt SHA is required, never invented here.
"""
import gc
import json
import re
from pathlib import Path

ORG=Path('D:/UE/Lance_Work/00_engine/outputs/scene_folder_organization_20261012_v1')
TEMP=Path('D:/UE/Lance_Work/00_engine/temp/scene_folder_organization_20261012_v1')
ROOT='/Game/PostCity';DEST='/Game/Scenes/PostCity'
BASE_SHA='689c41dd9e02854da4682e9e408eed2ae50abd9d25b41c56969bdeaac4041d58'
SOURCE_SHA='28a7f2e6b4ff1fd536ede07459f4a52e76351926710391055f62f59e0828f696'
CONT_SHA='bd5bb70a7349efcf265e855fe510e97e38213e736558bca439bf279c5ed95aeb'
FAILED_SHA='41b39b799303f6bdc085050cd70937e648ffdb88af032adc97a5bc30dbb4af32'
APPLY_SHA='fe722e2c70de4a8cc36a8b6185d28fc070d7762ba3f93bf4cd3d4dbf4a100c59'
PROPOSAL_SHA='8f1a003479da3c744de031e8192007198e24c3a26e4112fbd047e6d5a75a6c46'
FRESH_PRODUCER_SHA='726f6cf8cb157301dd591e5cf865de5df54e69a77ecb6aba8365fc89e3e0f185'
PRESERVED_V3_SHA='336de99bebb69c76a40d44ad0dc7882d82f0657522afb8f93c2b114d4383eba9'
PRESERVED_V4_SHA='181283209dca20ba109327f64be355023b13ccd02cf948a5471c85a41c9ed71e'
SCANNER_SOURCE=Path('D:/UE/UE_5.8/Engine/Source/Runtime/AssetRegistry/Private/AssetRegistry.cpp')
SCANNER_SHA='0200285704dd44d2a43e4143d9cb78c5918c9a8f5381bc8dc946aca1534aeafe'
HISTORICAL_HELPER_SHA='7e92c8a0eb32711d58b0043440dd14b02b4443abf09e4a0ac9241a6a83c424be'
OLD_CLASS='/Script/Engine.PhysicalMaterial';PM_CLASS='/Script/PhysicsCore.PhysicalMaterial'
PM_NAMES=('PM_NonSlippery','PM_Slippery')
PM_PACKAGES=tuple(ROOT+'/Materials/PhysicsMaterials/'+n for n in PM_NAMES)
COPY_NAMES=('Car_Pickup_BackTireConfig','Car_Pickupt_FrontTireConfig')
COPY_PACKAGES=tuple(DEST+'/Models/Vehicles/Drivable/Pickup/'+n for n in COPY_NAMES)
EDGES=tuple({'package':p,'dependency':d} for p in COPY_PACKAGES for d in PM_PACKAGES)
ROUTES=tuple({'old':p,'new':DEST+p[len(ROOT):]} for p in PM_PACKAGES)
PM_FIELDS=('Friction','StaticFriction','FrictionCombineMode','bOverrideFrictionCombineMode',
 'Restitution','RestitutionCombineMode','bOverrideRestitutionCombineMode','Density',
 'SleepLinearVelocityThreshold','SleepAngularVelocityThreshold','SleepCounterThreshold',
 'RaiseMassToPower','SurfaceType','Strength','DamageModifier','DebugColor',
 'SoftCollisionMode','SoftCollisionThickness','BaseFrictionImpulse')
OPTIONS=('include_soft_package_references','include_hard_package_references','include_game_package_references',
 'include_editor_only_package_references','include_searchable_names','include_soft_management_references','include_hard_management_references')
OFFICIAL={
 'D:/UE/UE_5.8/Engine/Config/BaseEngine.ini':'dc5b359ee95ccff0ccdfa4181b2875451b4a33474c0bb896fd8fef23aed1bf8e',
 'D:/UE/UE_5.8/Engine/Source/Runtime/PhysicsCore/Public/PhysicalMaterials/PhysicalMaterial.h':'62ef424389f469dc466526c66eab3c9020455bdcd8e8ec5b7405cf6cd0deac59',
 'D:/UE/UE_5.8/Engine/Build/Build.version':'d35d3d5f4de0636fbb62386b63dee8056889fb2baf199d012dc32ee77f7a2997'}
DECLARATION='+ClassRedirects=(OldName="PhysicalMaterial",NewName="/Script/PhysicsCore.PhysicalMaterial")'


def require(ok,message):
    if not ok:raise RuntimeError('Exact Post compatibility: '+message)


def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def receipt(m,path,digest):
    path=Path(path)
    require(isinstance(digest,str) and re.fullmatch('[0-9a-f]{64}',digest) and m.sha(path)==digest,
            'Actual receipt bytes changed: '+str(path))
    return read(path)


def edge_ids(rows):return sorted((r['package'].casefold(),r['dependency'].casefold()) for r in rows)


def exact_edges(rows):
    require(len(rows)==4 and edge_ids(rows)==edge_ids(EDGES),'Only the four literal preserved opaque->PM edges are valid')


def old_edges(deps):
    return [{'package':p,'dependency':d} for p,values in deps.items() for d in values
            if d.casefold()==ROOT.casefold() or d.casefold().startswith(ROOT.casefold()+'/')]


def validate_routed_imports(original,current):
    require(set(original)==set(COPY_PACKAGES),'Exact original two opaque owner packages required')
    result=[]
    for owner in COPY_PACKAGES:
        old=original[owner]
        require(len(old)==3 and {p.casefold() for p in old}=={p.casefold() for p in PM_PACKAGES}|{'/script/physxvehicles'},
                'Original serialized PM2 plus PhysX package imports required')
        expected=[DEST+p[len(ROOT):] if p.casefold() in {x.casefold() for x in PM_PACKAGES} else p for p in old]
        require(owner in current and len(current[owner])==3
            and sorted(x.casefold() for x in current[owner])==sorted(x.casefold() for x in expected),
            'Current exact imports are not the literal two PackageRedirect result')
        result += [{'package':owner,'dependency':d} for d in current[owner] if d.casefold() in
            {(DEST+p[len(ROOT):]).casefold() for p in PM_PACKAGES}]
    require(len(result)==4,'Exactly four current routed-new PM edges required')
    return result


def expected_records(m,base):
    records=m.normalized_records(base['assets'],canonical_classes=False);seen=set()
    require(base['root']==ROOT and len(records)==1200 and len(base['maps'])==2,'Immutable original Post1200/2 only')
    for row in records:
        if row['package'] in PM_PACKAGES:
            require(row['name']==row['package'].rsplit('/',1)[-1] and row['class']==OLD_CLASS
                    and row['package'] not in seen,'Exact original PM2 class identities required')
            seen.add(row['package']);row['class']=PM_CLASS
    require(seen==set(PM_PACKAGES),'Both exact original PM records required')
    return records


def canonical_t3d(raw):
    pattern=r'(?<![A-Za-z0-9_])(/Game/Scenes/PostCity(?:/[A-Za-z0-9_]+)*(?:\.[A-Za-z0-9_:]+)?)(?![A-Za-z0-9_/.:])'
    return re.sub(pattern,lambda match:ROOT+match.group(1)[len(DEST):],raw)


def decode_export(data):
    if data.startswith(b'\xff\xfe'):return data[2:].decode('utf-16-le',errors='strict'),'utf-16-le-bom'
    if data.startswith(b'\xfe\xff'):return data[2:].decode('utf-16-be',errors='strict'),'utf-16-be-bom'
    if data.startswith(b'\xef\xbb\xbf'):return data[3:].decode('utf-8',errors='strict'),'utf-8-bom'
    return data.decode('utf-8',errors='strict'),'utf-8-no-bom'


def export_evidence(m,row):
    path=Path(row['file']);require(path.resolve().is_relative_to(TEMP.resolve()),'Actual public export outside task evidence')
    raw=path.read_bytes();text,encoding=decode_export(raw)
    require(m.sha(path)==row['sha256'] and text==row['raw'] and encoding==row['encoding'],'Full public T3D byte/decode witness differs')


def public_equal(before,after):
    require(len(before['physical_materials'])==len(after['physical_materials'])==2
            and len(before['wheel_blueprints'])==len(after['wheel_blueprints'])==2,'Exact public PM2/Wheel2 coverage')
    for left,right in zip(before['physical_materials'],after['physical_materials']):
        require(left['package'] in PM_PACKAGES and right['package']==DEST+left['package'][len(ROOT):]
            and right['path']==DEST+left['path'][len(ROOT):] and left['class']==right['class']==PM_CLASS
            and set(left['parameters'])==set(PM_FIELDS) and left['parameters']==right['parameters']
            and left['full_t3d']['raw']==canonical_t3d(right['full_t3d']['raw']),'PM19/fullT3D differs')
    for left,right in zip(before['wheel_blueprints'],after['wheel_blueprints']):
        require(right['package']==DEST+left['package'][len(ROOT):]
            and left['generated_class'] is right['generated_class'] is None
            and left['generated_class_available'] is right['generated_class_available'] is False
            and left['cdo'] is right['cdo'] is None and left['cdo_available'] is right['cdo_available'] is False
            and left['null_public_scope_observed'] is right['null_public_scope_observed'] is True,
            'Original exact null Wheel class/CDO scope changed')
        require(right['blueprint']['object']==DEST+left['blueprint']['object'][len(ROOT):]
            and right['blueprint']['class']==left['blueprint']['class']
            and left['blueprint']['raw']==canonical_t3d(right['blueprint']['raw']),'Complete Wheel Blueprint export differs')


def physical(m,folder):
    folder=Path(folder);require(folder.is_dir(),'Required physical directory missing: '+str(folder))
    require(not (getattr(folder.lstat(),'st_file_attributes',0)&0x400),'Reparse physical root not allowed')
    out={}
    for p in folder.rglob('*'):
        require(not (getattr(p.lstat(),'st_file_attributes',0)&0x400),'Reparse physical descendant not allowed')
        if p.is_file():out[p.relative_to(folder).as_posix()]={'bytes':p.stat().st_size,'sha256':m.sha(p)}
    return out


def validate_data(m,base,fresh,source,cont,applied,proposal,recovery,cleanup,cleanup_pre):
    """Pure semantic gates; all documents must first be read at their actual pins."""
    require(fresh['schema']=='post_exact_package_compatibility_fresh_witness_v5' and fresh['success'] is True
        and fresh['root']==ROOT and fresh['destination']==DEST and fresh['require_retired'] is True
        and fresh['candidate_sha256']==FRESH_PRODUCER_SHA and fresh['current_helper_sha256']==m.sha(m.__file__) and fresh['legacy_helper_sha256']==HISTORICAL_HELPER_SHA and fresh['post_contract_sha256']==m.sha(__file__)
        and fresh['errors']==[] and fresh['dirty_after']==[] and fresh['entry_restore']['success'] is True
        and fresh['raw_old_records']==[] and fresh['current_old_files']=={}
        and fresh['stored_old_dependencies_are_zero'] is True
        and fresh['source_serialized_old_addresses_are_zero'] is False
        and fresh['current_raw_old_dependency_edges']==[] and fresh['source_opaque_files_absent'] is True
        and fresh['opaque_asset_load_success_not_claimed'] is True
        and all(fresh[k]==0 for k in ('opaque_asset_object_loads','save_calls','native_calls','delete_calls'))
        and fresh['camera_render_started'] is False,'Actual clean AFTER-cleanup witness required')
    expected=expected_records(m,base)
    for key in ('target_raw_assets','target_raw_assets_after'):
        raw=fresh[key]
        require(len(raw)==1200 and m.registry_identities([dict(r,package=m.canon(r['package'],ROOT)) for r in raw])
                ==m.registry_identities(expected),'Full raw1200 identities differ beyond literal PM2 class')
    opaque=[]
    for package,name in zip(COPY_PACKAGES,COPY_NAMES):
        record={'package':package,'name':name,'class':'/Script/PhysXVehicles.TireConfig'}
        opaque.append({'record':record,'official_registry_full_name':record['class']+' '+package+'.'+name})
    require(fresh['opaque_official_registry_full_name_before']==fresh['opaque_official_registry_full_name_after']==opaque,
            'Exact public registry opaque2 identities/full object paths differ')
    exact_edges(fresh['source_original_serialized_old_edges'])
    require(fresh['source_original_serialized_copy_dependencies']==cont['historical_copy_serialized_dependencies'],
            'Immutable original serialized import graph changed')
    routed=validate_routed_imports(fresh['source_original_serialized_copy_dependencies'],fresh['all_target_dependencies'])
    require(edge_ids(routed)==edge_ids(fresh['current_exact_routed_new_pm_edges'])
        ==edge_ids(fresh['current_exact_routed_new_pm_edges_after']), 'Actual routed-new4 witness differs')
    for key in ('all_target_dependencies','all_target_dependencies_after'):
        deps=fresh[key];require(len(deps)==1200 and {r['package'] for r in fresh['target_raw_assets']}==set(deps),'Full dependency graph coverage')
        require(old_edges(deps)==[],'Any actual old dependency rejects compatibility')
        validate_routed_imports(fresh['source_original_serialized_copy_dependencies'],deps)
    require(fresh['all_target_dependencies']==fresh['all_target_dependencies_after'], 'Complete current raw graph changed')
    originals={r['package'].casefold() for r in base['assets']}
    for key in ('global_old_referencers','global_old_referencers_after'):
        refs=fresh[key];require({p.casefold() for p in refs}==originals,'Original1200 referencer coverage')
        require(not any(p.casefold() not in originals for values in refs.values() for p in values),
                'Actual outside old-root referencer remains')
    require(cont['success'] and cont['native_call_count']==1 and cont['additional_native_calls']==0
        and cont['normal_quit_eligible'] and applied['success'] and applied['editor_process_count']==0
        and applied['literal_routes']==cont['required_package_routes']==list(ROUTES)
        and applied['stored_old_dependencies_are_zero'] is False,'Once-native/Editor0 literal Config chain differs')
    exact_edges(cont['historical_copy_serialized_old_edges'])
    require(proposal['target_full_file_sha256']==recovery['target_full_file_sha256']
        ==fresh['target_full_file_sha_before']==fresh['target_full_file_sha_after']
        and len(fresh['target_full_file_sha_after'])==1200
        and fresh['full_original_backup_file_sha256']==cont['backup_full_file_sha256']
        and len(cont['backup_full_file_sha256'])==1200,'Recovered full1200/backup dataset changed')
    require(cleanup['schema']=='post_exact_routed_old_root_offline_cleanup_v3' and cleanup['success'] is True
        and cleanup['root']==ROOT and cleanup['editor_process_count']==0 and cleanup['camera_render_started'] is False
        and cleanup['deleted_files']==cleanup_pre['exact_old_files']
        and cleanup['deleted_file_count']==len(cleanup['deleted_files'])==112 and cleanup['remaining_old_file_count']==0
        and cleanup['opaque_assets_retired'] is False and cleanup['old_root_unused_claimed'] is True
        and cleanup['source_serialized_old_addresses_are_zero'] is False
        and cleanup['stored_old_dependencies_are_zero'] is True
        and cleanup['target_full_file_sha256']==fresh['target_full_file_sha_after']
        and cleanup['full_original_backup_file_sha256']==fresh['full_original_backup_file_sha256']
        and cleanup['literal_package_routes']==list(ROUTES),'Exact112 old-residual cleanup chain differs; opaque2 are preserved')
    require(cleanup_pre['schema']=='post_exact_routed_old_root_cleanup_preconditions_v3'
        and cleanup_pre['success'] is True and cleanup_pre['stored_old_dependencies_are_zero'] is True
        and cleanup_pre['raw_outside_old_edges']==[] and cleanup_pre['source_original_serialized_old_edges']==cont['historical_copy_serialized_old_edges']
        and cleanup_pre['current_all_target_dependencies']==fresh['all_target_dependencies_after']
        and edge_ids(cleanup_pre['current_exact_routed_new_pm_edges'])==edge_ids(routed), 'Actual strict current-old0 cleanup preconditions differ')
    oldfacts={r['relative']:{'bytes':r['bytes'],'sha256':r['sha256']} for r in cleanup_pre['exact_old_files']}
    require(len(oldfacts)==112 and oldfacts==cont['old_full_file_sha256']
        and len(cleanup_pre['exact_old_files'])==112, 'Cleanup literal112 file set differs from once-native checkpoint')
    require(validated_fresh_public(m,source['public_source'],fresh['public_target'],fresh['finite_acceptance_pin'])['accepted'] is True,'Fresh public/construction proof rejected')
    routes=fresh['actual_old_pm_route_loads'];require(len(routes)==2,'Actual official old-route2 loads required')
    for before,actual in zip(source['public_source']['physical_materials'],routes):
        require(actual['original_requested_object_path']==before['path']
            and actual['actual_loaded_object_path']==DEST+before['path'][len(ROOT):]
            and actual['actual_class']==PM_CLASS and actual['parameters']==before['parameters']
            and before['full_t3d']['raw']==canonical_t3d(actual['full_t3d']['raw']),'Actual oldroute PM19/fullT3D differs')
    maps={r['map']:r for r in fresh['actual_maps']};wanted={r['map'] for r in base['maps']}
    require(len(maps)==2 and set(maps)==wanted and len(fresh['raw_component_transforms'])==2,'Full actual2 map coverage')
    for before in base['maps']:
        after=maps[before['map']];path=DEST+before['map'][len(ROOT):]
        finite=validate_fresh_map(m,ORG/'baseline_PostCity_v1.json',base,before,after,fresh['raw_component_transforms'][path],fresh['finite_acceptance_pin'])
        require(finite['accepted'] is True and m.compare_map(before,finite['comparison_copy'])[0] and m.compare_component_transforms(base['component_transforms'][before['map']],finite['relative_copy']),'Full actual map finite construction comparison rejected')
    require(fresh['full_public_values_and_two_maps_relative_verified'] is True,'Fresh full public/map scope incomplete')
    return expected


def validated_asset_contract(m,root,base_path,base,actual_after_cleanup_sha256):
    """Only literalPost, actual immutable after-cleanup pin; never retirement."""
    require(root==ROOT and Path(base_path).resolve()==(ORG/'baseline_PostCity_v1.json').resolve()
        and m.sha(base_path)==BASE_SHA and read(base_path)==base,'Literal immutable Post baseline required')
    path=ORG/'post_exact_package_compatibility_fresh_after_cleanup_v5.json'
    fresh=receipt(m,path,actual_after_cleanup_sha256)
    source=receipt(m,ORG/'post_original_compatibility_public_witness_v2.json',SOURCE_SHA)
    cont=receipt(m,ORG/'PostCity_single_native1198_continuation_v1.json',CONT_SHA)
    failed=receipt(m,ORG/'PostCity_exact_opaque_compatibility_content_v4.json',FAILED_SHA)
    applied=receipt(m,ORG/'post_exact_package_compatibility_config_offline_apply_v3.json',APPLY_SHA)
    proposal=receipt(m,applied['precondition_receipt'],PROPOSAL_SHA)
    recovery=receipt(m,proposal['opaque_backup_recovery_receipt']['path'],proposal['opaque_backup_recovery_receipt']['sha256'])
    cleanup=receipt(m,fresh['cleanup_receipt']['path'],fresh['cleanup_receipt']['sha256'])
    cleanup_pre=receipt(m,cleanup['precondition_receipt'],cleanup['precondition_sha256'])
    require(failed['success'] is False and failed['native_call_count']==1 and failed['native_returned']
        and failed['save_new_external_returned'],'Preserved original native failure changed')
    for key,pin in (('continuation_receipt',CONT_SHA),('failed_native_receipt',FAILED_SHA),
            ('config_apply_receipt',APPLY_SHA),('config_proposal',PROPOSAL_SHA),('source_public_receipt',SOURCE_SHA),('baseline',BASE_SHA)):
        require(fresh[key]['sha256']==pin,'Fresh immutable link differs: '+key)
    require(applied['continuation_receipt']['sha256']==CONT_SHA and applied['failed_native_receipt']['sha256']==FAILED_SHA
        and proposal['continuation_receipt']['sha256']==CONT_SHA and recovery['continuation_receipt']['sha256']==CONT_SHA
        and fresh['opaque_backup_recovery_receipt']==proposal['opaque_backup_recovery_receipt']
        and cleanup['config_apply_receipt']['sha256']==APPLY_SHA,'Actual recovery/config/cleanup chain link differs')
    expected=validate_data(m,base,fresh,source,cont,applied,proposal,recovery,cleanup,cleanup_pre)
    require(fresh['preserved_v3_failure']['sha256']==PRESERVED_V3_SHA
        and m.sha(fresh['preserved_v3_failure']['path'])==PRESERVED_V3_SHA,'Actual scanner diagnostic history changed')
    require(fresh['preserved_v4_failure']['sha256']==PRESERVED_V4_SHA and m.sha(fresh['preserved_v4_failure']['path'])==PRESERVED_V4_SHA and read(fresh['preserved_v4_failure']['path'])['success'] is False,'Preserved actual v4 strict failure changed')
    scanner=fresh['official_scanner_package_redirect_source']
    require(Path(scanner['path']).resolve()==SCANNER_SOURCE.resolve() and scanner['sha256']==SCANNER_SHA
        and m.sha(SCANNER_SOURCE)==SCANNER_SHA and scanner['line']==7728,'Official AR package redirect mechanism changed')
    for p,digest in OFFICIAL.items():require(m.sha(p)==digest,'Official class/build source changed')
    require(Path(next(iter(OFFICIAL))).read_text(encoding='utf-8-sig').splitlines()[868]==DECLARATION,'Exact official PM class declaration line869 differs')
    for key in ('engine_build','official_config_repeated_section_source'):
        pin=proposal[key];require(m.sha(pin['path'])==pin['sha256'],'Official Config parser/build changed')
    require(cleanup_pre['candidate_sha256']=='caaa86eeb9da084f94415daa26f8ddd4b5b58a590576baaf8fad516d2313df28'
        and Path(cleanup['precondition_receipt']).resolve()==(ORG/'post_exact_routed_old_root_cleanup_preconditions_v3.json').resolve()
        and Path(fresh['cleanup_receipt']['path']).resolve()==(ORG/'post_exact_routed_old_root_offline_cleanup_v3.json').resolve(),
            'Only reviewed literal Post cleanup producer and receipts accepted')
    require(cleanup['fresh_success_receipt']==cleanup_pre['fresh_success_receipt'], 'Actual cleanup/before-cleanup fresh link differs')
    before_cleanup=receipt(m,cleanup_pre['fresh_success_receipt']['path'],cleanup_pre['fresh_success_receipt']['sha256'])
    require(before_cleanup['schema']=='post_exact_package_compatibility_fresh_witness_v5'
        and before_cleanup['candidate_sha256']==FRESH_PRODUCER_SHA and before_cleanup['success'] is True
        and before_cleanup['current_helper_sha256']==m.sha(m.__file__) and before_cleanup['post_contract_sha256']==m.sha(__file__) and before_cleanup['finite_acceptance_pin']==fresh['finite_acceptance_pin']
        and before_cleanup['require_retired'] is False and before_cleanup['stored_old_dependencies_are_zero'] is True
        and before_cleanup['target_full_file_sha_after']==fresh['target_full_file_sha_after']
        and before_cleanup['all_target_dependencies_after']==fresh['all_target_dependencies_after'], 'Actual pre/post cleanup unchanged1200 graph/files link differs')
    require(m.sha(applied['config_target'])==applied['config_after_sha256'],'Actual route Config bytes changed')
    config_text,_=decode_export(Path(applied['config_target']).read_bytes())
    actual_lines=[line.strip() for line in config_text.splitlines() if line.strip().startswith('+PackageRedirects=') and ROOT in line]
    route_lines=['+PackageRedirects=(OldName="'+r['old']+'",NewName="'+r['new']+'")' for r in ROUTES]
    require(actual_lines==route_lines, 'Only exact two literal Post PackageRedirect declarations allowed')
    config=physical(m,m.PROJECT/'Config');original=proposal['whole_config_before']
    require(set(config)==set(original) and all(config[k]==original[k] for k in config if k!='DefaultEngine.ini')
        and physical(m,applied['whole_config_backup'])==original and config==cleanup['whole_config_current'],'Unrelated Config or original whole backup changed')
    require(physical(m,m.PROJECT/'Content/Scenes/PostCity')==fresh['target_full_file_sha_after']
        and physical(m,TEMP/'rollback/Content/PostCity')==fresh['full_original_backup_file_sha256'],'Actual full target/backup1200 bytes changed')
    old=m.PROJECT/'Content/PostCity';require(not old.exists() or not any(p.is_file() for p in old.rglob('*')),'Old source physical files remain')
    require(len(cont['opaque_file_copy_facts'])==2,'Exact retained opaque2 facts required')
    for row in cont['opaque_file_copy_facts']:
        require(row['original_record']['package']==ROOT+'/Models/Vehicles/Drivable/Pickup/'+row['original_record']['name']
            and row['original_record']['name'] in COPY_NAMES and row['original_record']['class']=='/Script/PhysXVehicles.TireConfig'
            and not Path(row['source']).exists() and m.sha(row['backup'])==m.sha(row['destination'])==row['sha256']
            and Path(row['backup']).stat().st_size==Path(row['destination']).stat().st_size==row['bytes'],'Opaque2 literal preservation/sourceabsence differs')
    for public in (source['public_source'],fresh['public_target']):
        for row in public['physical_materials']:export_evidence(m,row['full_t3d'])
        for row in public['wheel_blueprints']:export_evidence(m,row['blueprint'])
    for row in fresh['actual_old_pm_route_loads']:export_evidence(m,row['full_t3d'])
    witness={'schema':'post_exact_package_compatibility_contract_v2','root':ROOT,'destination':DEST,
        'fresh_after_cleanup_receipt':{'path':str(path),'sha256':actual_after_cleanup_sha256},
        'baseline_sha256':BASE_SHA,'source_public_receipt':{'path':str(ORG/'post_original_compatibility_public_witness_v2.json'),'sha256':SOURCE_SHA},
        'config_apply_receipt':{'path':str(ORG/'post_exact_package_compatibility_config_offline_apply_v3.json'),'sha256':APPLY_SHA},
        'cleanup_receipt':fresh['cleanup_receipt'],'opaque_backup_recovery_receipt':fresh['opaque_backup_recovery_receipt'],
        'literal_package_routes':list(ROUTES),'original_serialized_old_dependency_edges':fresh['source_original_serialized_old_edges'],
        'original_serialized_old_dependency_count':4,'source_serialized_old_addresses_are_zero':False,
        'current_raw_old_dependency_edges':[],'current_raw_old_dependency_count':0,'stored_old_dependencies_are_zero':True,
        'current_exact_routed_new_pm_edges':fresh['current_exact_routed_new_pm_edges_after'],
        'validated_routed_new_dependency_count':4,'unresolved_old_dependency_count':0,
        'finite_pm2_registry_class_pairs':[{'package':p,'old_class':OLD_CLASS,'new_class':PM_CLASS} for p in PM_PACKAGES],
        'actual_old_pm_route_loads':fresh['actual_old_pm_route_loads'],'opaque_recovered_file_facts':fresh['opaque_recovered_file_facts'],
        'opaque_assets_retired':False,'opaque_asset_load_success_not_claimed':True,'retirement_contract':False,
        'current_helper_sha256':m.sha(m.__file__),'historical_producer_helper_sha256':HISTORICAL_HELPER_SHA,'finite_acceptance_pin':fresh['finite_acceptance_pin'],'finite_map_comparison_witnesses':fresh['finite_map_comparison_witnesses'],'raw_records_preserved':True,'actor_classes_changed':False,'contract_sha256':m.sha(__file__)}
    return expected,witness


def primitive(value):
    if value is None or isinstance(value,(str,bool,int,float)):return value
    if hasattr(value,'export_text'):return str(value.export_text())
    if hasattr(value,'name') and hasattr(value,'value'):return {'name':str(value.name),'value':value.value}
    raise RuntimeError('Required PM public value unsupported: '+type(value).__name__)


def validate_live(u,m,witness,expected):
    """No map/opaque loads; actual current AR plus official supported PM2 route loads."""
    require(witness['root']==ROOT and witness['schema']=='post_exact_package_compatibility_contract_v2','Validated literal compatibility witness required')
    registry=u.AssetRegistryHelpers.get_asset_registry();require(not registry.is_loading_assets(),'Registry loading')
    raw=[m.asset_record(a) for a in registry.get_assets_by_path(DEST,recursive=True)]
    filtered=[m.asset_record(a) for a in m.assets(u,DEST)]
    require(not registry.get_assets_by_path(ROOT,recursive=True) and len(raw)==len(filtered)==1200
        and m.registry_identities(raw)==m.registry_identities(filtered)
        and m.registry_identities([dict(r,package=m.canon(r['package'],ROOT)) for r in raw])==m.registry_identities(expected),'Live raw old0/new1200 complete identities differ')
    options=u.AssetRegistryDependencyOptions()
    for name in OPTIONS:options.set_editor_property(name,True)
    deps={r['package']:sorted(str(p) for p in registry.get_dependencies(r['package'],options) or []) for r in raw}
    edges=old_edges(deps);require(edges==[],'Current live raw old dependencies are not zero')
    fresh=receipt(m,witness['fresh_after_cleanup_receipt']['path'],witness['fresh_after_cleanup_receipt']['sha256'])
    require(deps==fresh['all_target_dependencies_after'],'Live full1200 import graph changed from actual fresh proof')
    routed=validate_routed_imports(fresh['source_original_serialized_copy_dependencies'],deps)
    source=receipt(m,witness['source_public_receipt']['path'],SOURCE_SHA);obj=None;loads=[]
    try:
        for before in source['public_source']['physical_materials']:
            obj=u.load_object(None,before['path'])
            require(obj is not None and str(obj.get_path_name())==DEST+before['path'][len(ROOT):]
                and str(obj.get_class().get_path_name())==PM_CLASS,'Current official old PM path does not resolve to exact supported destination')
            params={field:primitive(obj.get_editor_property(field)) for field in PM_FIELDS}
            require(params==before['parameters'],'Current supported PM19 public values changed')
            loads.append({'old':before['path'],'actual':str(obj.get_path_name()),'class':PM_CLASS,'parameters':params});obj=None
    finally:obj=None;gc.collect()
    require(m.dirty(u)==[],'Readonly supported route checks dirtied packages')
    return dict(witness,live_current_raw_old_dependency_edges=edges,live_current_exact_routed_new_pm_edges=routed,live_supported_route_loads=loads,
        opaque_asset_object_loads=0,live_reference_options={k:bool(options.get_editor_property(k)) for k in OPTIONS})


def validate_global_raw_edges(raw,witness):
    # Generic global old0 remains strict, even for this compatible scene.
    require(witness['schema']=='post_exact_package_compatibility_contract_v2' and witness['root']==ROOT
        and witness['stored_old_dependencies_are_zero'] is True and raw==[],
        'All-project current old dependency graph must remain empty')
    return {'stale_scene_dependencies':[], 'post_package_compatibility_witness':witness}

# Immutable finite construction mechanism, independent of package preservation.
MECHANISM_PATH=TEMP/'ue_post_city_construction_finite_contract_candidate_v1.py'
MECHANISM_SHA='6aed3503bc1fef8e1e2324b5f4833660b370196336a25aeb3ea7fe97d61bb175'
_MECHANISM_CACHE=None
def mechanism(m):
    import importlib.util,sys
    global _MECHANISM_CACHE
    require(m.sha(MECHANISM_PATH)==MECHANISM_SHA,'Finite mechanism code changed')
    if _MECHANISM_CACHE is not None:return _MECHANISM_CACHE
    if str(TEMP) not in sys.path:sys.path.insert(0,str(TEMP))
    spec=importlib.util.spec_from_file_location('post_complete_finite_construction_runtime',MECHANISM_PATH)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);_MECHANISM_CACHE=module;return module

def validated_fresh_public(m,source_public,public_target,acceptance_pin):
    public_equal(source_public,public_target)
    return mechanism(m).validated_fresh_public(m,source_public,public_target,acceptance_pin)

def validate_fresh_map(m,base_path,base,before,after,relative,acceptance_pin):
    return mechanism(m).validate_fresh_map(m,base_path,base,before,after,relative,acceptance_pin)

def validated_map_comparison(u,m,root,base_path,base,before,after,raw_relative):
    require(root==ROOT,'Finite map contract only literal Post')
    fresh_path=ORG/'post_exact_package_compatibility_fresh_after_cleanup_v5.json'
    fresh=read(fresh_path)
    finite=validate_fresh_map(m,base_path,base,before,after,raw_relative,fresh['finite_acceptance_pin'])
    require(finite['accepted'] is True,'Actual map construction comparison rejected')
    return finite['comparison_copy'],finite['relative_copy'],finite['witness']
