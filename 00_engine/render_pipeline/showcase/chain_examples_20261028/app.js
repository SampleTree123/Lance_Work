'use strict';
const data = window.SHOWCASE_DATA;
const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const h = escapeHTML;
const nodes = data.nodes;
function videoCard(id, version, changed) {
  const n = nodes[id], l=n.labels, o=n.output;
  const attrs = [
    ['identity','人物',h(l.identity)+' <span class="subtle">'+h(l.sex)+'</span>'],
    ['hair','发型',h(l.hair)], ['hair_color','发色',h(l.hair_color)],
    ['wardrobe','服装',l.wardrobe.map(x=>'<span class="wardrobe-item">'+h(x.slot)+' · '+h(x.label)+'</span>').join('')],
    ['action','动作',h(l.action)+'<br><span class="subtle">'+h(n.state.action)+'</span>'],
    ['camera','镜头',h(l.camera)+'<br><span class="subtle">'+h(n.state.camera)+'</span>'],
    ['site','场景',h(l.site)], ['expression','表情',h(n.expression)]
  ];
  return `<article class="video-card"><div class="version"><strong>${version===0?'原始视频':'第'+version+'轮结果'}</strong><span>VERSION ${String(version).padStart(2,'0')}</span></div>
    <div class="video-wrap"><video controls muted playsinline preload="none" poster="posters/${h(id)}.jpg" aria-label="${h(id)}，${version===0?'原始视频':'第'+version+'轮结果'}"><source src="media/${h(id)}.mp4" type="video/mp4"></video><div class="video-error" hidden>视频尚未就位。<br>请确认media文件夹已完整下载。</div></div>
    <div class="node-id">${h(id)}</div><dl class="attributes">${attrs.map(([key,label,value])=>`<div class="attr ${changed===key?'changed':''}"><dt>${h(label)}</dt><dd>${value}</dd></div>`).join('')}</dl>
    <details class="card-details"><summary>完整属性与资产编号</summary><pre>${h(JSON.stringify(n.state,null,2))}</pre><pre>${h(JSON.stringify(l.wardrobe,null,2))}</pre></details>
    <div class="spec"><span>${h(l.aspect)} · ${o.width}×${o.height} · ${o.frames/o.fps}s / ${o.fps}fps</span><a href="media/${h(id)}.mp4" target="_blank" rel="noopener">打开视频 ↗</a></div></article>`;
}
function editCard(e) {
  const d=e.description;
  const assetDetails=d.added_assets ? '<details><summary>变化部件的精确编号</summary><ul>'+d.removed_assets.map(x=>'<li>移除 '+h(x.id)+'</li>').join('')+d.added_assets.map(x=>'<li>加入 '+h(x.id)+'</li>').join('')+'</ul></details>' : '';
  const constraints=(e.text_constraints||[]).filter(x=>x.instruction).map(x=>x.instruction).join(' ');
  return `<aside class="edge" aria-label="第${e.edit_round}轮编辑"><div class="edge-line">EDIT ${String(e.edit_round).padStart(2,'0')} →</div><span class="axis-pill">${h(e.axis_label)}</span><h3>${h(d.title)}</h3><div class="change-box"><div class="from">${h(d.before)}</div><div class="change-arrow">↓</div><div class="to">${h(d.after)}</div></div><div class="preserve">其余节点属性保持不变。${h(constraints)}</div>${assetDetails}</aside>`;
}
const container=document.getElementById('chains');
container.innerHTML=data.chains.map((c,index)=>{
  const root=nodes[c.root_node], axes=[...new Set(c.steps.map(e=>e.axis_label))];
  return `<section class="chain" id="${h(c.example_id)}" data-length="${c.edit_count}"><div class="chain-head"><div class="chain-title"><span class="chain-index">${h(c.example_id)}</span><div><h2>${c.edit_count}轮编辑 · ${h(axes.join(' / '))}</h2><div class="chain-meta">${h(root.labels.sex)} · ${h(root.labels.aspect)} · ${h(c.session_id)} · ${h(c.split)} · 完整直链</div></div></div><div class="toolbar"><button class="primary" data-action="play">从头播放本链</button><button data-action="pause">暂停</button><button class="scroll-btn" data-action="left" aria-label="向左查看">←</button><button class="scroll-btn" data-action="right" aria-label="向右查看">→</button></div></div>
    <div class="ribbon" tabindex="0" aria-label="${h(c.example_id)}编辑链，可横向滚动">${videoCard(c.root_node,0,null)+c.steps.map((e,i)=>editCard(e)+videoCard(e.target_node,i+1,e.axis)).join('')}</div><div class="play-status" aria-live="polite"></div></section>`;
}).join('');
container.addEventListener('error',event=>{
  const video=event.target.closest?.('video');
  if(video) video.parentElement.querySelector('.video-error').hidden=false;
},true);
document.querySelector('.filters').addEventListener('click',event=>{
  const button=event.target.closest('button[data-length]');if(!button)return;
  const length=button.dataset.length;let count=0;
  document.querySelectorAll('.filters button').forEach(b=>{const active=b===button;b.classList.toggle('active',active);b.setAttribute('aria-pressed',String(active));});
  document.querySelectorAll('.chain').forEach(c=>{c.hidden=length!=='all'&&c.dataset.length!==length;if(c.hidden)c.querySelectorAll('video').forEach(v=>v.pause());else count++;});
  document.getElementById('count').textContent='显示'+count+'条链';
});
container.addEventListener('click',async event=>{
  const button=event.target.closest('button[data-action]');if(!button)return;
  const section=button.closest('.chain'), videos=[...section.querySelectorAll('video')], action=button.dataset.action;
  if(action==='left'||action==='right'){section.querySelector('.ribbon').scrollBy({left:(action==='left'?-1:1)*515,behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});return;}
  if(action==='pause'){section.dataset.playRequest='';videos.forEach(v=>v.pause());section.querySelector('.play-status').textContent='已暂停';return;}
  document.querySelectorAll('.chain').forEach(c=>{c.dataset.playRequest='';c.querySelectorAll('video').forEach(v=>v.pause());});
  const request=String(Date.now());section.dataset.playRequest=request;
  videos.forEach(v=>{v.muted=true;v.currentTime=0;});
  const results=await Promise.allSettled(videos.map(v=>v.play()));
  if(section.dataset.playRequest!==request)return;
  section.querySelector('.play-status').textContent=results.some(x=>x.status==='rejected')?'部分视频未能自动播放，请使用各视频播放按钮。':'已从头播放本链；播放器加载速度可能不同，可单独暂停对照。';
});
