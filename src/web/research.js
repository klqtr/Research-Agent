"use strict";
const modeLabels={deterministic_workflow:"确定性文献工作流 · 未调用 LLM",extractive_fallback:"模型流程不可用 · 仅返回原文摘录",real_llm_native_tools:"真实模型原生工具流程",real_llm_rag_compatibility:"真实模型 RAG 兼容模式 · 非原生规划"};
const supportLabels={fully_supported:"完整原文支持",partially_supported:"部分支持 · 需复核",evidence_conflict:"差异/冲突候选 · 需复核",insufficient_evidence:"缺乏证据",cannot_judge:"无法判断"};
const reasonLabels={complete_source_quotation_only:"与完整来源摘录一致",source_fragment_or_heading_not_complete_statement:"来源为片段或标题，暂不发布结论",numeric_discrepancy_candidate_not_general_contradiction_proof:"数值不同，需核对实验配置",cross_version_quantity_discrepancy_requires_review:"不同版本的数值证据需要复核",paraphrase_not_independently_verified:"改写尚未得到独立核验",no_lexical_support_signal:"未找到支持这项断言的线索",only_some_claim_atoms_are_complete_quotes:"仅部分断言可对应原文",invalid_claim_or_citation_version:"断言或引用版本不一致",unverifiable_quote:"引文无法在来源中核对",missing_claim_or_citation:"缺少断言或来源"};
let lastResearchRun=null;

