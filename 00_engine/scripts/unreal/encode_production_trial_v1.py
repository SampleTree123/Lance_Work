"""Encode completed 1440p four-trial MRQ attempts; no UE or raw-frame deletion.

Atomic publication happens only after independent FFprobe timing/frame checks,
FFmpeg full decode and comparison of decoded frame0 with PNG frame_0000.
"""
from __future__ import annotations
import argparse
from datetime import datetime
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import time
from PIL import Image
import numpy as np
import cv2

RUN=Path(__file__).resolve().parents[2]/'outputs/production_workflow_20261017_v1'
FFMPEG_CANDIDATES=(Path('C:/ProgramData/anaconda3/Lib/site-packages/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe'),)
FFPROBE_CANDIDATES=(Path('C:/ProgramData/GamePPPublic/PCBenchmark/ffprobe.exe'),
    Path('C:/ProgramData/anaconda3/pkgs/ffmpeg-8.0.0-gpl_h70aa942_905/Library/bin/ffprobe.exe'))


def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def pin(path):return {'path':str(Path(path).resolve(strict=True)),'sha256':sha(path)}
def object_sha(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
def write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);temp=path.with_suffix(path.suffix+'.partial')
    temp.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8');temp.replace(path)
def identifier(value):
    if not isinstance(value,str) or not re.fullmatch('[A-Za-z0-9][A-Za-z0-9_-]{0,95}',value) or value.upper() in {'CON','PRN','AUX','NUL',*(f'COM{i}' for i in range(1,10)),*(f'LPT{i}' for i in range(1,10))}:
        raise ValueError('Unsafe attempt or shot identifier')
    return value
def owned(root,path):
    target=Path(path).resolve();target.relative_to(Path(root).resolve());return target


def tool_path(name,explicit=None):
    candidates=([Path(explicit)] if explicit else list(FFMPEG_CANDIDATES if name=='ffmpeg' else FFPROBE_CANDIDATES))
    system=shutil.which(name)
    if system and not explicit:candidates.append(Path(system))
    for candidate in candidates:
        if not candidate.is_file():continue
        try:result=subprocess.run([str(candidate),'-version'],capture_output=True,text=True,timeout=10)
        except (OSError,subprocess.TimeoutExpired):continue
        if result.returncode==0 and result.stdout.startswith(name+' version'):
            return candidate,{'path':str(candidate),'sha256':sha(candidate),'version':result.stdout.splitlines()[0]}
    raise FileNotFoundError('No working local '+name+' binary; provide --'+name)


def validate_plan(plan):
    shots=plan.get('shots',[])
    if plan.get('schema')!='production_four_trials_v1' or len(shots)!=4 or len({s['shot_id'] for s in shots})!=4:
        raise ValueError('Require exact four-trial formal plan')
    for shot in shots:
        identifier(shot['shot_id'])
        if shot.get('fps')!=30 or shot.get('frame_count')!=300 or shot.get('duration_seconds')!=10 or (shot['width'],shot['height']) not in ((2560,1440),(1440,2560)):
            raise ValueError('Require 1440p/portrait 30fps exactly300frames/10seconds')
    return {s['shot_id']:s for s in shots}


def validate_render(receipt,attempt,shots):
    if receipt.get('attempt_id')!=attempt or receipt.get('success') is not True or receipt.get('status')!='completed':
        raise ValueError('Render attempt lacks exact terminal success')
    if any(error.get('fatal') for error in receipt.get('errors',[])):raise ValueError('Render has a fatal error')
    c=receipt['render_contract'];jobs=receipt['jobs'];ids=[identifier(job['shot_id']) for job in jobs]
    if not ids or len(set(ids))!=len(ids) or set(ids)!=set(c['frame_counts_by_shot']) or not set(ids)<=set(shots):raise ValueError('Job identities differ from plan/render contract')
    if c.get('fps')!=30 or c.get('range_start_inclusive')!=0 or c.get('format')!='PNG':raise ValueError('Require zero-based30fps PNG contract')
    for sid in ids:
        shot=shots[sid]
        if c['frame_counts_by_shot'][sid]!=300 or (c['width'],c['height'])!=(shot['width'],shot['height']):raise ValueError('Render dimensions/frame count disagree')
    return jobs


def check_frame_names(names):
    if sorted(names)!=[f'frame_{i:04d}.png' for i in range(300)]:raise ValueError('Require exactly frame_0000.png through frame_0299.png, without offset/gap/extra')


def png_evidence(folder,width,height):
    files=sorted(Path(folder).glob('*.png'));check_frame_names([p.name for p in files]);records=[]
    for file in files:
        owned(folder,file)
        with Image.open(file) as image:
            if image.format!='PNG' or image.size!=(width,height):raise ValueError('PNG format/resolution mismatch:'+str(file))
        stat=file.stat();records.append({'name':file.name,'bytes':stat.st_size,'mtime_ns':stat.st_mtime_ns,'sha256':sha(file)})
    return files,records


