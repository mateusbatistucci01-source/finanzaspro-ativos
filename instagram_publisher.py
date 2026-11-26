#!/usr/bin/env python3
"""
Publicador automático no Instagram via Meta Graph API + GitHub Raw Assets + CSV Queue.

Suporta posts de imagem única e carrosséis (álbuns de 2 a 10 slides).
Usa apenas biblioteca padrão do Python para rede/CSV/env e Pillow (PIL) opcional
para preparar imagens JPEG 4:5 (1080x1350) em `ativos_instagram/`.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

# Garantir saída UTF-8 no terminal Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_ENV_PATH = BASE_DIR / ".env"
DEFAULT_CSV_PATH = BASE_DIR / "historico_grupos.csv"
DEFAULT_LOG_PATH = BASE_DIR / "logs" / "instagram_publish.log"
SOURCE_ASSETS_DIR = BASE_DIR / "ativos_anuncios"
INSTAGRAM_ASSETS_DIR = BASE_DIR / "ativos_instagram"

NAVY_BG_RGB = (10, 25, 47)  # #0A192F
MAX_IG_CAPTION_LEN = 2200
MAX_IG_IMAGE_BYTES = 8 * 1024 * 1024
MIN_IG_RATIO = 0.80  # 4:5
MAX_IG_RATIO = 1.91
MIN_CAROUSEL_ITEMS = 2
MAX_CAROUSEL_ITEMS = 10
GREEN_EMOJIS = ("🟢", "✅", "💚", "💵", "💹", "🟩", "🍏", "🥗", "🌿")
VALID_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".jfif", ".webp"}


def load_env(env_path: Path = DEFAULT_ENV_PATH) -> dict[str, str]:
    """Lê variáveis de um arquivo .env sem sobrescrever variáveis já definidas."""
    loaded: dict[str, str] = {}
    if not env_path.exists():
        return loaded

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and (
            (value.startswith('"') and value.endswith('"'))
            or (value.startswith("'") and value.endswith("'"))
        ):
            value = value[1:-1]
        loaded[key] = value
        if key not in os.environ or not os.environ[key]:
            os.environ[key] = value
    return loaded


def save_env_var(key: str, value: str, env_path: Path = DEFAULT_ENV_PATH) -> None:
    """Atualiza ou adiciona uma variável no arquivo .env preservando o restante."""
    lines: list[str] = []
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()

    replaced = False
    new_lines: list[str] = []
    for line in lines:
        if re.match(rf"^\s*{re.escape(key)}\s*=", line):
            new_lines.append(f"{key}={value}")
            replaced = True
        else:
            new_lines.append(line)
    if not replaced:
        new_lines.append(f"{key}={value}")

    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    os.environ[key] = value


def mask_token(token: str) -> str:
    """Mascara o token para exibição segura em logs e terminal."""
    if not token:
        return "(vazio)"
    if len(token) <= 12:
        return "***"
    return f"{token[:6]}...{token[-6:]}"


def get_graph_base_url(token: str, version: str) -> str:
    """Seleciona graph.instagram.com para tokens IGA/IGAA e graph.facebook.com para tokens EAA."""
    if token.startswith(("IGAA", "IGA")):
        return f"https://graph.instagram.com/{version}"
    return f"https://graph.facebook.com/{version}"


def build_github_raw_url(
    rel_path: str,
    user: str,
    repo: str,
    branch: str = "main",
) -> str:
    """Constrói URL raw pública do GitHub codificando segmentos conforme RFC 3986."""
    clean_rel = rel_path.replace("\\", "/").lstrip("/")
    encoded_segments = "/".join(
        urllib.parse.quote(part, safe="") for part in clean_rel.split("/") if part
    )
    return f"https://raw.githubusercontent.com/{user}/{repo}/{branch}/{encoded_segments}"


def resolve_image_urls(
    raw_value: str,
    gh_user: str,
    gh_repo: str,
    gh_branch: str = "main",
) -> list[str]:
    """
    Resolve `imagem_url` em lista de URLs HTTPS.
    Aceita:
      - URL única: `https://.../img.jpg`
      - Múltiplas URLs separadas por `;` ou `|` (carrossel de 2 a 10 slides)
      - Caminho relativo de pasta local de slides (ex.: `ativos_instagram/carrossel_01` ou `folder:ativos_instagram/carrossel_01`)
      - Caminho relativo de arquivo local (ex.: `ativos_instagram/anuncio_01_planilha.jpg`)
    """
    cleaned = (raw_value or "").strip()
    if not cleaned:
        return []

    if cleaned.lower().startswith("folder:"):
        cleaned = cleaned[7:].strip()

    # Múltiplos itens separados por ';' ou '|'
    if ";" in cleaned or "|" in cleaned:
        parts = [p.strip() for p in re.split(r"[;|]", cleaned) if p.strip()]
        urls: list[str] = []
        for part in parts:
            if part.lower().startswith("https://"):
                urls.append(part)
            else:
                urls.append(build_github_raw_url(part, gh_user, gh_repo, gh_branch))
        return urls

    # URL única HTTPS
    if cleaned.lower().startswith("https://"):
        return [cleaned]

    # Pasta local de slides
    candidate_dir = Path(cleaned)
    if not candidate_dir.is_absolute():
        candidate_dir = BASE_DIR / cleaned
    if candidate_dir.exists() and candidate_dir.is_dir():
        slide_files = sorted(
            p for p in candidate_dir.iterdir()
            if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg"}
        )
        urls = []
        for sf in slide_files:
            rel = sf.relative_to(BASE_DIR).as_posix()
            urls.append(build_github_raw_url(rel, gh_user, gh_repo, gh_branch))
        return urls

    # Arquivo relativo único
    return [build_github_raw_url(cleaned, gh_user, gh_repo, gh_branch)]


def _parse_http_error(err: urllib.error.HTTPError) -> tuple[int, str, dict[str, Any] | None]:
    raw_body = ""
    try:
        raw_body = err.read().decode("utf-8", errors="replace")
    except Exception:
        raw_body = str(err)
    parsed: dict[str, Any] | None = None
    try:
        parsed = json.loads(raw_body)
    except Exception:
        parsed = None
    return err.code, raw_body, parsed


def http_get_json(url: str, timeout: int = 20) -> tuple[bool, dict[str, Any]]:
    """Executa GET JSON na Graph API retornando (sucesso, payload_ou_erro)."""
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return True, json.loads(body)
    except urllib.error.HTTPError as exc:
        code, raw_body, parsed = _parse_http_error(exc)
        return False, {"http_status": code, "raw": raw_body, "json": parsed}
    except Exception as exc:
        return False, {"error": str(exc)}


def http_post_form(url: str, data: dict[str, str], timeout: int = 30) -> tuple[bool, dict[str, Any]]:
    """Executa POST x-www-form-urlencoded retornando (sucesso, payload_ou_erro)."""
    encoded = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=encoded,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return True, json.loads(body)
    except urllib.error.HTTPError as exc:
        code, raw_body, parsed = _parse_http_error(exc)
        return False, {"http_status": code, "raw": raw_body, "json": parsed}
    except Exception as exc:
        return False, {"error": str(exc)}


def check_image_url(url: str, timeout: int = 15) -> dict[str, Any]:
    """Verifica se uma URL HTTPS responde 200 OK com Content-Type image/jpeg e <= 8 MB."""
    if not url.lower().startswith("https://"):
        return {
            "ok": False,
            "status": None,
            "content_type": "",
            "content_length": None,
            "error": "URL deve começar com https://",
        }

    for method, headers in (("HEAD", {}), ("GET", {"Range": "bytes=0-0"})):
        req = urllib.request.Request(url, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status = getattr(resp, "status", 200)
                ctype = (resp.headers.get("Content-Type") or "").lower()
                clen_raw = resp.headers.get("Content-Length")
                clen = int(clen_raw) if clen_raw and clen_raw.isdigit() else None
                is_jpeg = "image/jpeg" in ctype or "image/jpg" in ctype
                size_ok = clen is None or clen <= MAX_IG_IMAGE_BYTES
                err_msg = None
                if status not in (200, 206):
                    err_msg = f"HTTP {status}"
                elif not is_jpeg:
                    err_msg = f"Content-Type inválido para Instagram Feed: '{ctype}' (exige image/jpeg)"
                elif not size_ok:
                    err_msg = f"Arquivo excede 8 MB ({clen} bytes)"
                return {
                    "ok": err_msg is None,
                    "status": status,
                    "content_type": ctype,
                    "content_length": clen,
                    "error": err_msg,
                }
        except urllib.error.HTTPError as exc:
            if method == "HEAD" and exc.code in (403, 405):
                continue
            return {
                "ok": False,
                "status": exc.code,
                "content_type": "",
                "content_length": None,
                "error": f"HTTP {exc.code} (imagem ainda não acessível publicamente; rode git push se for arquivo novo)",
            }
        except Exception as exc:
            return {
                "ok": False,
                "status": None,
                "content_type": "",
                "content_length": None,
                "error": str(exc),
            }
    return {
        "ok": False,
        "status": None,
        "content_type": "",
        "content_length": None,
        "error": "Falha ao consultar URL da imagem",
    }


def validate_caption(caption: str) -> list[str]:
    """Valida limites e regras de marca FINANZASPRO na legenda."""
    errors: list[str] = []
    if not caption or not caption.strip():
        errors.append("Legenda (copy) está vazia.")
    if len(caption) > MAX_IG_CAPTION_LEN:
        errors.append(f"Legenda excede {MAX_IG_CAPTION_LEN} caracteres ({len(caption)}).")
    found_green = [emoji for emoji in GREEN_EMOJIS if emoji in caption]
    if found_green:
        errors.append(f"Contém emoji(s) verde(s) proibido(s): {' '.join(found_green)}")
    return errors


def discover_ig_accounts(token: str, version: str) -> list[dict[str, str]]:
    """
    Descobre contas Instagram Business vinculadas ao token.
    Suporta:
      - Tokens Unified / Instagram Login (`IGAA...`) via `graph.instagram.com/{version}/me`
      - Tokens System User (`EAA...`) via `graph.facebook.com/{version}/me/assigned_instagram_accounts`
      - Tokens User (`EAA...`) via `graph.facebook.com/{version}/me/accounts?fields=instagram_business_account`
    """
    accounts: list[dict[str, str]] = []
    seen_ids: set[str] = set()

    if token.startswith(("IGAA", "IGA")):
        ok, data = http_get_json(
            f"https://graph.instagram.com/{version}/me?"
            + urllib.parse.urlencode({"fields": "id,user_id,username,name", "access_token": token})
        )
        if ok and (data.get("user_id") or data.get("id")):
            ig_id = str(data.get("user_id") or data.get("id"))
            accounts.append(
                {
                    "id": ig_id,
                    "username": str(data.get("username", "")),
                    "name": str(data.get("name", "")),
                    "source": "graph.instagram.com/me",
                }
            )
        return accounts

    # 1) System User: /me/assigned_instagram_accounts
    ok_sys, sys_data = http_get_json(
        f"https://graph.facebook.com/{version}/me/assigned_instagram_accounts?"
        + urllib.parse.urlencode({"fields": "id,username,name", "access_token": token})
    )
    if ok_sys:
        for item in sys_data.get("data", []):
            ig_id = str(item.get("id", ""))
            if ig_id and ig_id not in seen_ids:
                seen_ids.add(ig_id)
                accounts.append(
                    {
                        "id": ig_id,
                        "username": str(item.get("username", "")),
                        "name": str(item.get("name", "")),
                        "source": "me/assigned_instagram_accounts",
                    }
                )

    # 2) User token: /me/accounts?fields=instagram_business_account
    ok_accts, accts_data = http_get_json(
        f"https://graph.facebook.com/{version}/me/accounts?"
        + urllib.parse.urlencode(
            {
                "fields": "id,name,instagram_business_account{id,username,name}",
                "access_token": token,
            }
        )
    )
    if ok_accts:
        for page in accts_data.get("data", []):
            ig_biz = page.get("instagram_business_account")
            if ig_biz and ig_biz.get("id"):
                ig_id = str(ig_biz["id"])
                if ig_id not in seen_ids:
                    seen_ids.add(ig_id)
                    accounts.append(
                        {
                            "id": ig_id,
                            "username": str(ig_biz.get("username", "")),
                            "name": str(ig_biz.get("name", "")),
                            "source": f"page:{page.get('name', '')}",
                        }
                    )

    return accounts


def read_csv_rows(csv_path: Path) -> tuple[list[str], list[dict[str, str]]]:
    """Lê todas as linhas do CSV em UTF-8 preservando cabeçalho."""
    if not csv_path.exists():
        raise FileNotFoundError(f"Arquivo CSV não encontrado: {csv_path}")
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = [dict(row) for row in reader]
    return fieldnames, rows


def atomic_write_csv(csv_path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    """Escreve o CSV de forma atômica preservando UTF-8 e RFC 4180."""
    fd, tmp_name = tempfile.mkstemp(
        prefix=".tmp_hist_", suffix=".csv", dir=str(csv_path.parent)
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        os.replace(tmp_path, csv_path)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        raise


def append_log(entry: dict[str, Any], log_path: Path = DEFAULT_LOG_PATH) -> None:
    """Registra resultado de execução em logs/instagram_publish.log sem expor segredos."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _convert_image_to_ig_jpeg(src: Path, out_path: Path, force_4_5: bool = False) -> tuple[tuple[int, int], tuple[int, int]]:
    """Converte imagem para sRGB JPEG compatível com Instagram (4:5..1.91:1 ou 1080x1350 fixo para carrosséis)."""
    from PIL import Image

    with Image.open(src) as im:
        orig_w, orig_h = im.size
        if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
            rgba = im.convert("RGBA")
            canvas = Image.new("RGB", rgba.size, NAVY_BG_RGB)
            canvas.paste(rgba, mask=rgba.split()[3])
            rgb = canvas
        else:
            rgb = im.convert("RGB")

        w, h = rgb.size
        ratio = w / h

        if force_4_5 or ratio < MIN_IG_RATIO:
            target_w, target_h = 1080, 1350
            if (w, h) == (target_w, target_h):
                final_im = rgb
            else:
                scale = min(target_w / w, target_h / h)
                new_w = max(1, round(w * scale))
                new_h = max(1, round(h * scale))
                resized = rgb.resize((new_w, new_h), Image.Resampling.LANCZOS)
                canvas = Image.new("RGB", (target_w, target_h), NAVY_BG_RGB)
                offset_x = (target_w - new_w) // 2
                offset_y = (target_h - new_h) // 2
                canvas.paste(resized, (offset_x, offset_y))
                final_im = canvas
        elif ratio > MAX_IG_RATIO:
            target_w, target_h = 1080, 566
            scale = min(target_w / w, target_h / h)
            new_w = max(1, round(w * scale))
            new_h = max(1, round(h * scale))
            resized = rgb.resize((new_w, new_h), Image.Resampling.LANCZOS)
            canvas = Image.new("RGB", (target_w, target_h), NAVY_BG_RGB)
            offset_x = (target_w - new_w) // 2
            offset_y = (target_h - new_h) // 2
            canvas.paste(resized, (offset_x, offset_y))
            final_im = canvas
        else:
            if w > 1440:
                scale = 1440 / w
                final_im = rgb.resize(
                    (1440, max(1, round(h * scale))),
                    Image.Resampling.LANCZOS,
                )
            else:
                final_im = rgb

        out_path.parent.mkdir(parents=True, exist_ok=True)
        final_im.save(
            out_path,
            format="JPEG",
            quality=92,
            optimize=True,
            progressive=False,
        )
        return (orig_w, orig_h), final_im.size