function researchBody(useModel){
 const policy=$("research-version").value;
 return {question:$("question").value,paper_ids:[...document.querySelectorAll('input[name="paper"]:checked')].map(item=>item.value),use_model:useModel,
         version_policy:policy,explicit_version:policy==="explicit"?Number($("explicit-version").value):null,allow_network:$("research-network").checked};
}
function renderResearch(result){
 lastResearchRun=result.run_id;
 const synthesis=result.synthesis||{claims:[],audit:[]},context=result.version_context||{},accounting=result.accounting||{};
 $("trace").textContent=`运行 ${result.run_id}\n${result.phase} · ${result.rounds||0} 轮模型 · ${result.tool_count||0} 次工具\n`+result.trace.map(item=>`${item.phase} / ${item.tool||item.round||""} / ${item.status||""}`).join("\n");
 $("answer").innerHTML=`<span class="badge">${esc(modeLabels[result.mode]||result.mode)}</span><p>${esc(result.limitations)}</p>${result.fallback_reason?`<p>${esc(result.fallback_reason)}</p>`:""}<p>版本策略 ${esc(context.policy)} · ${context.selected_ids?.length||0} 份来源 · ${context.warnings?.length||0} 份较旧版本提示</p><button id="resume-research">读取 / 恢复此工作流</button>`+
  (synthesis.claims.length?"<h2>来源表述 / 需科研人员复核</h2>":"<h2>当前未发布可核验结论</h2>")+synthesis.claims.map(claim=>`<article class="evidence"><blockquote>${esc(claim.text)}</blockquote><small>通过保守引文关卡；不证明现实事实或一般语义蕴含。</small></article>`).join("")+
  `<h3>逐项支持度</h3>`+(synthesis.audit||[]).map(item=>`<p class="support-${item.release?'accepted':'review'}">${esc(supportLabels[item.status]||item.status)} · ${esc(reasonLabels[item.reason]||"需要来源复核")}</p>`).join("")+
  `<h3>证据与版本</h3>`+(result.evidence||[]).map(item=>`<article class="evidence"><small>${esc(item.title)} / v${item.source_version||"?"} / 第${item.page}页</small><blockquote>${esc(item.text)}</blockquote><button data-research-paper="${esc(item.paper_id)}" data-research-page="${item.page}" data-research-chunk="${esc(item.id)}">定位原文 ↗</button></article>`).join("")+
  `<p>本工作流预留 ${accounting.attempts_reserved||0} 次模型请求；实际费用 ${accounting.actual_cost_usd===null||accounting.actual_cost_usd===undefined?'未知 / 未计价':esc(accounting.actual_cost_usd)+' USD'}。缺少usage/单价时不填0。</p>`;
 document.querySelectorAll("[data-research-paper]").forEach(button=>button.onclick=()=>busy(button,()=>read(button.dataset.researchPaper,Number(button.dataset.researchPage),button.dataset.researchChunk)));
 $("resume-research").onclick=event=>busy(event.target,async()=>renderResearch(await api(`/api/research/${lastResearchRun}/resume`,{})));
}
$("ask-button").onclick=event=>busy(event.target,async()=>renderResearch(await api("/api/research",researchBody(false))));
$("workflow-button").onclick=event=>busy(event.target,async()=>renderResearch(await api("/api/research",researchBody($("use-model").checked))));
$("model-status").onclick=event=>busy(event.target,async()=>{$("model-details").textContent=JSON.stringify(await api("/api/model/status"),null,2);});
$("model-health").onclick=event=>busy(event.target,async()=>{$("model-details").textContent=JSON.stringify(await api("/api/model/probe",{inference:false}),null,2);});
$("model-capabilities").onclick=event=>busy(event.target,async()=>{if(!$("allow-capability-probe").checked)throw new Error("请先勾选允许两次计入预算的真实能力探测。");$("model-details").textContent=JSON.stringify(await api("/api/model/probe",{inference:true}),null,2);});
$("translate-page").onclick=event=>busy(event.target,async()=>{
 const id=currentPaper.id,page=currentPage,request=readerRequest,glossary={};
 for(const entry of $("translation-glossary").value.split(/[;；]/).filter(item=>item.trim())){
  const index=entry.indexOf("=");if(index<1)throw new Error("术语格式为英文=译文，以分号分隔。");glossary[entry.slice(0,index).trim()]=entry.slice(index+1).trim();
 }
 const result=await api(`/api/papers/${id}/pages/${page}/translation`,{target:"Chinese",glossary});
 if(readerRequest!==request||currentPaper.id!==id||currentPage!==page)return;
 $("translation").innerHTML=`<p>${esc(result.validation_scope)}</p>`+result.segments.map(segment=>`<article data-translation-block="${esc(segment.id)}"><p>${esc(segment.translation)}</p><button data-translation-source="${esc(segment.id)}">对照原段落 ↗</button></article>`).join("");
 document.querySelectorAll("[data-translation-source]").forEach(button=>button.onclick=()=>{
  const source=document.getElementById(button.dataset.translationSource);if(source){document.querySelectorAll("#original .highlight").forEach(item=>item.classList.remove("highlight"));source.classList.add("highlight");source.scrollIntoView({block:"center"});}
  $("pdf-page").src=`/api/papers/${id}/pages/${page}/image?chunk_id=${encodeURIComponent(button.dataset.translationSource)}`;
 });
 toast("译文已按段落定位并检查保护标记；真实语言质量仍需人工审阅。");
});
$("diff-button").onclick=event=>busy(event.target,async()=>{
 const first=$("version-first").value,second=$("version-second").value;
 const diff=await api(`/api/diff?first=${encodeURIComponent(first)}&second=${encodeURIComponent(second)}`);$("diff-output").textContent=diff.diff||"正文块无差异";
 try{const facts=await api(`/api/version-facts?first=${encodeURIComponent(first)}&second=${encodeURIComponent(second)}`);$("version-facts").innerHTML=`<p>${esc(facts.limitations||"")}</p>`+facts.changes.map(change=>`<article class="evidence"><h4>数值变化候选 · 需复核</h4><p>v${change.old.version} 第${change.old.page}页 → v${change.new.version} 第${change.new.page}页</p><blockquote>${esc(change.old.quote)}</blockquote><blockquote>${esc(change.new.quote)}</blockquote></article>`).join("")+(facts.changes.length?"":"<p>未发现当前规则覆盖的数值变化；不代表结论没有改变。上方仍提供真实原文差异。</p>");}
 catch(error){$("version-facts").textContent=error.message;}
});
$("load-research-map").onclick=event=>busy(event.target,async()=>{
 const result=await api("/api/research-map");$("research-map").innerHTML=`<p>${esc(result.limitations)}</p><h3>主题候选</h3>`+result.topics.map(topic=>`<p>${topic.id}. ${esc(topic.terms.join(" / "))} · ${topic.paper_ids.length} 篇</p>`).join("")+"<h3>首发时间线</h3>"+result.timeline.map(item=>`<p><b>${esc(item.first_submitted?.slice(0,10)||'日期未知')}</b> ${esc(item.title)} / 本地 v${item.version||'?'}</p>`).join("");
});
