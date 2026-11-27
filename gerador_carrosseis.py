#!/usr/bin/env python3
"""
Gerador Automático em Lote de Carrosséis Instagram (1080x1350 JPEG) — FinanzasPro (@mateorivas_finanzas).

Renderiza carrosséis de 6 slides a partir de arquivos JSON de especificação usando
HTML/CSS + Playwright/Chromium headless (com fallback automático para Chrome/Edge headless local)
e Pillow para garantir exportação sRGB JPEG exata 1080x1350 <= 8 MB.

Travas de marca aplicadas automaticamente:
- Paleta estritamente sem verde: #0A192F, #112240, #3B82F6, #FFFFFF, #E2E8F0
- Espanhol neutro (tuteo), zero emojis verdes
- Integração automática com assets/biblioteca_visual/ (10 fotos 4:5) + print real Visión General no Slide 5
- Indicador "Desliza →" nos slides 1 a 5 e CTA de comentário no Slide 6
"""

from __future__ import annotations

import argparse
import base64
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from PIL import Image

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent
VISUAL_LIB_DIR = BASE_DIR / "assets" / "biblioteca_visual"
SPREADSHEET_PROOF_PATH = BASE_DIR / "ativos" / "demonstração planilha - vision geral.jpeg"
DEFAULT_OUTPUT_DIR = BASE_DIR / "ativos_instagram"

SLIDE_W = 1080
SLIDE_H = 1350
MAX_JPEG_BYTES = 8 * 1024 * 1024
ALLOWED_CTA_KEYWORDS = {"PLANILLA", "CONTROL", "SISTEMA", "METODO", "QUIERO"}
GREEN_EMOJIS = ("🟢", "✅", "💚", "💵", "💹", "🟩", "🍏", "🥗", "🌿")

# Mapa canônico das 10 imagens editoriais em assets/biblioteca_visual/
VISUAL_ALIASES: dict[str, str] = {
    "mateo_01": "01_mateo.jpg",
    "mateo_02": "02_mateo.jpg",
    "mateo_03": "03_mateo.jpg",
    "mateo_04": "mateo_4.jpg",
    "mateo_05": "mateo_5.jpg",
    "cena_casal": "_06A Dor Real do Casal.jpg",
    "cena_hormiga": "7_gastoshormiga.jpg",
    "cena_cartao": "08_cartãodecredito.jpg",
    "cena_celular": "09_celularclareza.jpg",
    "cena_horizonte": "10_horizontedaliberdade.jpg",
}

PORTRAIT_KEYS = {"mateo_01", "mateo_02", "mateo_03", "mateo_04", "mateo_05", "cena_casal"}


def esc(text: str) -> str:
    """Escapa texto HTML preservando quebra de linha explícita se houver."""
    return html.escape(str(text), quote=True)


def render_accent_text(text: str) -> str:
    """Converte marcação **palavra** em <span class='accent'>palavra</span> com escape seguro."""
    parts = re.split(r"(\*\*.*?\*\*)", str(text))
    rendered: list[str] = []
    for part in parts:
        if part.startswith("**") and part.endswith("**") and len(part) > 4:
            rendered.append(f'<span class="accent">{esc(part[2:-2])}</span>')
        else:
            rendered.append(esc(part))
    return "".join(rendered)


def resolve_visual_path(ref: str) -> Path:
    """Resolve alias ('mateo_01', 'cena_hormiga', 'planilha_vision_geral') ou caminho de arquivo."""
    if not ref:
        raise ValueError("Referência de imagem vazia.")
    if ref == "planilha_vision_geral":
        if not SPREADSHEET_PROOF_PATH.exists():
            raise FileNotFoundError(f"Print da planilha não encontrado: {SPREADSHEET_PROOF_PATH}")
        return SPREADSHEET_PROOF_PATH

    if ref in VISUAL_ALIASES:
        candidate = VISUAL_LIB_DIR / VISUAL_ALIASES[ref]
        if candidate.exists():
            return candidate
        raise FileNotFoundError(f"Imagem da biblioteca visual não encontrada: {candidate}")

    # Busca direta em assets/biblioteca_visual/ ou caminho relativo ao projeto
    for base in (VISUAL_LIB_DIR, BASE_DIR):
        candidate = base / ref
        if candidate.exists():
            return candidate

    direct = Path(ref)
    if direct.exists():
        return direct

    raise FileNotFoundError(f"Imagem não encontrada: '{ref}' (verifique assets/biblioteca_visual/)")


def image_to_data_uri(img_path: Path, max_dim: int = 1600) -> str:
    """Converte imagem para JPEG otimizado em data URI base64 para renderização rápida e fiel."""
    with Image.open(img_path) as im:
        rgb = im.convert("RGB")
        if max(rgb.size) > max_dim:
            rgb.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        try:
            rgb.save(tmp_path, format="JPEG", quality=90, optimize=True)
            b64 = base64.b64encode(tmp_path.read_bytes()).decode("ascii")
        finally:
            tmp_path.unlink(missing_ok=True)
    return f"data:image/jpeg;base64,{b64}"


def validate_no_green_text(obj: Any, context: str = "") -> None:
    """Garante ausência total de emojis verdes em qualquer texto do carrossel."""
    if isinstance(obj, str):
        found = [e for e in GREEN_EMOJIS if e in obj]
        if found:
            raise ValueError(f"Emoji(s) verde(s) proibido(s) em {context}: {' '.join(found)}")
    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            validate_no_green_text(item, f"{context}[{idx}]")
    elif isinstance(obj, dict):
        for k, v in obj.items():
            validate_no_green_text(v, f"{context}.{k}")