def cmd_prepare_images(include_all: bool = False) -> int:
    """
    Converte imagens de ativos_anuncios/ e subpastas de carrosséis (ex.: ativos_anuncios/carrossel_01/*.png)
    para JPEG sRGB 1080x1350 em ativos_instagram/.
    """
    try:
        import PIL  # noqa: F401
    except ImportError:
        print("ERRO: Pillow (PIL) não está instalado. Instale com: pip install Pillow")
        return 1

    if not SOURCE_ASSETS_DIR.exists():
        print(f"ERRO: Pasta de origem não encontrada: {SOURCE_ASSETS_DIR}")
        return 1

    INSTAGRAM_ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    user = os.getenv("GITHUB_USER", "mateusbatistucci01-source")
    repo = os.getenv("GITHUB_REPO", "finanzaspro-ativos")
    branch = os.getenv("GITHUB_BRANCH", "main")

    root_candidates = sorted(
        p for p in SOURCE_ASSETS_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in VALID_IMAGE_EXTS
        and (include_all or p.name.startswith("anuncio_"))
    )
    carousel_dirs = sorted(
        d for d in SOURCE_ASSETS_DIR.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    )

    if not root_candidates and not carousel_dirs:
        print(f"Nenhuma imagem ou pasta de carrossel encontrada em {SOURCE_ASSETS_DIR}")
        return 1

    if root_candidates:
        print(f"=== Preparando imagens individuais JPEG para Instagram ({INSTAGRAM_ASSETS_DIR}) ===")
        print(f"{'Arquivo':<32} {'Orig':<12} {'Final':<12} {'Ratio':<7} {'KB':<8} URL GitHub")
        print("-" * 115)

        for src in root_candidates:
            out_path = INSTAGRAM_ASSETS_DIR / f"{src.stem}.jpg"
            (orig_w, orig_h), (fw, fh) = _convert_image_to_ig_jpeg(src, out_path, force_4_5=False)
            size_kb = out_path.stat().st_size / 1024
            rel = f"ativos_instagram/{out_path.name}"
            raw_url = build_github_raw_url(rel, user, repo, branch)
            print(
                f"{out_path.name:<32} {f'{orig_w}x{orig_h}':<12} "
                f"{f'{fw}x{fh}':<12} {fw/fh:<7.3f} {size_kb:<8.1f} {raw_url}"
            )

    for cdir in carousel_dirs:
        slides = sorted(
            p for p in cdir.iterdir()
            if p.is_file() and p.suffix.lower() in VALID_IMAGE_EXTS
        )
        if not slides:
            continue
        out_subdir = INSTAGRAM_ASSETS_DIR / cdir.name
        print(f"\n=== Preparando carrossel '{cdir.name}' ({len(slides)} slides -> 1080x1350 sRGB) ===")
        slide_urls: list[str] = []
        for src in slides:
            out_path = out_subdir / f"{src.stem}.jpg"
            (orig_w, orig_h), (fw, fh) = _convert_image_to_ig_jpeg(src, out_path, force_4_5=True)
            size_kb = out_path.stat().st_size / 1024
            rel = f"ativos_instagram/{cdir.name}/{out_path.name}"
            raw_url = build_github_raw_url(rel, user, repo, branch)
            slide_urls.append(raw_url)
            print(
                f"  - {out_path.name:<28} {orig_w}x{orig_h} -> {fw}x{fh} ({fw/fh:.3f}, {size_kb:.1f} KB)"
            )
        if len(slide_urls) < MIN_CAROUSEL_ITEMS or len(slide_urls) > MAX_CAROUSEL_ITEMS:
            print(
                f"  [AVISO] Carrossel no Instagram exige entre {MIN_CAROUSEL_ITEMS} e {MAX_CAROUSEL_ITEMS} slides "
                f"(encontrados: {len(slide_urls)})."
            )
        print(f"  Valor pronto para coluna imagem_url no CSV:\n  {';'.join(slide_urls)}")

    print("\nConcluído. Lembre-se de rodar git add/commit/push quando quiser tornar as imagens públicas no GitHub.")
    return 0


