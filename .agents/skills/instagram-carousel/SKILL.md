---
name: instagram-carousel
description: >
  Cria carrosséis editoriais de 6 slides (1080x1350 JPEG) para o @mateorivas_finanzas
  (FinanzasPro) usando HTML/CSS + Playwright/Chromium headless via gerador_carrosseis.py.
  Aplica rigorosamente a paleta azul-marinho sem verde, espanhol neutro (tuteo),
  biblioteca visual editorial (assets/biblioteca_visual/), prova real da planilha
  Visión General no Slide 5 e CTA de comentário no Slide 6.
---

# Instagram Carousel Generator — FinanzasPro (`@mateorivas_finanzas`)

Baseado em `marcolang/Marketing-Skills` (`instagram-carousel`, commit `bb848026613e84f03b2d7d39c30b4f031f8cf338`) e adaptado com as travas obrigatórias de marca, retenção e publicação automática da **FinanzasPro**.

---

## 1. Travas Obrigatórias da Marca FinanzasPro (NÃO NEGOCIÁVEIS)

1. **Identidade & Persona Fixas:**
   - **Marca:** FinanzasPro
   - **Persona / Handle:** Mateo Rivas — `@mateorivas_finanzas`
   - **Tom:** Analítico, direto, empático e prático (sem sensacionalismo, sem jargão bancário, sem clichês de IA).
2. **Paleta Oficial — ESTRITAMENTE SEM VERDE:**
   ```css
   --fp-navy:    #0A192F; /* Fundo principal e overlay escuro de alto contraste */
   --fp-surface: #112240; /* Cards, blocos bento, molduras glassmorphism */
   --fp-blue:    #3B82F6; /* Destaque principal, barra de progresso, CTA, números */
   --fp-white:   #FFFFFF; /* Títulos e textos principais */
   --fp-slate:   #E2E8F0; /* Subtítulos, corpo de texto, divisores suaves */
   ```
   - **ZERO VERDE:** É estritamente proibido usar qualquer tom de verde em fundos, badges, gráficos, ícones ou emojis (`🟢`, `✅`, `💚`, `💵`, `💹`, `🟩`, `🍏`). Utilize apenas marcadores azuis/neutros (`🔹`, `•`, `→`, `👇`).
3. **Idioma — Espanhol Neutro Panhispânico (*tuteo*):**
   - Usar exclusivamente **tuteo (`tú`)** natural para México, Colômbia, Espanha e toda LATAM (`tienes`, `puedes`, `organiza`, `registra`, `mira`, `desliza`, `comenta`).
   - **Proibido:** voseo argentino (`mirá`, `registrá`, `armá`, `acá`), `vosotros` (`tenéis`, `podéis`) e gírias locais (`plata`, `lana`, `chamba`, `guita`, `tío`).
4. **Formato Técnico Obrigatório (Meta Graph API / Instagram Feed):**
   - Exatamente **6 slides verticais `1080×1350` (4:5)** por carrossel.
   - Exportação em **JPEG sRGB** (`quality=92`, `progressive=False`, **≤ 8 MB** por slide).
   - Estrutura de pastas: `ativos_instagram/carrossel_XX/slide_01.jpg` até `slide_06.jpg`.
5. **Claim Gate (Regra Rígida de Veracidade):**
   - Citar apenas recursos reais da FinanzasPro em Google Sheets (`Hacer una copia` privada na conta do usuário, sem precisar saber fórmulas, uso no celular ou computador; abas reais `Visión General`, `Ingresos`, `Gastos`, `Presupuesto` 50/30/20, `Deudas`, `Metas`, `Pagos Fijos`, `Patrimonio`, `Resumen Anual`, `Alertas`).
   - Proibido inventar números de clientes/vendas, depoimentos fictícios, urgência falsa ou promessas de ganho garantido. Cenários numéricos são sempre apresentados como exemplos ilustrativos.

---

## 2. Arquitetura Obrigatória dos 6 Slides

| Slide | Papel Estratégico | Fundo / Visual | Indicador Rodapé |
|---|---|---|---|
| **01** | **Capa / Gancho de Choque** — promessa específica, número ou dor real que para o scroll em < 1s | Foto full-bleed de `assets/biblioteca_visual/` (alternar Mateo e cenas/metáforas entre carrosséis) + overlay `#0A192F` de alto contraste | Barra 1/6 + **`Desliza →`** |
| **02** | **Diagnóstico / Espelho** — comparação concreta (antes vs. depois ou cronologia do mês) gerando identificação imediata | Foto editorial de `assets/biblioteca_visual/` com overlay `#0A192F` denso + cards `#112240` | Barra 2/6 + **`Desliza →`** |
| **03** | **Quebra de Crença** — 3 motivos claros pelos quais métodos manuais/notas soltas/apps complexos falham antes da semana 2 | Foto editorial com overlay `#0A192F` + 3 blocos numerados `01` `02` `03` (`white-space: nowrap`) | Barra 3/6 + **`Desliza →`** |
| **04** | **Mecanismo / Passo a Passo Visual** — barra visual 50/30/20 ou fluxo em 3 etapas + 3 cards bento `#112240` | Fundo `#0A192F` com textura/foto sutil + barra em tons de `#3B82F6` (zero verde) + 3 cards | Barra 4/6 + **`Desliza →`** |
| **05** | **Prova Visual Real da Planilha** — demonstração tangível sem promessas vazias | Print real da aba **`Visión General`** (`ativos/demonstração planilha - vision geral.jpeg`) dentro de moldura `#112240` + 3 callouts reais | Barra 5/6 + **`Desliza →`** |
| **06** | **CTA de Conversão por Comentário** — gatilho de DM automatizado | Foto editorial com overlay `#0A192F` + glow `#3B82F6` + botão gigante com palavra-chave oficial | Barra 6/6 (100%) — **SEM `Desliza →`** (mostrar `Comenta <PALABRA> 👇`) |