def validate_probe(data,width,height):
    streams=data.get('streams',[])
    videos=[s for s in streams if s.get('codec_type')=='video']
    if len(videos)!=1 or len(streams)!=1:raise ValueError('Require one video stream and no audio stream')
    s=videos[0]
    if (s.get('width'),s.get('height'))!=(width,height) or s.get('codec_name')!='h264' or s.get('pix_fmt')!='yuv420p':raise ValueError('FFprobe codec/resolution differs')
    if int(s.get('nb_read_frames',-1))!=300 or Fraction(s.get('avg_frame_rate','0'))!=30 or Fraction(s.get('r_frame_rate','0'))!=30:raise ValueError('FFprobe frame count/rate differs')
    for value in (s.get('duration'),data.get('format',{}).get('duration')):
        if value is None or not math.isclose(float(value),10.,abs_tol=1e-5):raise ValueError('FFprobe duration differs')
    if abs(float(s.get('start_time','inf')))>1e-6:raise ValueError('Video timestamp has a frame offset')
    frames=data.get('frames',[])
    if len(frames)!=300:raise ValueError('FFprobe did not inspect every frame')
    for index,frame in enumerate(frames):
        if abs(float(frame.get('best_effort_timestamp_time','inf'))-index/30)>1e-5:raise ValueError('Video frame timestamp differs from zero-based source frame')
    return {'decoded_frames':300,'fps':30.,'duration_seconds':10.,'width':width,'height':height,
        'first_frame_timestamp_seconds':0.,'last_frame_timestamp_seconds':299/30,'all_frame_timestamps_verified':True}


def first_frame_comparison(video,png):
    capture=cv2.VideoCapture(str(video))
    try:ok,frame=capture.read()
    finally:capture.release()
    if not ok:raise ValueError('Cannot decode first video frame')
    actual=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
    with Image.open(png) as source:expected=np.asarray(source.convert('RGB'))
    if expected.shape!=actual.shape:raise ValueError('First decoded frame dimensions differ from PNG0000')
    # A CRF18 YUV420 delivery is lossy. This detects wrong/blank frames and major
    # color/offset failures; exact input numbering + every PTS prove indexing.
    error=np.abs(actual.astype(np.float32)-expected.astype(np.float32))
    mae=float(error.mean())
    if not math.isfinite(mae) or mae>12.:raise ValueError('First decoded frame does not match PNG0000 within delivery-codec RGB budget')
    return {'png_name':Path(png).name,'png_sha256':sha(png),'decoded_rgb_mean_absolute_error':mae,
        'mean_absolute_error_limit_8bit':12.,'scope':'Lossy RGB comparison; frame indexing is additionally bound by explicit start_number0 and300 zero-based timestamps.'}


def verify_video(video,png,width,height,ffmpeg,ffprobe):
    started=time.monotonic()
    result=subprocess.run([str(ffprobe),'-v','error','-count_frames','-show_streams','-show_format','-show_frames',
        '-show_entries','frame=best_effort_timestamp_time:stream=codec_type,codec_name,width,height,pix_fmt,avg_frame_rate,r_frame_rate,nb_read_frames,duration,start_time:format=duration,start_time',
        '-of','json',str(video)],capture_output=True,text=True,check=True)
    if result.stderr.strip():raise ValueError('FFprobe reported decoding errors:'+result.stderr[:500])
    evidence=validate_probe(json.loads(result.stdout),width,height)
    decoded=subprocess.run([str(ffmpeg),'-v','error','-xerror','-nostats','-i',str(video),'-map','0:v:0','-an',
        '-fps_mode','passthrough','-progress','pipe:1','-f','null','-'],capture_output=True,text=True,check=True)
    counts=[int(row.split('=',1)[1]) for row in decoded.stdout.splitlines() if row.startswith('frame=')]
    if decoded.stderr.strip() or not counts or counts[-1]!=300 or 'progress=end' not in decoded.stdout:raise ValueError('FFmpeg full decode has errors or lacks300frames')
    evidence.update(ffprobe_full_decode_success=True,ffmpeg_full_decode_success=True,ffmpeg_full_decode_frames=300,
                    first_frame=first_frame_comparison(video,png),verification_seconds=time.monotonic()-started)
    return evidence


def elapsed(receipt,start,end):
    try:return (datetime.fromisoformat(receipt[end])-datetime.fromisoformat(receipt[start])).total_seconds()
    except (KeyError,ValueError,TypeError):return None