def cmd_check(csv_path: Path) -> int:
    """Valida token Meta, descobre/valida IG_USER_ID, permissões e fila Instagram no CSV."""
    token = os.getenv("IG_ACCESS_TOKEN", "").strip()
    ig_user_id = os.getenv("IG_USER_ID", "").strip()
    version = os.getenv("IG_GRAPH_API_VERSION", "v22.0").strip() or "v22.0"
    gh_user = os.getenv("GITHUB_USER", "mateusbatistucci01-source")
    gh_repo = os.getenv("GITHUB_REPO", "finanzaspro-ativos")
    gh_branch = os.getenv("GITHUB_BRANCH", "main")
    base = get_graph_base_url(token, version)

    print("=== Diagnóstico FINANZASPRO — Instagram Publisher ===")
    print(f"API Host    : {base}")
    print(f"Token (.env): {mask_token(token)}")
    print(f"IG_USER_ID  : {ig_user_id or '(não preenchido)'}")
    print(f"GitHub Repo : {gh_user}/{gh_repo} (branch: {gh_branch})")

    if not token:
        print("\n[ERRO] IG_ACCESS_TOKEN não configurado no .env.")
        return 1

    ok_me, me_data = http_get_json(
        f"{base}/me?" + urllib.parse.urlencode({"fields": "id,name", "access_token": token})
    )
    if not ok_me:
        print(f"\n[ERRO] Falha ao validar token em /me: {me_data}")
        return 1

    print(f"\n[OK] Token válido! Identidade Meta: {me_data.get('name')} (ID: {me_data.get('id')})")

    if "graph.facebook.com" in base:
        ok_perms, perms_data = http_get_json(
            f"{base}/me/permissions?" + urllib.parse.urlencode({"access_token": token})
        )
        if ok_perms:
            granted = [
                p["permission"]
                for p in perms_data.get("data", [])
                if p.get("status") == "granted"
            ]
            print(f"[OK] Permissões ativas: {', '.join(granted) if granted else '(nenhuma)'}")

    if not ig_user_id:
        discovered = discover_ig_accounts(token, version)
        if discovered:
            chosen = discovered[0]
            ig_user_id = chosen["id"]
            save_env_var("IG_USER_ID", ig_user_id, DEFAULT_ENV_PATH)
            print(
                f"[AUTO] IG_USER_ID descoberto via {chosen['source']} e salvo no .env: "
                f"@{chosen['username']} ({ig_user_id})"
            )
        else:
            print(
                "\n[AÇÃO NECESSÁRIA] Não foi possível descobrir IG_USER_ID automaticamente.\n"
                "Copie o ID da sua conta Instagram Business no Meta Business Suite\n"
                "(Configurações do Negócio > Contas > Contas do Instagram) e cole em IG_USER_ID= no .env."
            )

    if ig_user_id:
        ok_ig, ig_data = http_get_json(
            f"{base}/{urllib.parse.quote(ig_user_id)}?"
            + urllib.parse.urlencode(
                {
                    "fields": "id,username,name,followers_count,media_count",
                    "access_token": token,
                }
            )
        )
        if ok_ig:
            print(
                f"[OK] Conta Instagram conectada: @{ig_data.get('username')} "
                f"({ig_data.get('name')}, ID: {ig_data.get('id')}, "
                f"seguidores: {ig_data.get('followers_count')}, posts: {ig_data.get('media_count')})"
            )
        else:
            print(f"[AVISO] Não foi possível ler IG_USER_ID={ig_user_id}: {ig_data}")

    if csv_path.exists():
        _, rows = read_csv_rows(csv_path)
        ig_pending = [
            r for r in rows
            if r.get("canal") == "instagram" and r.get("status") == "PENDENTE"
        ]
        print(f"\n=== Fila Instagram em {csv_path.name} ({len(ig_pending)} PENDENTE) ===")
        for r in ig_pending:
            urls = resolve_image_urls(r.get("imagem_url", ""), gh_user, gh_repo, gh_branch)
            kind = f"CAROUSEL({len(urls)})" if len(urls) > 1 else "SINGLE"
            checks = [check_image_url(u) for u in urls]
            ok_count = sum(1 for c in checks if c["ok"])
            if urls and ok_count == len(urls):
                status_txt = f"OK ({ok_count}/{len(urls)} image/jpeg)"
            else:
                first_err = next((c["error"] for c in checks if not c["ok"]), "Sem imagem")
                status_txt = f"PENDENTE PUSH / ERRO ({ok_count}/{len(urls)} OK): {first_err}"
            print(
                f"  - {r.get('id')} | {kind:<11} | {r.get('angulo'):<19} | "
                f"{r.get('titulo', '')[:40]}... | {status_txt}"
            )
    else:
        print(f"\n[AVISO] CSV não encontrado em {csv_path}")

    return 0


