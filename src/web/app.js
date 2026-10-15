"use strict";
const $ = id => document.getElementById(id);
const localTime = value => value ? new Date(value).toLocaleString("zh-CN",{timeZone:"Asia/Shanghai",hour12:false})+"（北京时间）" : "尚无记录";
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
let papers = [], currentPaper = null, currentPage = 1;
const titles = {library:"从文献出发，让研究有据可查。",ask:"先找到证据，再形成结论。",graph:"看见文献之间的真实联系。",search:"把握前沿，保持审慎。",copilot:"让每个研究想法可检验。"};
function toast(text) { $("toast").textContent=text;$("toast").classList.remove("hidden");setTimeout(()=>$("toast").classList.add("hidden"),7000); }
async function api(url,body,method) { const response=await fetch(url,{method:method||(body?"POST":"GET"),headers:body?{"Content-Type":"application/json"}:{},body:body?JSON.stringify(body):undefined});const data=await response.json();if(!response.ok)throw new Error(typeof data.detail==="string"?data.detail:data.error||JSON.stringify(data));return data; }
async function busy(button,action) {button.disabled=true;try{await action();}catch(e){toast(e.message);}finally{button.disabled=false;}}
function show(view) {document.querySelectorAll(".view").forEach(e=>e.classList.toggle("active",e.id===view));document.querySelectorAll("nav button").forEach(e=>e.classList.toggle("active",e.dataset.view===view));$("view-title").textContent=titles[view];}
document.querySelectorAll("nav button").forEach(b=>b.onclick=()=>show(b.dataset.view));
async function refresh() {
 const health=await api("/api/health");$("status").textContent="本地服务已连接";$("model-badge").textContent=health.model_enabled?"真实模型已配置 · 需显式启用":"抽取式模式 · 未调用 LLM";
 papers=await api("/api/papers");$("paper-count").textContent=papers.length;
 $("papers").innerHTML=papers.length?papers.map(p=>`<article class="paper-card"><span class="tag">PDF / ${p.pages.length} PAGES ${p.version?" / V"+p.version:""}</span><h3>${esc(p.title)}</h3><small>${esc(p.author||p.filename)}</small><small>${p.chunk_count} 证据块 · ${p.warnings.length} 项解析提示</small><button data-read="${esc(p.id)}">阅读与溯源 ↗</button><div class="inline"><button data-like="${esc(p.id)}" data-vote="1">感兴趣 ＋</button><button data-like="${esc(p.id)}" data-vote="-1">减少推荐 −</button></div></article>`).join(""):'<div class="panel empty"><h2>从第一篇论文开始</h2><p>上传学术 PDF，或按 README 导入公开论文样例。<br>遇到相近版本时，系统会请求你的版本决策。</p></div>';
 $("paper-choices").innerHTML=papers.map(p=>`<label class="check"><input type="checkbox" name="paper" value="${esc(p.id)}">${esc(p.title.slice(0,80)) + (p.version ? " / v"+p.version : "")}</label>`).join("");["version-first","version-second"].forEach(id=>$(id).innerHTML=papers.map(p=>`<option value="${esc(p.id)}">${esc(p.title.slice(0,55))} ${p.version?"v"+p.version:""}</option>`).join(""));if(papers.length>1)$("version-second").selectedIndex=1;document.querySelectorAll("[data-like]").forEach(b=>b.onclick=()=>busy(b,async()=>{await api("/api/feedback",{paper_id:b.dataset.like,vote:Number(b.dataset.vote)});toast("已保存本地研究兴趣反馈，下次检索排序时使用。");}));document.querySelectorAll("[data-read]").forEach(b=>b.onclick=()=>busy(b,()=>read(b.dataset.read)));await loadWatches();
}
$("upload").onchange=async e=>{for(const file of e.target.files){try{const form=new FormData();form.append("file",file);let response=await fetch("/api/papers",{method:"POST",body:form});let data=await response.json();if(response.status===409){const proceed=confirm(`${file.name}\n${data.duplicates.map(d=>d.recommendation+" · 相似度 "+d.similarity).join("\n")}\n是否将两版同时保留？取消则不导入。`);if(!proceed)continue;response=await fetch("/api/papers?decision=keep_both",{method:"POST",body:form});data=await response.json();}if(!response.ok)throw new Error(data.error||data.detail||"导入失败");toast(`已导入 ${file.name}\n${data.warnings.join("\n")}`);}catch(err){toast(err.message);}}await refresh();e.target.value="";};
let citationReturn = null, readerRequest = 0;
function linkedText(text) {
 return esc(text).replace(/\[([0-9,\s]+)\]/g, (match, list) => list.split(",").map(value=>value.trim()).filter(value=>/^\d{1,3}$/.test(value)).map(value=>`<button class="citation-link" data-ref="${value}">[${value}]</button>`).join(", "));
}
async function read(id,page=1,chunkId="") {
 show("library");const request=++readerRequest;const loaded=currentPaper?.id===id?currentPaper:await api(`/api/papers/${encodeURIComponent(id)}`);if(request!==readerRequest)return;currentPaper=loaded;currentPage=page;
 $("reader").classList.remove("hidden");$("reader-title").textContent=currentPaper.title;
 $("pdf-page").src=`/api/papers/${id}/pages/${page}/image?chunk_id=${encodeURIComponent(chunkId)}`;
 $("original-link").href=`/api/papers/${id}/pdf#page=${page}`;$("page-label").textContent=`${page} / ${currentPaper.pages.length}`;
 $("page-jump").value=page;$("page-jump").max=currentPaper.pages.length;$("prev-page").disabled=page<=1;$("next-page").disabled=page>=currentPaper.pages.length;
 $("original").innerHTML=currentPaper.chunks.filter(c=>c.page===page).map(c=>`<p class="${c.id===chunkId?"highlight":""}" id="${esc(c.id)}">${linkedText(c.text)}</p>`).join("")||"该页无可用文本。";
 $("translation").textContent="翻译需要已启用的真实模型。";$("page-analysis").classList.add("hidden");
 $("headings").innerHTML=currentPaper.headings.map(h=>`<button style="margin-left:${Math.max(0,(h.level||1)-1)*9}px" data-page="${h.page}">${esc(h.title.slice(0,65))}</button>`).join("");
 document.querySelectorAll("[data-page]").forEach(b=>b.onclick=()=>read(id,Number(b.dataset.page)));
 document.querySelectorAll("[data-ref]").forEach(b=>b.onclick=()=>{
   const pattern=new RegExp("^\\["+b.dataset.ref+"\\](?:\\s|$)");
   const ref=currentPaper.references.find(r=>pattern.test(r.text));
   if(!ref){toast("未定位此编号的参考文献，请使用References标题查看原文。");return;}
   citationReturn={id,page,chunkId:b.closest("p")?.id||chunkId};$("back-citation").classList.remove("hidden");read(id,ref.page,ref.chunk_id);
 });
 if(chunkId){const element=document.getElementById(chunkId);if(element)element.scrollIntoView({block:"center"});}
 $("reader").scrollIntoView({behavior:"smooth"});
}
$("close-reader").onclick=()=>$("reader").classList.add("hidden");
let syncing=false;["original","translation"].forEach((id,i)=>$(id).onscroll=()=>{if(syncing)return;syncing=true;const a=$(id),b=$(["translation","original"][i]);b.scrollTop=a.scrollTop/Math.max(1,a.scrollHeight-a.clientHeight)*(b.scrollHeight-b.clientHeight);requestAnimationFrame(()=>syncing=false);});
$("translate-page").onclick=e=>busy(e.target,async()=>{const text=currentPaper.chunks.filter(c=>c.page===currentPage).map(c=>c.text).join("\n");const r=await api("/api/translate",{text,target:"Chinese"});$("translation").textContent=r.output;toast("已收到真实模型翻译，请核对公式与术语。");});
$("ask-button").onclick=e=>busy(e.target,async()=>{const result=await api("/api/ask",{question:$("question").value,paper_ids:[...document.querySelectorAll('input[name="paper"]:checked')].map(c=>c.value),use_model:$("use-model").checked});$("trace").textContent=result.trace.map(t=>`${t.step} → ${t.status} ${t.detail||""}`).join("\n");$("answer").innerHTML=`<span class="badge">${esc(result.mode)} · ${result.latency_ms} ms</span><p>${esc(result.disclaimer)}</p>${result.error?'<p>'+esc(result.error)+'</p>':''}${result.abstained?'<h2>证据不足或模型不可用，未生成结论。</h2>':''}`+(result.mode==="real_llm" ? result.claims : []).map(c=>`<div class="evidence"><blockquote>${esc(c.text)}</blockquote></div>`).join("")+"<h2>可复核证据</h2>"+result.evidence.map(c=>`<div class="evidence"><small>${esc(c.title)} / 第 ${c.page} 页</small><blockquote>${esc(c.text)}</blockquote><button data-source="${esc(c.paper_id)}" data-source-page="${c.page}" data-chunk="${esc(c.id)}">定位原文 ↗</button></div>`).join("");document.querySelectorAll("[data-source]").forEach(b=>b.onclick=()=>read(b.dataset.source,Number(b.dataset.sourcePage),b.dataset.chunk));});
$("search-button").onclick=e=>busy(e.target,async()=>{const r=await api("/api/search?q="+encodeURIComponent($("search-query").value));$("search-results").innerHTML=r.results.map(p=>`<article><h3>${esc(p.title)}</h3><small>${esc(p.published)} ${p.code_available?' / GitHub 线索':''}</small><p>${esc(p.abstract)}</p><p>${esc(p.reason)}</p><p>${esc(p.recommendation_note||"")} ${p.recommendation_score!==undefined?"相关性得分 "+p.recommendation_score:""}</p>${/^https?:\/\/(?:arxiv\.org|export\.arxiv\.org)\//.test(p.url)?`<a href="${esc(p.url)}" target="_blank" rel="noopener">查看来源 ↗</a>`:''}</article>`).join("");});
$("outline-button").onclick=e=>busy(e.target,async()=>{const r=await api("/api/outline",{text:$("idea").value});$("outline").innerHTML=`<p>${esc(r.disclaimer)}</p>`+r.sections.map(s=>`<h3>${esc(s.title)}</h3><p>${esc(s.instruction)}</p>`).join("")+"<h3>References / 已导入条目</h3>"+r.references.map(p=>`<p>${esc(p.title)} — ${esc(p.source)}</p>`).join("")+`<h3>Mermaid 架构脚本</h3><pre>${esc(r.mermaid)}</pre>`;});
$("csv-upload").onchange=async e=>{if(e.target.files[0])$("csv-text").value=await e.target.files[0].text();};
$("csv-button").onclick=e=>busy(e.target,async()=>{const r=await api("/api/csv",{text:$("csv-text").value});const entries=Object.entries(r.series),entry=entries.find(([key])=>key!=="method")||entries[0];const[name,series]=entry,values=series.values;const min=Math.min(0,...values),max=Math.max(0,...values),range=max-min||1,zero=270-(0-min)/range*210,width=500/values.length;$("chart").innerHTML=`<text x="40" y="25" fill="#18312d">${esc(name)} / descriptive only</text><line x1="40" y1="${zero}" x2="570" y2="${zero}" stroke="#bdcbbb"/>`+values.map((v,i)=>{const y=270-(v-min)/range*210;return `<rect x="${50+i*width}" y="${Math.min(y,zero)}" width="${Math.max(1,width-14)}" height="${Math.max(1,Math.abs(zero-y))}" rx="3" fill="#35684e"/><text x="${50+i*width}" y="${y-8}" fill="#18312d">${esc(v)}</text><text x="${50+i*width}" y="300" fill="#667965">${esc(String(r.labels[i]).slice(0,12))}</text>`;}).join("");$("caption").textContent=r.caption;});
refresh().catch(e=>toast(e.message));

