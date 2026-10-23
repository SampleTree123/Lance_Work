"""Registered selected-lash pixel scope, constrained to exact named object/meshes.

Keeps existing original material scope and adds only the registered exact object/mesh names.
Standard6 channels only. No texture write, substitution, allowance or repair.
"""
import importlib
import json
import os
import cc_refresh_material_pixels_v1 as original

def mesh_owners(contract):
    result={}
    for part in contract['expected_parts']:
        for mesh in part['mesh_names']:result.setdefault(mesh,set()).add(part['name'])
    return result


class Component:
    def __init__(self,component,allowed_new=()):self.component=component;self.allowed_new=set(allowed_new)
    def __getattr__(self,name):return getattr(self.component,name)
    def GetMaterialNames(self,mesh):
        return [name for name in(self.component.GetMaterialNames(mesh)or[])if original.in_scope(str(mesh),str(name))or str(mesh)in self.allowed_new]


class Api:
    def __init__(self,api,contract):
        self.contract=contract;self.mapping=mesh_owners(contract);self.api=api;self.MATERIAL_TEXTURE_CHANNELS=[(n,e)for n,e in api.MATERIAL_TEXTURE_CHANNELS if n in original.CHANNELS]
    def __getattr__(self,name):return getattr(self.api,name)
    def hair_material_component(self,avatar,owner):
        component,source=self.api.hair_material_component(avatar,owner)
        allowed=set(self.mapping)if owner is avatar else set()
        if owner is not avatar:
            getter=getattr(owner,'GetAvatarPartType',None)
            if callable(getter)and int(getter())==9:allowed={m for m,objects in self.mapping.items()if str(owner.GetName())in objects}
        return (Component(component,allowed)if component is not None else None),source


def capture(avatar,root,label,api,require_new,contract):
    if not label.replace('_','').isalnum():raise ValueError('Simple unique pixel checkpoint label required')
    exporter=importlib.import_module('cc_skin_detail_experiment_v1')
    destination=os.path.join(root,'pixels_'+label);store=os.path.join(root,'pixel_objects')
    if os.path.exists(destination):raise ValueError('Refuse existing pixel checkpoint')
    os.makedirs(store,exist_ok=True);scoped=Api(api,contract);capture_error=None
    try:result=exporter.capture_materials(avatar,destination,scoped)
    except Exception as exc:
        capture_error=str(exc);path=os.path.join(destination,'materials.json')
        if os.path.isfile(path):
            with open(path,encoding='utf-8-sig')as handle:result=json.load(handle)
        else:result={'materials':[],'observation_errors':[{'stage':'capture','error':str(exc)}]}
    decode_errors=[]
    for row in result['materials']:
        for channel,record in row['textures'].items():
            original.object_record(record,store,api);record['sha256_kind']='exported_png_bytes'
            try:
                image=api.QtGui.QImage(record['path']);record['file_decoded']=not image.isNull()
                record['decoded_width'],record['decoded_height']=int(image.width()),int(image.height())
                if image.isNull()or(image.width(),image.height())!=(record['width'],record['height']):raise ValueError('Saved PNG decode/dimension mismatch')
            except Exception as exc:
                record['file_decoded']=False;decode_errors.append(dict(owner=row['owner'],mesh=row['mesh'],material=row['material'],channel=channel,error=str(exc)))
        for record in row.get('missing_textures',{}).values():
            if record.get('evidence'):original.object_record(record['evidence'],store,api)
    errors=result.get('observation_errors',[])
    missing=original.CHANNELS-{name for name,_ in scoped.MATERIAL_TEXTURE_CHANNELS}
    if missing:errors.append(dict(stage='texture:channel_scope',error='Required channels absent: '+','.join(sorted(missing))))
    texture_errors=[e for e in errors if str(e.get('stage','')).startswith('texture:')or e.get('stage')in original.CHANNELS or e.get('stage')=='capture']
    skins={row['material']for row in result['materials']if row['mesh']=='CC_Base_Body'and row['material']in original.SKINS and row['textures'].get('diffuse',{}).get('file_decoded')}
    support={row['mesh']for row in result['materials']if row['mesh']in original.SUPPORT_MESHES}
    new={row['mesh']for row in result['materials']if new_lash_row(row,contract)and any(x.get('file_decoded')for x in row['textures'].values())}
    native=[r for r in result['materials']if(r['owner'],r['mesh'],r['material'])==('avatar','CC_Base_Body','Std_Eyelash')]
    keys=[(r['owner'],r['mesh'],r['material'])for r in result['materials']]
    complete=not texture_errors and not decode_errors and skins==original.SKINS and original.EYE_SUPPORT_MESHES|{'CC_Base_Tongue'}<=support and len(native)==1 and len(keys)==len(set(keys))and(new==set(mesh_owners(contract)) if require_new else not new)
    result.update(checkpoint=label,capture_exception=capture_error,decode_errors=decode_errors,texture_observation_errors=texture_errors,
        metadata_observation_errors=[e for e in errors if e not in texture_errors],pixel_capture_complete=complete,
        skin_diffuse_coverage=sorted(skins),support_mesh_coverage=sorted(support),new_lash_mesh_pixel_coverage=sorted(new),
        selected_lash_material_keys=[list(k)for k in keys if authorized_lash(dict(owner=k[0],mesh=k[1],material=k[2]),contract)],
        scope='Original scope plus exact registered selected-lash object/mesh names; six standard channels, availability/dimensions/file-decoded RGBA only. Custom shader slots outside scope.',
        channel_scope=sorted(original.CHANNELS),material_writes=False,exporter_implementation_sha256=api.sha256_file(exporter.__file__))
    api.write_json(result,os.path.join(destination,'materials.json'));return result


def new_lash_row(row,contract):
    objects=mesh_owners(contract).get(row['mesh'],set())
    return bool(objects)and row['owner']in {'avatar'}|{'avatar/GetAvatarParts:'+name for name in objects}
def authorized_lash(row,contract):return(row['owner'],row['mesh'],row['material'])==('avatar','CC_Base_Body','Std_Eyelash')or new_lash_row(row,contract)


def compare_nonlash(before,after,api,contract):
    # Inventory additions are authorized only for the precise new mesh names;
    # original native-lash material key itself must still exist in the full capture.
    old=dict(before,materials=[r for r in before['materials']if not authorized_lash(r,contract)])
    new=dict(after,materials=[r for r in after['materials']if not authorized_lash(r,contract)])
    result=original.compare_pixels(old,new,api)
    result['authorized_selected_lash_keys_before']=[(r['owner'],r['mesh'],r['material'])for r in before['materials']if authorized_lash(r,contract)]
    result['authorized_selected_lash_keys_after']=[(r['owner'],r['mesh'],r['material'])for r in after['materials']if authorized_lash(r,contract)]
    return result


def compare_all(before,after,api):return original.compare_pixels(before,after,api)
