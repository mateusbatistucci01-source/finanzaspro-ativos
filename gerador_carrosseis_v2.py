#!/usr/bin/env python3
"""
Gerador v2 de Carrosséis Instagram — FinanzasPro (@mateorivas_finanzas).

Evolução do gerador_carrosseis.py com o sistema de layouts desenhado no Paper
(arquivo "FINANZASPRO - Carrosseis Mateo Rivas", página "Lote FP-023 a FP-032 — 3 Temas"):

- 3 temas oficiais (estritamente sem verde):
    dark   -> #0A192F / #112240 / #3B82F6 / #FFFFFF
    light  -> #F8FAFC / #FFFFFF / #0A192F / #3B82F6   (Branco Clean)
    slate  -> #1E293B / #0F172A / #3B82F6 / #E2E8F0   (Alternativo Ardósia)
- Quantidade dinâmica de slides: 5 a 8 por carrossel (último slide sempre CTA).
- Layouts editoriais: cover (fullbleed | cutout | framed), statement, list, compare,
  steps, bar, proof, cta.
- Auto-ajuste tipográfico em JS (encolhe títulos se o conteúdo transbordar).
- Validação: 1080x1350 JPEG <= 8 MB, "Desliza →" em todos menos o último,
  palavra-chave válida no CTA, zero emojis verdes e auditoria de pixels verdes.

Uso:
    python gerador_carrosseis_v2.py --spec lotes/lote_carrosseis_fp023_fp032.json
    python gerador_carrosseis_v2.py --spec ... --only FP-024
"""

from __future__ import annotations

import argparse
import colorsys
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

from PIL import Image

import re
import gerador_carrosseis as v1
from gerador_carrosseis import esc


def render_accent_text(text: str) -> str:
    """Converte **texto** em accent e preserva tags seguras <b> e <span class="light-w...">."""
    raw = str(text)
    tokens: list[tuple[str, str]] = []

    def _stash(match: re.Match[str]) -> str:
        key = f"__RICH_{len(tokens)}__"
        tokens.append((key, match.group(0)))
        return key

    protected = re.sub(
        r"<br\s*/?>|</?b>|<span\s+class=\"light-w[^\"]*\"(?:\s+style=\"color:var\(--body\)\")?>|</span>",
        _stash,
        raw,
    )
    rendered = v1.render_accent_text(protected)
    for key, original in tokens:
        rendered = rendered.replace(key, original)
    return rendered

BASE_DIR = Path(__file__).resolve().parent
VISUAL_LIB_DIR = BASE_DIR / "assets" / "biblioteca_visual"
ATIVOS_DIR = BASE_DIR / "ativos"
DEFAULT_OUTPUT_DIR = BASE_DIR / "ativos_instagram"
SLIDE_W, SLIDE_H = 1080, 1350
MIN_SLIDES, MAX_SLIDES = 5, 8

ALLOWED_CTA_KEYWORDS = {
    "PLANILLA", "CONTROL", "SISTEMA", "METODO", "QUIERO",
    "FUGAS", "DEUDAS", "REGLA", "30DIAS", "FONDO", "DIAGNOSTICO",
}

VISUAL_ALIASES: dict[str, str] = {
    **v1.VISUAL_ALIASES,
    "mateo_11_clean": "11_mateo_cb1013b4_2K.jpg",          # sala branca, escrevendo no caderno
    "mateo_12_corredor": "12_mateo_fad31de3_2K.jpg",       # corredor urbano, blazer + celular
    "mateo_13_estudio": "13_mateo_c41c23ba_2K.jpg",        # estúdio escuro, close
    "mateo_14_laptop": "14_mateo_dcd1e704_2K.jpg",         # apontando, laptop, luz quente
    "mateo_15_recorte": "15_mateo_45aa9165_2K.jpg",        # fundo branco (recorte), apontando
    "cena_super": "16_Caixa_de_Supermercado_63bcd601_2K.jpg",
    "cena_balde": "18]__Metáfora_Visual_do__Balde_526a7cb9_2K.jpg",
    "cena_tren": "19_Jovem_Profissional_Pensativo_Olhando_pela_ef07015b_2K.jpg",
    "cena_bloques": "20_Painel_Arquitetônico_de_Blocos_Empilhados_7665c67c_2K.jpg",
}

PRINT_ALIASES: dict[str, str] = {
    "planilha_vision_geral": "demonstração planilha - vision geral.jpeg",
    "planilha_presupuesto": "demonstração planilha - presupuesto.jpeg",
    "planilha_ingresos": "demonstração planilha - ingresos.jpeg",
    "planilha_resumen_anual": "demonstração planilha - resumen anual.jpeg",
}

PRINT_TITLES = {
    "planilha_vision_geral": "FinanzasPro · Visión General",
    "planilha_presupuesto": "FinanzasPro · Presupuesto",
    "planilha_ingresos": "FinanzasPro · Ingresos",
    "planilha_resumen_anual": "FinanzasPro · Resumen Anual",
}

