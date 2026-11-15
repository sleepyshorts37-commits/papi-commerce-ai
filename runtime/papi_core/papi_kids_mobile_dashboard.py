"""Accessible mobile-first PAPI KIDS dashboard HTML renderer.

The dashboard is intentionally read-only. Manuscript selection previews text in the
browser only; it does not upload files or call providers.
"""
from __future__ import annotations

from html import escape
from typing import Any

_ALLOWED_STATUSES = {
    "not_started": "À préparer",
    "planned": "Planifiée",
    "generated": "Générée",
    "pending_visual_review": "À examiner",
    "approved": "Approuvée",
    "rejected": "À corriger",
    "blocked": "Bloquée",
}


def _safe_text(value: Any, field: str, max_length: int = 500) -> str:
    if not isinstance(value, str) or len(value) > max_length:
        raise ValueError(f"Champ invalide : {field}")
    return escape(value, quote=True)


def render_papi_kids_mobile_dashboard(
    *,
    book_id: str,
    title: str,
    page_count: int,
    scenes: list[dict[str, Any]],
    overall_status: str = "En préparation",
    last_updated: str = "Non renseigné",
) -> str:
    """Render a self-contained dashboard without secrets, network calls or mutations."""
    if not isinstance(book_id, str) or not book_id.startswith("PKP-"):
        raise ValueError("Identifiant de livre invalide.")
    if not isinstance(page_count, int) or isinstance(page_count, bool) or not 1 <= page_count <= 200:
        raise ValueError("Nombre de pages invalide.")
    if not isinstance(scenes, list) or len(scenes) != page_count:
        raise ValueError("Une entrée de suivi est requise pour chaque page.")
    safe_title = _safe_text(title, "title", 200)
    safe_id = _safe_text(book_id, "book_id", 40)
    safe_status = _safe_text(overall_status, "overall_status", 80)
    safe_updated = _safe_text(last_updated, "last_updated", 80)

    cards = []
    for expected, scene in enumerate(scenes, start=1):
        if not isinstance(scene, dict) or scene.get("page_number") != expected:
            raise ValueError("Les scènes doivent être ordonnées et numérotées sans doublon.")
        status = scene.get("status", "not_started")
        if status not in _ALLOWED_STATUSES:
            raise ValueError(f"Statut inconnu pour la page {expected}.")
        label = _ALLOWED_STATUSES[status]
        heading = _safe_text(str(scene.get("heading", f"Page {expected}")), "heading", 120)
        detail = _safe_text(str(scene.get("detail", "")), "detail", 300)
        cards.append(
            f'<article class="scene" data-status="{status}">'
            f'<div class="scene-top"><span class="page">Page {expected:02d}</span>'
            f'<span class="pill status-{status}">{label}</span></div>'
            f'<h3>{heading}</h3><p>{detail or "Aucun détail disponible."}</p></article>'
        )

    return """<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#172554">
<title>PAPI KIDS — Tableau de production</title>
<style>
:root{font-family:system-ui,-apple-system,sans-serif;color:#172033;background:#f4f6fb}
*{box-sizing:border-box}body{margin:0}header{background:#172554;color:white;padding:24px 18px 28px}
header .brand{font-size:13px;letter-spacing:.12em;font-weight:800;opacity:.8}
h1{font-size:25px;line-height:1.2;margin:10px 0 6px}header p{margin:0;color:#dbeafe}
main{max-width:850px;margin:auto;padding:16px}
section{background:white;border:1px solid #e3e8f2;border-radius:16px;padding:17px;margin:0 0 14px}
h2{font-size:18px;margin:0 0 12px}.muted{color:#64748b;font-size:13px}
.metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:9px}
.metric{background:#f1f5f9;border-radius:12px;padding:12px}.metric strong{display:block;font-size:23px}
.metric span{font-size:12px;color:#526078}.bookid{font-size:12px;font-weight:700;color:#64748b}
.progress{height:9px;background:#e2e8f0;border-radius:20px;overflow:hidden;margin:12px 0 5px}
.progress span{display:block;height:100%;background:#2563eb;width:0}
input,button{font:inherit}input[type=file]{width:100%;padding:12px;border:1px dashed #94a3b8;border-radius:10px;background:#f8fafc}
.notice{background:#fff7ed;border-left:4px solid #f59e0b;padding:11px;border-radius:8px;font-size:13px}
#preview{white-space:pre-wrap;overflow-wrap:anywhere;max-height:220px;overflow:auto;background:#f8fafc;padding:12px;border-radius:9px;font-size:13px}
.filters{display:flex;gap:8px;overflow:auto;padding:2px 0 12px}
.filters button{border:1px solid #cbd5e1;background:white;border-radius:20px;padding:8px 12px;white-space:nowrap}
.filters button[aria-pressed=true]{background:#172554;color:white;border-color:#172554}
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px}
.scene{border:1px solid #e2e8f0;border-radius:12px;padding:12px;min-width:0}
.scene-top{display:flex;align-items:center;justify-content:space-between;gap:5px}
.page{font-size:12px;font-weight:800;color:#64748b}.pill{font-size:11px;padding:4px 7px;border-radius:20px;background:#e2e8f0}
.status-approved{background:#dcfce7;color:#166534}.status-rejected,.status-blocked{background:#fee2e2;color:#991b1b}
.status-pending_visual_review{background:#fef3c7;color:#92400e}
.scene h3{font-size:14px;margin:10px 0 5px}.scene p{font-size:12px;color:#64748b;margin:0;overflow-wrap:anywhere}
footer{text-align:center;color:#64748b;font-size:12px;padding:12px 0 28px}
@media(max-width:420px){.grid{grid-template-columns:1fr}.metrics{gap:6px}.metric{padding:9px}.metric strong{font-size:20px}}
</style></head><body>
<header><div class="brand">PAPI KIDS PUBLISHING</div>
<h1>"""+safe_title+"""</h1><p>Suivi de fabrication du livre</p></header>
<main>
<section><div class="bookid">"""+safe_id+"""</div><h2>État du projet</h2>
<p>"""+safe_status+"""</p>
<div class="metrics"><div class="metric"><strong>"""+str(page_count)+"""</strong><span>Pages prévues</span></div>
<div class="metric"><strong>"""+str(sum(1 for s in scenes if s.get("status") == "approved"))+"""</strong><span>Illustrations approuvées</span></div>
<div class="metric"><strong>"""+str(sum(1 for s in scenes if s.get("status") == "pending_visual_review"))+"""</strong><span>À examiner</span></div></div>
<div class="progress" role="progressbar" aria-label="Illustrations approuvées" aria-valuemin="0" aria-valuemax="100" aria-valuenow="""+str(round(100*sum(1 for s in scenes if s.get("status")=="approved")/page_count))+"""><span style="width:"""+str(round(100*sum(1 for s in scenes if s.get("status")=="approved")/page_count))+"""%"></span></div>
<p class="muted">Dernière mise à jour : """+safe_updated+"""</p></section>
<section><h2>Transmettre un manuscrit</h2>
<input id="manuscript" type="file" accept=".md,.txt,text/markdown,text/plain">
<p class="muted">Formats acceptés : .md et .txt, maximum 2 Mo.</p>
<label for="upload-token">Jeton de dépôt fourni par l'administrateur</label>
<input id="upload-token" type="password" autocomplete="off" placeholder="Jeton sécurisé du serveur">
<button id="upload-button" type="button" disabled>Envoyer le manuscrit</button>
<p id="upload-result" class="muted" role="status" aria-live="polite">Aucun fichier envoyé.</p>
<div class="notice">L'envoi utilise HTTPS et un jeton Bearer saisi ici. Le jeton n'est pas enregistré par cette interface. L'envoi ne déclenche pas la génération IA.</div>
<pre id="preview" hidden></pre></section>
<section><h2>Consulter l'état d'un manuscrit</h2>
<label for="status-upload-id">Référence du dépôt</label>
<input id="status-upload-id" type="text" inputmode="text" autocomplete="off" placeholder="PKP-UP-…">
<button id="status-button" type="button">Vérifier l'avancement</button>
<p id="status-result" class="muted" role="status" aria-live="polite">Saisissez la référence et le jeton serveur.</p>
<label for="review-token">Jeton de validation humaine</label>
<input id="review-token" type="password" autocomplete="off" placeholder="Jeton de revue distinct">
<button id="editorial-preview-button" type="button">Examiner le plan éditorial</button>
<div id="editorial-preview" aria-live="polite"></div>
<div id="asset-review-list" aria-live="polite"></div>
<hr>
<h2>Mes livres</h2>
<button id="library-button" type="button">Actualiser ma bibliothèque</button>
<div id="book-list" aria-live="polite"></div>
</section>
<section><h2>Suivi des illustrations</h2>
<div class="filters" aria-label="Filtrer les pages">
<button type="button" data-filter="all" aria-pressed="true">Toutes</button>
<button type="button" data-filter="pending_visual_review" aria-pressed="false">À examiner</button>
<button type="button" data-filter="approved" aria-pressed="false">Approuvées</button>
<button type="button" data-filter="rejected" aria-pressed="false">À corriger</button>
</div><div class="grid">"""+ "".join(cards)+"""</div></section>
<footer>Interface de consultation — aucune génération, dépense ou publication déclenchée.</footer>
</main>
<script>
"use strict";
const fileInput=document.getElementById("manuscript");
const preview=document.getElementById("preview");
const tokenInput=document.getElementById("upload-token");
const uploadButton=document.getElementById("upload-button");
const uploadResult=document.getElementById("upload-result");
const statusButton=document.getElementById("status-button");
const statusId=document.getElementById("status-upload-id");
const statusResult=document.getElementById("status-result");
const reviewTokenInput=document.getElementById("review-token");
const editorialPreviewButton=document.getElementById("editorial-preview-button");
const editorialPreview=document.getElementById("editorial-preview");
const assetReviewList=document.getElementById("asset-review-list");
const libraryButton=document.getElementById("library-button");
const bookList=document.getElementById("book-list");
fileInput.addEventListener("change",()=>{
 const file=fileInput.files&&fileInput.files[0];
 preview.hidden=true;preview.textContent="";
 uploadButton.disabled=!file;
 if(!file)return;
 if(!/\.(md|txt)$/i.test(file.name)||file.size>2*1024*1024){
  preview.hidden=false;preview.textContent="Fichier refusé : choisissez un .md ou .txt de 2 Mo maximum.";return;
 }
 const reader=new FileReader();
 reader.onload=()=>{preview.textContent=String(reader.result||"").slice(0,12000);preview.hidden=false;};
 reader.onerror=()=>{preview.textContent="Lecture locale impossible.";preview.hidden=false;};
 reader.readAsText(file);
});
uploadButton.addEventListener("click",async()=>{
 const file=fileInput.files&&fileInput.files[0];
 const token=tokenInput.value;
 if(!file||!token){uploadResult.textContent="Sélectionnez un fichier et saisissez le jeton.";return;}
 uploadButton.disabled=true;uploadResult.textContent="Envoi sécurisé en cours…";
 try{
  const response=await fetch("/api/papi-kids/manuscripts",{
   method:"POST",headers:{"Authorization":"Bearer "+token,
    "Content-Type":file.name.toLowerCase().endsWith(".md")?"text/markdown":"text/plain",
    "X-Filename":encodeURIComponent(file.name)},body:file,credentials:"same-origin"
  });
  const result=await response.json();
  if(!response.ok)throw new Error(result.error||"upload_failed");
  uploadResult.textContent="Manuscrit reçu. Référence : "+result.upload_id+". Analyse éditoriale en attente.";
  statusId.value=result.upload_id;
  await loadLibrary();
  tokenInput.value="";
 }catch(error){uploadResult.textContent="Échec de l'envoi : "+String(error.message||error);}
 finally{uploadButton.disabled=false;}
});
statusButton.addEventListener("click",async()=>{
 const id=statusId.value.trim();
 const token=tokenInput.value;
 if(!/^PKP-UP-[0-9a-f]{32}$/.test(id)||!token){
  statusResult.textContent="Référence ou jeton invalide.";return;
 }
 statusButton.disabled=true;statusResult.textContent="Consultation sécurisée…";
 try{
  const response=await fetch("/api/papi-kids/manuscripts/"+encodeURIComponent(id),{
   method:"GET",headers:{"Authorization":"Bearer "+token},credentials:"same-origin"
  });
  const result=await response.json();
  if(!response.ok)throw new Error(result.error||"status_failed");
  const job=result.job||{};
  statusResult.textContent="Livre : "+result.book_status+
   " — tâche : "+(job.status||"non créée")+
   " — tentatives : "+(job.attempts??0)+"/"+(job.max_attempts??0);
  renderIllustrationReviews(result.illustrations||[],id);
 }catch(error){statusResult.textContent="État indisponible : "+String(error.message||error);}
 finally{statusButton.disabled=false;}
});

editorialPreviewButton.addEventListener("click",async()=>{
 const id=statusId.value.trim();
 const token=reviewTokenInput.value;
 if(!/^PKP-UP-[0-9a-f]{32}$/.test(id)||!token){
  editorialPreview.textContent="Référence de dépôt ou jeton de validation invalide.";return;
 }
 editorialPreviewButton.disabled=true;
 editorialPreview.textContent="Chargement du plan éditorial…";
 try{
  const response=await fetch("/api/papi-kids/manuscripts/"+encodeURIComponent(id)+"/editorial-preview",{
   method:"GET",headers:{"Authorization":"Bearer "+token},credentials:"same-origin"
  });
  const result=await response.json();
  if(!response.ok)throw new Error(result.error||"editorial_preview_failed");
  renderEditorialPreview(result);
 }catch(error){editorialPreview.textContent="Aperçu indisponible : "+String(error.message||error);}
 finally{editorialPreviewButton.disabled=false;}
});
function renderEditorialPreview(result){
 editorialPreview.replaceChildren();
 const heading=document.createElement("h3");heading.textContent=result.title||"Plan éditorial PKP-0001";
 const status=document.createElement("p");
 status.textContent="Analyse : "+result.analysis_status+" — manuscrit canonique : "+(result.source_match?"correspondance confirmée":"différent de la V2 PKP-0001");
 editorialPreview.append(heading,status);
 const bible=document.createElement("details");
 const bibleSummary=document.createElement("summary");bibleSummary.textContent="Bible des personnages";
 const bibleText=document.createElement("pre");bibleText.textContent=result.character_bible||"";
 bible.append(bibleSummary,bibleText);editorialPreview.appendChild(bible);
 const storyboard=document.createElement("details");
 const storyboardSummary=document.createElement("summary");storyboardSummary.textContent="Storyboard";
 const storyboardText=document.createElement("pre");storyboardText.textContent=result.storyboard||"";
 storyboard.append(storyboardSummary,storyboardText);editorialPreview.appendChild(storyboard);
 (result.prompts||[]).forEach(prompt=>{
  const details=document.createElement("details");
  const summary=document.createElement("summary");
  summary.textContent="Page "+prompt.page_number+" — "+prompt.title;
  const body=document.createElement("pre");body.textContent=prompt.prompt;
  details.append(summary,body);editorialPreview.appendChild(details);
 });
 if(result.approval_eligible){
  const approve=document.createElement("button");approve.type="button";
  approve.textContent="Approuver les 24 prompts et la bible graphique";
  approve.addEventListener("click",()=>submitEditorialApproval(result));
  editorialPreview.appendChild(approve);
 }else{
  const warning=document.createElement("p");
  warning.textContent=(result.warnings||["Plan non admissible à l'approbation."]).join(" ");
  editorialPreview.appendChild(warning);
 }
}
async function submitEditorialApproval(preview){
 const token=reviewTokenInput.value;
 if(!token)return;
 const approveButton=editorialPreview.querySelector("button");
 if(approveButton)approveButton.disabled=true;
 try{
  const response=await fetch("/api/papi-kids/manuscripts/"+encodeURIComponent(preview.upload_id)+"/editorial-approval",{
   method:"POST",headers:{"Authorization":"Bearer "+token,"Content-Type":"application/json"},
   body:JSON.stringify({approved:true,source_bundle_sha256:preview.source_bundle_sha256}),
   credentials:"same-origin"
  });
  const result=await response.json();
  if(!response.ok)throw new Error(result.error||"editorial_approval_failed");
  const status=document.createElement("p");
  status.textContent="Plan éditorial approuvé par "+result.reviewer_id+" le "+result.approved_at+". La génération reste désactivée jusqu'à une autorisation distincte.";
  editorialPreview.appendChild(status);
 }catch(error){
  const status=document.createElement("p");status.textContent="Approbation refusée : "+String(error.message||error);
  editorialPreview.appendChild(status);
  if(approveButton)approveButton.disabled=false;
 }
}

async function loadLibrary(){
 const token=tokenInput.value;
 if(!token){bookList.textContent="Saisissez le jeton de dépôt pour consulter vos livres.";return;}
 libraryButton.disabled=true;bookList.textContent="Chargement de la bibliothèque…";
 try{
  const response=await fetch("/api/papi-kids/manuscripts",{
   method:"GET",headers:{"Authorization":"Bearer "+token},credentials:"same-origin"
  });
  const result=await response.json();
  if(!response.ok)throw new Error(result.error||"library_failed");
  bookList.replaceChildren();
  if(!result.books.length){bookList.textContent="Aucun manuscrit reçu.";return;}
  result.books.forEach(book=>{
   const item=document.createElement("div");item.className="book-library-item";
   const heading=document.createElement("strong");heading.textContent=book.title||book.upload_id;
   const details=document.createElement("p");
   details.textContent=book.book_status+" — tâche : "+(book.job_status||"non créée")+
    " — illustrations : "+book.approved_illustration_count+"/"+book.illustration_count+
    " approuvées — "+book.upload_id;
   const open=document.createElement("button");open.type="button";open.textContent="Ouvrir le suivi";
   open.addEventListener("click",()=>{statusId.value=book.upload_id;statusButton.click();});
   item.append(heading,details,open);bookList.appendChild(item);
  });
 }catch(error){bookList.textContent="Bibliothèque indisponible : "+String(error.message||error);}
 finally{libraryButton.disabled=false;}
}
libraryButton.addEventListener("click",loadLibrary);
function renderIllustrationReviews(assets,uploadId){
 assetReviewList.replaceChildren();
 if(!assets.length){assetReviewList.textContent="Aucune illustration enregistrée.";return;}
 assets.forEach(asset=>{
  const item=document.createElement("div");item.className="asset-review-item";
  const label=document.createElement("p");
  const sourceWidth=asset.source_width_px||asset.width_px;
  const sourceHeight=asset.source_height_px||asset.height_px;
  const resolutionState=asset.upscaling_method==="native"?"source natif":
   (asset.resolution_reviewed_by?"super-résolution revue":"super-résolution à vérifier");
  label.textContent="Page "+asset.page_number+" — v"+asset.version+
   " — source "+sourceWidth+"×"+sourceHeight+" → final "+asset.width_px+"×"+asset.height_px+
   " — "+(asset.upscaling_method||"native")+" — "+resolutionState+" — "+asset.review_status;
  item.appendChild(label);
  if(asset.review_status==="pending_review"||asset.review_status==="rejected"){
   ["approved","rejected"].forEach(decision=>{
    const button=document.createElement("button");button.type="button";
    button.textContent=decision==="approved"?"Approuver":"Refuser";
    button.addEventListener("click",()=>submitIllustrationReview(asset.asset_id,decision));
    item.appendChild(button);
   });
  }
  assetReviewList.appendChild(item);
 });
}
async function submitIllustrationReview(assetId,decision){
 const token=reviewTokenInput.value;
 if(!token){statusResult.textContent="Saisissez le jeton de validation humaine.";return;}
 try{
  const response=await fetch("/api/papi-kids/assets/"+encodeURIComponent(assetId)+"/review",{
   method:"POST",headers:{"Authorization":"Bearer "+token,"Content-Type":"application/json"},
   body:JSON.stringify({decision}),credentials:"same-origin"
  });
  const result=await response.json();
  if(!response.ok)throw new Error(result.error||"review_failed");
  statusResult.textContent="Décision enregistrée : "+result.review_status;
  statusButton.click();
 }catch(error){statusResult.textContent="Revue non enregistrée : "+String(error.message||error);}
}
document.querySelectorAll("[data-filter]").forEach(button=>{
 button.addEventListener("click",()=>{
  const filter=button.dataset.filter;
  document.querySelectorAll("[data-filter]").forEach(b=>b.setAttribute("aria-pressed",String(b===button)));
  document.querySelectorAll(".scene").forEach(card=>{
   card.hidden=filter!=="all"&&card.dataset.status!==filter;
  });
 });
});
</script></body></html>"""
