"""One registered preset: historical names/styles constrain actual new capture.

Historical reports do not supply current topology or magnitude bounds. New
counts/ordered-face hashes are measured in this case and then held strict.
"""
import math


def load(reference,asset,api):
    if api.sha256_file(reference['path'])!=reference['sha256']:raise ValueError('Historical selected-lash contract changed')
    data=api.read_json(reference['path']);rows=[r for r in data['assets']if r['asset_id']==asset['asset_id']]
    if len(data['assets'])!=9 or len(rows)!=1:raise ValueError('Exactly one existing nine-pool asset required')
    row=rows[0]
    if row['current_asset']['sha256']!=asset['sha256']or api.sha256_file(asset['path'])!=asset['sha256']:raise ValueError('Current registered selected asset differs')
    parts=row['historically_observed_parts'];pairs=[]
    if row.get('part_signature_equal_across_all_six_cases')is not True or row['observed_part_count']!=len(parts):raise ValueError('Consistent observed historical inventory required')
    if any(m.get('expected')!=0 or m.get('actual')!=1 for m in row['style_morphs']):raise ValueError('Observed selected-style0_to1 reference required')
    for part in parts:
        if part['avatar_part_type']!='9'or not part['mesh_names']:raise ValueError('Historical exact type9 object/mesh names required')
        pairs.extend(('avatar/9:'+part['name'],name)for name in part['mesh_names'])
    styles=[r['id']for r in row['style_morphs']]
    if len(styles)!=2 or len(set(styles))!=2 or len(set(pairs))!=len(pairs):raise ValueError('Exact selected two-style/named inventory required')
    return {'asset':{k:asset[k]for k in('asset_id','path','sha256')},'historical_reference':reference,
        'expected_parts':parts,'expected_mesh_pairs':[list(p)for p in pairs],'selected_style_ids':styles,
        'all_style_ids':sorted({m['id']for a in data['assets']for m in a['style_morphs']}),
        'historical_asset_sha_recorded':row['historical_asset_sha256_recorded'],
        'topology_source':'This actual new-part capture only; historical topology absent.','magnitude_upper_bound_registered':False}


def mesh_key(row):return tuple(row[k]for k in('owner','name','vertex_count','face_count','faces_sha256'))
def part_key(row):return tuple(row[k]for k in('owner','type','name'))


def bind_additions(before,after,contract):
    old={mesh_key(r)for r in before['meshes']};allrows=[mesh_key(r)for r in after['meshes']]
    parts_old={part_key(r)for r in before['parts']};parts_after={part_key(r)for r in after['parts']}
    expected_parts={('avatar','9',p['name'])for p in contract['expected_parts']}
    added=[r for r in after['meshes']if mesh_key(r)not in old]
    pairs=[(r['owner'],r['name'])for r in added];wanted={tuple(p)for p in contract['expected_mesh_pairs']}
    if (len(old)!=len(before['meshes'])or len(set(allrows))!=len(allrows)or not old<=set(allrows)
            or parts_after!=parts_old|expected_parts or parts_old&expected_parts
            or len(parts_after)!=len(after['parts'])or len(parts_old)!=len(before['parts'])
            or set(pairs)!=wanted or len(pairs)!=len(wanted)):
        raise ValueError('Actual new inventory differs from exact selected historical object/mesh names or removes original support')
    for row in added:
        if row['vertex_count']<=0 or row['face_count']<=0 or len(row['faces_sha256'])!=64:raise ValueError('Actual positive topology signature required')
    return {'asset':contract['asset'],'added_meshes':[{k:r[k]for k in('owner','name','vertex_count','face_count','faces_sha256')}for r in added],
        'added_parts':[dict(owner=o,type=t,name=n)for o,t,n in sorted(expected_parts)],'actual_topology_measured':True,'magnitude_upper_bound_registered':False}


def compare_existing(before,after,addition,comparator):
    additions={mesh_key(r)for r in addition['added_meshes']};owners={r['owner']for r in addition['added_meshes']};parts={part_key(r)for r in addition['added_parts']}
    oldkeys=[mesh_key(r)for r in before['meshes']];keys=[mesh_key(r)for r in after['meshes']]
    oldparts=[part_key(r)for r in before['parts']];newparts=[part_key(r)for r in after['parts']]
    structure=len(set(oldkeys))==len(oldkeys)and len(set(keys))==len(keys)and set(keys)==set(oldkeys)|additions and set(newparts)==set(oldparts)|parts and len(set(newparts))==len(newparts)
    oldt={(r['owner'],r['space'])for r in before.get('owner_transforms',[])};newt=[(r['owner'],r['space'])for r in after.get('owner_transforms',[])]
    transform=not before.get('owner_transform_errors')and not after.get('owner_transform_errors')and len(set(newt))==len(newt)and set(newt)==oldt|{(o,s)for o in owners for s in('local','world')}
    def original(s):
        return dict(s,meshes=sorted([m for m in s['meshes']if m['owner']not in owners],key=mesh_key),
            parts=sorted([p for p in s['parts']if part_key(p)not in parts],key=part_key),
            owner_transforms=[t for t in s.get('owner_transforms',[])if t['owner']not in owners])
    result=comparator(original(before),original(after))
    result.update(allowed_new_parts_exact=structure,added_owner_transforms_observed=bool(transform),observed_added_meshes=addition['added_meshes'],passed=result['passed']and structure and bool(transform))
    return result


def capture_styles(avatar,contract,api):
    component,catalog,_=api.morph_catalog(avatar);result={}
    for identifier,item in catalog.items():
        categories=[str(c).replace('\\','/').lower()for c in item.get('categories',[])]
        if identifier in contract['all_style_ids']or any(c.startswith('actor/eyelash')for c in categories):
            weight=float(component.GetShapingMorphWeight(identifier))
            if not math.isfinite(weight):raise ValueError('Nonfinite actual lash style weight')
            result[identifier]={'weight':weight,'categories':item.get('categories',[]),'display':item.get('display')}
    return result


def check_selected_styles(before,after,contract):
    selected=set(contract['selected_style_ids']);changes=[]
    for identifier in selected:
        if identifier not in after or abs(after[identifier]['weight']-1)>1e-7:raise ValueError('Selected actual style control did not read back1')
        if identifier in before and abs(before[identifier]['weight'])>1e-7:raise ValueError('Selected style source was already nonzero')
    for identifier in set(before)|set(after):
        a=before.get(identifier);b=after.get(identifier)
        if identifier in selected:continue
        left=a['weight']if a else 0.;right=b['weight']if b else 0.
        if abs(left-right)<=1e-7:continue
        categories=' '.join((a or b).get('categories',[])).replace('\\','/').lower()
        if identifier not in contract['all_style_ids']and 'cc5 characters'in categories and abs(left-1)<=1e-7 and abs(right)<=1e-7:
            changes.append({'id':identifier,'from':left,'to':right,'reason':'actual identity eyelash1_to0 replaced by selected preset'})
        else:raise ValueError('Unselected lash style changed')
    return {'passed':True,'selected_ids':sorted(selected),'selected_source_absent_ids':sorted(selected-set(before)),
        'identity_lash_replacements':changes,'scope':'Actual SDK weights; absence is recorded, not claimed as an observed zero.'}


def check_persisted_styles(reference,actual):
    if set(reference)!=set(actual)or any(abs(reference[k]['weight']-actual[k]['weight'])>1e-7 for k in reference):raise ValueError('Applied selected-lash style weights changed during persistence')
    return {'passed':True,'actual_controls_compared':len(reference),'weight_tolerance':1e-7}