THEMES: dict[str, dict[str, str]] = {
    "dark": {
        "bg": "#0A192F", "surface": "#112240", "accent": "#3B82F6", "accent_text": "#3B82F6",
        "ink": "#FFFFFF", "body": "#E2E8F0", "muted": "rgba(226,232,240,0.70)",
        "line": "rgba(226,232,240,0.16)", "track": "rgba(226,232,240,0.20)",
        "ov": "10,25,47", "pill_bg": "#3B82F6", "pill_fg": "#FFFFFF", "pill_border": "#3B82F6",
        "seg1": "#1D4ED8", "seg2": "#3B82F6", "seg3": "#60A5FA", "seg4": "#BFDBFE",
        "dim": "#94A3B8", "frame": "rgba(59,130,246,0.40)",
    },
    "light": {
        "bg": "#F8FAFC", "surface": "#FFFFFF", "accent": "#3B82F6", "accent_text": "#2563EB",
        "ink": "#0A192F", "body": "#334155", "muted": "#475569",
        "line": "#E2E8F0", "track": "#E2E8F0",
        "ov": "248,250,252", "pill_bg": "#0A192F", "pill_fg": "#FFFFFF", "pill_border": "#0A192F",
        "seg1": "#0A192F", "seg2": "#1D4ED8", "seg3": "#3B82F6", "seg4": "#93C5FD",
        "dim": "#94A3B8", "frame": "#E2E8F0",
    },
    "slate": {
        "bg": "#1E293B", "surface": "#0F172A", "accent": "#3B82F6", "accent_text": "#3B82F6",
        "ink": "#FFFFFF", "body": "#E2E8F0", "muted": "#94A3B8",
        "line": "rgba(226,232,240,0.16)", "track": "rgba(226,232,240,0.20)",
        "ov": "30,41,59", "pill_bg": "#0F172A", "pill_fg": "#FFFFFF", "pill_border": "#3B82F6",
        "seg1": "#1D4ED8", "seg2": "#3B82F6", "seg3": "#60A5FA", "seg4": "#94A3B8",
        "dim": "#94A3B8", "frame": "rgba(226,232,240,0.18)",
    },
}


# --------------------------------------------------------------------------------------
# Imagens
# --------------------------------------------------------------------------------------
def resolve_image(ref: str) -> Path:
    if ref in PRINT_ALIASES:
        p = ATIVOS_DIR / PRINT_ALIASES[ref]
    elif ref in VISUAL_ALIASES:
        p = VISUAL_LIB_DIR / VISUAL_ALIASES[ref]
    else:
        p = VISUAL_LIB_DIR / ref
        if not p.exists():
            p = BASE_DIR / ref
    if not p.exists():
        raise FileNotFoundError(f"Imagem não encontrada: {ref} -> {p}")
    return p


class ImageCache:
    def __init__(self) -> None:
        self._cache: dict[str, str] = {}

    def uri(self, ref: str) -> str:
        if ref not in self._cache:
            self._cache[ref] = v1.image_to_data_uri(resolve_image(ref), max_dim=1700)
        return self._cache[ref]


# --------------------------------------------------------------------------------------
# CSS
# --------------------------------------------------------------------------------------
def theme_css(theme: dict[str, str]) -> str:
    vars_css = "\n".join(f"  --{k.replace('_', '-')}: {v};" for k, v in theme.items())
    return f":root {{\n{vars_css}\n}}\n" + BASE_CSS


BASE_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
* { box-sizing: border-box; margin: 0; padding: 0; }
html, body { width: 1080px; height: 1350px; overflow: hidden; background: var(--bg); }
body { font-family: 'Inter', 'Segoe UI', system-ui, sans-serif; color: var(--ink);
       -webkit-font-smoothing: antialiased; font-feature-settings: 'tnum' 1, 'ss01' 1; }
.slide { position: relative; width: 1080px; height: 1350px; overflow: hidden; background: var(--bg);
         display: flex; flex-direction: column; }
.layer { position: relative; z-index: 3; }
.abs-fill { position: absolute; inset: 0; }
.photo { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; z-index: 0; }
.flip { transform: scaleX(-1); }

/* Header */
.header { display: flex; justify-content: space-between; align-items: center; padding: 56px 68px 0 68px; }
.handle-wrap { display: flex; align-items: center; gap: 12px; }
.dot { width: 14px; height: 14px; border-radius: 50%; background: var(--accent); flex-shrink: 0; }
.handle { font-size: 25px; font-weight: 700; color: var(--ink); letter-spacing: -0.005em; }
.badge { font-size: 19px; font-weight: 600; letter-spacing: 0.12em; color: var(--muted);
         text-transform: uppercase; white-space: nowrap; }