def process(attempt,run=RUN,ffmpeg=None,ffprobe=None):
    identifier(attempt);run=Path(run).resolve();plan_path=run/'four_trials_plan.json';plan=read(plan_path);shots=validate_plan(plan)
    receipt_path=owned(run,run/'render_receipts'/(attempt+'.json'));receipt=read(receipt_path);jobs=validate_render(receipt,attempt,shots)
    output_root=owned(run,run/'renders'/attempt)
    if Path(receipt['output_root']).resolve()!=output_root:raise ValueError('Raw output root differs from the owned attempt')
    ffmpeg,ffmpeg_record=tool_path('ffmpeg',ffmpeg);ffprobe,ffprobe_record=tool_path('ffprobe',ffprobe)
    pins={'plan':pin(plan_path),'render_receipt':pin(receipt_path)};results=[]
    for job in jobs:
        sid=job['shot_id'];shot=shots[sid];width,height=shot['width'],shot['height']
        media=owned(run,run/'media_receipts'/(sid+'.json'));video=owned(run,run/'videos'/(sid+'.mp4'))
        poster=video.with_suffix('.jpg');folder=owned(run,output_root/sid)
        # A validated delivery remains reviewable after root separately removes
        # its raw frames. Re-encoding always needs a fresh explicit attempt.
        if media.exists():
            old=read(media)
            if old.get('schema')!='production_trial_media_v1' or old.get('status')!='encoded_verified' or old.get('attempt')!=attempt or old.get('pins')!=pins or old.get('shot_plan_sha256')!=object_sha(shot):raise ValueError('Existing media binding differs; preserved')
            if not video.is_file() or sha(video)!=old['video']['sha256'] or not poster.is_file() or sha(poster)!=old['poster']['sha256']:raise ValueError('Existing video/poster changed; preserved')
            results.append(old);continue
        if video.exists():raise ValueError('Unreceipted video exists; preserved:'+sid)
        scan_started=time.monotonic();files,pngs=png_evidence(folder,width,height);scan_seconds=time.monotonic()-scan_started
        video.parent.mkdir(parents=True,exist_ok=True);media.parent.mkdir(parents=True,exist_ok=True)
        temporary=video.with_name(video.stem+'.encoding.mp4')
        if temporary.exists():raise ValueError('Prior partial encoding exists; inspect before retry:'+str(temporary))
        command=[str(ffmpeg),'-v','error','-xerror','-nostdin','-n','-framerate','30','-start_number','0','-i',str(folder/'frame_%04d.png'),
            '-frames:v','300','-an','-c:v','libx264','-preset','medium','-crf','18','-pix_fmt','yuv420p','-fps_mode','passthrough',
            '-video_track_timescale','15360','-movflags','+faststart',str(temporary)]
        encode_started=time.monotonic();encoded=subprocess.run(command,capture_output=True,text=True,check=True);encode_seconds=time.monotonic()-encode_started
        if encoded.stderr.strip():raise ValueError('FFmpeg encode reported errors:'+encoded.stderr[:500])
        decoded=verify_video(temporary,files[0],width,height,ffmpeg,ffprobe)
        for file,record in zip(files,pngs):
            stat=file.stat()
            if stat.st_size!=record['bytes'] or stat.st_mtime_ns!=record['mtime_ns']:raise ValueError('Raw frame changed during encoding')
        if pin(plan_path)!=pins['plan'] or pin(receipt_path)!=pins['render_receipt']:raise ValueError('Frozen plan/render receipt changed during encoding')
        with Image.open(files[0]) as image:
            image=image.convert('RGB');image.thumbnail((720,720));poster_temp=poster.with_suffix('.poster.partial.jpg');image.save(poster_temp,quality=92)
        result={'schema':'production_trial_media_v1','status':'encoded_verified','success':True,'shot_id':sid,'attempt':attempt,'pins':pins,
            'shot_plan_sha256':object_sha(shot),'motion_id':shot['motion_id'],'motion_label':shot['motion_label'],'camera_id':shot['camera_id'],
            'camera_label':shot['camera_label'],'width':width,'height':height,'fps':30,'frames':300,'duration_seconds':10.,
            'png_sequence_sha256':object_sha(pngs),'png_frames':pngs,'raw_folder':str(folder),'decode':decoded,
            'encode_command':command,'tools':{'ffmpeg':ffmpeg_record,'ffprobe':ffprobe_record},
            'timing':{'preparation_seconds':read(run/'prepared'/(sid+'.json')).get('preparation_seconds') if (run/'prepared'/(sid+'.json')).is_file() else None,
                'render_seconds':elapsed(receipt,'submitted_at','finished_at'),'png_validation_seconds':scan_seconds,
                'encoding_seconds':encode_seconds,'media_validation_seconds':decoded['verification_seconds']},
            'raw_frames_deleted':False,'human_acceptance':'pending'}
        # Publish only completed validated media. A crash after rename still
        # preserves unreceipted files for inspection rather than overwriting.
        temporary.replace(video);poster_temp.replace(poster)
        result['video']={'path':video.relative_to(run).as_posix(),'sha256':sha(video),'bytes':video.stat().st_size}
        result['poster']={'path':poster.relative_to(run).as_posix(),'sha256':sha(poster)}
        write(media,result);results.append(result)
        print('Verified '+sid,flush=True)
    result={'schema':'production_trial_attempt_media_v1','success':True,'attempt':attempt,
        'shots':[{'shot_id':r['shot_id'],'receipt':pin(run/'media_receipts'/(r['shot_id']+'.json'))} for r in results],
        'raw_frames_deleted':False}
    write(run/'media_validation'/(attempt+'.json'),result);return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('attempt');parser.add_argument('--run-root',type=Path,default=RUN)
    parser.add_argument('--ffmpeg',type=Path);parser.add_argument('--ffprobe',type=Path);args=parser.parse_args()
    print(json.dumps(process(args.attempt,args.run_root,args.ffmpeg,args.ffprobe),ensure_ascii=False))