$("prev-page").onclick=()=>read(currentPaper.id,currentPage-1);
$("next-page").onclick=()=>read(currentPaper.id,currentPage+1);

$("back-citation").onclick=()=>{if(citationReturn){const back=citationReturn;citationReturn=null;$("back-citation").classList.add("hidden");read(back.id,back.page,back.chunkId);}};
$("diff-button").onclick=e=>busy(e.target,async()=>{const first=$("version-first").value,second=$("version-second").value;if(!first||!second)throw new Error("请先导入文献");const r=await api(`/api/diff?first=${encodeURIComponent(first)}&second=${encodeURIComponent(second)}`);$("diff-output").textContent=r.diff||"正文块没有差异。";});
$("workflow-button").onclick=e=>busy(e.target,async()=>{const r=await api("/api/workflow",{question:$("question").value,paper_ids:[...document.querySelectorAll('input[name="paper"]:checked')].map(c=>c.value),use_model:$("use-model").checked});$("trace").textContent=r.trace.map(t=>`${t.phase}: ${t.tool||t.mode||"completed"}`).join("\n");$("answer").innerHTML=`<span class="badge">${esc(r.mode)}</span><p>${esc(r.limitations)}</p>`+Object.entries(r.outputs).map(([name,value])=>`<article class="evidence"><h3>${esc(({retrieve:"文献证据",graph:"引用图谱",future_work:"未来研究线索",outline:"写作框架"})[name])}</h3><p>${name==="retrieve"?`${value.evidence.length}条候选证据；${value.abstained?"未形成结论":"抽取原文供复核"}`:name==="graph"?`${value.nodes.length}个论文家族，${value.edges.length}条引用关系`:name==="future_work"?`${value.length}条待后续文献验证的原文线索`:`${value.sections.length}节框架，${value.references.length}条本地文献`}</p></article>`).join("");});

