'use strict';
window.renderBranches=(data,videoCard,editCard)=>{
 const h=v=>String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 function tree(c){
  const children=Array.from({length:c.node_ids.length},()=>[]);c.steps.forEach(e=>children[e.source_history_occurrence].push(e.output_history_occurrence));
  const xy={};let leaf=0;function place(i,depth){const ys=children[i].map(j=>place(j,depth+1));const y=ys.length?ys.reduce((a,b)=>a+b,0)/ys.length:55+leaf++*112;xy[i]=[70+depth*185,y];return y;}place(0,0);
  const width=Math.max(...Object.values(xy).map(p=>p[0]))+85;
  const edges=c.steps.map(e=>{const a=xy[e.source_history_occurrence],b=xy[e.output_history_occurrence];return `<g class="${e.is_branch?'branch-connector':'normal-connector'}"><path d="M ${a[0]+40} ${a[1]} C ${a[0]+90} ${a[1]},${b[0]-90} ${b[1]},${b[0]-46} ${b[1]}" fill="none" stroke="currentColor" stroke-width="2" marker-end="url(#arrow-${h(c.example_id)})"/><text x="${(a[0]+b[0])/2}" y="${(a[1]+b[1])/2-10}" text-anchor="middle">${h(e.axis_label)}${e.is_branch?' · 分叉':''}</text></g>`}).join('');
  return `<div class="tree-scroll"><svg class="tree" role="img" aria-label="${h(c.example_id)}真实父子关系" viewBox="0 0 ${width} 225" style="width:${width}px"><defs><marker id="arrow-${h(c.example_id)}" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8" fill="#697e8c"/></marker></defs>${edges}${Object.entries(xy).map(([i,[x,y]])=>`<g><rect x="${x-40}" y="${y-20}" width="80" height="40" rx="7"/><text x="${x}" y="${y+5}" text-anchor="middle">V${i}${i==='0'?' 原始':''}</text></g>`).join('')}</svg></div>`;
 }
 return data.chains.map(c=>{
  const root=data.nodes[c.root_node],branch=c.steps.find(e=>e.is_branch);
  return `<section class="chain branch-chain" id="${h(c.example_id)}" data-length="${c.edit_count}"><div class="chain-head"><div class="chain-title"><span class="chain-index">${h(c.example_id)}</span><div><h2>${c.edit_count}轮编辑 · 从 V${branch.source_history_occurrence} 分叉</h2><div class="chain-meta">${h(root.labels.sex)} · ${h(root.labels.aspect)} · ${h(c.session_id)} · ${h(c.split)}</div></div></div><div class="toolbar"><button class="primary" data-action="play">从头播放本例</button><button data-action="pause">暂停</button></div></div>
  <div class="branch-explanation">第 ${branch.edit_round} 轮回到 <b>V${branch.source_history_occurrence}</b>，生成 <b>V${branch.output_history_occurrence}</b>；本轮不以 V${branch.edit_round-1} 为编辑起点。虚线表示这次分叉编辑。</div>${tree(c)}
  ${c.paths.map((path,index)=>`<div class="path-heading"><strong>路径 ${index===0?'A':'B'}</strong><span>${path.map(i=>'V'+i).join(' → ')} · 共享前缀为同一视频，重复展示便于比较</span></div><div class="ribbon" tabindex="0" aria-label="${h(c.example_id)}路径${index===0?'A':'B'}">${path.map((v,j)=>{if(!j)return videoCard(c.node_ids[v],v,null);const e=c.steps[v-1];return editCard(e)+videoCard(c.node_ids[v],v,e.axis)}).join('')}</div>`).join('')}<div class="play-status" aria-live="polite"></div></section>`;
 }).join('');
};
