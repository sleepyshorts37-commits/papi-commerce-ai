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
<p class="muted">Formats acceptés pour l'aperçu local : .md et .txt, maximum 2 Mo.</p>
<div class="notice">Aperçu local uniquement : ce tableau de bord ne téléverse pas encore le manuscrit vers le serveur et ne lance aucune génération.</div>
<pre id="preview" hidden></pre></section>
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
fileInput.addEventListener("change",()=>{
 const file=fileInput.files&&fileInput.files[0];
 preview.hidden=true;preview.textContent="";
 if(!file)return;
 if(!/\\.(md|txt)$/i.test(file.name)||file.size>2*1024*1024){
  preview.hidden=false;preview.textContent="Fichier refusé : choisissez un .md ou .txt de 2 Mo maximum.";return;
 }
 const reader=new FileReader();
 reader.onload=()=>{preview.textContent=String(reader.result||"").slice(0,12000);preview.hidden=false;};
 reader.onerror=()=>{preview.textContent="Lecture locale impossible.";preview.hidden=false;};
 reader.readAsText(file);
});
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
