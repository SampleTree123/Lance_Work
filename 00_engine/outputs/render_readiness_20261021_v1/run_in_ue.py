"""Serial diagnostic transport, preserving the already-open UE session."""
import sys,json,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,'D:/UE/Lance_Work/00_engine/scripts/unreal')
import scene_site_review_panel_v1 as panel
script=(ROOT/sys.argv[1]).resolve()
if not script.is_relative_to(ROOT) or not script.is_file():raise ValueError('Owned script required')
pinned=json.loads((ROOT.parent/'pair_scene_review_20261019_v1/session.json').read_text(encoding='utf-8'))
with panel.bridge.command_lock():
 module=panel.bridge.load_remote_execution(panel.bridge.DEFAULT_ENGINE_ROOT.resolve())
 panel.install_complete_reply_receiver(module)
 session=module.RemoteExecution();session.start()
 try:
  time.sleep(2)
  node=panel.bridge.select_node(list(session.remote_nodes),pinned['node_id'],None)
  session.open_command_connection(node['node_id'])
  session._command_connection._command_channel_socket.settimeout(180)
  source=str(script)
  command='exec(compile(open('+repr(source)+',encoding="utf-8").read(),'+repr(source)+',"exec"),{"__file__":'+repr(source)+'})'
  result=session.run_command(command,unattended=True,exec_mode=module.MODE_EXEC_FILE,raise_on_failure=False)
  script.with_name(script.stem+'_remote.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
  print(json.dumps(result,ensure_ascii=False)[:7000],flush=True)
  if result.get('success') is not True:raise RuntimeError('UE command failed')
 finally:session.stop()
