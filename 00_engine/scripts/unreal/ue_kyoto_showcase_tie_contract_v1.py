"""Finite comparison-copy contract, no UE imports/operations or raw rewriting.

Only three pinned Showcase duplicate-name/class pairs may permute their two
complete captured actor records. Every other field/list/value remains exact.
This proves the existing capture schema, not uncaptured actor Level ownership.
"""
import copy,hashlib,json
from pathlib import Path
ORG=Path('D:/UE/Lance_Work/00_engine/outputs/scene_folder_organization_20261012_v1')
ROOT='/Game/KyotoAlley'
SHOWCASE=ROOT+'/Maps/KyotoAlley_Showcase'
DAY=ROOT+'/Maps/Sublevels/KyotoAlley_Showcase_DayLight'
NIGHT=ROOT+'/Maps/Sublevels/KyotoAlley_Showcase_NightLight'
BASE=ORG/'baseline_KyotoAlley_v1.json'
BASE_SHA='9a2c02668d75f5119ddf8fdb0865c79e4aa3392747bb4a9094e2222ff7640a51'
FAILED=ORG/'verified_KyotoAlley_vdriver_20261012T211827402688Z_verify_KyotoAlley.json'
FAILED_SHA='85cabb50c3d0dedf046ff000202a5b04e65325eff645c563b8644535a85f667a'
TIES=(('ExponentialHeightFog_1','/Script/Engine.ExponentialHeightFog',(43,44)),
      ('LightSource','/Script/Engine.DirectionalLight',(82,83)),
      ('SpotLight_1','/Script/Engine.SpotLight',(519,520)))

def require(ok,message):
    if not ok:raise RuntimeError(message)

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def encoded(value):
    # Full recursive JSON, no discarded fields, aliases, float tolerance, or
    # sorting of semantic arrays. Dict key order alone has no JSON meaning.
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)

def source_fixture(base_path,base):
    require(Path(base_path).resolve()==BASE.resolve() and sha(BASE)==BASE_SHA,'Exact immutable755/4 Kyoto source baseline required')
    frozen=json.loads(BASE.read_text(encoding='utf-8-sig'))
    require(encoded(base)==encoded(frozen) and frozen['success'] is True and len(frozen['assets'])==755 and len(frozen['maps'])==4,'Source baseline differs')
    maps={x['map']:x for x in frozen['maps']}
    require(set(maps)=={ROOT+'/Maps/KyotoAlley_Overview',SHOWCASE,DAY,NIGHT},'Only exact four retained maps')
    source=maps[SHOWCASE]
    require(source['actor_count']==len(source['actors'])==533 and source['levels']==[
        SHOWCASE+'.KyotoAlley_Showcase:PersistentLevel',DAY+'.KyotoAlley_Showcase_DayLight:PersistentLevel',
        NIGHT+'.KyotoAlley_Showcase_NightLight:PersistentLevel'],'Exact Showcase533/three loaded Levels required')
    for name,actor_class,indices in TIES:
        positions=[i for i,a in enumerate(source['actors']) if a['name']==name]
        require(tuple(positions)==indices and all(source['actors'][i]['class']==actor_class for i in positions),'Pinned source tie identities differ')
        require(all(a['components']==[] for a in source['actors'] if a['name']==name),'Pinned tie static-component contents differ')
        relative=[a for a in frozen['component_transforms'][SHOWCASE] if a['name']==name]
        require(relative==[{'name':name,'components':[]},{'name':name,'components':[]}],'Original relative tie records differ')
    return source,maps

def validated_kyoto_tie_comparison(m,root,base_path,base,before,after):
    """Drop-in before generic compare_map. Return (comparison_copy,witness).

    m is accepted for the parent verifier's adapter shape, not used to normalize
    any value. Maps other than the exact Kyoto Showcase use the ordinary path.
    """
    if root!=ROOT or before.get('map')!=SHOWCASE:return after,None
    source,_=source_fixture(base_path,base)
    require(encoded(before)==encoded(source),'Before map is not pinned full Showcase source')
    require(after.get('map')==SHOWCASE and after.get('actor_count')==len(after.get('actors',[]))==533,'Actual Showcase map/count changed')
    result=copy.deepcopy(after);pairs=[]
    for name,actor_class,indices in TIES:
        positions=[i for i,a in enumerate(after['actors']) if a.get('name')==name]
        require(tuple(positions)==indices and all(after['actors'][i].get('class')==actor_class for i in positions),'Actual exact same-name/class pair identity changed')
        unused=list(positions);mapping=[]
        for target in indices:
            key=encoded(source['actors'][target])
            matches=[i for i in unused if encoded(after['actors'][i])==key]
            require(len(matches)==1,'No unique complete actor-content bijection: '+name)
            origin=matches[0];unused.remove(origin);result['actors'][target]=copy.deepcopy(after['actors'][origin])
            mapping.append({'baseline_index':target,'raw_actual_index':origin,'complete_actor_sha256':hashlib.sha256(key.encode('utf-8')).hexdigest()})
        require(not unused,'Unmatched actual tie actor')
        pairs.append({'name':name,'class':actor_class,'count':2,'mapping':mapping})
    # This is deliberately stricter than generic MID numeric tolerance. The
    # exceptional comparison copy can differ only by these literal permutations.
    require(encoded(result)==encoded(source),'Other complete map content differs; tie contract cannot accept it')
    witness={'schema':'kyoto_showcase_exact_actor_tie_witness_v1','baseline_sha256':BASE_SHA,'map':SHOWCASE,
             'actor_count':533,'permitted_groups':pairs,'contract_path':str(Path(__file__)),'contract_sha256':sha(__file__),
             'raw_actual_map_sha256':hashlib.sha256(encoded(after).encode('utf-8')).hexdigest(),
             'comparison_map_sha256':hashlib.sha256(encoded(result).encode('utf-8')).hexdigest(),
             'scope':'Only permutation of three literal pairs of complete captured actor records; all other fields/arrays/values and names/classes exact; raw evidence unchanged',
             'relative_transform_scope':'Six original duplicate relative rows contain empty component arrays; ordinary complete component-transform comparison remains strict',
             'ownership_limit':'Original capture omitted actor owningLevel. No actor-to-Level association is inferred from enumeration or standalone world transforms.'}
    return result,witness

def capture_public_tie_level_identities(u):
    """Optional root-only read of already loaded Showcase, no map switch/save.

    GetLevel is official BlueprintCallable Actor.h:3370-3371. This does not
    retroactively fill immutable source fields. Root would need source+target
    witnesses to establish ownership, independently of this comparison contract.
    """
    actors=[];actor=None;level=None;result=[]
    try:
        actors=list(u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors())
        for actor in actors:
            if actor.get_name() in {x[0] for x in TIES}:
                level=actor.get_level()
                result.append({'name':actor.get_name(),'class':actor.get_class().get_path_name(),
                               'actor_path':actor.get_path_name(),'owning_level':level.get_path_name()})
                level=None
        return json.loads(json.dumps(result))
    finally:
        actors.clear();actor=None;level=None
        import gc;gc.collect()