$("analyze-page").onclick=e=>busy(e.target,async()=>{
 const paperId=currentPaper.id,pageNum=currentPage;const r=await api(`/api/papers/${paperId}/pages/${pageNum}/analysis`);if(currentPaper.id!==paperId||currentPage!==pageNum)return;
 const target=$("page-analysis");target.classList.remove("hidden");
 target.innerHTML=`<h3>第${r.page}页结构候选</h3><p>${r.cache_hit?"已加载缓存":"本次按页计算"}；合并单元格、科学计数与缺值需对照原文复核。</p>`+r.tables.map(t=>`<article><h4>${esc(t.caption||"无表题线框表格")}</h4><small>${t.row_count}行 × ${t.column_count}列 · 待复核</small><div class="table-scroll"><table>${t.rows.map(row=>`<tr>${row.map(cell=>`<td>${esc(cell)}</td>`).join("")}</tr>`).join("")}</table></div><a href="/api/papers/${currentPaper.id}/pages/${currentPage}/tables/${t.id}/csv">导出未核验CSV</a> <button data-table-highlight="${t.id}">定位表格区域</button></article>`).join("")+(r.tables.length?"":"<p>未定位表格候选；不代表本页一定没有表格。</p>")+`<h4>图像与公式线索</h4><p>${r.embedded_images.length}个嵌入图像；${r.figure_captions.length}条图注；${r.formula_candidates.length}条数学glyph候选。</p>`+r.figure_captions.map(c=>`<p>${esc(c.text)}</p>`).join("")+r.formula_candidates.slice(0,8).map(c=>`<pre>${esc(c.text)}</pre>`).join("")+r.limitations.map(t=>`<p>${esc(t)}</p>`).join("");
 document.querySelectorAll("[data-table-highlight]").forEach(b=>b.onclick=()=>{$("pdf-page").src=`/api/papers/${currentPaper.id}/pages/${currentPage}/image?table_id=${b.dataset.tableHighlight}`;});
 target.scrollIntoView({behavior:"smooth",block:"nearest"});
});