def base_css() -> str:
    """CSS compartilhado da marca FinanzasPro (paleta estritamente sem verde)."""
    return """
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=Plus+Jakarta+Sans:wght@600;700;800&display=swap');

    :root {
      --navy: #0A192F;
      --surface: #112240;
      --blue: #3B82F6;
      --white: #FFFFFF;
      --slate: #E2E8F0;
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    html, body {
      width: 1080px;
      height: 1350px;
      overflow: hidden;
      background: #0A192F;
      color: #FFFFFF;
      font-family: 'Plus Jakarta Sans', 'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif;
      -webkit-font-smoothing: antialiased;
      font-variant-numeric: tabular-nums;
    }

    .slide {
      position: relative;
      width: 1080px;
      height: 1350px;
      overflow: hidden;
      background: #0A192F;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      padding: 54px 68px 54px 68px;
    }

    .bg-photo {
      position: absolute;
      inset: 0;
      width: 100%;
      height: 100%;
      object-fit: cover;
      object-position: center center;
      z-index: 0;
    }

    .bg-photo.portrait {
      object-position: center 18%;
    }

    .bg-grid {
      position: absolute;
      inset: 0;
      z-index: 1;
      background-image:
        linear-gradient(to right, rgba(59, 130, 246, 0.065) 1px, transparent 1px),
        linear-gradient(to bottom, rgba(59, 130, 246, 0.065) 1px, transparent 1px);
      background-size: 64px 64px;
      pointer-events: none;
    }

    .overlay-cover {
      position: absolute;
      inset: 0;
      z-index: 1;
      background: linear-gradient(
        180deg,
        rgba(10, 25, 47, 0.80) 0%,
        rgba(10, 25, 47, 0.24) 24%,
        rgba(10, 25, 47, 0.34) 44%,
        rgba(10, 25, 47, 0.88) 64%,
        rgba(10, 25, 47, 0.97) 84%,
        rgba(10, 25, 47, 0.99) 100%
      );
    }

    .overlay-deep {
      position: absolute;
      inset: 0;
      z-index: 1;
      background: linear-gradient(
        180deg,
        rgba(10, 25, 47, 0.88) 0%,
        rgba(10, 25, 47, 0.82) 45%,
        rgba(10, 25, 47, 0.94) 100%
      );
    }

    .overlay-cta {
      position: absolute;
      inset: 0;
      z-index: 1;
      background:
        radial-gradient(circle at 50% 52%, rgba(59, 130, 246, 0.22) 0%, rgba(10, 25, 47, 0.0) 56%),
        linear-gradient(
          180deg,
          rgba(10, 25, 47, 0.86) 0%,
          rgba(10, 25, 47, 0.80) 45%,
          rgba(10, 25, 47, 0.95) 100%
        );
    }

    .content-layer {
      position: relative;
      z-index: 2;
    }

    /* Header */
    .header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding-bottom: 24px;
      border-bottom: 1px solid rgba(226, 232, 240, 0.14);
    }

    .handle-wrap {
      display: flex;
      align-items: center;
      gap: 14px;
    }

    .brand-dot {
      width: 14px;
      height: 14px;
      border-radius: 50%;
      background: #3B82F6;
      box-shadow: 0 0 18px rgba(59, 130, 246, 0.9);
      flex-shrink: 0;
    }

    .handle {
      font-size: 25px;
      font-weight: 700;
      letter-spacing: -0.01em;
      color: #FFFFFF;
    }

    .header-pill {
      display: inline-flex;
      align-items: center;
      gap: 10px;
      padding: 11px 22px;
      border-radius: 999px;
      background: rgba(17, 34, 64, 0.85);
      border: 1px solid rgba(59, 130, 246, 0.42);
      color: #E2E8F0;
      font-size: 18px;
      font-weight: 700;
      letter-spacing: 0.09em;
      text-transform: uppercase;
      white-space: nowrap;
      flex-shrink: 0;
    }

    .header-pill .pill-num {
      color: #3B82F6;
    }

    /* Typography */
    .kicker {
      font-size: 21px;
      font-weight: 800;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      color: #3B82F6;
      margin-bottom: 18px;
    }

    .headline {
      font-size: 74px;
      font-weight: 800;
      line-height: 1.05;
      letter-spacing: -0.03em;
      color: #FFFFFF;
    }

    .headline.md {
      font-size: 64px;
      line-height: 1.08;
    }

    .headline.sm {
      font-size: 56px;
      line-height: 1.1;
    }

    .accent {
      color: #3B82F6;
    }

    .subtitle {
      margin-top: 24px;
      font-size: 29px;
      font-weight: 500;
      line-height: 1.42;
      color: #E2E8F0;
    }

    /* Cover bottom anchor */
    .cover-body {
      margin-top: auto;
      margin-bottom: 36px;
    }

    .cover-hook-pill {
      display: inline-flex;
      align-items: center;
      gap: 12px;
      margin-top: 30px;
      padding: 14px 24px;
      border-radius: 16px;
      background: rgba(17, 34, 64, 0.88);
      border: 1px solid rgba(59, 130, 246, 0.45);
      color: #E2E8F0;
      font-size: 23px;
      font-weight: 600;
    }

    .cover-hook-pill strong {
      color: #FFFFFF;
    }

    /* Middle layout wrapper */
    .main-stack {
      flex: 1;
      display: flex;
      flex-direction: column;
      justify-content: center;
      gap: 30px;
      padding: 20px 0;
    }

    /* Diagnostic 2-col cards */
    .compare-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 24px;
      margin-top: 8px;
    }

    .card {
      background: rgba(17, 34, 64, 0.88);
      border: 1px solid rgba(226, 232, 240, 0.14);
      border-radius: 26px;
      padding: 32px 28px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      gap: 20px;
    }

    .card.featured {
      border: 1.5px solid rgba(59, 130, 246, 0.65);
      box-shadow: 0 18px 48px rgba(59, 130, 246, 0.16);
    }

    .card-top {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }

    .card-label {
      font-size: 19px;
      font-weight: 800;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: #E2E8F0;
    }

    .card.featured .card-label {
      color: #3B82F6;
    }

    .badge {
      padding: 8px 16px;
      border-radius: 999px;
      font-size: 17px;
      font-weight: 800;
      letter-spacing: 0.05em;
      white-space: nowrap;
      flex-shrink: 0;
      background: rgba(10, 25, 47, 0.85);
      color: #E2E8F0;
      border: 1px solid rgba(226, 232, 240, 0.2);
    }

    .badge.blue {
      background: #3B82F6;
      color: #FFFFFF;
      border-color: #3B82F6;
    }

    .metric-list {
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .metric-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 14px;
      padding-bottom: 14px;
      border-bottom: 1px solid rgba(226, 232, 240, 0.10);
      font-size: 24px;
      color: #E2E8F0;
    }

    .metric-row:last-child {
      border-bottom: none;
      padding-bottom: 0;
    }

    .metric-val {
      font-weight: 800;
      color: #FFFFFF;
      white-space: nowrap;
      flex-shrink: 0;
    }

    .card.featured .metric-val {
      color: #3B82F6;
    }

    .result-box {
      padding: 22px 24px;
      border-radius: 18px;
      background: rgba(10, 25, 47, 0.85);
      border: 1px solid rgba(226, 232, 240, 0.14);
    }

    .card.featured .result-box {
      background: rgba(59, 130, 246, 0.14);
      border-color: rgba(59, 130, 246, 0.45);
    }

    .result-label {
      font-size: 17px;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: #E2E8F0;
      margin-bottom: 8px;
    }

    .result-value {
      font-size: 46px;
      font-weight: 900;
      letter-spacing: -0.02em;
      color: #E2E8F0;
      white-space: nowrap;
    }

    .card.featured .result-value {
      color: #3B82F6;
    }

    .footnote {
      font-size: 20px;
      color: rgba(226, 232, 240, 0.78);
      line-height: 1.35;
    }

    /* Belief Shift stacked numbered rows */
    .points-stack {
      display: flex;
      flex-direction: column;
      gap: 20px;
    }

    .point-card {
      display: flex;
      align-items: flex-start;
      gap: 26px;
      padding: 28px 32px;
      border-radius: 24px;
      background: rgba(17, 34, 64, 0.90);
      border: 1px solid rgba(59, 130, 246, 0.28);
    }

    .point-num {
      font-size: 42px;
      font-weight: 900;
      line-height: 1;
      color: #3B82F6;
      min-width: 66px;
      white-space: nowrap;
      flex-shrink: 0;
      padding-top: 4px;
    }

    .point-title {
      font-size: 29px;
      font-weight: 800;
      color: #FFFFFF;
      margin-bottom: 8px;
      line-height: 1.2;
    }

    .point-desc {
      font-size: 24px;
      font-weight: 400;
      color: #E2E8F0;
      line-height: 1.4;
    }

    .takeaway-bar {
      padding: 26px 32px;
      border-radius: 22px;
      background: rgba(59, 130, 246, 0.14);
      border: 1.5px solid rgba(59, 130, 246, 0.5);
      font-size: 26px;
      font-weight: 700;
      line-height: 1.38;
      color: #FFFFFF;
    }

    /* Mechanism visual bar + 3 bento steps */
    .bar-card {
      padding: 30px 32px;
      border-radius: 26px;
      background: rgba(17, 34, 64, 0.90);
      border: 1px solid rgba(59, 130, 246, 0.34);
      display: flex;
      flex-direction: column;
      gap: 20px;
    }

    .bar-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
    }

    .bar-title {
      font-size: 21px;
      font-weight: 800;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: #E2E8F0;
    }

    .bar-right {
      font-size: 20px;
      font-weight: 800;
      color: #3B82F6;
      white-space: nowrap;
    }

    .segmented-bar {
      display: flex;
      width: 100%;
      height: 68px;
      border-radius: 16px;
      overflow: hidden;
      gap: 6px;
    }

    .seg {
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 22px;
      font-weight: 800;
      color: #FFFFFF;
      white-space: nowrap;
      padding: 0 14px;
    }

    .seg-0 { background: #1D4ED8; }
    .seg-1 { background: #3B82F6; }
    .seg-2 { background: #60A5FA; color: #0A192F; }

    .steps-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 20px;
    }

    .step-card {
      background: rgba(17, 34, 64, 0.90);
      border: 1px solid rgba(59, 130, 246, 0.28);
      border-radius: 24px;
      padding: 30px 26px;
      display: flex;
      flex-direction: column;
      gap: 14px;
    }

    .step-tag {
      font-size: 18px;
      font-weight: 800;
      letter-spacing: 0.1em;
      color: #3B82F6;
      text-transform: uppercase;
      white-space: nowrap;
    }

    .step-title {
      font-size: 28px;
      font-weight: 800;
      line-height: 1.2;
      color: #FFFFFF;
    }

    .step-desc {
      font-size: 22px;
      font-weight: 400;
      line-height: 1.42;
      color: #E2E8F0;
    }

    /* Slide 5 Proof Mockup */
    .mockup-window {
      border-radius: 24px;
      overflow: hidden;
      background: #112240;
      border: 1.5px solid rgba(59, 130, 246, 0.45);
      box-shadow: 0 24px 60px rgba(0, 0, 0, 0.48);
    }

    .mockup-chrome {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 16px 22px;
      background: #0F203D;
      border-bottom: 1px solid rgba(226, 232, 240, 0.12);
    }

    .win-dots {
      display: flex;
      gap: 9px;
    }

    .win-dot {
      width: 13px;
      height: 13px;
      border-radius: 50%;
      background: rgba(59, 130, 246, 0.45);
    }

    .win-dot.strong {
      background: #3B82F6;
    }

    .win-title {
      font-size: 19px;
      font-weight: 600;
      color: #E2E8F0;
      white-space: nowrap;
    }

    .win-tag {
      font-size: 16px;
      font-weight: 800;
      letter-spacing: 0.08em;
      color: #3B82F6;
      white-space: nowrap;
    }

    .mockup-img-wrap {
      background: #0A192F;
      padding: 8px;
    }

    .mockup-img {
      display: block;
      width: 100%;
      height: 505px;
      object-fit: cover;
      object-position: top center;
      border-radius: 12px;
    }

    .callouts-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 18px;
    }

    .callout-card {
      background: rgba(17, 34, 64, 0.90);
      border: 1px solid rgba(59, 130, 246, 0.30);
      border-radius: 20px;
      padding: 22px 22px;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }

    .callout-title {
      font-size: 19px;
      font-weight: 800;
      letter-spacing: 0.05em;
      color: #3B82F6;
      text-transform: uppercase;
    }

    .callout-desc {
      font-size: 21px;
      line-height: 1.38;
      color: #E2E8F0;
    }

    /* Slide 6 CTA */
    .cta-center {
      flex: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      text-align: center;
      gap: 28px;
    }

    .cta-top-pill {
      padding: 13px 28px;
      border-radius: 999px;
      background: rgba(17, 34, 64, 0.92);
      border: 1px solid rgba(59, 130, 246, 0.45);
      color: #E2E8F0;
      font-size: 20px;
      font-weight: 800;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      white-space: nowrap;
    }

    .cta-box {
      width: 100%;
      padding: 46px 44px;
      border-radius: 32px;
      background: rgba(17, 34, 64, 0.92);
      border: 1.5px solid rgba(59, 130, 246, 0.55);
      box-shadow: 0 24px 64px rgba(59, 130, 246, 0.22);
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 24px;
    }

    .cta-prompt {
      font-size: 28px;
      font-weight: 600;
      color: #E2E8F0;
    }

    .cta-keyword {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-width: 540px;
      padding: 28px 56px;
      border-radius: 26px;
      background: #3B82F6;
      color: #FFFFFF;
      font-size: 76px;
      font-weight: 900;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      box-shadow: 0 0 54px rgba(59, 130, 246, 0.55);
      white-space: nowrap;
    }

    .cta-secondary {
      font-size: 23px;
      font-weight: 600;
      color: #E2E8F0;
      opacity: 0.88;
    }

    .cta-instruction {
      max-width: 820px;
      font-size: 29px;
      font-weight: 600;
      line-height: 1.42;
      color: #FFFFFF;
    }

    /* Footer */
    .footer {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 24px;
      padding-top: 24px;
      border-top: 1px solid rgba(226, 232, 240, 0.14);
    }

    .progress-wrap {
      display: flex;
      align-items: center;
      gap: 16px;
      flex: 1;
      max-width: 480px;
    }

    .progress-track {
      flex: 1;
      height: 8px;
      border-radius: 999px;
      background: rgba(226, 232, 240, 0.18);
      overflow: hidden;
    }

    .progress-fill {
      height: 100%;
      border-radius: 999px;
      background: #3B82F6;
    }

    .progress-count {
      font-size: 20px;
      font-weight: 800;
      color: #E2E8F0;
      white-space: nowrap;
    }

    .swipe-indicator {
      display: inline-flex;
      align-items: center;
      gap: 10px;
      padding: 12px 24px;
      border-radius: 999px;
      background: rgba(59, 130, 246, 0.16);
      border: 1px solid rgba(59, 130, 246, 0.45);
      color: #FFFFFF;
      font-size: 22px;
      font-weight: 800;
      letter-spacing: 0.02em;
      white-space: nowrap;
      flex-shrink: 0;
    }

    .swipe-indicator.cta-foot {
      background: rgba(17, 34, 64, 0.9);
      border-color: rgba(59, 130, 246, 0.5);
      color: #3B82F6;
    }
    """