def select_target_posts(
    csv_path: Path,
    post_id: str | None,
    limit: int,
    image_path: str | None,
    caption: str | None,
) -> tuple[list[dict[str, str]], list[str] | None, list[dict[str, str]] | None]:
    """Seleciona posts do CSV ou cria item avulso via --image-path + --caption."""
    if image_path or caption:
        if not (image_path and caption):
            raise ValueError("Modo avulso exige --image-path E --caption juntos.")
        return (
            [{"id": "AVULSO", "titulo": "(avulso)", "copy": caption, "imagem_url": image_path}],
            None,
            None,
        )

    fieldnames, all_rows = read_csv_rows(csv_path)
    selected: list[dict[str, str]] = []
    for row in all_rows:
        if row.get("canal") != "instagram":
            continue
        if post_id:
            if row.get("id") == post_id:
                selected.append(row)
                break
        elif row.get("status") == "PENDENTE":
            selected.append(row)
            if len(selected) >= limit:
                break
    return selected, fieldnames, all_rows


def _wait_container_finished(
    base: str,
    container_id: str,
    token: str,
    poll_interval: int = 3,
    poll_timeout: int = 60,
) -> None:
    """Aguarda um container da Meta Graph API atingir status_code == FINISHED."""
    deadline = time.time() + poll_timeout
    last_status: dict[str, Any] = {}
    while time.time() < deadline:
        ok_st, st_res = http_get_json(
            f"{base}/{urllib.parse.quote(container_id)}?"
            + urllib.parse.urlencode({"fields": "status_code,status", "access_token": token})
        )
        if not ok_st:
            raise RuntimeError(f"Erro ao consultar status do container {container_id}: {st_res}")
        last_status = st_res
        status_code = st_res.get("status_code")
        if status_code == "FINISHED":
            return
        if status_code in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Container {container_id} falhou: {st_res}")
        time.sleep(poll_interval)
    raise TimeoutError(
        f"Timeout ({poll_timeout}s) aguardando container {container_id} (último status: {last_status})"
    )


