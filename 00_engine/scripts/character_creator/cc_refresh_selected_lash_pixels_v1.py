"""Exact selected-lash pixel scope; read-only SaveFile/decoded PNG evidence.

Keeps existing original material scope and adds only the two evidenced meshes.
Standard6 channels only. No texture write, substitution, allowance or repair.
"""
import importlib
import json
import os
import cc_refresh_material_pixels_v1 as original

NEW_MESHES=frozenset(('Lash_Low_Bushy','Lash_Up_Bushy'))


class Component:
    def __init__(self,component,allow_new=True):self.component=component;self.allow_new=allow_new
    def __getattr__(self,name):return getattr(self.component,name)
    def GetMaterialNames(self,mesh):
        return [name for name in(self.component.GetMaterialNames(mesh)or[])if original.in_scope(str(mesh),str(name))or self.allow_new and str(mesh)in NEW_MESHES]


class Api:
    def __init__(self,api):
        self.api=api;self.MATERIAL_TEXTURE_CHANNELS=[(n,e)for n,e in api.MATERIAL_TEXTURE_CHANNELS if n in original.CHANNELS]
    def __getattr__(self,name):return getattr(self.api,name)
    def hair_material_component(self,avatar,owner):
        component,source=self.api.hair_material_component(avatar,owner)
        allow_new=owner is avatar
        if not allow_new:
            getter=getattr(owner,'GetAvatarPartType',None)
            allow_new=callable(getter)and int(getter())==9 and str(owner.GetName())in NEW_MESHES
        return (Component(component,allow_new)if component is not None else None),source


def capture(avatar,root,label,api,require_new):
    if not label.replace('_','').isalnum():raise ValueError('Simple unique pixel checkpoint label required')
    exporter=importlib.import_module('cc_skin_detail_experiment_v1')
    destination=os.path.join(root,'pixels_'+label);store=os.path.join(root,'pixel_objects')
    if os.path.exists(destination):raise ValueError('Refuse existing pixel checkpoint')
    os.makedirs(store,exist_ok=True);scoped=Api(api);capture_error=None
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
    new={row['mesh']for row in result['materials']if new_lash_row(row)and any(x.get('file_decoded')for x in row['textures'].values())}
    native=[r for r in result['materials']if(r['owner'],r['mesh'],r['material'])==('avatar','CC_Base_Body','Std_Eyelash')]
    keys=[(r['owner'],r['mesh'],r['material'])for r in result['materials']]
    complete=not texture_errors and not decode_errors and skins==original.SKINS and original.EYE_SUPPORT_MESHES|{'CC_Base_Tongue'}<=support and len(native)==1 and len(keys)==len(set(keys))and(new==NEW_MESHES if require_new else not new)
    result.update(checkpoint=label,capture_exception=capture_error,decode_errors=decode_errors,texture_observation_errors=texture_errors,
        metadata_observation_errors=[e for e in errors if e not in texture_errors],pixel_capture_complete=complete,
        skin_diffuse_coverage=sorted(skins),support_mesh_coverage=sorted(support),new_lash_mesh_pixel_coverage=sorted(new),
        selected_lash_material_keys=[list(k)for k in keys if k==('avatar','CC_Base_Body','Std_Eyelash')or k[1]in NEW_MESHES],
        scope='Original scope plus exact two selected-lash mesh names; six standard channels, availability/dimensions/file-decoded RGBA only. Custom shader slots outside scope.',
        channel_scope=sorted(original.CHANNELS),material_writes=False,exporter_implementation_sha256=api.sha256_file(exporter.__file__))
    api.write_json(result,os.path.join(destination,'materials.json'));return result


def new_lash_row(row):return row['mesh']in NEW_MESHES and row['owner']in('avatar','avatar/GetAvatarParts:'+row['mesh'])
def authorized_lash(row):return(row['owner'],row['mesh'],row['material'])==('avatar','CC_Base_Body','Std_Eyelash')or new_lash_row(row)


def compare_nonlash(before,after,api):
    # Inventory additions are authorized only for the precise new mesh names;
    # original native-lash material key itself must still exist in the full capture.
    old=dict(before,materials=[r for r in before['materials']if not authorized_lash(r)])
    new=dict(after,materials=[r for r in after['materials']if not authorized_lash(r)])
    result=original.compare_pixels(old,new,api)
    result['authorized_selected_lash_keys_before']=[(r['owner'],r['mesh'],r['material'])for r in before['materials']if authorized_lash(r)]
    result['authorized_selected_lash_keys_after']=[(r['owner'],r['mesh'],r['material'])for r in after['materials']if authorized_lash(r)]
    return result


def compare_all(before,after,api):return original.compare_pixels(before,after,api)
