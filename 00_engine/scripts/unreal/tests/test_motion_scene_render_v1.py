"""Behavioral MRQ configuration check with a lightweight Unreal API stand-in."""
from pathlib import Path
from types import SimpleNamespace as NS
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import ue_motion_scene_render_v1 as render


class Setting:
    def set_editor_property(self,key,value):setattr(self,key,value)
    def set_is_enabled(self,value):self.enabled=value
    def add_or_update_console_variable(self,*args):return True


class Config:
    def __init__(self):self.settings={}
    def find_or_add_setting_by_class(self,cls):return self.settings.setdefault(cls,Setting())
    def initialize_transient_settings(self):pass


class Sequence:
    def __init__(self,count):self.count=count
    def get_display_rate(self):return NS(numerator=30,denominator=1)
    def get_playback_start(self):return 0
    def get_playback_end(self):return self.count
    def get_tracks(self):return [CameraCut(self.count)]


class CameraCut:
    def __init__(self,count):self.count=count
    def get_sections(self):return [NS(get_start_frame=lambda:-16,get_end_frame=lambda:self.count)]


@pytest.mark.parametrize('real_warmup',[False,True])
def test_mixed_duration_queue_uses_each_saved_sequence_end(tmp_path,monkeypatch,real_warmup):
    configs=[]
    class Queue:
        def allocate_new_job(self,cls):
            config=Config();configs.append(config)
            return NS(get_configuration=lambda:config)
    class Executor:
        def __init__(self,subsystem):
            delegate=NS(add_callable_unique=lambda f:None)
            self.on_executor_errored_delegate=delegate;self.on_individual_job_work_finished_delegate=delegate;self.on_executor_finished_delegate=delegate
        def set_is_rendering_offscreen(self,value):pass
    subsystem=NS(is_rendering=lambda:False,get_active_executor=lambda:None,render_queue_instance_with_executor_instance=lambda *a:None)
    u=NS(Paths=NS(project_dir=lambda:str(render.PROJECT)),MoviePipelineQueueSubsystem=object,
        get_editor_subsystem=lambda cls:subsystem,EditorLoadingAndSavingUtils=NS(get_dirty_content_packages=lambda:[],get_dirty_map_packages=lambda:[]),
        EditorAssetLibrary=NS(does_asset_exist=lambda p:True),LevelSequence=Sequence,
        load_asset=lambda path:Sequence(105 if 'Short' in path else 639),MoviePipelineQueue=Queue,MoviePipelineExecutorJob=object,
        SoftObjectPath=lambda p:p,DirectoryPath=Setting,IntPoint=lambda w,h:(w,h),FrameRate=lambda n,d:(n,d),MoviePipelinePIEExecutor=Executor,MovieSceneCameraCutTrack=CameraCut)
    for name in ['MoviePipelineOutputSetting','MoviePipelineDeferredPassBase','MoviePipelineImageSequenceOutput_PNG','MoviePipelineAntiAliasingSetting','MoviePipelineConsoleVariableSetting']:setattr(u,name,type(name,(),{}))
    monkeypatch.setattr(render,'RUN',tmp_path)
    monkeypatch.setattr(render,'file_pin',lambda p:{'path':str(p),'sha256':'unit-test'})
    monkeypatch.setattr(render,'queue_snapshot',lambda sub:{'jobs':[]})
    folder='/SceneTrials/' if real_warmup else '/Sequences/'
    jobs=[{'shot_id':name,'map':render.ASSET_ROOT+'/Maps/Test','sequence':render.ASSET_ROOT+folder+name} for name in ['Short','Long']]
    state=render.start_render(u,jobs,'variable_duration',720,1280,camera_cut_warmup_shot_ids=['Short'] if real_warmup else [])
    outputs=[c.settings[u.MoviePipelineOutputSetting] for c in configs]
    assert [(x.custom_start_frame,x.custom_end_frame) for x in outputs]==[(0,105),(0,639)]
    assert all(x.output_resolution==(720,1280) for x in outputs)
    assert state['receipt']['render_contract']['frame_counts_by_shot']=={'Short':105,'Long':639}
    assert state['receipt']['status']=='submitted'
    assert [c.settings[u.MoviePipelineAntiAliasingSetting].use_camera_cut_for_warm_up for c in configs]==[real_warmup,False]
