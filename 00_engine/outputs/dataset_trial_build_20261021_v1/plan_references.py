"""Plan unrendered references from session-used edges of one trial candidate.

Usage: python plan_references.py --candidate full_squares_uniform_nodes
Only writes reference_manifest.json/reference_summary.json/REFERENCES.md there.
"""
from __future__ import annotations

import argparse
from collections import Counter,defaultdict
import copy
import hashlib
import json
from pathlib import Path
import random

import normalize_catalog as nc

HERE=Path(__file__).resolve().parent
VIEWS=('front','back')


def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def stable(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def digest(value):return hashlib.sha256(stable(value).encode('utf-8')).hexdigest()[:24]
def pin(path):return {'path':str(Path(path).resolve()),'sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest()}
def write(path,value):Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


class Planner:
    def __init__(self,candidate,seed):
        self.candidate=Path(candidate).resolve();self.seed=seed
        self.catalog=nc.load_catalog();self.rules=read(HERE/'rules.json')
        self.items={};self.links=[];self.hair_pools={};self.used={}
        self.inputs=[pin(HERE/x) for x in ('rules.json','catalog.json','plan_references.py','normalize_catalog.py')]
        self.identities={r['id']:r for p in self.catalog['sexes'].values() for r in p['identities']}
        self.hairs=defaultdict(dict);self.assets={}
        for sex,pool in self.catalog['sexes'].items():
            for row in pool['hairs']:self.hairs[row['hair_id']][sex]=row
            for row in pool['shared_shoes']:
                self.assets[row['asset_id']]=dict(row,slot='shoes',source='shared_shoe')
            for family in pool['families']:
                for group in family['groups']:
                    rows=sum(group['slot_options'].values(),[])+group['required_assets']+group['optional_assets']
                    for row in rows:
                        old=self.assets.get(row['asset_id'])
                        if old is not None and old['mesh_paths']!=row['mesh_paths']:
                            raise ValueError('One garment ID maps to different actual meshes')
                        self.assets[row['asset_id']]=dict(row,source='family_asset')
        self.actions={r['id']:r for r in self.catalog['actions']}
        self.sites={r['id']:r for r in self.catalog['sites']}
        self.cameras={r['id']:r for r in self.catalog['cameras']}
        self.wardrobes={}

    def add(self,kind,key,**details):
        requirement={'kind':kind,'key':key}
        rid='ref_'+digest(requirement)
        row={'id':rid,**requirement,'media_type':'clip' if kind=='motion' else 'image',
             'status':'planned_not_rendered','media_path':None,
             'profile_status':'unfrozen','resolution':None,'fps':None,'duration_seconds':None,
             **details}
        if rid in self.items:
            if self.items[rid]!=row:raise ValueError('Same reference key has different specification')
        else:self.items[rid]=row
        return rid

    def wardrobe(self,state):
        key=stable([state['sex'],state['wardrobe']])
        if key not in self.wardrobes:
            resolution=nc.validate_choice(state['sex'],state['wardrobe'])
            ids=resolution['selected_family_asset_ids'][:]
            if resolution['shared_shoe_id']:ids.append(resolution['shared_shoe_id'])
            self.wardrobes[key]=[self.assets[x] for x in ids]
        return self.wardrobes[key]

    def garment_pair(self,asset):
        return [self.add('wardrobe_piece',{'asset_id':asset['asset_id'],'view':view},
                         asset_id=asset['asset_id'],slot=asset['slot'],view=view,
                         mesh_paths=asset['mesh_paths'],body_present=False,
                         background='neutral',preserve_3d_shape=True,
                         actual_item_is_all_listed_meshes=True)
                for view in VIEWS]

    def hair_pool(self,hair_id):
        if hair_id in self.hair_pools:return self.hair_pools[hair_id]
        # Exactly two carriers for the UNIQUE hair ID. Cross-sex availability
        # does not multiply photos. One legal fit sex serves this reference pool.
        rng=random.Random(f'{self.seed}:hair_carriers:{hair_id}')
        sex=rng.choice(sorted(self.hairs[hair_id]))
        ids=sorted(r['id'] for r in self.catalog['sexes'][sex]['identities'])
        carriers=rng.sample(ids,2);variants=[]
        hair=self.hairs[hair_id][sex]
        for number,identity in enumerate(carriers):
            refs=[self.add('hair',{'hair_id':hair_id,'carrier_identity':identity,
                                 'fit_sex':sex,'view':view,'hair_color':'black'},
                           hair_id=hair_id,carrier_identity=identity,carrier_sex=sex,
                           hair_fit=hair['fit'],view=view,hair_color='black',
                           carrier_meshes=self.identities[identity]['meshes'])
                  for view in VIEWS]
            variants.append({'variant_id':f'{hair_id}:carrier{number+1}',
                             'carrier_identity':identity,'carrier_sex':sex,
                             'reference_ids':refs,'views':list(VIEWS)})
        pool={'hair_id':hair_id,'fit_sex':sex,'variants':variants,
              'photos':4,'variant_counts_as_new_chain':False,
              'cross_sex_target_may_share_this_legal_fit_carrier_pool':True}
        self.hair_pools[hair_id]=pool
        return pool

    def requirements(self,source,target,step):
        axis=step['axis'];refs=[];text=[];extra={}
        if axis=='identity':
            identity=self.identities[target['identity']]
            refs=[self.add('identity',{'identity':target['identity'],'view':'front_face'},
                           identity=target['identity'],sex=target['sex'],view='front_face',
                           character_meshes=identity['meshes'],
                           full_body_skin_and_shape_edit_allowed=True)]
        elif axis=='hair':
            pool=self.hair_pool(target['hair'])
            extra={'hair_reference_pool_id':target['hair'],
                   'hair_reference_variant_pool':copy.deepcopy(pool['variants']),
                   'target_fit_sex':target['sex']}
        elif axis=='wardrobe':
            target_assets=self.wardrobe(target)
            if step['mode']=='single_piece':
                slot=step.get('slot')
                if slot is None:
                    changed=[s for s,v in target['wardrobe']['slot_choices'].items()
                             if v!=source['wardrobe']['slot_choices'].get(s)]
                    if len(changed)!=1:raise ValueError('Single-piece edge lacks exactly one changed slot')
                    slot=changed[0]
                asset_id=target['wardrobe']['slot_choices'][slot]
                if asset_id is None:
                    text.append({'kind':'remove_optional_piece','slot':slot,
                                 'instruction':f'移除{slot}槽位的衣物，保留其余衣物和鞋。',
                                 'media_reference_required':False})
                    extra['reference_absence_reason']='target_optional_piece_is_none'
                else:refs=self.garment_pair(self.assets[asset_id])
                extra['single_piece_target_slot']=slot
                extra['target_piece_ids']=[] if asset_id is None else [asset_id]
            elif step['mode']=='whole_outfit':
                for asset in target_assets:refs.extend(self.garment_pair(asset))
                extra['target_piece_ids']=[a['asset_id'] for a in target_assets]
                extra['complete_outfit_reference_including_accessories_and_shoes']=True
            else:raise ValueError('Unknown wardrobe mode')
            barefoot=not any(a['slot']=='shoes' for a in target_assets)
            extra['target_barefoot']=barefoot
            if barefoot:
                text.append({'kind':'barefoot','instruction':'目标保持赤脚，不添加鞋。',
                             'media_reference_required':False})
            elif step['mode']=='single_piece':
                text.append({'kind':'preserve_shoes','instruction':'保持源视频的鞋不变。',
                             'media_reference_required':False})
        elif axis=='site':
            key={'site':target['site'],'action':target['action'],'camera':target['camera'],
                 'sex':target['sex'],'symbolic_aspect':target['aspect'],
                 'camera_profile':'pending_unfrozen_main_profile'}
            refs=[self.add('scene',key,site_id=target['site'],site=self.sites[target['site']],
                           action_id=target['action'],camera_id=target['camera'],sex=target['sex'],
                           person_present=False,view='target_camera_initial_frame',
                           actual_initial_camera_transform=None,
                           exact_initial_frame_signature=None,
                           initial_frame_binding_status='pending_final_camera_and_media_profile',
                           action_dimension_required_because_camera_initial_pose_is_motion_dependent=True,
                           clip_required=False)]
        elif axis=='action':
            key={'action':target['action'],'camera':target['camera'],'sex':target['sex'],
                 'symbolic_aspect':target['aspect'],'motion_profile':'pending_unfrozen_main_profile'}
            variants=[v for v in self.actions[target['action']]['variants'] if v['sex']==target['sex']]
            if len(variants)!=1:raise ValueError('Motion reference lacks exact target-sex version')
            refs=[self.add('motion',key,action_id=target['action'],camera_id=target['camera'],
                           sex=target['sex'],available_target_sex_action_variant=variants[0],
                           carrier_identity=None,carrier_status='pending_user_freeze',
                           camera_rule=self.cameras[target['camera']],
                           match_target=['camera_rule','phase','speed','duration'],
                           phase=None,speed=None,target_duration_seconds=None,
                           clock_binding_status='pending_final_main_profile',
                           production10_source_is_available_asset_not_frozen_media_profile=True)]
        elif axis in ('camera','hair_color','color'):
            text.append({'kind':'text_only','axis':axis,
                         'target':target['camera'] if axis=='camera' else target['hair_color'],
                         'media_reference_required':False,'text_template_status':'pending'})
        else:raise ValueError('Unknown edit axis: '+axis)
        return {'reference_ids':refs,'text_constraints':text,**extra}

    def run(self):
        totals=Counter();split_summary={};used_requests={}
        for split in ('train','test'):
            folder=self.candidate/split
            if not folder.is_dir():continue
            for file in ('nodes.json','edges.json','sessions.jsonl'):self.inputs.append(pin(folder/file))
            nodes={r['id']:r for r in read(folder/'nodes.json')}
            registered={(r['source'],r['target']):r for r in read(folder/'edges.json')}
            local=Counter();used_edges=set();used_refs=set()
            with (folder/'sessions.jsonl').open(encoding='utf-8-sig') as stream:
                for line in stream:
                    session=json.loads(line);local['sessions']+=1
                    for number,step in enumerate(session['steps'],1):
                        pair=(step['source'],step['target'])
                        if pair not in registered:raise ValueError('Session uses unregistered graph edge')
                        edge=registered[pair]
                        for field in ('axis','mode','slot'):
                            if edge.get(field)!=step.get(field):
                                raise ValueError('Session step differs from registered edge')
                        source,target=nodes[pair[0]],nodes[pair[1]]
                        edge_key=f'{split}:{pair[0]}->{pair[1]}'
                        if edge_key not in used_requests:
                            used_requests[edge_key]=self.requirements(source['state'],target['state'],step)
                        requirement=copy.deepcopy(used_requests[edge_key])
                        if step['axis']=='hair':
                            variants=requirement['hair_reference_variant_pool']
                            rng=random.Random(f'{self.seed}:{split}:{session["id"]}:{number}:hair_pair')
                            selected=rng.choice(variants)
                            requirement['selected_hair_variant_id']=selected['variant_id']
                            requirement['reference_ids']=selected['reference_ids'][:]
                        link={'split':split,'session_id':session['id'],'edit_round':number,
                              'source_history_occurrence':step['source_position'],
                              'source_node':pair[0],'target_node':pair[1],
                              'source_canonical_id':source['canonical_id'],
                              'target_canonical_id':target['canonical_id'],
                              'used_edge_key':edge_key,'axis':step['axis'],'mode':step['mode'],
                              **requirement}
                        self.links.append(link);used_edges.add(pair)
                        used_refs.update(requirement['reference_ids']);local['edit_step_occurrences']+=1
                        local['axis_'+step['axis']]+=1
                        if not requirement['reference_ids']:local['no_media_link_occurrences']+=1
            local['unique_used_edges']=len(used_edges);local['unique_selected_reference_items']=len(used_refs)
            split_summary[split]=dict(local);totals.update(local)
        kinds=Counter(r['kind'] for r in self.items.values())
        media=Counter(r['media_type'] for r in self.items.values())
        summary={'schema':'trial_reference_summary_20261021_v1','candidate':self.candidate.name,
                 'seed':self.seed,'media_generated':False,'reference_count_against_main_node_budget':False,
                 'unique_reference_items':len(self.items),'unique_images':media['image'],
                 'unique_motion_clips':media['clip'],'unique_reference_items_by_kind':dict(kinds),
                 'unique_hair_ids':len(self.hair_pools),'hair_photos_per_unique_hair':4,
                 'hair_carrier_pairs_per_unique_hair':2,
                 'reference_link_occurrences':len(self.links),
                 'unique_used_edges':sum(s['unique_used_edges'] for s in split_summary.values()),
                 'split_counts':split_summary,
                 'reference_pool_shared_across_splits':True,
                 'hair_carrier_variants_add_structural_sessions':False,
                 'all_media_paths_null':all(r['media_path'] is None for r in self.items.values()),
                 'motion_carrier_status':'pending_user_freeze',
                 'scene_initial_frames_status':'symbolic_demands_pending_exact_final_transform',
                 'unfrozen':self.rules['unfrozen'],
                 'count_scope':'actual_session_used_edges_only; media requirement dedup; not rendered file count'}
        manifest={'schema':'trial_reference_manifest_20261021_v1','candidate':str(self.candidate),
                  'seed':self.seed,'media_generated':False,'inputs':self.inputs,
                  'requirements':sorted(self.items.values(),key=lambda r:r['id']),
                  'hair_reference_pools':list(self.hair_pools.values()),
                  'reference_links':self.links,
                  'note':'One link per used session-step occurrence. Carrier pair choices never create sessions.'}
        self.validate(manifest,summary)
        write(self.candidate/'reference_manifest.json',manifest)
        write(self.candidate/'reference_summary.json',summary)
        self.documentation(summary)
        return summary

    def validate(self,manifest,summary):
        ids=set(self.items)
        assert summary['all_media_paths_null']
        assert summary['unique_reference_items_by_kind'].get('hair',0)==4*len(self.hair_pools)
        for link in self.links:
            assert set(link['reference_ids'])<=ids
            if link['axis']=='hair':
                records=[self.items[r] for r in link['reference_ids']]
                assert len(records)==2 and {r['view'] for r in records}==set(VIEWS)
                assert len({r['carrier_identity'] for r in records})==1
                assert all(r['hair_color']=='black' for r in records)
            if link['axis'] in ('camera','hair_color','color'):assert not link['reference_ids']
            if link.get('reference_absence_reason')=='target_optional_piece_is_none':
                assert not link['reference_ids']
            if link['axis']=='wardrobe':
                records=[self.items[r] for r in link['reference_ids']]
                assert all(r['body_present'] is False for r in records)
                assert len(records)==2*len(link['target_piece_ids'])
                if link.get('target_barefoot'):
                    assert any(t['kind']=='barefoot' for t in link['text_constraints'])

    def documentation(self,s):
        k=s['unique_reference_items_by_kind']
        rows=[f'| {kind} | {count} |' for kind,count in sorted(k.items())]
        text='\n'.join([
            '# 本候选参考需求', '',
            '本清单只从会话实际使用的编辑边产生；没有渲染照片或视频，所有 `media_path` 均为 null。参考素材不占主视频节点预算，也不因更换头发参考载体增加会话。', '',
            f'候选 `{self.candidate.name}`：{s["unique_used_edges"]} 条实际使用的唯一边，{s["reference_link_occurrences"]} 次会话编辑使用；需求去重后 {s["unique_images"]} 张图、{s["unique_motion_clips"]} 段动作参考。不是现有媒体数量。', '',
            '| 类型 | 去重后参考项目数 |','| --- | ---: |',*rows,'',
            '身份：按目标 identity 去重，每人一张正面面部图。头发：按 unique hairID 去重，各选一个合法 fit 性别的两名随机库内身份；每人正反两张、固定黑色，共四张。跨性别可用发型共享这四张，不默增为八张。每个会话编辑在同一载体的正反一对中随机选择；两对选择池和实际选择均记录于 reference_links，固定 seed 可重现。','',
            '单件服装：只给目标变化部件的正反两图，保持其它衣物和鞋；若目标是合法 optional None，则清单明确写移除、无图。整套：给目标实际选中的全部衣物、固定部件、可选附件和鞋的正反图。锁定衣柜每个实际 asset item 保留全部 mesh_paths，不虚构拆槽；有多个 mesh 的资产仍是一个 item。所有衣物图无身体、中性背景、保留立体形状。无鞋状态明确写赤脚，没有“赤脚鞋图”。','',
            '场景：空背景单图，键保留 target site、action、camera、sex 和当前符号 aspect。动作会改变初始相机位置，因此不能只按场景×镜头合并。最终初始相机变换和 frame signature 仍待参数冻结；当前只是精确符号需求键，不能声称已确认实际帧复用。','',
            '动作：按目标 action×camera×sex×符号 aspect 去重，记录目标性别的真实动作版本，匹配主视频的镜头规则、相位、速度和时长。载体尚未冻结，标 pending；当前 production10 路径只是可用来源，不代表采用10秒、30fps或其余旧媒体参数。镜头变化和发色变化只含文本目标，无媒体参考。','',
            '训练/测试参考池可复用，主视频仍遵守完整状态不重合；本文件不新增人物、场景或参考素材的 holdout 约束。引用次数、唯一编辑边、去重媒体需求和主节点数是不同口径。','',
            '未确定：分辨率、帧率、时长、画幅，以及身份/头发/服装参考拍摄实现、参考与编辑文本模板、动作载体。相位/速度/时长须跟随最终主视频参数绑定；若最终初始取景还依赖身份等其它变量，场景键必须进一步加入对应变量或精确 transform，重建后再渲染。','',
            '输入文件哈希位于 reference_manifest.json.inputs；每条 reference_links 对应原会话 id、edit_round、source_history_occurrence 和 used_edge_key，可追溯实际来源。',''])
        (self.candidate/'REFERENCES.md').write_text(text,encoding='utf-8')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate',required=True,type=Path)
    parser.add_argument('--seed',default=20261021,type=int)
    args=parser.parse_args()
    candidate=args.candidate
    if not candidate.is_absolute() and not candidate.is_dir():candidate=HERE/candidate
    candidate=candidate.resolve()
    if not candidate.is_relative_to(HERE):raise ValueError('Candidate must be inside this trial output')
    summary=Planner(candidate,args.seed).run()
    print(json.dumps({k:v for k,v in summary.items() if k not in ('unfrozen','split_counts')},ensure_ascii=False))


if __name__=='__main__':main()