def publish_single_post(
    ig_user_id: str,
    token: str,
    version: str,
    image_url: str,
    caption: str,
    poll_interval: int = 3,
    poll_timeout: int = 60,
) -> dict[str, Any]:
    """Cria container de imagem única, aguarda FINISHED e publica no feed do Instagram."""
    base = get_graph_base_url(token, version)
    ok_create, create_res = http_post_form(
        f"{base}/{urllib.parse.quote(ig_user_id)}/media",
        {
            "image_url": image_url,
            "caption": caption,
            "access_token": token,
        },
    )
    if not ok_create or "id" not in create_res:
        raise RuntimeError(f"Erro ao criar container de mídia: {create_res}")

    creation_id = str(create_res["id"])
    _wait_container_finished(base, creation_id, token, poll_interval, poll_timeout)

    ok_pub, pub_res = http_post_form(
        f"{base}/{urllib.parse.quote(ig_user_id)}/media_publish",
        {
            "creation_id": creation_id,
            "access_token": token,
        },
    )
    if not ok_pub or "id" not in pub_res:
        raise RuntimeError(f"Erro ao publicar container {creation_id}: {pub_res}")

    return {"type": "SINGLE", "creation_id": creation_id, "media_id": str(pub_res["id"])}


def publish_carousel_post(
    ig_user_id: str,
    token: str,
    version: str,
    image_urls: list[str],
    caption: str,
    poll_interval: int = 3,
    poll_timeout: int = 60,
) -> dict[str, Any]:
    """Cria itens de carrossel (2..10 slides), aguarda FINISHED, cria container pai CAROUSEL e publica."""
    if not (MIN_CAROUSEL_ITEMS <= len(image_urls) <= MAX_CAROUSEL_ITEMS):
        raise ValueError(
            f"Carrossel requer entre {MIN_CAROUSEL_ITEMS} e {MAX_CAROUSEL_ITEMS} slides (recebido: {len(image_urls)})."
        )

    base = get_graph_base_url(token, version)
    children_ids: list[str] = []

    # 1) Criar container individual para cada slide
    for idx, url in enumerate(image_urls, start=1):
        ok_item, item_res = http_post_form(
            f"{base}/{urllib.parse.quote(ig_user_id)}/media",
            {
                "image_url": url,
                "is_carousel_item": "true",
                "access_token": token,
            },
        )
        if not ok_item or "id" not in item_res:
            raise RuntimeError(f"Erro ao criar slide {idx}/{len(image_urls)}: {item_res}")
        children_ids.append(str(item_res["id"]))

    # 2) Aguardar todos os slides atingirem FINISHED
    for cid in children_ids:
        _wait_container_finished(base, cid, token, poll_interval, poll_timeout)

    # 3) Criar container pai CAROUSEL
    ok_parent, parent_res = http_post_form(
        f"{base}/{urllib.parse.quote(ig_user_id)}/media",
        {
            "media_type": "CAROUSEL",
            "children": ",".join(children_ids),
            "caption": caption,
            "access_token": token,
        },
    )
    if not ok_parent or "id" not in parent_res:
        raise RuntimeError(f"Erro ao criar container pai CAROUSEL: {parent_res}")

    creation_id = str(parent_res["id"])
    _wait_container_finished(base, creation_id, token, poll_interval, poll_timeout)

    # 4) Publicar carrossel
    ok_pub, pub_res = http_post_form(
        f"{base}/{urllib.parse.quote(ig_user_id)}/media_publish",
        {
            "creation_id": creation_id,
            "access_token": token,
        },
    )
    if not ok_pub or "id" not in pub_res:
        raise RuntimeError(f"Erro ao publicar carrossel {creation_id}: {pub_res}")

    return {
        "type": "CAROUSEL",
        "slides_count": len(children_ids),
        "children_ids": children_ids,
        "creation_id": creation_id,
        "media_id": str(pub_res["id"]),
    }


