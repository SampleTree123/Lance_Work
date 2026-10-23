"""Recoverable pilot encoding. Owner: SCENE_CAMERA_SEQUENCE.md section 7.

Existing videos require matching source pins, receipts and a new full decode.
"""
from pathlib import Path
import argparse,hashlib,json,math,re,subprocess
import cv2
from PIL import Image,ImageDraw
RUN=Path('D:/UE/Lance_Work/00_engine/outputs/unreal_character_import/camera_motion_pilot_20261009_v1')
FFMPEG=Path('C:/ProgramData/anaconda3/Lib/site-packages/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe')

def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as stream:
  for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()

def identifier(value):
 if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,95}',value):raise ValueError('Unsafe attempt/shot identifier')
 return value

def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def atomic_json(path,value):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);temp=path.with_suffix(path.suffix+'.tmp')
 temp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');temp.replace(path)

def png_evidence(folder):
 files=sorted(Path(folder).glob('*.png'))
 if [p.name for p in files]!=[f'frame_{i:04d}.png' for i in range(300)]:raise ValueError('Missing/extra PNG frames '+str(folder))
 records=[{'name':p.name,'bytes':p.stat().st_size,'sha256':sha(p)} for p in files]
 digest=hashlib.sha256(json.dumps(records,sort_keys=True,separators=(',',':')).encode()).hexdigest()
 return files,records,digest

def decode_video(path,width,height):
 cap=cv2.VideoCapture(str(path));fps=cap.get(cv2.CAP_PROP_FPS);count=0;dimensions=set()
 try:
  while True:
   ok,im=cap.read()
   if not ok:break
   dimensions.add((im.shape[1],im.shape[0]));count+=1
 finally:cap.release()
 if not math.isfinite(fps) or abs(fps-30)>1e-8 or count!=300 or dimensions!={(width,height)}:raise ValueError('Full decoded contract failed '+str(path))
 return {'decoded_frames':count,'fps':fps,'measured_duration_seconds':count/fps,'dimensions':[width,height]}

def verify_resume(existing,expected,video,width,height):
 if existing.get('schema')!='camera_pilot_encoded_shot_v1' or existing.get('status')!='encoded_verified':raise ValueError('Existing receipt is not verified')
 for key,value in expected.items():
  if existing.get(key)!=value:raise ValueError('Existing video input binding differs: '+key)
 if not video.exists() or sha(video)!=existing['video_sha256']:raise ValueError('Existing video pin differs; inspect before reuse')
 decoded=decode_video(video,width,height)
 if decoded!=existing['decode']:raise ValueError('Existing video decoded metadata differs')
 return decoded

def contact_sheet(files,indices,path,shot,columns=5,cell=(384,216)):
 width,height=cell;rows=(len(indices)+columns-1)//columns
 output=Image.new('RGB',(columns*width,rows*(height+28)),(28,28,28));draw=ImageDraw.Draw(output)
 for index,frame in enumerate(indices):
  x=(index%columns)*width;y=(index//columns)*(height+28)
  with Image.open(files[frame]) as image:output.paste(image.convert('RGB').resize(cell),(x,y+28))
  draw.text((x+7,y+7),f'{shot} | {frame/30:.2f}s / f{frame}',fill='white')
 output.save(path,quality=94)

def needs_dense_contact(shot):return any(label in shot for label in ('follow_','orbit_','zoom_','dolly_','_pan','static_upper','static_head'))

def process(attempt):
 identifier(attempt);receiptpath=RUN/'render_receipts'/f'{attempt}.json';receipt=read(receiptpath)
 if receipt.get('success') is not True or receipt.get('status')!='completed':raise ValueError('Render has no terminal success')
 receipt_hash=sha(receiptpath);contract=receipt['render_contract'];width,height=contract['width'],contract['height']
 if contract['fps']!=30 or contract['frame_count']!=300 or contract['duration_seconds']!=10:raise ValueError('Frozen ten-second media contract differs')
 videos=RUN/'videos';videos.mkdir(exist_ok=True);contacts=RUN/'contacts';contacts.mkdir(exist_ok=True)
 per_shot=RUN/'media_receipts';per_shot.mkdir(exist_ok=True);results=[]
 for job in receipt['jobs']:
  shot=identifier(job['shot_id']);src=RUN/'renders'/attempt/shot;files,pngs,png_sha=png_evidence(src)
  out=videos/(shot+'.mp4');shot_receipt=per_shot/(shot+'.json')
  expected={'attempt':attempt,'shot_id':shot,'render_receipt_sha256':receipt_hash,'png_sequence_sha256':png_sha,'render_job':job,'video':out.relative_to(RUN).as_posix()}
  if out.exists():
   if not shot_receipt.exists():raise ValueError('Existing MP4 has no verification receipt; retained for inspection, not overwritten: '+shot)
   evidence=read(shot_receipt);decoded=verify_resume(evidence,expected,out,width,height)
  else:
   if shot_receipt.exists():raise ValueError('Receipt exists but MP4 is missing: '+shot)
   subprocess.run([str(FFMPEG),'-v','error','-n','-framerate','30','-i',str(src/'frame_%04d.png'),'-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(out)],check=True)
   decoded=decode_video(out,width,height)
   evidence={'schema':'camera_pilot_encoded_shot_v1','status':'encoded_verified',**expected,'video_sha256':sha(out),'decode':decoded,'png_frames':pngs}
   # Persist verified video before derived posters, allowing contact-generation recovery.
   atomic_json(shot_receipt,evidence)
  poster=videos/(shot+'.jpg');contact=contacts/(shot+'.jpg')
  with Image.open(files[0]) as image:image.convert('RGB').save(poster,quality=92)
  contact_sheet(files,[0,75,150,225,299],contact,shot);dense=None
  if needs_dense_contact(shot):
   dense=contacts/(shot+'_timeline.jpg');contact_sheet(files,[round(i*299/19) for i in range(20)],dense,shot)
  results.append({'shot_id':shot,'video':out.relative_to(RUN).as_posix(),'poster':poster.relative_to(RUN).as_posix(),'contact':contact.relative_to(RUN).as_posix(),'timeline_contact':dense.relative_to(RUN).as_posix() if dense else None,**decoded,'sha256':evidence['video_sha256'],'render_status':'rendered','visual_review':'pending','verification_receipt':shot_receipt.relative_to(RUN).as_posix(),'verification_receipt_sha256':sha(shot_receipt)})
  print('Verified camera media '+shot,flush=True)
 if sha(receiptpath)!=receipt_hash:raise ValueError('Render receipt changed during encoding')
 report={'schema':'camera_pilot_media_validation_v1','success':True,'attempt':attempt,'videos':results,'visual_review':'pending','render_receipt_sha256':receipt_hash,'contact_frames':[0,75,150,225,299],'dense_contact_frames':[round(i*299/19) for i in range(20)]}
 path=RUN/f'media_validation_{attempt}.json'
 if path.exists():
  previous=read(path)
  if previous!=report:raise ValueError('Existing final media report differs; preserve and inspect')
  return previous
 with path.open('x',encoding='utf-8') as stream:json.dump(report,stream,ensure_ascii=False,indent=2)
 return report

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('attempt');args=parser.parse_args();result=process(args.attempt)
 print(json.dumps({'success':True,'videos':len(result['videos'])}))
