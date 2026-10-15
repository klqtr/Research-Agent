"use strict";
let citationGraph = null;

function focusGraph(id) { $("graph-focus").value=id;renderCitationGraph(); }
function renderCitationGraph() {
 const graph=citationGraph;if(!graph)return;
 const focus=$("graph-focus").value,positions={},byId=new Map(graph.nodes.map((node,i)=>[node.id,{...node,number:i+1}]));
 const edges=graph.edges.filter(edge=>!focus||edge.source===focus||edge.target===focus);
 const active=new Set(edges.flatMap(edge=>[edge.source,edge.target]));if(focus)active.add(focus);
 graph.nodes.forEach((node,i)=>{const angle=i/Math.max(1,graph.nodes.length)*Math.PI*2-Math.PI/2;positions[node.id]=[350+Math.cos(angle)*265,280+Math.sin(angle)*235];});
 $("graph-svg").innerHTML='<defs><marker id="citation-arrow" viewBox="0 0 10 10" refX="24" refY="5" markerWidth="5" markerHeight="5" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" fill="#6e927f"/></marker></defs>'+edges.map(edge=>{const a=positions[edge.source],b=positions[edge.target];return `<line x1="${a[0]}" y1="${a[1]}" x2="${b[0]}" y2="${b[1]}" stroke="#6e927f" stroke-opacity="${focus?.65:.25}" marker-end="url(#citation-arrow)"><title>${esc(byId.get(edge.source).title)} → ${esc(byId.get(edge.target).title)}</title></line>`;}).join("")+graph.nodes.map((node,i)=>{const[x,y]=positions[node.id],opacity=!focus||active.has(node.id)?1:.2;return `<g data-graph-node="${esc(node.id)}" opacity="${opacity}" tabindex="0" role="button" aria-label="聚焦 ${esc(node.title)}"><title>${i+1}. ${esc(node.title)} / ${node.pagerank}</title><circle cx="${x}" cy="${y}" r="${16+Math.min(8,node.pagerank*40)}" fill="${node.id===focus?'#b28b3e':'#35684e'}"/><text x="${x}" y="${y+4}" text-anchor="middle" fill="white">${i+1}</text></g>`;}).join("");
 document.querySelectorAll("[data-graph-node]").forEach(node=>{node.onclick=()=>focusGraph(node.dataset.graphNode);node.onkeydown=e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();focusGraph(node.dataset.graphNode);}};});
 $("graph-summary").textContent=`${graph.nodes.length} 个论文家族 · ${graph.edges.length} 条匹配引用 · 当前显示 ${edges.length} 条 · PageRank ${graph.algorithm.iterations} 次迭代`;
 $("graph-note").textContent=graph.limitations;
 $("ranks").innerHTML=graph.nodes.map((node,i)=>`<button class="rank-row ${node.id===focus?'selected':''}" data-rank="${esc(node.id)}"><span class="rank-index">${i+1}</span><span>${esc(node.title)}<small>${node.first_submission_year||'年份未核验'} · ${node.arxiv_id?esc(node.arxiv_id):'非 arXiv'} · PR ${node.pagerank.toFixed(5)}</small></span></button>`).join("");
 document.querySelectorAll("[data-rank]").forEach(button=>button.onclick=()=>focusGraph(button.dataset.rank));
 $("graph-edges").innerHTML=edges.map(edge=>`<article class="evidence"><b>${byId.get(edge.source).number} → ${byId.get(edge.target).number}</b><p>${esc(byId.get(edge.source).title)} → ${esc(byId.get(edge.target).title)}</p><blockquote>${esc(edge.reference_quote)}</blockquote><small>${edge.basis.includes('identifier')?'arXiv ID 匹配':'完整归一化标题匹配'} · 第 ${edge.source_page||'?'} 页 · ${edge.numeric_body_mentions===null?'作者年份引文未计频':`正文数字引文出现 ${edge.numeric_body_mentions} 次（非质量指标）`}</small><p><button data-edge-source="${esc(edge.source)}" data-edge-page="${edge.source_page||1}" data-edge-chunk="${esc(edge.source_chunk_id||'')}">${edge.source_chunk_id?'定位引用证据 ↗':'仅定位参考文献页 ↗'}</button></p></article>`).join("")||"<p>该节点没有匹配的本地引用边；不代表论文没有参考文献。</p>";
 document.querySelectorAll("[data-edge-source]").forEach(button=>button.onclick=()=>busy(button,()=>read(button.dataset.edgeSource,Number(button.dataset.edgePage),button.dataset.edgeChunk)));
}

$("graph-focus").onchange=renderCitationGraph;
$("refresh-graph").onclick=e=>busy(e.target,async()=>{
 citationGraph=await api("/api/graph");
 $("graph-focus").innerHTML='<option value="">全部节点</option>'+citationGraph.nodes.map((node,i)=>`<option value="${esc(node.id)}">${i+1}. ${esc(node.title)}</option>`).join("");
 renderCitationGraph();$("export-graph").disabled=false;
 const future=await api("/api/future-work");
 $("future").innerHTML=future.map(item=>`<div class="evidence"><blockquote>${esc(item.text)}</blockquote><small>第${item.page}页 · ${esc(item.status)}</small></div>`).join("")||"未识别到明确 Future Work 片段。";
});
$("export-graph").onclick=()=>{
 const clone=$("graph-svg").cloneNode(true);clone.setAttribute("xmlns","http://www.w3.org/2000/svg");clone.setAttribute("width","1000");clone.setAttribute("height","800");
 // Keep the numbered legend in the exported file so nodes remain identifiable.
 clone.setAttribute("viewBox",`0 0 1000 ${620+citationGraph.nodes.length*23}`);clone.setAttribute("height",String(620+citationGraph.nodes.length*23));
 citationGraph.nodes.forEach((node,i)=>{const text=document.createElementNS("http://www.w3.org/2000/svg","text");text.setAttribute("x","25");text.setAttribute("y",String(610+i*23));text.setAttribute("fill","#18312d");text.setAttribute("font-size","12");text.textContent=`${i+1}. ${node.title} / PR ${node.pagerank}`;clone.appendChild(text);});
 const url=URL.createObjectURL(new Blob([new XMLSerializer().serializeToString(clone)],{type:"image/svg+xml"}));const link=document.createElement("a");link.href=url;link.download="ResearchTrace_citation_graph.svg";link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
};