def cmd_run_queue(args: argparse.Namespace) -> int:
    """Executa --dry-run (padrão) ou --publish sobre a fila ou post avulso."""
    token = os.getenv("IG_ACCESS_TOKEN", "").strip()
    ig_user_id = os.getenv("IG_USER_ID", "").strip()
    version = os.getenv("IG_GRAPH_API_VERSION", "v22.0").strip() or "v22.0"
    gh_user = os.getenv("GITHUB_USER", "mateusbatistucci01-source")
    gh_repo = os.getenv("GITHUB_REPO", "finanzaspro-ativos")
    gh_branch = os.getenv("GITHUB_BRANCH", "main")
    base = get_graph_base_url(token, version)

    try:
        targets, fieldnames, all_rows = select_target_posts(
            csv_path=Path(args.csv),
            post_id=args.id,
            limit=args.limit,
            image_path=args.image_path,
            caption=args.caption,
        )
    except Exception as exc:
        print(f"ERRO: {exc}")
        return 1

    if not targets:
        print("Nenhuma linha 'instagram' elegível encontrada (verifique status=PENDENTE ou --id).")
        return 0

    mode_label = "PUBLISH (REAL)" if args.publish else "DRY-RUN (SIMULAÇÃO)"
    print(f"=== Modo: {mode_label} | Itens selecionados: {len(targets)} ===")

    if args.publish and (not token or not ig_user_id):
        print(
            "ERRO: Para usar --publish, configure IG_ACCESS_TOKEN e IG_USER_ID no arquivo .env.\n"
            "Execute `python instagram_publisher.py --check` para descobrir/validar."
        )
        return 1

    has_error = False
    for item in targets:
        pid = item.get("id", "?")
        caption = item.get("copy", "")
        raw_img_field = item.get("imagem_url", "")
        image_urls = resolve_image_urls(raw_img_field, gh_user, gh_repo, gh_branch)
        is_carousel = len(image_urls) > 1
        cap_errors = validate_caption(caption)

        url_errors: list[str] = []
        if not image_urls:
            url_errors.append("Nenhuma imagem encontrada em imagem_url.")
        elif is_carousel and not (MIN_CAROUSEL_ITEMS <= len(image_urls) <= MAX_CAROUSEL_ITEMS):
            url_errors.append(
                f"Carrossel deve ter entre {MIN_CAROUSEL_ITEMS} e {MAX_CAROUSEL_ITEMS} slides (encontrados: {len(image_urls)})."
            )

        img_checks = [(u, check_image_url(u)) for u in image_urls]
        all_images_ok = bool(img_checks) and all(c["ok"] for _, c in img_checks)

        post_kind = f"CAROUSEL ({len(image_urls)} slides)" if is_carousel else "SINGLE IMAGE"
        print(f"\n--- Item {pid} ({item.get('angulo', 'avulso')}) | Tipo: {post_kind} ---")
        print(f"Título      : {item.get('titulo', '')}")
        for idx, (u, chk) in enumerate(img_checks, start=1):
            label = f"Slide {idx:02d}" if is_carousel else "Imagem URL"
            print(f"{label:<12}: {u}")
            print(f"  Check     : {'OK' if chk['ok'] else 'FALHA'} -> {chk}")
        print(f"Legenda     : {len(caption)}/{MAX_IG_CAPTION_LEN} chars")
        if cap_errors:
            print(f"Check Copy  : FALHA -> {'; '.join(cap_errors)}")
        else:
            print("Check Copy  : OK (sem emojis verdes, dentro do limite)")
        if url_errors:
            print(f"Check Mídia : FALHA -> {'; '.join(url_errors)}")

        target_id = ig_user_id or "<IG_USER_ID>"
        if is_carousel:
            payload_preview = {
                "step_1_items": [
                    {
                        "endpoint": f"POST {base}/{target_id}/media",
                        "body": {
                            "image_url": u,
                            "is_carousel_item": "true",
                            "access_token": mask_token(token),
                        },
                    }
                    for u in image_urls
                ],
                "step_2_parent": {
                    "endpoint": f"POST {base}/{target_id}/media",
                    "body": {
                        "media_type": "CAROUSEL",
                        "children": ",".join(f"<ITEM_ID_{i}>" for i in range(1, len(image_urls) + 1)),
                        "caption": caption[:120] + ("..." if len(caption) > 120 else ""),
                        "access_token": mask_token(token),
                    },
                },
                "step_3_publish": {
                    "endpoint": f"POST {base}/{target_id}/media_publish",
                    "body": {
                        "creation_id": "<PARENT_CREATION_ID>",
                        "access_token": mask_token(token),
                    },
                },
            }
        else:
            payload_preview = {
                "endpoint_step_1": f"POST {base}/{target_id}/media",
                "body_step_1": {
                    "image_url": image_urls[0] if image_urls else "",
                    "caption": caption[:120] + ("..." if len(caption) > 120 else ""),
                    "access_token": mask_token(token),
                },
                "endpoint_step_2": f"POST {base}/{target_id}/media_publish",
                "body_step_2": {
                    "creation_id": "<CREATION_ID>",
                    "access_token": mask_token(token),
                },
            }
        print("Payload API :", json.dumps(payload_preview, ensure_ascii=False, indent=2))

        if not args.publish:
            continue

        if cap_errors or url_errors or not all_images_ok:
            print(f"[BLOQUEADO] Item {pid} não publicado devido a falhas de validação acima.")
            has_error = True
            continue

        try:
            if is_carousel:
                result = publish_carousel_post(
                    ig_user_id=ig_user_id,
                    token=token,
                    version=version,
                    image_urls=image_urls,
                    caption=caption,
                )
            else:
                result = publish_single_post(
                    ig_user_id=ig_user_id,
                    token=token,
                    version=version,
                    image_url=image_urls[0],
                    caption=caption,
                )
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[PUBLICADO] {pid} ({result['type']}) -> media_id={result['media_id']} em {now_str}")

            if fieldnames is not None and all_rows is not None and pid != "AVULSO":
                for row in all_rows:
                    if row.get("id") == pid:
                        row["data_hora"] = now_str
                        row["status"] = "PUBLICADO"
                        break
                atomic_write_csv(Path(args.csv), fieldnames, all_rows)

            append_log(
                {
                    "timestamp": now_str,
                    "id": pid,
                    "status": "PUBLICADO",
                    **result,
                    "image_urls": image_urls,
                }
            )
        except Exception as exc:
            has_error = True
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[ERRO] Falha ao publicar {pid}: {exc}")
            append_log(
                {
                    "timestamp": now_str,
                    "id": pid,
                    "status": "ERRO",
                    "error": str(exc),
                    "image_urls": image_urls,
                }
            )

    return 1 if has_error else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Publicador Instagram FINANZASPRO (imagem única e carrossel 2-10 slides via Meta Graph API)."
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="Valida token, descobre/valida IG_USER_ID e verifica fila CSV.")
    mode.add_argument("--prepare-images", action="store_true", help="Gera JPEGs 1080x1350 em ativos_instagram/ (inclui pastas de carrossel).")
    mode.add_argument("--dry-run", action="store_true", help="Simula publicação sem chamar endpoints de escrita (padrão).")
    mode.add_argument("--publish", action="store_true", help="Publica de fato no Instagram (single ou carrossel) e atualiza o CSV.")

    parser.add_argument("--all-images", action="store_true", help="Com --prepare-images, converte todas as imagens soltas de ativos_anuncios/.")
    parser.add_argument("--csv", default=str(DEFAULT_CSV_PATH), help="Caminho para historico_grupos.csv.")
    parser.add_argument("--id", help="Publicar/simular um ID específico (ex.: FP-013).")
    parser.add_argument("--limit", type=int, default=1, help="Quantidade máxima de posts da fila (padrão: 1).")
    parser.add_argument("--image-path", help="URL(s) ou caminho(s) separados por ';' ou '|' (ou pasta de slides) para post avulso.")
    parser.add_argument("--caption", help="Legenda para post avulso.")
    return parser


def main() -> int:
    load_env(DEFAULT_ENV_PATH)
    parser = build_parser()
    args = parser.parse_args()

    if args.check:
        return cmd_check(Path(args.csv))
    if args.prepare_images:
        return cmd_prepare_images(include_all=args.all_images)
    return cmd_run_queue(args)


if __name__ == "__main__":
    raise SystemExit(main())