.on-photo .handle { color: #FFFFFF; }
.on-photo .badge { color: #E2E8F0; }

/* Body */
.body { flex: 1; min-height: 0; display: flex; flex-direction: column; padding: 0 68px; overflow: hidden; }
.body.center { justify-content: center; }
.body.bottom { justify-content: flex-end; padding-bottom: 28px; }
.body.top { justify-content: flex-start; padding-top: 72px; }
.kicker { font-size: 21px; font-weight: 700; letter-spacing: 0.16em; color: var(--accent-text);
          text-transform: uppercase; margin-bottom: 22px; }
.h1 { font-size: 96px; font-weight: 900; line-height: 1.0; letter-spacing: -0.04em; color: var(--ink); }
.h2 { font-size: 72px; font-weight: 900; line-height: 1.04; letter-spacing: -0.035em; color: var(--ink); }
.h3 { font-size: 58px; font-weight: 900; line-height: 1.07; letter-spacing: -0.03em; color: var(--ink); }
.accent { color: var(--accent); }
.light-w { font-weight: 300; }
.sub { margin-top: 26px; font-size: 30px; font-weight: 500; line-height: 1.4; color: var(--body); max-width: 880px; }
.small { font-size: 22px; font-weight: 500; line-height: 1.4; color: var(--muted); }
.rule { width: 72px; height: 6px; background: var(--accent); margin-bottom: 22px; }
.nowrap { white-space: nowrap; }

/* Cover */
.cover-ov { position: absolute; inset: 0; z-index: 1; }
.stat { display: flex; flex-direction: column; gap: 6px; }
.stat-num { font-size: 150px; font-weight: 900; line-height: 1; letter-spacing: -0.05em; color: var(--ink);
            white-space: nowrap; }
.stat-label { font-size: 22px; font-weight: 700; letter-spacing: 0.14em; color: var(--accent-text); text-transform: uppercase; }
.chip { display: inline-flex; align-self: flex-start; align-items: center; gap: 10px; margin-top: 30px;
        padding: 14px 24px; border-radius: 14px; font-size: 23px; font-weight: 600;
        background: rgba(var(--ov),0.82); border: 1px solid var(--frame); color: var(--body); }
.chip b { color: var(--ink); }
.framed { position: relative; border-radius: 28px; overflow: hidden; flex-shrink: 0; }
.framed img { width: 100%; height: 100%; object-fit: cover; display: block; }

/* Statement */
.mega { font-size: 210px; font-weight: 900; line-height: 0.92; letter-spacing: -0.055em; color: var(--accent);
        white-space: nowrap; }
.mega-label { margin-top: 14px; font-size: 22px; font-weight: 700; letter-spacing: 0.14em; color: var(--muted);
              text-transform: uppercase; }
.side-wrap { display: flex; gap: 48px; align-items: stretch; flex: 1; min-height: 0; }
.side-text { flex: 1; display: flex; flex-direction: column; justify-content: center; }
.side-photo { width: 400px; border-radius: 28px; overflow: hidden; flex-shrink: 0; }
.side-photo img { width: 100%; height: 100%; object-fit: cover; display: block; }

/* List */
.rows { display: flex; flex-direction: column; margin-top: 44px; }
.row { display: flex; align-items: baseline; gap: 34px; padding: 26px 0; border-top: 1px solid var(--line); }
.row:last-child { border-bottom: 1px solid var(--line); }
.row-big { font-weight: 900; letter-spacing: -0.04em; line-height: 1; color: var(--accent);
           flex-shrink: 0; white-space: nowrap; }
.row-big.ink { color: var(--ink); }
.row-big.dim { color: var(--dim); }
.row-title { font-size: 31px; font-weight: 800; line-height: 1.2; color: var(--ink); letter-spacing: -0.01em; }
.row-desc { margin-top: 8px; font-size: 23px; font-weight: 400; line-height: 1.42; color: var(--body); }
.takeaway { margin-top: 34px; padding-left: 26px; border-left: 6px solid var(--accent);
            font-size: 28px; font-weight: 700; line-height: 1.38; color: var(--ink); }

/* Compare */
.cmp { display: flex; margin-top: 46px; border-top: 1px solid var(--line); border-bottom: 1px solid var(--line); }
.cmp-col { flex: 1; padding: 34px 0; display: flex; flex-direction: column; }
.cmp-col + .cmp-col { border-left: 1px solid var(--line); padding-left: 44px; }
.cmp-col:first-child { padding-right: 44px; }
.cmp-label { font-size: 20px; font-weight: 800; letter-spacing: 0.14em; text-transform: uppercase; color: var(--muted); }
.cmp-col.is-win .cmp-label { color: var(--accent-text); }
.cmp-result { margin-top: 14px; font-size: 76px; font-weight: 900; letter-spacing: -0.045em; line-height: 1;
              color: var(--dim); white-space: nowrap; }
.cmp-col.is-win .cmp-result { color: var(--accent); }
.cmp-rlabel { margin-top: 10px; font-size: 21px; font-weight: 500; color: var(--muted); }
.cmp-rows { margin-top: 30px; display: flex; flex-direction: column; gap: 18px; }
.cmp-row { display: flex; flex-direction: column; gap: 4px; }
.cmp-row span:first-child { font-size: 19px; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase; color: var(--muted); }
.cmp-row span:last-child { font-size: 27px; font-weight: 700; color: var(--ink); line-height: 1.25; }
.foot { margin-top: 26px; font-size: 21px; color: var(--muted); line-height: 1.4; }

/* Steps */
.steps { display: flex; flex-direction: column; margin-top: 46px; }
.step { display: flex; gap: 30px; }
.step-tag { width: 170px; flex-shrink: 0; padding-top: 6px; font-size: 21px; font-weight: 800; letter-spacing: 0.08em;
            color: var(--accent-text); text-transform: uppercase; white-space: nowrap; }
.step-rail { width: 22px; flex-shrink: 0; display: flex; flex-direction: column; align-items: center; }
.step-dot { width: 22px; height: 22px; border-radius: 50%; border: 5px solid var(--accent); background: var(--bg); margin-top: 6px; }
.step-line { flex: 1; width: 3px; background: var(--line); margin-top: 6px; }
.step:last-child .step-line { display: none; }
.step-body { flex: 1; padding-bottom: 38px; }
.step-title { font-size: 32px; font-weight: 800; color: var(--ink); line-height: 1.2; letter-spacing: -0.01em; }
.step-desc { margin-top: 8px; font-size: 23px; line-height: 1.42; color: var(--body); }

/* Bar */
.bar-meta { margin-top: 46px; display: flex; justify-content: space-between; align-items: baseline; }
.bar-meta span:first-child { font-size: 21px; font-weight: 700; letter-spacing: 0.12em; color: var(--muted); text-transform: uppercase; }
.bar-meta span:last-child { font-size: 44px; font-weight: 900; color: var(--ink); letter-spacing: -0.03em; white-space: nowrap; }
.bar { margin-top: 18px; display: flex; gap: 6px; height: 104px; }
.seg { border-radius: 14px; display: flex; align-items: center; justify-content: center; font-size: 26px;
       font-weight: 800; color: #FFFFFF; white-space: nowrap; overflow: hidden; }
.seg-1 { background: var(--seg1); } .seg-2 { background: var(--seg2); }
.seg-3 { background: var(--seg3); color: #0A192F; } .seg-4 { background: var(--seg4); color: #0A192F; }
.legend { margin-top: 30px; display: flex; flex-direction: column; }
.lg-row { display: flex; align-items: center; gap: 22px; padding: 20px 0; border-top: 1px solid var(--line); }
.lg-sw { width: 26px; height: 26px; border-radius: 7px; flex-shrink: 0; }
.lg-text { flex: 1; }
.lg-title { font-size: 28px; font-weight: 800; color: var(--ink); }
.lg-desc { margin-top: 4px; font-size: 21px; color: var(--body); line-height: 1.35; }
.lg-val { font-size: 38px; font-weight: 900; letter-spacing: -0.03em; color: var(--ink); white-space: nowrap; flex-shrink: 0; }

/* Proof */
.win { margin-top: 40px; border-radius: 22px; overflow: hidden; border: 1.5px solid var(--frame);
       background: #0A192F; box-shadow: 0 30px 70px rgba(10,25,47,0.28); flex-shrink: 0; }
.win-bar { display: flex; justify-content: space-between; align-items: center; padding: 16px 22px; background: #112240; }
.win-dots { display: flex; gap: 9px; }
.win-dots i { width: 13px; height: 13px; border-radius: 50%; background: rgba(59,130,246,0.45); display: block; }
.win-dots i:last-child { background: #3B82F6; }
.win-title { font-size: 19px; font-weight: 600; color: #E2E8F0; }
.win-tag { font-size: 16px; font-weight: 800; letter-spacing: 0.1em; color: #3B82F6; }
.win img { display: block; width: 100%; }
.callouts { margin-top: 34px; display: flex; gap: 30px; }
.callout { flex: 1; border-top: 4px solid var(--accent); padding-top: 18px; }
.callout-t { font-size: 20px; font-weight: 800; letter-spacing: 0.08em; text-transform: uppercase; color: var(--accent-text); }
.callout-d { margin-top: 8px; font-size: 22px; line-height: 1.4; color: var(--body); }

/* CTA */
.kw-box { margin-top: 36px; display: flex; align-items: center; gap: 30px; }
.kw { padding: 26px 46px; border-radius: 24px; background: var(--accent); color: #FFFFFF; font-size: 76px;
      font-weight: 900; letter-spacing: 0.04em; white-space: nowrap; box-shadow: 0 18px 50px rgba(59,130,246,0.38); }
.kw-hint { font-size: 25px; font-weight: 600; line-height: 1.35; color: var(--body); }
.gets { margin-top: 40px; display: flex; flex-direction: column; }
.gets-title { font-size: 20px; font-weight: 800; letter-spacing: 0.14em; text-transform: uppercase; color: var(--muted); margin-bottom: 8px; }
.get { display: flex; gap: 20px; align-items: baseline; padding: 18px 0; border-top: 1px solid var(--line); }
.get-arrow { color: var(--accent); font-size: 28px; font-weight: 900; flex-shrink: 0; width: 30px; }
.get-text { font-size: 27px; line-height: 1.38; color: var(--ink); font-weight: 500; }
.get-text b { font-weight: 800; }

/* Hook + footer */
.hook { padding: 0 68px 22px 68px; font-size: 24px; font-weight: 700; color: var(--accent-text); }
.on-photo-hook { color: #FFFFFF; }
.footer { display: flex; justify-content: space-between; align-items: center; padding: 0 68px 56px 68px; }
.prog { display: flex; align-items: center; gap: 14px; }
.track { width: 300px; height: 6px; border-radius: 6px; background: var(--track); overflow: hidden; }
.fill { height: 6px; border-radius: 6px; background: var(--accent); }
.count { font-size: 19px; font-weight: 700; color: var(--muted); }
.on-photo .count { color: #E2E8F0; }
.pill { padding: 15px 28px; border-radius: 999px; background: var(--pill-bg); border: 1.5px solid var(--pill-border);
        color: var(--pill-fg); font-size: 22px; font-weight: 800; white-space: nowrap; }
"""

FIT_JS = """
<script>
(function(){
  function fit(){
    var bodies = document.querySelectorAll('.body');
    bodies.forEach(function(b){
      var guard = 0;
      while (b.scrollHeight > b.clientHeight + 1 && guard < 30) {
        var els = b.querySelectorAll('.shrink');
        if (!els.length) break;
        els.forEach(function(e){
          var fs = parseFloat(getComputedStyle(e).fontSize);
          e.style.fontSize = (fs * 0.95) + 'px';
        });
        guard++;
      }
      if (b.scrollHeight > b.clientHeight + 1) { document.body.setAttribute('data-overflow', '1'); }
    });
  }
  if (document.fonts && document.fonts.ready) { document.fonts.ready.then(fit); } else { fit(); }
  window.addEventListener('load', fit);
})();
</script>
"""


# --------------------------------------------------------------------------------------
# Peças
# --------------------------------------------------------------------------------------
def header(badge: str, idx: int, total: int, on_photo: bool = False) -> str:
    cls = "header layer on-photo" if on_photo else "header layer"
    return (
        f'<div class="{cls}"><div class="handle-wrap"><span class="dot"></span>'
        f'<span class="handle">@mateorivas_finanzas</span></div>'
        f'<span class="badge">{esc(badge)} · {idx:02d}/{total:02d}</span></div>'
    )


def footer(idx: int, total: int, keyword: str | None, on_photo: bool = False) -> str:
    pct = round(idx / total * 100, 2)
    right = (
        '<div class="pill">Desliza →</div>'
        if idx < total
        else f'<div class="pill">Comenta {esc(keyword or "")} 👇</div>'
    )
    cls = "footer layer on-photo" if on_photo else "footer layer"
    return (
        f'<div class="{cls}"><div class="prog"><div class="track"><div class="fill" style="width:{pct}%"></div></div>'
        f'<span class="count">{idx:02d}/{total:02d}</span></div>{right}</div>'
    )


def hook_html(slide: dict[str, Any], on_photo: bool = False) -> str:
    if not slide.get("hook"):
        return ""
    cls = "hook layer on-photo-hook" if on_photo else "hook layer"
    return f'<div class="{cls}">{render_accent_text(slide["hook"])}</div>'


def kicker(slide: dict[str, Any]) -> str:
    return f'<div class="kicker">{esc(slide["kicker"])}</div>' if slide.get("kicker") else ""


def headline(slide: dict[str, Any], cls: str = "h2", style: str = "") -> str:
    size = slide.get("headline_size")
    st = f"font-size:{size}px;" if size else ""
    st += style
    return f'<h1 class="{cls} shrink" style="{st}">{render_accent_text(slide["headline"])}</h1>'


def sub(slide: dict[str, Any], key: str = "subtitle") -> str:
    return f'<p class="sub shrink">{render_accent_text(slide[key])}</p>' if slide.get(key) else ""


# --------------------------------------------------------------------------------------
# Layouts
# --------------------------------------------------------------------------------------
def layout_cover(s: dict[str, Any], theme_name: str, img: ImageCache) -> tuple[str, bool]:
    style = s.get("style", "fullbleed")
    flip = " flip" if s.get("flip") else ""
    pos = s.get("object_position", "center 20%")
    if style == "fullbleed":
        if theme_name == "light":
            ov = ("linear-gradient(180deg, rgba(248,250,252,0.78) 0%, rgba(248,250,252,0.0) 14%, "
                  "rgba(248,250,252,0.0) 50%, rgba(248,250,252,0.92) 66%, #F8FAFC 78%)")
            on_photo = False
        else:
            ov = ("linear-gradient(180deg, rgba(var(--ov),0.62) 0%, rgba(var(--ov),0.05) 20%, "
                  "rgba(var(--ov),0.18) 40%, rgba(var(--ov),0.90) 63%, rgb(var(--ov)) 82%)")
            on_photo = True
        stat = ""
        if s.get("chip"):
            stat = f'<div class="chip">{render_accent_text(s["chip"])}</div>'
        inner = (
            f'<img class="photo{flip}" src="{img.uri(s["image"])}" style="object-position:{pos}" />'
            f'<div class="cover-ov" style="background:{ov}"></div>'
            f'__HEADER__'
            f'<div class="body bottom layer">{kicker(s)}{headline(s, "h1")}{sub(s)}{stat}</div>'
        )
        return inner, on_photo

    if style == "cutout":
        w = s.get("photo_width", 640)
        h = round(w * 2400 / 1792)
        right = s.get("photo_right", -40)
        stat_html = ""
        if s.get("stat"):
            stat_html = (
                f'<div class="stat" style="position:absolute; left:68px; top:{s.get("stat_top", 640)}px; z-index:3;">'
                f'<span class="stat-num">{esc(s["stat"])}</span>'
                f'<span class="stat-label">{esc(s.get("stat_label", ""))}</span></div>'
            )
        sub_html = ""
        if s.get("subtitle"):
            sub_html = (
                f'<div style="position:absolute; left:68px; bottom:150px; width:{1080 - w - 60}px; z-index:3;">'
                f'<div class="rule"></div><p style="font-size:30px; font-weight:500; line-height:1.4; color:var(--ink)">'
                f'{render_accent_text(s["subtitle"])}</p>'
                + (f'<p class="small" style="margin-top:14px">{esc(s["note"])}</p>' if s.get("note") else "")
                + "</div>"
            )
        inner = (
            f'<img class="{flip.strip()}" src="{img.uri(s["image"])}" '
            f'style="position:absolute; right:{right}px; bottom:0; width:{w}px; height:{h}px; object-fit:cover; '
            f'object-position:center top; z-index:0;" />'
            f'<div style="position:absolute; right:{w + right - 120}px; bottom:0; width:130px; height:{h}px; z-index:1; '
            f'background:linear-gradient(90deg, var(--bg) 0%, rgba(var(--ov),0) 100%);"></div>'
            f'<div style="position:absolute; right:0; top:{1350 - h - 2}px; width:{w + 40}px; height:140px; z-index:1; '
            f'background:linear-gradient(180deg, var(--bg) 0%, rgba(var(--ov),0) 100%);"></div>'
            f'__HEADER__'
            f'<div class="layer" style="padding:64px 68px 0 68px;">{kicker(s)}'
            f'{headline(s, "h1", "max-width:900px;")}</div>'
            f'{stat_html}{sub_html}<div style="flex:1"></div>'
        )
        return inner, False

    # framed
    ph = s.get("photo_height", 640)
    inner = (
        f'__HEADER__'
        f'<div class="body top layer" style="padding-top:40px;">'
        f'<div class="framed" style="height:{ph}px; margin-bottom:46px;">'
        f'<img class="{flip.strip()}" src="{img.uri(s["image"])}" style="object-position:{pos}" /></div>'
        f'{kicker(s)}{headline(s, "h2")}{sub(s)}</div>'
    )
    return inner, False


def layout_statement(s: dict[str, Any], theme_name: str, img: ImageCache) -> tuple[str, bool]:
    mega = ""
    if s.get("mega"):
        mega = (
            f'<div class="mega shrink" style="{f"font-size:{s["mega_size"]}px" if s.get("mega_size") else ""}">'
            f'{esc(s["mega"])}</div>'
            + (f'<div class="mega-label">{esc(s["mega_label"])}</div>' if s.get("mega_label") else "")
            + '<div style="height:48px"></div>'
        )
    text = f'{kicker(s)}{mega}{headline(s, "h2")}{sub(s, "body")}'
    if s.get("takeaway"):
        text += f'<div class="takeaway shrink">{render_accent_text(s["takeaway"])}</div>'
    placement = s.get("image_placement", "side" if s.get("image") else None)
    if s.get("image") and placement == "side":
        pos = s.get("object_position", "center center")
        body = (
            f'<div class="body layer" style="padding-top:56px; padding-bottom:30px;"><div class="side-wrap">'
            f'<div class="side-text">{text}</div>'
            f'<div class="side-photo"><img src="{img.uri(s["image"])}" style="object-position:{pos}" /></div>'
            f'</div></div>'
        )
    elif s.get("image") and placement == "top":
        pos = s.get("object_position", "center center")
        body = (
            f'<div class="body top layer" style="padding-top:40px;">'
            f'<div class="framed" style="height:{s.get("photo_height", 480)}px; margin-bottom:44px;">'
            f'<img src="{img.uri(s["image"])}" style="object-position:{pos}" /></div>{text}</div>'
        )
    else:
        body = f'<div class="body center layer">{text}</div>'
    return "__HEADER__" + body, False


def layout_list(s: dict[str, Any], theme_name: str, img: ImageCache) -> tuple[str, bool]:
    items = s["items"]
    longest = max(len(str(it.get("big", ""))) for it in items)
    big_size = s.get("big_size") or (96 if longest <= 3 else 80 if longest <= 4 else 64 if longest <= 6 else 54)
    big_w = s.get("big_width") or round(big_size * 0.62 * longest + 20)
    tones = s.get("tones") or []
    rows = []
    for i, it in enumerate(items):
        tone = tones[i] if i < len(tones) else ("" if i == 0 else "ink")
        big = (
            f'<span class="row-big {tone} shrink" style="font-size:{big_size}px; width:{big_w}px">{esc(it["big"])}</span>'
            if it.get("big") is not None
            else ""
        )
        desc = f'<div class="row-desc shrink">{render_accent_text(it["desc"])}</div>' if it.get("desc") else ""
        rows.append(
            f'<div class="row">{big}<div><div class="row-title shrink">{render_accent_text(it["title"])}</div>{desc}</div></div>'
        )
    take = f'<div class="takeaway shrink">{render_accent_text(s["takeaway"])}</div>' if s.get("takeaway") else ""
    align = s.get("align", "top")
    body = (
        f'<div class="body {align} layer" style="padding-top:{64 if align == "top" else 0}px;">'
        f'{kicker(s)}{headline(s, s.get("headline_class", "h2"))}{sub(s)}<div class="rows">{"".join(rows)}</div>{take}</div>'
    )
    return "__HEADER__" + body, False


def layout_compare(s: dict[str, Any], theme_name: str, img: ImageCache) -> tuple[str, bool]:
    def col(c: dict[str, Any], win: bool) -> str:
        rows = "".join(
            f'<div class="cmp-row"><span>{esc(r["label"])}</span><span>{esc(r["value"])}</span></div>'
            for r in c.get("rows", [])
        )
        return (
            f'<div class="cmp-col{" is-win" if win else ""}"><div class="cmp-label">{esc(c["label"])}</div>'
            f'<div class="cmp-result shrink">{esc(c["result"])}</div>'
            f'<div class="cmp-rlabel">{esc(c.get("result_label", ""))}</div>'
            f'<div class="cmp-rows">{rows}</div></div>'
        )

    foot = f'<p class="foot">{render_accent_text(s["footnote"])}</p>' if s.get("footnote") else ""
    take = f'<div class="takeaway shrink">{render_accent_text(s["takeaway"])}</div>' if s.get("takeaway") else ""
    body = (
        f'<div class="body center layer">{kicker(s)}{headline(s, "h2")}'
        f'<div class="cmp">{col(s["left"], False)}{col(s["right"], True)}</div>{take}{foot}</div>'
    )
    return "__HEADER__" + body, False


def layout_steps(s: dict[str, Any], theme_name: str, img: ImageCache) -> tuple[str, bool]:
    steps = "".join(
        f'<div class="step"><div class="step-tag">{esc(st["tag"])}</div>'
        f'<div class="step-rail"><div class="step-dot"></div><div class="step-line"></div></div>'
        f'<div class="step-body"><div class="step-title shrink">{render_accent_text(st["title"])}</div>'
        f'<div class="step-desc shrink">{render_accent_text(st["desc"])}</div></div></div>'
        for st in s["steps"]
    )
    take = f'<div class="takeaway shrink">{render_accent_text(s["takeaway"])}</div>' if s.get("takeaway") else ""
    body = f'<div class="body center layer">{kicker(s)}{headline(s, "h2")}{sub(s)}<div class="steps">{steps}</div>{take}</div>'
    return "__HEADER__" + body, False


def layout_bar(s: dict[str, Any], theme_name: str, img: ImageCache) -> tuple[str, bool]:
    segs = s["segments"]
    bar = "".join(
        f'<div class="seg seg-{(i % 4) + 1}" style="flex:{sg["weight"]}">{esc(sg.get("short", ""))}</div>'
        for i, sg in enumerate(segs)
    )
    theme = THEMES[theme_name]
    colors = [theme["seg1"], theme["seg2"], theme["seg3"], theme["seg4"]]
    legend = "".join(
        f'<div class="lg-row"><div class="lg-sw" style="background:{colors[i % 4]}"></div>'
        f'<div class="lg-text"><div class="lg-title shrink">{esc(sg["label"])}</div>'
        + (f'<div class="lg-desc shrink">{esc(sg["desc"])}</div>' if sg.get("desc") else "")
        + f'</div><div class="lg-val">{esc(sg["value"])}</div></div>'
        for i, sg in enumerate(segs)
    )
    meta = (
        f'<div class="bar-meta"><span>{esc(s.get("total_label", ""))}</span><span>{esc(s.get("total_value", ""))}</span></div>'
        if s.get("total_value")
        else ""
    )
    foot = f'<p class="foot">{render_accent_text(s["footnote"])}</p>' if s.get("footnote") else ""
    body = (
        f'<div class="body center layer">{kicker(s)}{headline(s, "h2")}{meta}<div class="bar">{bar}</div>'
        f'<div class="legend">{legend}</div>{foot}</div>'
    )
    return "__HEADER__" + body, False


def layout_proof(s: dict[str, Any], theme_name: str, img: ImageCache) -> tuple[str, bool]:
    ref = s.get("image", "planilha_vision_geral")
    callouts = "".join(
        f'<div class="callout"><div class="callout-t">{esc(c["title"])}</div><div class="callout-d shrink">{esc(c["desc"])}</div></div>'
        for c in s["callouts"]
    )
    title = s.get("window_title", PRINT_TITLES.get(ref, "FinanzasPro · Google Sheets"))
    body = (
        f'<div class="body center layer">{kicker(s)}{headline(s, "h3")}'
        f'<div class="win"><div class="win-bar"><div class="win-dots"><i></i><i></i><i></i></div>'
        f'<div class="win-title">{esc(title)}</div><div class="win-tag">COPIA PRIVADA</div></div>'
        f'<img src="{img.uri(ref)}" /></div><div class="callouts">{callouts}</div></div>'
    )
    return "__HEADER__" + body, False


def layout_cta(s: dict[str, Any], theme_name: str, img: ImageCache, keyword: str) -> tuple[str, bool]:
    gets = "".join(
        f'<div class="get"><span class="get-arrow">→</span><span class="get-text shrink">{render_accent_text(g)}</span></div>'
        for g in s["gets"]
    )
    gets_html = f'<div class="gets"><div class="gets-title">{esc(s.get("gets_title", "Lo que recibes por mensaje privado"))}</div>{gets}</div>'
    kw_html = (
        f'<div class="kw-box"><div class="kw">{esc(keyword)}</div>'
        f'<div class="kw-hint shrink">{render_accent_text(s.get("kw_hint", "Coméntalo aquí abajo y te escribo por DM."))}</div></div>'
    )
    note = f'<p class="foot">{render_accent_text(s["note"])}</p>' if s.get("note") else ""
    photo = ""
    if s.get("image"):
        pos = s.get("object_position", "center 25%")
        flip = " flip" if s.get("flip") else ""
        photo = (
            f'<div class="framed" style="height:{s.get("photo_height", 360)}px; margin-bottom:40px;">'
            f'<img class="{flip.strip()}" src="{img.uri(s["image"])}" style="object-position:{pos}" /></div>'
        )
    body = (
        f'<div class="body center layer">{photo}{kicker(s)}{headline(s, "h2")}{kw_html}{gets_html}{note}</div>'
    )
    return "__HEADER__" + body, False


LAYOUTS = {
    "cover": layout_cover,
    "statement": layout_statement,
    "list": layout_list,
    "compare": layout_compare,
    "steps": layout_steps,
    "bar": layout_bar,
    "proof": layout_proof,
}


def build_slide_html(spec: dict[str, Any], s: dict[str, Any], idx: int, total: int, img: ImageCache) -> str:
    theme_name = s.get("theme", spec["theme"])
    theme = THEMES[theme_name]
    keyword = spec["cta_keyword"]
    stype = s["type"]
    if stype == "cta":
        inner, on_photo = layout_cta(s, theme_name, img, keyword)
    else:
        inner, on_photo = LAYOUTS[stype](s, theme_name, img)
    badge = s.get("badge", spec.get("badge", "FINANZASPRO"))
    inner = inner.replace("__HEADER__", header(badge, idx, total, on_photo), 1)
    html_doc = f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8" /><meta name="viewport" content="width=1080" />
<style>{theme_css(theme)}</style></head>
<body><div class="slide">{inner}{hook_html(s, on_photo)}{footer(idx, total, keyword, on_photo)}</div>{FIT_JS}</body></html>"""
    return html_doc


# --------------------------------------------------------------------------------------
# Validação
# --------------------------------------------------------------------------------------
def green_ratio(jpg: Path) -> float:
    """Fração de pixels com matiz verde saturado (75°-165°, S>0.35, V>0.25)."""
    with Image.open(jpg) as im:
        small = im.convert("RGB").resize((270, 338))
        px = list(small.getdata())
    hits = 0
    for r, g, b in px:
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        if 75 / 360 <= h <= 165 / 360 and s > 0.35 and v > 0.25:
            hits += 1
    return hits / len(px)


def validate_spec(spec: dict[str, Any]) -> None:
    cid = spec.get("id", "?")
    slides = spec.get("slides", [])
    if not (MIN_SLIDES <= len(slides) <= MAX_SLIDES):
        raise ValueError(f"{cid}: carrossel deve ter entre {MIN_SLIDES} e {MAX_SLIDES} slides (recebido {len(slides)}).")
    if slides[-1]["type"] != "cta":
        raise ValueError(f"{cid}: último slide deve ser 'cta'.")
    if spec["theme"] not in THEMES:
        raise ValueError(f"{cid}: tema inválido {spec['theme']}")
    kw = spec["cta_keyword"].upper()
    if kw not in ALLOWED_CTA_KEYWORDS:
        raise ValueError(f"{cid}: palavra-chave inválida {kw}")
    if kw not in spec.get("copy", ""):
        raise ValueError(f"{cid}: legenda não contém a palavra-chave {kw}")
    v1.validate_no_green_text(spec, cid)


def render_carousel(spec: dict[str, Any], output_root: Path, img: ImageCache, keep_html: Path | None = None) -> list[Path]:
    validate_spec(spec)
    slides = spec["slides"]
    total = len(slides)
    out_dir = output_root / spec["folder"]
    if out_dir.exists():
        for old in out_dir.glob("slide_*.jpg"):
            old.unlink()
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix=f"fp2_{spec['folder']}_"))
    html_paths, png_paths, jpg_paths = [], [], []
    try:
        for i, s in enumerate(slides, start=1):
            doc = build_slide_html(spec, s, i, total, img)
            if i < total and "Desliza →" not in doc:
                raise RuntimeError(f"{spec['id']} slide {i}: falta 'Desliza →'")
            if i == total and ("Desliza →" in doc or spec["cta_keyword"] not in doc):
                raise RuntimeError(f"{spec['id']} slide final inválido")
            hp = tmp / f"slide_{i:02d}.html"
            hp.write_text(doc, encoding="utf-8")
            if keep_html:
                keep_html.mkdir(parents=True, exist_ok=True)
                shutil.copy(hp, keep_html / f"{spec['folder']}_slide_{i:02d}.html")
            html_paths.append(hp)
            png_paths.append(tmp / f"slide_{i:02d}.png")
            jpg_paths.append(out_dir / f"slide_{i:02d}.jpg")
        browser = v1.find_local_browser()
        try:
            import playwright.sync_api  # noqa: F401
            v1.render_html_files_playwright(html_paths, png_paths)
        except ImportError:
            if not browser:
                raise RuntimeError("Nem Playwright nem Chrome/Edge headless disponíveis.")
            v1.render_html_files_headless_browser(browser, html_paths, png_paths)
        for i, (pp, jp) in enumerate(zip(png_paths, jpg_paths), start=1):
            (w, h), size = v1.convert_png_to_ig_jpeg(pp, jp)
            gr = green_ratio(jp)
            stype = slides[i - 1]["type"]
            flag = ""
            if gr > 0.004:
                if stype == "proof":
                    flag = f" | verde {gr:.2%} (print real da planilha — permitido)"
                else:
                    raise RuntimeError(f"{spec['id']} slide {i}: {gr:.2%} de pixels verdes detectados")
            print(f"  [OK] {spec['folder']}/{jp.name} {w}x{h} {size / 1024:.0f} KB · {stype}{flag}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return jpg_paths


def main() -> int:
    ap = argparse.ArgumentParser(description="Gerador v2 multi-tema (5-8 slides) FinanzasPro.")
    ap.add_argument("--spec", required=True)
    ap.add_argument("--only")
    ap.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    ap.add_argument("--keep-html", help="Pasta para salvar o HTML de cada slide (debug).")
    args = ap.parse_args()
    raw = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    carousels = raw["carrosseis"] if isinstance(raw, dict) else raw
    if args.only:
        carousels = [c for c in carousels if args.only in (c.get("id"), c.get("folder"))]
        if not carousels:
            print(f"Nenhum carrossel corresponde a {args.only}")
            return 1
    img = ImageCache()
    total = 0
    for c in carousels:
        print(f"\n>>> {c['id']} ({c['folder']}) · tema {c['theme']} · {len(c['slides'])} slides · CTA {c['cta_keyword']}")
        total += len(render_carousel(c, Path(args.output_dir), img, Path(args.keep_html) if args.keep_html else None))
    print(f"\nConcluído: {len(carousels)} carrossel(is), {total} slides.")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