### Palavras-Chave Oficiais de CTA (Slide 6 + Legenda)
Escolha uma palavra-chave principal alinhada ao tema (e uma secundária opcional):
- `PLANILLA` — foco na ferramenta/planilha em Google Sheets
- `CONTROL` — foco em controle de gastos e salário
- `SISTEMA` — foco em organização completa e reserva/metas
- `METODO` — foco em passo a passo, dívidas e regra 50/30/20
- `QUIERO` — foco em acesso rápido / oferta direta

---

## 3. Biblioteca Visual Editorial (`assets/biblioteca_visual/`)

Todas as imagens em `assets/biblioteca_visual/` já estão em alta resolução vertical (`1792×2400`) e harmonia cromática `#0A192F` / `#3B82F6`:

- **Fotos do Mateo Rivas (5):**
  - `01_mateo.jpg` — Mateo no carro à noite olhando o celular
  - `02_mateo.jpg` — Mateo na mesa fazendo gesto de 3 dedos (ideal para 3 blocos / 3 erros / 50-30-20)
  - `03_mateo.jpg` — Mateo na varanda urbana com café (calma e controle financeiro)
  - `mateo_4.jpg` — Mateo de blazer em estúdio azul-marinho apontando/apresentando (ideal para CTA / apresentações)
  - `mateo_5.jpg` — Mateo na galeria comercial segurando cartão preto (consumo, cartão, dívidas)
- **Cenas Humanas & Metáforas Visuais (5):**
  - `_06A Dor Real do Casal.jpg` — Casal à noite preocupado diante de contas, cartão, calculadora e notebook
  - `7_gastoshormiga.jpg` — Café preto, sacola delivery, celular contactless com ícone azul e cartão preto
  - `08_cartãodecredito.jpg` — Cartão preto em labirinto de concreto sob feixe de luz azul
  - `09_celularclareza.jpg` — Mão segurando celular com dashboard azul limpo
  - `10_horizontedaliberdade.jpg` — Janela azul noturna, caderno fechado e laptop (paz e liberdade financeira)
- **Prova Visual Obrigatória (Slide 5):**
  - `ativos/demonstração planilha - vision geral.jpeg`

---

## 4. Regras Técnicas de Geração HTML e Exportação

1. **Sempre gerar HTML via Python (`Path.write_text`)** — nunca via shell heredoc/echo (evita corrupção de strings base64 com `$` ou crases).
2. **Sempre embutir imagens via `data:image/jpeg;base64,...`** em tags `<img>` com `object-fit: cover` (nunca caminhos relativos e nunca `background: url(...)` inline gigante).
3. **Contraste Garantido em Imagens:** Todo slide com fotografia usa camada overlay `linear-gradient` em `rgba(10, 25, 47, ...)` (`#0A192F`) garantindo contraste AAA para `#FFFFFF` e `#E2E8F0`, preservando o enquadramento do rosto do Mateo (`object-position: center 18%`).
4. **Anti-Quebra Tipográfica:** Badges, percentuais e números de etapa (`01`, `02`, `03`, `50/30/20`) devem usar `white-space: nowrap; flex-shrink: 0; font-variant-numeric: tabular-nums`.
5. **Renderização em Lote via `gerador_carrosseis.py`:**
   ```bash
   python gerador_carrosseis.py --spec lotes/lote_carrosseis_fp018_fp022.json
   ```
   - O script renderiza automaticamente todos os 6 slides em `1080×1350` via Playwright/Chromium headless (ou Chrome/Edge headless local como fallback automático), converte via Pillow para JPEG sRGB (`<= 8 MB`, `progressive=False`) em `ativos_instagram/carrossel_XX/slide_01.jpg` .. `slide_06.jpg`, e executa validação automática (dimensões, tamanho, ausência de verde, `Desliza →` nos slides 1–5 e palavra-chave válida no slide 6).
6. **Fila e Publicação Automática:**
   - Cadastrar o carrossel no `historico_grupos.csv` (`canal=instagram`, 6 URLs raw do GitHub separadas por `;`, `link_hotmart=https://go.hotmart.com/D108359728X`, `status=PENDENTE`).
   - Validar com `python instagram_publisher.py --dry-run --id <ID>`.
   - O workflow `.github/workflows/publicar_carrossel_18h30.yml` publica automaticamente o próximo `CAROUSEL` `PENDENTE` todos os dias às **18h30 (Brasília)**.
