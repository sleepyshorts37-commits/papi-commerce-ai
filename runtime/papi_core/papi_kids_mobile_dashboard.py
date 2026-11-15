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
input,button,textarea{font:inherit}input[type=file]{width:100%;padding:12px;border:1px dashed #94a3b8;border-radius:10px;background:#f8fafc}
label{display:block;font-size:13px;font-weight:650;margin:12px 0 5px}
input:not([type=checkbox]):not([type=file]),select{width:100%;padding:10px;border:1px solid #cbd5e1;border-radius:9px;background:white}
input[type=checkbox]{width:auto;min-height:18px}
textarea{width:100%;min-height:88px;padding:10px;border:1px solid #cbd5e1;border-radius:9px}
#kdp-metadata-result{overflow-wrap:anywhere}
.safety-issue{border:1px solid #fbbf24;background:#fffbeb;padding:10px;border-radius:10px;margin:8px 0}
.safety-issue strong{font-size:12px}.safety-issue p{font-size:13px;margin:5px 0}
.safety-actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}
.safety-actions button{padding:9px 12px;border:1px solid #94a3b8;border-radius:9px;background:#f8fafc}
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
<div id="asset-review-list" aria-live="polite"></div>
<hr>
<h2>Validation de sécurité jeunesse</h2>
<p class="muted">Les alertes sont des signaux à examiner, pas un verdict automatique. La validation reste humaine.</p>
<label for="safety-review-token">Jeton distinct de revue sécurité</label>
<input id="safety-review-token" type="password" autocomplete="off" placeholder="Jeton sécurité côté serveur">
<div id="safety-review-list" aria-live="polite"></div>
<hr>
<h2>Fiche commerciale Amazon KDP</h2>
<p class="muted">Complétez les champs connus. Les champs manquants restent explicitement bloquants ; aucune donnée commerciale n'est inventée.</p>
<label for="metadata-token">Jeton distinct des métadonnées KDP</label>
<input id="metadata-token" type="password" autocomplete="off" placeholder="Jeton KDP côté serveur">
<label for="kdp-title">Titre</label><input id="kdp-title" type="text" maxlength="200">
<label for="kdp-author">Auteur</label><input id="kdp-author" type="text" maxlength="100">
<label for="kdp-description">Description commerciale</label><textarea id="kdp-description" maxlength="4000"></textarea>
<label for="kdp-language">Langue (code, ex. fr)</label><input id="kdp-language" type="text" maxlength="5" value="fr">
<label for="kdp-keywords">Mots-clés (un par ligne, maximum 7)</label><textarea id="kdp-keywords"></textarea>
<label for="kdp-categories">Catégories KDP (une par ligne, maximum 3)</label><textarea id="kdp-categories"></textarea>
<div class="metrics">
<div><label for="kdp-age-min">Âge minimum</label><input id="kdp-age-min" type="number" min="3" max="18"></div>
<div><label for="kdp-age-max">Âge maximum</label><input id="kdp-age-max" type="number" min="3" max="18"></div>
<div><label for="kdp-price">Prix catalogue</label><input id="kdp-price" type="number" min="0" step="0.01"></div>
</div>
<label for="kdp-rights-holder">Titulaire des droits</label><input id="kdp-rights-holder" type="text">
<label for="kdp-rights-evidence">Référence de preuve des droits</label><input id="kdp-rights-evidence" type="text">
<label><input id="kdp-rights-confirmed" type="checkbox"> J'atteste disposer des droits commerciaux</label>
<label for="kdp-territories">Territoires (worldwide ou codes pays séparés par virgule)</label><input id="kdp-territories" type="text">
<label for="kdp-isbn-strategy">ISBN broché</label>
<select id="kdp-isbn-strategy"><option value="">À choisir</option><option value="kdp_free_isbn">ISBN gratuit KDP</option><option value="own_isbn">Mon ISBN personnel</option></select>
<label for="kdp-isbn">ISBN-13 personnel (si choisi)</label><input id="kdp-isbn" type="text">
<label for="kdp-publisher">Éditeur (si ISBN personnel)</label><input id="kdp-publisher" type="text">
<label for="kdp-marketplace">Marketplace</label><input id="kdp-marketplace" type="text">
<label for="kdp-currency">Devise (ex. EUR, USD)</label><input id="kdp-currency" type="text" maxlength="3">
<label for="kdp-pricing-date">Date de vérification du prix</label><input id="kdp-pricing-date" type="date">
<label><input id="kdp-pricing-verified" type="checkbox"> Prix et redevance vérifiés</label>
<button id="kdp-metadata-save" type="button">Enregistrer le brouillon KDP</button>
<div id="kdp-metadata-result" class="muted" role="status" aria-live="polite">Aucune fiche enregistrée.</div>
<hr>
<h2>Fabrication du package KDP</h2>
<p class="notice">La fabrication utilise uniquement le profil privé du serveur et les illustrations déjà approuvées. Elle ne téléverse ni ne publie le livre.</p>
<label for="kdp-build-token">Jeton distinct de fabrication KDP</label>
<input id="kdp-build-token" type="password" autocomplete="off" placeholder="Jeton de fabrication côté serveur">
<button id="kdp-build-button" type="button">Fabriquer les fichiers KDP</button>
<div id="kdp-build-result" class="muted" role="status" aria-live="polite">Aucun package fabriqué.</div>
<hr>
<h2>État de l'infrastructure</h2>
<p class="muted">Contrôle des variables et du stockage sans afficher les valeurs des secrets et sans appeler les fournisseurs.</p>
<label for="readiness-token">Jeton distinct de diagnostic</label>
<input id="readiness-token" type="password" autocomplete="off" placeholder="Jeton diagnostic côté serveur">
<button id="readiness-button" type="button">Vérifier la préparation</button>
<div id="readiness-result" class="muted" role="status" aria-live="polite">Diagnostic non exécuté.</div>
<hr>
<h2>Inspection humaine des fichiers KDP</h2>
<p class="muted">Téléchargez chaque fichier, inspectez-le sur iPhone, puis approuvez ou refusez la version exacte.</p>
<label for="kdp-review-token">Jeton distinct de revue des fichiers KDP</label>
<input id="kdp-review-token" type="password" autocomplete="off" placeholder="Jeton de revue KDP côté serveur">
<div id="kdp-package-review-list" aria-live="polite">Aucun package à inspecter.</div>

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
const assetReviewList=document.getElementById("asset-review-list");
const safetyReviewTokenInput=document.getElementById("safety-review-token");
const safetyReviewList=document.getElementById("safety-review-list");
const metadataTokenInput=document.getElementById("metadata-token");
const metadataSaveButton=document.getElementById("kdp-metadata-save");
const metadataResult=document.getElementById("kdp-metadata-result");
const kdpBuildTokenInput=document.getElementById("kdp-build-token");
const kdpBuildButton=document.getElementById("kdp-build-button");
const kdpBuildResult=document.getElementById("kdp-build-result");
const readinessTokenInput=document.getElementById("readiness-token");
const readinessButton=document.getElementById("readiness-button");
const readinessResult=document.getElementById("readiness-result");
const kdpReviewTokenInput=document.getElementById("kdp-review-token");
const kdpPackageReviewList=document.getElementById("kdp-package-review-list");
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
  const packageBuild=result.kdp_package_build||{};
  statusResult.textContent="Livre : "+result.book_status+
   " — tâche : "+(job.status||"non créée")+
   " — tentatives : "+(job.attempts??0)+"/"+(job.max_attempts??0)+
   (packageBuild.status?" — package v"+packageBuild.package_version+" : "+packageBuild.status:"");
  renderIllustrationReviews(result.illustrations||[],id);
  renderSafetyReview(job.analysis&&job.analysis.child_safety_screening,
   result.content_safety_review,id);
  renderKdpMetadata(result.kdp_listing_metadata||{},result.kdp_listing_metadata_status||"",result.kdp_listing_metadata_blockers||[]);
  renderKdpPackageReview(result.kdp_package_build||{},result.kdp_package_reviews||{},id);
 }catch(error){statusResult.textContent="État indisponible : "+String(error.message||error);}
 finally{statusButton.disabled=false;}
});
function renderKdpPackageReview(packageBuild,reviews,uploadId){
 kdpPackageReviewList.replaceChildren();
 if(!packageBuild||!packageBuild.package_version){
  kdpPackageReviewList.textContent="Aucun package KDP fabriqué pour ce manuscrit.";
  return;
 }
 const summary=document.createElement("p");
 summary.textContent="Package v"+packageBuild.package_version+" — "+packageBuild.status+
  " — empreinte manifeste : "+(packageBuild.manifest_sha256||"non disponible");
 kdpPackageReviewList.appendChild(summary);
 const artifacts=[
  ["interior",(packageBuild.pdfs||{}).interior,"PDF intérieur"],
  ["cover",(packageBuild.pdfs||{}).cover,"Couverture"],
  ["ebook",packageBuild.ebook,"EPUB"]
 ];
 artifacts.forEach(([artifact,record,label])=>{
  if(!record)return;
  const card=document.createElement("section");card.className="card";
  const title=document.createElement("h3");title.textContent=label;
  const detail=document.createElement("p");
  detail.textContent="Pages : "+record.page_count+" — SHA-256 : "+record.sha256+
   " — préflight : "+record.preflight;
  card.append(title,detail);
  const reviewKey="v"+packageBuild.package_version+":"+artifact;
  const review=reviews[reviewKey];
  if(review&&review.artifact_sha256===record.sha256){
   const status=document.createElement("p");
   status.textContent="Décision : "+(review.approved?"APPROUVÉ":"REFUSÉ")+
    " — "+(review.reviewer_id||"")+
    " — "+(review.reviewed_at||"");
   card.appendChild(status);
   if(review.approved){kdpPackageReviewList.appendChild(card);return;}
  }
  const download=document.createElement("button");download.type="button";
  download.textContent="Ouvrir / télécharger "+label;
  download.addEventListener("click",()=>openKdpPackageArtifact(uploadId,artifact));
  card.appendChild(download);
  const notes=document.createElement("textarea");
  notes.placeholder="Notes d'inspection (minimum 20 caractères).";
  notes.maxLength=2000;
  card.appendChild(notes);
  const actions=document.createElement("div");actions.className="safety-actions";
  ["approved","rejected"].forEach(decision=>{
   const button=document.createElement("button");button.type="button";
   button.textContent=decision==="approved"?"Approuver ce fichier":"Refuser ce fichier";
   button.addEventListener("click",()=>submitKdpPackageReview(
    uploadId,artifact,record.sha256,decision,notes.value
   ));
   actions.appendChild(button);
  });
  card.appendChild(actions);kdpPackageReviewList.appendChild(card);
 });
}
async function openKdpPackageArtifact(uploadId,artifact){
 const token=kdpReviewTokenInput.value;
 if(!token){kdpPackageReviewList.insertAdjacentText("afterbegin","Saisissez le jeton de revue KDP.");return;}
 const popup=window.open("about:blank","_blank");
 try{
  const response=await fetch("/api/papi-kids/manuscripts/"+encodeURIComponent(uploadId)+
   "/kdp-package/"+artifact,{
   method:"GET",headers:{"Authorization":"Bearer "+token},credentials:"same-origin"
  });
  if(!response.ok)throw new Error("download_failed");
  const blob=await response.blob(),url=URL.createObjectURL(blob);
  if(popup)popup.location.href=url;
  else{
   const link=document.createElement("a");link.href=url;link.download=artifact==="ebook"?"book.epub":artifact+".pdf";
   document.body.appendChild(link);link.click();link.remove();
  }
 }catch(error){if(popup)popup.close();kdpPackageReviewList.insertAdjacentText("afterbegin","Téléchargement impossible : "+String(error.message||error));}
}
async function submitKdpPackageReview(uploadId,artifact,sha256,decision,notes){
 const token=kdpReviewTokenInput.value;
 if(!token){kdpPackageReviewList.insertAdjacentText("afterbegin","Saisissez le jeton de revue KDP.");return;}
 if(notes.trim().length<20){kdpPackageReviewList.insertAdjacentText("afterbegin","Ajoutez au moins 20 caractères de notes d'inspection.");return;}
 try{
  const response=await fetch("/api/papi-kids/manuscripts/"+encodeURIComponent(uploadId)+"/kdp-package-review",{
   method:"POST",headers:{"Authorization":"Bearer "+token,"Content-Type":"application/json"},
   body:JSON.stringify({artifact,artifact_sha256:sha256,decision,notes}),
   credentials:"same-origin"
  });
  const result=await response.json();
  if(!response.ok)throw new Error(result.error||"package_review_failed");
  kdpReviewTokenInput.value="";
  statusResult.textContent="Revue "+artifact+" enregistrée : "+result.decision;
  statusButton.click();
 }catch(error){kdpPackageReviewList.insertAdjacentText("afterbegin","Revue impossible : "+String(error.message||error));}
}
function renderKdpMetadata(metadata,status,blockers){
 const fields={
  "kdp-title":metadata.title||"",
  "kdp-author":metadata.author||"",
  "kdp-description":metadata.description||"",
  "kdp-language":metadata.language||"fr",
  "kdp-keywords":Array.isArray(metadata.keywords)?metadata.keywords.join("\n"):"",
  "kdp-categories":Array.isArray(metadata.categories)?metadata.categories.join("\n"):"",
  "kdp-age-min":metadata.reading_age_min??"",
  "kdp-age-max":metadata.reading_age_max??"",
  "kdp-rights-holder":metadata.rights_holder||"",
  "kdp-rights-evidence":metadata.rights_evidence_ref||"",
  "kdp-territories":Array.isArray(metadata.territories)?metadata.territories.join(", "):(metadata.territories||""),
  "kdp-isbn-strategy":metadata.isbn_strategy||"",
  "kdp-isbn":metadata.isbn||"",
  "kdp-publisher":metadata.publisher||"",
  "kdp-marketplace":metadata.marketplace||"",
  "kdp-currency":metadata.currency||"",
  "kdp-price":metadata.list_price??"",
  "kdp-pricing-date":metadata.pricing_verified_at||""
 };
 Object.entries(fields).forEach(([id,value])=>{document.getElementById(id).value=String(value);});
 document.getElementById("kdp-rights-confirmed").checked=metadata.commercial_use_confirmed===true;
 document.getElementById("kdp-pricing-verified").checked=metadata.pricing_verified===true;
 metadataResult.replaceChildren();
 if(status){
  metadataResult.textContent="Fiche enregistrée : "+status;
  if(blockers&&blockers.length){
   const list=document.createElement("ul");
   blockers.forEach(item=>{const li=document.createElement("li");li.textContent=item;list.appendChild(li);});
   metadataResult.appendChild(list);
  }
 }else{metadataResult.textContent="Aucune fiche enregistrée.";}
}
function readKdpMetadataForm(){
 const lines=id=>document.getElementById(id).value.split(/\r?\n/).map(v=>v.trim()).filter(Boolean);
 const integer=id=>{const value=document.getElementById(id).value;return value===""?null:Number.parseInt(value,10);};
 const price=document.getElementById("kdp-price").value;
 const territories=document.getElementById("kdp-territories").value.trim();
 return {
  title:document.getElementById("kdp-title").value,
  author:document.getElementById("kdp-author").value,
  description:document.getElementById("kdp-description").value,
  language:document.getElementById("kdp-language").value.trim(),
  keywords:lines("kdp-keywords"),
  categories:lines("kdp-categories"),
  reading_age_min:integer("kdp-age-min"),
  reading_age_max:integer("kdp-age-max"),
  commercial_use_confirmed:document.getElementById("kdp-rights-confirmed").checked,
  rights_holder:document.getElementById("kdp-rights-holder").value,
  rights_evidence_ref:document.getElementById("kdp-rights-evidence").value,
  territories:territories.toLowerCase()==="worldwide"?"worldwide":territories.split(",").map(v=>v.trim()).filter(Boolean),
  isbn_strategy:document.getElementById("kdp-isbn-strategy").value,
  isbn:document.getElementById("kdp-isbn").value,
  publisher:document.getElementById("kdp-publisher").value,
  marketplace:document.getElementById("kdp-marketplace").value,
  currency:document.getElementById("kdp-currency").value.trim().toUpperCase(),
  list_price:price===""?null:Number(price),
  pricing_verified:document.getElementById("kdp-pricing-verified").checked,
  pricing_verified_at:document.getElementById("kdp-pricing-date").value
 };
}
metadataSaveButton.addEventListener("click",async()=>{
 const id=statusId.value.trim(),token=metadataTokenInput.value;
 if(!/^PKP-UP-[0-9a-f]{32}$/.test(id)){metadataResult.textContent="Vérifiez d'abord le statut pour sélectionner un manuscrit.";return;}
 if(!token){metadataResult.textContent="Saisissez le jeton distinct des métadonnées KDP.";return;}
 metadataSaveButton.disabled=true;metadataResult.textContent="Enregistrement du brouillon…";
 try{
  const response=await fetch("/api/papi-kids/manuscripts/"+encodeURIComponent(id)+"/kdp-metadata",{
   method:"POST",headers:{"Authorization":"Bearer "+token,"Content-Type":"application/json"},
   body:JSON.stringify({metadata:readKdpMetadataForm()}),credentials:"same-origin"
  });
  const result=await response.json();
  if(!response.ok)throw new Error(result.error||"metadata_save_failed");
  metadataTokenInput.value="";
  metadataResult.textContent="Version "+result.version+" — "+result.status+
   " — blocages : "+result.blocker_count;
  if(result.blockers&&result.blockers.length){
   const list=document.createElement("ul");
   result.blockers.forEach(item=>{const li=document.createElement("li");li.textContent=item;list.appendChild(li);});
   metadataResult.appendChild(list);
  }
 }catch(error){metadataResult.textContent="Fiche non enregistrée : "+String(error.message||error);}
 finally{metadataSaveButton.disabled=false;}
});
kdpBuildButton.addEventListener("click",async()=>{
 const id=statusId.value.trim(),token=kdpBuildTokenInput.value;
 if(!/^PKP-UP-[0-9a-f]{32}$/.test(id)){kdpBuildResult.textContent="Vérifiez d'abord le statut du manuscrit.";return;}
 if(!token){kdpBuildResult.textContent="Saisissez le jeton distinct de fabrication KDP.";return;}
 if(!window.confirm("Lancer la fabrication des PDF et, si configuré, de l'EPUB ? Aucune publication ne sera effectuée."))return;
 kdpBuildButton.disabled=true;kdpBuildResult.textContent="Fabrication en cours…";
 try{
  const response=await fetch("/api/papi-kids/manuscripts/"+encodeURIComponent(id)+"/build-kdp-package",{
   method:"POST",headers:{"Authorization":"Bearer "+token,"Content-Type":"application/json"},
   body:JSON.stringify({confirm:true}),credentials:"same-origin"
  });
  const result=await response.json();
  if(!response.ok)throw new Error(result.error||"kdp_build_failed");
  kdpBuildTokenInput.value="";
  kdpBuildResult.textContent="Package : "+result.status+
   " — inspection humaine encore requise — upload KDP désactivé.";
  statusButton.click();
 }catch(error){kdpBuildResult.textContent="Fabrication bloquée : "+String(error.message||error);}
 finally{kdpBuildButton.disabled=false;}
});
readinessButton.addEventListener("click",async()=>{
 const token=readinessTokenInput.value;
 if(!token){readinessResult.textContent="Saisissez le jeton distinct de diagnostic.";return;}
 readinessButton.disabled=true;readinessResult.textContent="Vérification en cours…";
 try{
  const response=await fetch("/api/papi-kids/readiness",{
   method:"GET",headers:{"Authorization":"Bearer "+token},credentials:"same-origin"
  });
  const result=await response.json();
  if(!response.ok)throw new Error(result.error||"readiness_failed");
  readinessTokenInput.value="";
  readinessResult.replaceChildren();
  const summary=document.createElement("p");
  summary.textContent="État : "+result.status+
   " — stockage/DB : "+(result.core_ready?"OK":"à corriger")+
   " — workflows propriétaire : "+(result.owner_workflows_ready?"OK":"à corriger")+
   " — génération image configurée : "+(result.image_generation_ready?"oui":"non");
  readinessResult.appendChild(summary);
  (result.blockers||[]).forEach(item=>{
   const line=document.createElement("p");line.textContent="Blocage : "+item;
   readinessResult.appendChild(line);
  });
  const missing=document.createElement("p");
  missing.textContent="Variables absentes : "+Object.values(result.checks||{})
   .flatMap(check=>Array.isArray(check.missing)?check.missing:[])
   .join(", ");
  readinessResult.appendChild(missing);
  const note=document.createElement("p");
  note.textContent="Aucun secret affiché ; aucun appel fournisseur effectué ; dépenses : 0.";
  readinessResult.appendChild(note);
 }catch(error){readinessResult.textContent="Diagnostic impossible : "+String(error.message||error);}
 finally{readinessButton.disabled=false;}
});
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
function renderSafetyReview(screening,review,uploadId){
 safetyReviewList.replaceChildren();
 if(!screening||!screening.manuscript_sha256){
  safetyReviewList.textContent="Analyse de sécurité indisponible ou manuscrit non structuré : revue éditoriale manuelle requise.";
  return;
 }
 const summary=document.createElement("p");
 summary.textContent="Pages analysées : "+screening.page_count+
  " — alertes : "+screening.issue_count+
  " (critiques : "+screening.critical_issue_count+", élevées : "+screening.high_issue_count+").";
 safetyReviewList.appendChild(summary);
 (screening.pages||[]).forEach(page=>{
  (page.issues||[]).forEach(issue=>{
   const card=document.createElement("div");card.className="safety-issue";
   const title=document.createElement("strong");
   title.textContent="Page "+page.page_number+" — "+issue.severity;
   const description=document.createElement("p");description.textContent=issue.description;
   const excerpt=document.createElement("p");excerpt.textContent="Extrait : "+issue.excerpt;
   card.append(title,description,excerpt);safetyReviewList.appendChild(card);
  });
 });
 if(review&&review.manuscript_sha256!==screening.manuscript_sha256){
  const stale=document.createElement("p");
  stale.textContent="La revue précédente est périmée : le manuscrit a changé.";
  safetyReviewList.appendChild(stale);
 }
 if(review&&review.manuscript_sha256===screening.manuscript_sha256){
  const state=document.createElement("p");
  state.textContent="Décision humaine : "+(review.approved?"APPROUVÉ":"REFUSÉ")+
   " — réviseur : "+(review.reviewer_id||"non renseigné")+
   " — date : "+(review.reviewed_at||"non renseignée");
  safetyReviewList.appendChild(state);
  if(review.approved)return;
 }
 const notes=document.createElement("textarea");
 notes.id="safety-review-notes";
 notes.maxLength=2000;
 notes.placeholder=screening.issue_count>0?
  "Expliquez la résolution des alertes (minimum 20 caractères pour approuver).":
  "Notes de revue (facultatif si aucune alerte).";
 safetyReviewList.appendChild(notes);
 const actions=document.createElement("div");actions.className="safety-actions";
 ["approved","rejected"].forEach(decision=>{
  const button=document.createElement("button");button.type="button";
  button.textContent=decision==="approved"?"Valider la sécurité":"Refuser / demander correction";
  button.addEventListener("click",()=>submitSafetyReview(
   uploadId,screening.manuscript_sha256,decision,notes.value,screening.issue_count
  ));
  actions.appendChild(button);
 });
 safetyReviewList.appendChild(actions);
}
async function submitSafetyReview(uploadId,manuscriptSha256,decision,notes,issueCount){
 const token=safetyReviewTokenInput.value;
 if(!token){statusResult.textContent="Saisissez le jeton distinct de revue sécurité.";return;}
 if(decision==="approved"&&issueCount>0&&notes.trim().length<20){
  statusResult.textContent="Ajoutez au moins 20 caractères de justification pour approuver les alertes.";
  return;
 }
 try{
  const response=await fetch("/api/papi-kids/manuscripts/"+
   encodeURIComponent(uploadId)+"/safety-review",{
   method:"POST",
   headers:{"Authorization":"Bearer "+token,"Content-Type":"application/json"},
   body:JSON.stringify({decision,manuscript_sha256:manuscriptSha256,notes}),
   credentials:"same-origin"
  });
  const result=await response.json();
  if(!response.ok)throw new Error(result.error||"safety_review_failed");
  statusResult.textContent="Revue sécurité enregistrée : "+(result.approved?"approuvée":"refusée")+
   " — "+result.evidence_ref;
  statusButton.click();
 }catch(error){statusResult.textContent="Revue sécurité non enregistrée : "+String(error.message||error);}
}
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