async function loadWatches(){
 const r=await api("/api/watchlist");
 $("watch-list").innerHTML=r.watches.map(w=>`<article class="evidence"><h3>${esc(w.query)}</h3><p>${w.enabled?"已启用":"已停用"} · 已刷新${w.runs_count}/${w.refresh_limit}次 · 间隔${w.interval_minutes}分钟</p><p>上次成功：${esc(w.last_success_at?localTime(w.last_success_at):"尚未成功刷新")} ${w.last_error?"；最近错误："+esc(w.last_error):""}</p><button data-watch-action="toggle" data-watch-id="${w.id}">${w.enabled?"停用自动追踪":w.runs_count>=w.refresh_limit?"增加2次并启用":"启用自动追踪"}</button> <button data-watch-action="refresh" data-watch-id="${w.id}">立即刷新（计入次数）</button> <button data-watch-action="history" data-watch-id="${w.id}">查看真实快照</button></article>`).join("")||"<p>没有追踪主题，系统不会进行后台检索。</p>";
 document.querySelectorAll("[data-watch-action]").forEach(button=>button.onclick=()=>busy(button,async()=>{
  const w=r.watches.find(w=>String(w.id)===button.dataset.watchId),action=button.dataset.watchAction;
  if(action==="toggle"){
   const body={enabled:!w.enabled};if(!w.enabled&&w.runs_count>=w.refresh_limit)body.refresh_limit=Math.min(48,w.refresh_limit+2);
   await api(`/api/watchlist/${w.id}`,body,"PATCH");await loadWatches();
  }else if(action==="refresh"){
   const result=await api(`/api/watchlist/${w.id}/refresh`,{});toast(result.status==="completed"?`已完成真实刷新，${result.new_count}个新版本/条目`:"刷新失败，错误已保存，没有使用模拟论文。");await loadWatches();
  }else{
   const history=await api(`/api/watchlist/${w.id}/runs`);
   $("watch-history").innerHTML=`<h3>${esc(w.query)} / 最近真实快照</h3>`+history.runs.map(run=>`<article class="evidence"><b>${esc(run.status)} · ${esc(localTime(run.finished_at))}</b><p>新增${run.new_count}项 ${esc(run.error||"")}</p>`+run.results.map(p=>`<p>${p.is_new_to_watch?"[新] ":""}${esc(p.title)}</p>`).join("")+"</article>").join("");
  }
 }));
}
$("save-watch").onclick=e=>busy(e.target,async()=>{await api("/api/watchlist",{query:$("search-query").value,interval_minutes:Number($("watch-interval").value),refresh_limit:Number($("watch-limit").value),enabled:$("watch-enabled").checked});await loadWatches();toast("追踪配置已保存。默认未启用时不会后台联网。");});

$("jump-page").onclick=e=>busy(e.target,async()=>{const page=Number($("page-jump").value);if(!Number.isInteger(page)||page<1||page>currentPaper.pages.length)throw new Error("页码超出文献范围");await read(currentPaper.id,page);});
