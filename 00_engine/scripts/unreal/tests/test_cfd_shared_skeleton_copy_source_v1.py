import copy
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import run_cfd_native_shared_skeleton_probe_v1 as shared


def setup_fake(monkeypatch,tmp_path,use_copy=True,corrupt_mode=False):
    names = ['root']+sorted(shared.FACE_TRANSLATION_BONES)
    class Node:
        def __init__(self,mode): self.mode=mode
        def get_editor_property(self,key):
            assert key=='translation_retargeting_mode'
            return self.mode
    class Skeleton:
        def __init__(self,modes): self.nodes=[Node(m) for m in modes]
        def get_editor_property(self,key):
            assert key=='bone_tree'
            return self.nodes
    canonical = Skeleton(['Animation']*len(names))
    validated = Skeleton(['Animation']+['Skeleton']*(len(names)-1))
    assets={'canonical':canonical,'probe':validated}
    packages={key:{'path':key,'sha256':key,'bytes':1} for key in ('canonical','probe','destination')}
    seen=[]
    def duplicate(name,folder,source):
        seen.append(source)
        target=copy.deepcopy(source)
        if corrupt_mode:
            target.nodes[0].mode='AnimationScaled'
        assets['destination']=target
        return target
    unreal=SimpleNamespace(Skeleton=Skeleton,load_asset=assets.get,
        AnimPoseExtensions=SimpleNamespace(get_reference_pose=lambda s:s,get_bone_names=lambda s:names),
        BoneTranslationRetargetingMode=SimpleNamespace(SKELETON='Skeleton'),
        EditorAssetLibrary=SimpleNamespace(does_asset_exist=lambda p:False),
        AssetToolsHelpers=SimpleNamespace(get_asset_tools=lambda:SimpleNamespace(duplicate_asset=duplicate)))
    monkeypatch.setitem(sys.modules,'unreal',unreal)
    monkeypatch.setattr(shared,'BASELINE',tmp_path/'baseline.json')
    monkeypatch.setattr(shared,'package_record',lambda path:packages[path])
    worker=SimpleNamespace(skeleton_reference_inventory=lambda s:[{'name':n,'reference':1} for n in names],
        guard=lambda p:None,save=lambda asset:None)
    monkeypatch.setattr(shared,'core',lambda:worker)
    case={'sex':'female','canonical_skeleton':'canonical','shared_skeleton':'scope/destination'}
    # Expose destination path to fake package/asset lookup.
    packages['scope/destination']=packages['destination']
    original_duplicate=duplicate
    def scoped_duplicate(name,folder,source):
        target=original_duplicate(name,folder,source)
        assets['scope/destination']=target
        return target
    unreal.AssetToolsHelpers.get_asset_tools=lambda:SimpleNamespace(duplicate_asset=scoped_duplicate)
    if use_copy:
        case.update(copy_source_skeleton='probe',copy_source_package=packages['probe'],canonical_package=packages['canonical'])
    monkeypatch.setattr(shared,'checked_config',lambda:{'cases':[case]})
    return assets,packages,seen,canonical,validated


def test_optional_copy_duplicates_validated_modes_and_protects_both_sources(monkeypatch,tmp_path):
    assets,packages,seen,canonical,validated=setup_fake(monkeypatch,tmp_path)
    assert shared.editor_setup()['success']
    assert seen == [validated]
    assert shared.verify_baseline()['copy_sources_and_translation_modes_unchanged']
    assets['scope/destination'].nodes[0].mode='AnimationScaled'
    with pytest.raises(RuntimeError,match='retarget modes changed'):
        shared.verify_baseline()
    assets['scope/destination'].nodes[0].mode='Animation'
    packages['probe']={**packages['probe'],'sha256':'changed'}
    with pytest.raises(RuntimeError,match='copy source package changed'):
        shared.verify_baseline()


def test_copy_rejects_unchanged_face_animation_mode_and_changed_other_mode(monkeypatch,tmp_path):
    assets,_,seen,_,validated=setup_fake(monkeypatch,tmp_path)
    validated.nodes[1].mode='Animation'
    with pytest.raises(RuntimeError,match='all ten face'):
        shared.editor_setup()
    assert seen == []
    setup_fake(monkeypatch,tmp_path,corrupt_mode=True)
    with pytest.raises(RuntimeError,match='translation retarget modes'):
        shared.editor_setup()
    assert not shared.BASELINE.exists()


def test_default_copy_still_uses_canonical_and_needs_no_face_mode_change(monkeypatch,tmp_path):
    _,_,seen,canonical,_=setup_fake(monkeypatch,tmp_path,use_copy=False)
    assert shared.editor_setup()['success']
    assert seen == [canonical]
    assert shared.verify_baseline()['success']
    assert 'copy_source_skeleton' not in shared.common.read(shared.BASELINE)['cases'][0]