def render_header(badge_label: str, slide_idx: int, total: int = 6) -> str:
    return f"""
    <div class="header content-layer">
      <div class="handle-wrap">
        <span class="brand-dot"></span>
        <span class="handle">@mateorivas_finanzas</span>
      </div>
      <div class="header-pill">
        <span>{esc(badge_label)}</span>
        <span class="pill-num">• {slide_idx:02d}/{total:02d}</span>
      </div>
    </div>
    """


def render_footer(slide_idx: int, total: int = 6, cta_keyword: str | None = None) -> str:
    pct = round((slide_idx / total) * 100, 2)
    if slide_idx < total:
        right_html = '<div class="swipe-indicator">Desliza →</div>'
    else:
        kw = esc(cta_keyword or "PLANILLA")
        right_html = f'<div class="swipe-indicator cta-foot">Comenta {kw} 👇</div>'
    return f"""
    <div class="footer content-layer">
      <div class="progress-wrap">
        <div class="progress-track">
          <div class="progress-fill" style="width: {pct}%;"></div>
        </div>
        <span class="progress-count">{slide_idx:02d}/{total:02d}</span>
      </div>
      {right_html}
    </div>
    """


def wrap_slide_html(body_inner: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=1080, initial-scale=1.0" />
  <style>{base_css()}</style>
</head>
<body>
  <div class="slide">
    {body_inner}
  </div>
</body>
</html>
"""


def build_slide_html(slide: dict[str, Any], slide_idx: int, total: int, cache: dict[str, str]) -> str:
    """Gera o HTML completo de um slide (1..6) conforme seu tipo."""
    stype = slide["type"]
    badge = slide.get("badge", "FINANZASPRO")

    def get_uri(ref: str) -> str:
        if ref not in cache:
            path = resolve_visual_path(ref)
            cache[ref] = image_to_data_uri(path)
        return cache[ref]

    if stype == "cover":
        img_ref = slide["image"]
        is_portrait = img_ref in PORTRAIT_KEYS or "mateo" in img_ref.lower() or "casal" in img_ref.lower()
        img_cls = "bg-photo portrait" if is_portrait else "bg-photo"
        hook_pill = slide.get("hook_pill", "")
        hook_html = (
            f'<div class="cover-hook-pill">{render_accent_text(hook_pill)}</div>'
            if hook_pill
            else ""
        )
        inner = f"""
        <img class="{img_cls}" src="{get_uri(img_ref)}" alt="" />
        <div class="overlay-cover"></div>
        {render_header(badge, slide_idx, total)}
        <div class="cover-body content-layer">
          <div class="kicker">{esc(slide.get("kicker", ""))}</div>
          <h1 class="headline">{render_accent_text(slide["headline"])}</h1>
          <p class="subtitle">{render_accent_text(slide["subtitle"])}</p>
          {hook_html}
        </div>
        {render_footer(slide_idx, total)}
        """
        return wrap_slide_html(inner)

    if stype == "diagnostic":
        bg_html = ""
        if slide.get("image"):
            img_ref = slide["image"]
            is_portrait = img_ref in PORTRAIT_KEYS or "mateo" in img_ref.lower()
            bg_html = f'<img class="bg-photo{" portrait" if is_portrait else ""}" src="{get_uri(img_ref)}" alt="" />'
        left = slide["left_card"]
        right = slide["right_card"]

        def render_card(card: dict[str, Any], featured: bool) -> str:
            rows_html = "".join(
                f'<div class="metric-row"><span>{esc(r["label"])}</span><span class="metric-val">{esc(r["value"])}</span></div>'
                for r in card["rows"]
            )
            badge_cls = "badge blue" if featured else "badge"
            card_cls = "card featured" if featured else "card"
            return f"""
            <div class="{card_cls}">
              <div class="card-top">
                <span class="card-label">{esc(card["label"])}</span>
                <span class="{badge_cls}">{esc(card["badge"])}</span>
              </div>
              <div class="metric-list">{rows_html}</div>
              <div class="result-box">
                <div class="result-label">{esc(card["result_label"])}</div>
                <div class="result-value">{esc(card["result_value"])}</div>
              </div>
            </div>
            """

        footnote_html = (
            f'<p class="footnote">{esc(slide["footnote"])}</p>' if slide.get("footnote") else ""
        )
        inner = f"""
        {bg_html}
        <div class="overlay-deep"></div>
        <div class="bg-grid"></div>
        {render_header(badge, slide_idx, total)}
        <div class="main-stack content-layer">
          <div>
            <div class="kicker">{esc(slide.get("kicker", ""))}</div>
            <h2 class="headline md">{render_accent_text(slide["headline"])}</h2>
          </div>
          <div class="compare-grid">
            {render_card(left, False)}
            {render_card(right, True)}
          </div>
          {footnote_html}
        </div>
        {render_footer(slide_idx, total)}
        """
        return wrap_slide_html(inner)

    if stype == "belief_shift":
        bg_html = ""
        if slide.get("image"):
            img_ref = slide["image"]
            is_portrait = img_ref in PORTRAIT_KEYS or "mateo" in img_ref.lower()
            bg_html = f'<img class="bg-photo{" portrait" if is_portrait else ""}" src="{get_uri(img_ref)}" alt="" />'
        points_html = "".join(
            f"""
            <div class="point-card">
              <div class="point-num">{idx:02d}</div>
              <div>
                <div class="point-title">{esc(pt["title"])}</div>
                <div class="point-desc">{esc(pt["desc"])}</div>
              </div>
            </div>
            """
            for idx, pt in enumerate(slide["points"], start=1)
        )
        takeaway_html = (
            f'<div class="takeaway-bar">{render_accent_text(slide["takeaway"])}</div>'
            if slide.get("takeaway")
            else ""
        )
        inner = f"""
        {bg_html}
        <div class="overlay-deep"></div>
        <div class="bg-grid"></div>
        {render_header(badge, slide_idx, total)}
        <div class="main-stack content-layer">
          <div>
            <div class="kicker">{esc(slide.get("kicker", ""))}</div>
            <h2 class="headline md">{render_accent_text(slide["headline"])}</h2>
          </div>
          <div class="points-stack">{points_html}</div>
          {takeaway_html}
        </div>
        {render_footer(slide_idx, total)}
        """
        return wrap_slide_html(inner)

    if stype == "mechanism":
        bg_html = ""
        if slide.get("image"):
            img_ref = slide["image"]
            is_portrait = img_ref in PORTRAIT_KEYS or "mateo" in img_ref.lower()
            bg_html = f'<img class="bg-photo{" portrait" if is_portrait else ""}" src="{get_uri(img_ref)}" alt="" />'
        segments_html = "".join(
            f'<div class="seg seg-{i % 3}" style="flex: {seg["weight"]};">{esc(seg["label"])}</div>'
            for i, seg in enumerate(slide["segments"])
        )
        steps_html = "".join(
            f"""
            <div class="step-card">
              <div class="step-tag">PASO {i:02d}</div>
              <div class="step-title">{esc(st["title"])}</div>
              <div class="step-desc">{esc(st["desc"])}</div>
            </div>
            """
            for i, st in enumerate(slide["steps"], start=1)
        )
        inner = f"""
        {bg_html}
        <div class="overlay-deep"></div>
        <div class="bg-grid"></div>
        {render_header(badge, slide_idx, total)}
        <div class="main-stack content-layer">
          <div>
            <div class="kicker">{esc(slide.get("kicker", ""))}</div>
            <h2 class="headline md">{render_accent_text(slide["headline"])}</h2>
          </div>
          <div class="bar-card">
            <div class="bar-header">
              <span class="bar-title">{esc(slide.get("bar_title", "ESTRUCTURA VISUAL"))}</span>
              <span class="bar-right">{esc(slide.get("bar_right", "100% CLARO"))}</span>
            </div>
            <div class="segmented-bar">{segments_html}</div>
          </div>
          <div class="steps-grid">{steps_html}</div>
        </div>
        {render_footer(slide_idx, total)}
        """
        return wrap_slide_html(inner)

    if stype == "proof":
        proof_ref = slide.get("image", "planilha_vision_geral")
        proof_uri = get_uri(proof_ref)
        callouts_html = "".join(
            f"""
            <div class="callout-card">
              <div class="callout-title">→ {esc(c["title"])}</div>
              <div class="callout-desc">{esc(c["desc"])}</div>
            </div>
            """
            for c in slide["callouts"]
        )
        inner = f"""
        <div class="bg-grid"></div>
        {render_header(badge, slide_idx, total)}
        <div class="main-stack content-layer" style="gap: 24px;">
          <div>
            <div class="kicker">{esc(slide.get("kicker", "VISTA REAL · GOOGLE SHEETS SIN FÓRMULAS"))}</div>
            <h2 class="headline sm">{render_accent_text(slide["headline"])}</h2>
          </div>
          <div class="mockup-window">
            <div class="mockup-chrome">
              <div class="win-dots">
                <span class="win-dot"></span>
                <span class="win-dot"></span>
                <span class="win-dot strong"></span>
              </div>
              <div class="win-title">{esc(slide.get("window_title", "FinanzasPro · Visión General (Google Sheets)"))}</div>
              <div class="win-tag">COPIA PRIVADA</div>
            </div>
            <div class="mockup-img-wrap">
              <img class="mockup-img" src="{proof_uri}" alt="FinanzasPro Visión General" />
            </div>
          </div>
          <div class="callouts-grid">{callouts_html}</div>
        </div>
        {render_footer(slide_idx, total)}
        """
        return wrap_slide_html(inner)

    if stype == "cta":
        keyword = str(slide["keyword"]).strip().upper()
        if keyword not in ALLOWED_CTA_KEYWORDS:
            raise ValueError(
                f"Palavra-chave CTA inválida '{keyword}'. Permitidas: {sorted(ALLOWED_CTA_KEYWORDS)}"
            )
        secondary = str(slide.get("secondary_keyword", "")).strip().upper()
        secondary_html = (
            f'<div class="cta-secondary">(también funciona con {esc(secondary)})</div>'
            if secondary
            else ""
        )
        bg_html = ""
        if slide.get("image"):
            img_ref = slide["image"]
            is_portrait = img_ref in PORTRAIT_KEYS or "mateo" in img_ref.lower()
            bg_html = f'<img class="bg-photo{" portrait" if is_portrait else ""}" src="{get_uri(img_ref)}" alt="" />'
        inner = f"""
        {bg_html}
        <div class="overlay-cta"></div>
        <div class="bg-grid"></div>
        {render_header(badge, slide_idx, total)}
        <div class="cta-center content-layer">
          <div class="cta-top-pill">{esc(slide.get("pill", "TU ATAJO EN GOOGLE SHEETS"))}</div>
          <h2 class="headline md">{render_accent_text(slide["headline"])}</h2>
          <div class="cta-box">
            <div class="cta-prompt">Comenta aquí abajo la palabra:</div>
            <div class="cta-keyword">{esc(keyword)}</div>
            {secondary_html}
          </div>
          <p class="cta-instruction">{render_accent_text(slide["instruction"])}</p>
        </div>
        {render_footer(slide_idx, total, cta_keyword=keyword)}
        """
        return wrap_slide_html(inner)

    raise ValueError(f"Tipo de slide não suportado: '{stype}'")


def find_local_browser() -> Path | None:
    """Encontra Google Chrome ou Microsoft Edge instalado localmente para modo headless."""
    candidates = [
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
        Path("/usr/bin/google-chrome"),
        Path("/usr/bin/chromium"),
        Path("/usr/bin/chromium-browser"),
    ]
    for path in candidates:
        if path.exists():
            return path
    for cmd in ("google-chrome", "chromium", "chromium-browser", "chrome", "msedge"):
        found = shutil.which(cmd)
        if found:
            return Path(found)
    return None


def convert_png_to_ig_jpeg(png_path: Path, jpg_path: Path) -> tuple[tuple[int, int], int]:
    """Garante 1080x1350 exatos, sRGB, baseline JPEG <= 8 MB."""
    with Image.open(png_path) as im:
        rgb = im.convert("RGB")
        if rgb.size != (SLIDE_W, SLIDE_H):
            rgb = rgb.resize((SLIDE_W, SLIDE_H), Image.Resampling.LANCZOS)
        jpg_path.parent.mkdir(parents=True, exist_ok=True)
        quality = 92
        while quality >= 70:
            rgb.save(
                jpg_path,
                format="JPEG",
                quality=quality,
                optimize=True,
                progressive=False,
            )
            size_bytes = jpg_path.stat().st_size
            if size_bytes <= MAX_JPEG_BYTES:
                return rgb.size, size_bytes
            quality -= 4
        raise RuntimeError(f"JPEG excedeu 8 MB mesmo em quality=70: {jpg_path}")


def render_html_files_playwright(html_paths: list[Path], png_paths: list[Path]) -> None:
    """Renderiza lista de arquivos HTML em PNG 1080x1350 usando Playwright Chromium."""
    from playwright.sync_api import sync_playwright

    local_browser = find_local_browser()
    with sync_playwright() as p:
        launch_kwargs: dict[str, Any] = {"headless": True}
        if local_browser and local_browser.exists():
            launch_kwargs["executable_path"] = str(local_browser)
        browser = p.chromium.launch(**launch_kwargs)
        page = browser.new_page(
            viewport={"width": SLIDE_W, "height": SLIDE_H},
            device_scale_factor=1,
        )
        for html_path, png_path in zip(html_paths, png_paths):
            page.goto(html_path.resolve().as_uri(), wait_until="networkidle")
            page.wait_for_timeout(1200)
            page.screenshot(
                path=str(png_path),
                clip={"x": 0, "y": 0, "width": SLIDE_W, "height": SLIDE_H},
            )
        browser.close()


def render_html_files_headless_browser(
    browser_exe: Path,
    html_paths: list[Path],
    png_paths: list[Path],
) -> None:
    """Renderiza HTML em PNG 1080x1350 usando Chrome/Edge --headless=new sem dependências extras."""
    for html_path, png_path in zip(html_paths, png_paths):
        cmd = [
            str(browser_exe),
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--hide-scrollbars",
            "--force-device-scale-factor=1",
            f"--window-size={SLIDE_W},{SLIDE_H}",
            "--virtual-time-budget=4500",
            "--run-all-compositor-stages-before-draw",
            f"--screenshot={png_path}",
            html_path.resolve().as_uri(),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
        if res.returncode != 0 or not png_path.exists():
            raise RuntimeError(
                f"Falha ao renderizar {html_path.name} com {browser_exe.name}: "
                f"rc={res.returncode} stderr={res.stderr[:400]}"
            )


def render_carousel(
    spec: dict[str, Any],
    output_root: Path,
    img_cache: dict[str, str],
    engine: str = "auto",
) -> list[Path]:
    """Renderiza um carrossel de 6 slides em output_root/<folder>/slide_01.jpg..slide_06.jpg."""
    slides = spec.get("slides", [])
    if len(slides) != 6:
        raise ValueError(f"Carrossel '{spec.get('id')}' deve ter exatamente 6 slides (recebido: {len(slides)}).")
    if slides[4].get("type") != "proof":
        raise ValueError(f"Slide 5 de '{spec.get('id')}' deve ser do tipo 'proof' (planilha Visión General).")
    if slides[5].get("type") != "cta":
        raise ValueError(f"Slide 6 de '{spec.get('id')}' deve ser do tipo 'cta'.")

    validate_no_green_text(spec, context=str(spec.get("id", "carousel")))

    folder_name = spec["folder"]
    out_dir = output_root / folder_name
    out_dir.mkdir(parents=True, exist_ok=True)

    use_playwright = False
    if engine in ("auto", "playwright"):
        try:
            import playwright.sync_api  # noqa: F401
            use_playwright = True
        except ImportError:
            if engine == "playwright":
                raise RuntimeError("Playwright não está instalado. Instale com: pip install playwright")
            use_playwright = False

    browser_exe = find_local_browser()
    if not use_playwright and not browser_exe:
        raise RuntimeError(
            "Nem Playwright nem Chrome/Edge headless encontrados no sistema. "
            "Instale Playwright (`pip install playwright && python -m playwright install chromium`)."
        )

    tmp_dir = Path(tempfile.mkdtemp(prefix=f"fp_{folder_name}_"))
    html_paths: list[Path] = []
    png_paths: list[Path] = []
    jpg_paths: list[Path] = []

    try:
        for idx, slide in enumerate(slides, start=1):
            html_content = build_slide_html(slide, idx, len(slides), img_cache)
            # Validação de trava: "Desliza →" nos slides 1-5 e ausente no slide 6
            if idx <= 5 and "Desliza →" not in html_content:
                raise RuntimeError(f"Indicador 'Desliza →' ausente no slide {idx} de {spec.get('id')}")
            if idx == 6 and "Desliza →" in html_content:
                raise RuntimeError(f"Indicador 'Desliza →' não deve aparecer no slide 6 de {spec.get('id')}")

            hpath = tmp_dir / f"slide_{idx:02d}.html"
            ppath = tmp_dir / f"slide_{idx:02d}.png"
            jpath = out_dir / f"slide_{idx:02d}.jpg"
            hpath.write_text(html_content, encoding="utf-8")
            html_paths.append(hpath)
            png_paths.append(ppath)
            jpg_paths.append(jpath)

        if use_playwright:
            render_html_files_playwright(html_paths, png_paths)
        else:
            assert browser_exe is not None
            render_html_files_headless_browser(browser_exe, html_paths, png_paths)

        for idx, (ppath, jpath) in enumerate(zip(png_paths, jpg_paths), start=1):
            (w, h), size_bytes = convert_png_to_ig_jpeg(ppath, jpath)
            print(
                f"  [OK] {folder_name}/{jpath.name} -> {w}x{h} JPEG ({size_bytes / 1024:.1f} KB)"
            )
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    return jpg_paths


def check_assets() -> int:
    """Valida todas as 10 fotos em assets/biblioteca_visual/ + print Visión General."""
    print("=== Auditoria da Biblioteca Visual FinanzasPro ===")
    ok = True
    for alias, fname in VISUAL_ALIASES.items():
        path = VISUAL_LIB_DIR / fname
        if path.exists():
            with Image.open(path) as im:
                print(f"  [OK] {alias:<15} -> {fname:<30} ({im.size[0]}x{im.size[1]})")
        else:
            print(f"  [ERRO] {alias:<15} -> AUSENTE: {path}")
            ok = False

    if SPREADSHEET_PROOF_PATH.exists():
        with Image.open(SPREADSHEET_PROOF_PATH) as im:
            print(f"  [OK] planilha_proof  -> {SPREADSHEET_PROOF_PATH.name:<30} ({im.size[0]}x{im.size[1]})")
    else:
        print(f"  [ERRO] planilha_proof  -> AUSENTE: {SPREADSHEET_PROOF_PATH}")
        ok = False

    browser = find_local_browser()
    print(f"  Browser headless: {browser if browser else 'não encontrado (usará Playwright)'}")
    return 0 if ok else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Renderizador Automático em Lote de Carrosséis FinanzasPro (1080x1350 JPEG)."
    )
    parser.add_argument(
        "--spec",
        help="Caminho para JSON contendo um carrossel ou lista de carrosséis (chave 'carrosseis' ou array).",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Diretório de saída (padrão: ativos_instagram).",
    )
    parser.add_argument(
        "--only",
        help="Renderizar apenas um carrossel específico pelo id (ex.: FP-018) ou pasta (ex.: carrossel_02).",
    )
    parser.add_argument(
        "--engine",
        choices=("auto", "playwright", "chrome"),
        default="auto",
        help="Motor de renderização HTML->PNG (padrão: auto).",
    )
    parser.add_argument(
        "--check-assets",
        action="store_true",
        help="Audita as 10 imagens de assets/biblioteca_visual/ e o print Visión General.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.check_assets:
        return check_assets()

    if not args.spec:
        parser.error("Informe --spec <arquivo.json> ou --check-assets.")

    spec_path = Path(args.spec)
    if not spec_path.exists():
        print(f"ERRO: Arquivo de especificação não encontrado: {spec_path}")
        return 1

    raw = json.loads(spec_path.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        carousels = raw
    elif isinstance(raw, dict) and "carrosseis" in raw:
        carousels = raw["carrosseis"]
    elif isinstance(raw, dict) and "slides" in raw:
        carousels = [raw]
    else:
        print("ERRO: JSON inválido. Esperado array, objeto com 'carrosseis' ou objeto com 'slides'.")
        return 1

    if args.only:
        carousels = [
            c for c in carousels
            if c.get("id") == args.only or c.get("folder") == args.only
        ]
        if not carousels:
            print(f"ERRO: Nenhum carrossel corresponde a --only={args.only}")
            return 1

    output_root = Path(args.output_dir)
    img_cache: dict[str, str] = {}

    print(f"=== FinanzasPro Carousel Factory | {len(carousels)} carrossel(is) | saída: {output_root} ===")
    total_slides = 0
    for c in carousels:
        cid = c.get("id", "?")
        folder = c.get("folder", "?")
        print(f"\n>>> Renderizando {cid} ({folder}) — {c.get('titulo', '')}")
        generated = render_carousel(c, output_root, img_cache, engine=args.engine)
        total_slides += len(generated)

    print(f"\nConcluído! {len(carousels)} carrossel(is) / {total_slides} slides JPEG 1080x1350 gerados.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
