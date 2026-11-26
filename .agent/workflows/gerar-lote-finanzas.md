---
description: Lê as últimas linhas de historico_grupos.csv e adiciona 12 novas entradas inéditas em espanhol neutro (status PENDENTE) para abastecer o cenário Make.com do FINANZASPRO.
---

# Workflow: `/gerar-lote-finanzas`

Sempre que este workflow for acionado, execute os passos abaixo em ordem para abastecer `historico_grupos.csv` com **12 novas linhas inéditas** prontas para a distribuição multicanal (Make.com + `instagram_publisher.py`: Pinterest, Facebook Page, Telegram Grupos e Instagram).

---

## Passo 1 — Auditoria do Histórico (Anti-Repetição)

1. Leia `historico_grupos.csv` (priorizando as últimas 36 linhas, ou o arquivo inteiro se tiver menos de 100 linhas).
2. Extraia e registre internamente:
   - O **último `id`** existente (ex.: `FP-012`) para gerar os próximos 12 IDs sequenciais (`FP-013` a `FP-024`, sempre com 3 dígitos `FP-XXX`).
   - O **prefixo de storage atual** em `imagem_url` (ex.: se o usuário já trocou `https://SEU_STORAGE` por `https://finanzasprooficial.vercel.app`, herde automaticamente esse domínio real nas novas linhas; caso contrário, mantenha `https://SEU_STORAGE`).
   - Todos os `titulo`, frases de abertura (`copy`), micro-momentos e ângulos usados nas últimas 24–36 linhas para garantir **zero repetição de gancho, título ou cena cotidiana**.

---

## Passo 2 — Inventário Dinâmico de `./ativos/`, `./ativos_anuncios/` e `./ativos_instagram/`

1. Liste os arquivos reais de imagem (`.png`, `.jpg`, `.jpeg`, `.webp`) existentes em `./ativos/`, `./ativos_anuncios/` e `./ativos_instagram/`.
2. Ignore arquivos que não sejam imagens estáticas (`.mp4`, `.exe`, `.pdf`, etc.) e ignore folhas de referência interna com barras laterais (como `persona - mateo rivas referencia visual corpo.jpg`, salvo se tiver sido substituída/recortada).
3. Verifique as regras específicas por canal:
   - **`telegram_grupos`**: **nunca associe imagem > 5 MB** (limite rígido da API do Telegram para envio por URL).
   - **`instagram`**: **use exclusivamente arquivos `.jpg`/`.jpeg` compatíveis** (preferencialmente `ativos_instagram/*.jpg` em 4:5 / `1080x1350`, ≤ 8 MB, proporção entre `0.80` e `1.91`; **nunca associe `.png`**), mantendo o prefixo GitHub raw `https://raw.githubusercontent.com/mateusbatistucci01-source/finanzaspro-ativos/main/`.
4. Codifique todos os nomes de arquivo em **RFC 3986** (`%20` para espaços, `%C3%A7` para `ç`, `%C3%A3` para `ã`, preservando exatamente o nome real do arquivo).

---

## Passo 3 — Diretrizes Obrigatórias de Copy, Psicologia e Marca

Aplique rigorosamente as regras das skills `@boring-marketing-direct-response-copy` e `@creative-psychology-hooks`:

1. **Idioma — Espanhol Neutro Panhispânico:**
   - Use **tuteo padrão (`tú`)** natural para Colômbia, México, Espanha e LATAM (`tienes`, `puedes`, `organiza`, `registra`, `mira`, `descubre`).
   - **Proibido:** voseo argentino (`registrá`, `armá`, `mirá`, `entendés`, `acá`), `vosotros` (`tenéis`, `podéis`) e gírias ou moedas restritas a um único país (`lana`, `plata`, `chamba`, `guita`, `tío`, `domicilio` isolado). Prefira termos universais (`sueldo`, `ingresos`, `dinero`, `pedidos de comida`, `resumen bancario`, `teléfono`, `planificador`).
2. **Identidade Visual & Textual (Zero Verde):**
   - Paleta FINANZASPRO: `#0A192F`, `#112240`, `#3B82F6`, `#FFFFFF`, `#E2E8F0` — **zero verde**.
   - **Proibido usar emojis verdes** (círculo verde, check verde, coração verde, notas verdes, gráfico com barra verde). Use apenas marcadores neutros/azuis como `🔹`, `👇`, `•`, `→`.
3. **Claim Gate (Regra Rígida de Veracidade):**
   - Use **somente fatos reais verificados do FINANZASPRO**:
     - Planificador financeiro digital pronto para uso no **Google Sheets** (`Hacer una copia` na própria conta Google do cliente; dados financeiros ficam privados na conta do usuário; funciona em computador ou telefone; sem exigir conhecimentos prévios ou criação de fórmulas).
     - Abas reais existentes: `Visión General` (saldo do mês, receitas, despesas, taxa de poupança, patrimônio líquido, dívida total, contas a pagar/vencidas, saúde financeira e gráficos), `Ingresos`, `Gastos`, `Presupuesto` (Regra 50/30/20 automática + limites e alertas por categoria), `Deudas` (organização e comparação de métodos de pagamento), `Metas` (`Fondo de emergencia` com valor e data), `Pagos Fijos`, `Patrimonio`, `Resumen Anual` (12 meses lado a lado), `Alertas`.
     - Recursos complementares disponíveis nos planos Completo/Premium: Manual de usuário, E-book Interactivo (5 capítulos + atividades + plano de 30 dias), Kit de Desafíos de Ahorro e Guía de Ahorro Inteligente.
   - **Proibido:** inventar número de clientes/vendas, fabricar depoimentos fictícios, criar urgência falsa ("últimos cupos", "solo por hoy") ou prometer ganhos financeiros garantidos. Cenários numéricos cotidianos (ex.: gastar 4 dólares/dia) devem ser claramente apresentados como exemplo de cálculo.
   - **Proibido clichês de IA:** "en el mundo actual", "lleva tus finanzas al siguiente nivel", "revoluciona", "desbloquea", "no busques más", "oferta imperdible", "descubre el secreto".
4. **Diversidade Psicológica (`@creative-psychology-hooks`):**
   - Trace mentalmente a cadeia **TEEP** (Thought → Emotion → Expression → Physiology) em cada gancho.
   - Distribua as 12 entradas nos **4 quadrantes de Valência/Intensidade** (exatamente **3 por quadrante**: Negativo/Alta, Negativo/Baixa, Positivo/Alta, Positivo/Baixa).
   - Alterne os **mecanismos Baader** (Pattern interrupt, Open loop, Direct claim, Identity call-out — nenhum mecanismo acima de 35% do lote).
   - Use **12 micro-momentos concretos e inéditos** (diferentes dos encontrados no Passo 1).
   - Para `facebook_page`, garanta **Promise Match** com a landing page `finanzasprooficial.vercel.app` ("No es falta de ingresos. Es falta de claridad.", organização de receitas, gastos, dívidas e metas no Google Sheets sem conhecimentos prévios).

---

## Passo 4 — Estrutura Exata das 12 Novas Linhas

Colunas obrigatórias (9 colunas exatas):
`id,data_hora,canal,angulo,titulo,copy,imagem_url,link_hotmart,status`

1. **Alternância de `canal` (3 ciclos exatos de 4 canais = 12 linhas):**
   - `pinterest` → `facebook_page` → `telegram_grupos` → `instagram` (repetido 3 vezes).
2. **Alternância dos 5 `angulo`:**
   - Cobrir todos os 5 ângulos: `gastos hormiga`, `regra 50/30/20`, `controle de dívidas`, `fundo de emergência`, `planilha dashboard` (2 a 3 ocorrências cada, **sem repetir o mesmo ângulo no mesmo canal dentro do lote** e variando a combinação em relação ao lote anterior).
3. **Links obrigatórios em `link_hotmart`:**
   - `pinterest`, `telegram_grupos` e `instagram` (usado no DM automático do funil de comentários) → `https://go.hotmart.com/D108359728X`
   - `facebook_page` → `https://finanzasprooficial.vercel.app/?utm_source=organico_make`
4. **Limites rígidos de API e formato por canal:**
   - **`pinterest`**: `titulo` ≤ **85 caracteres** (limite API: 100); `copy` ≤ **450 caracteres** (limite API: 500), com 3–4 hashtags neutras no final e CTA direto para o link.
   - **`facebook_page`**: `copy` entre **450 e 850 caracteres**, parágrafos curtos escaneáveis no celular, começando com o gancho principal e encerrando com chamada para o link abaixo (**não inserir a URL dentro de `copy`**, pois o Make concatena `link_hotmart`).
   - **`telegram_grupos`**: `titulo` + `copy` + `link_hotmart` ≤ **900 caracteres** no total (limite rígido API `sendPhoto`: **1.024 caracteres**). Tom de valor real/comunidade (não-spam) pronto para repasse em 15 segundos para grupos públicos externos.
   - **`instagram`**: `copy` entre **450 e 1.100 caracteres** (limite API: 2.200), gancho forte nos primeiros **125 caracteres**, tom analítico do Mateo Rivas, parágrafos curtos, **sem URL dentro do texto**, **zero emojis verdes**, 5–8 hashtags neutras no final e **CTA de gatilho por comentário** (em vez de "link na bio") variando conforme o tema do post entre as 5 palavras-chave oficiais:
     - `PLANILLA` (foco na ferramenta/planilha)
     - `SISTEMA` (foco em organização e automação financeira)
     - `CONTROL` (foco em controle de gastos e salário)
     - `METODO` (foco em passo a passo e regra financeira)
     - `QUIERO` (foco em oferta direta)
     - Fechamento padrão: *"Comenta **PALAVRA_CHAVE** (o **PALAVRA_SECUNDARIA**) aquí abajo y te envío el acceso directo por mensaje privado 👇"*
     - `imagem_url`: obrigatoriamente `.jpg`/`.jpeg` (preferencialmente `ativos_instagram/*.jpg`, `1080x1350`, proporção 4:5 a 1.91:1). Para **carrosséis (2 a 10 slides)**, informe as URLs separadas por `;` (ou o caminho da subpasta em `ativos_instagram/carrossel_XX`).
5. **Campos de controle:**
   - `data_hora`: vazio (`""`).
   - `status`: `PENDENTE`.

---

## Passo 5 — Append Seguro, Validação e Resumo

1. **Nunca sobrescreva** linhas existentes de `historico_grupos.csv`. Faça apenas **append** das 12 novas linhas em **UTF-8** com escapamento **RFC 4180** (campos com vírgulas, quebras de linha ou aspas entre `"..."`, escapando aspas internas como `""`).
2. Execute uma validação rápida (Python `csv.DictReader` ou PowerShell `Import-Csv -Encoding UTF8`) checando:
   - Exatamente 9 colunas em todas as linhas;
   - Incremento de +12 linhas válidas e IDs únicos;
   - Limites de caracteres por canal (`pinterest`, `facebook_page`, `telegram_grupos` e `instagram`);
   - Links exatos por canal e existência local de cada arquivo decodificado (`./ativos/`, `./ativos_anuncios/` ou `./ativos_instagram/`);
   - Para `instagram`: cada URL em `imagem_url` (separadas por `;` ou `|` no caso de carrossel de 2 a 10 slides) terminando em `.jpg`/`.jpeg` (nunca `.png`), proporção entre `0.80` e `1.91`, sem URLs dentro de `copy` e contendo CTA com uma das 5 palavras-chave oficiais (`PLANILLA`, `SISTEMA`, `CONTROL`, `METODO`, `QUIERO`);
   - Ausência de emojis verdes e de títulos duplicados.
3. Apresente ao usuário:
   - Tabela resumida das 12 novas linhas (`id`, `canal`, `angulo`, `titulo`, imagem associada);
   - Checagem de cobertura psicológica (mecanismos Baader + quadrantes Valência/Intensidade);
   - Lembrete prático para copiar/colar as 12 novas linhas ao final da aba `fila_publicacao` no Google Sheets (mantendo o cenário Make abastecido por mais 48 horas).

---

## Passo 6 — Fluxo de Carrossel Instagram (6 Slides `1080x1350` via Paper MCP)

### Grade Diária Oficial do Instagram (`@mateorivas_finanzas` — Horário de Brasília / `America/Sao_Paulo`)
- **14h30 — Reel (Topo de Funil):** descoberta, retenção rápida e alcance orgânico frio.
- **18h30 — Carrossel 6 Slides (Meio de Funil):** aprofundamento analítico, prova visual da planilha FinanzasPro e conversão para DM via gatilho de comentário (`PLANILLA`, `SISTEMA`, `CONTROL`, `METODO` ou `QUIERO`).

Sempre que o usuário solicitar um **carrossel para o Instagram** (`@mateorivas_finanzas`), execute este pipeline integrado ao **Paper Desktop MCP** (`file/01M8B6M4S34PMQ461SSV4CSX8H` em `http://127.0.0.1:29979/mcp`):

1. **Sistema Modular de 3 Variantes Cromáticas (Tokens no Paper — ZERO tons de verde):**
   Alterne entre as variantes oficiais nos lotes para manter variedade visual sem sair da marca:
   - **Variante A — Editorial Dark (`Template 01 — Editorial Dark (Mateo)`):** fundo `#0A192F` (`--fp-dark-bg`), cards `#112240` (`--fp-dark-surface`) com borda `1px solid rgba(59, 130, 246, 0.25)`, destaque `#3B82F6` (`--fp-dark-accent`), texto `#F8FAFC` (`--fp-dark-text`). Ideal para carrosséis com foto do Mateo Rivas.
   - **Variante B — Clean Fintech Light (`Template 02 — Clean Fintech Light (Bento)`):** fundo `#F8FAFC` (`--fp-light-bg`), cards `#FFFFFF` (`--fp-light-surface`) com borda `#E2E8F0` (`--fp-light-border`), títulos `#0A192F` (`--fp-light-ink`), destaque `#2563EB` (`--fp-light-accent`). Ideal para carrosséis educativos, bento grids e gráficos.
   - **Variante C — High-Contrast Alert (Tokens `--fp-alert-*`):** fundo `#060D1A` (`--fp-alert-bg`), cards `#0F172A` (`--fp-alert-surface`), destaques `#38BDF8` (`--fp-alert-cyan`) e alertas numéricos `#F59E0B` (`--fp-alert-amber`). Ideal para choques sobre perda de dinheiro e dívidas.
   - **Acabamento obrigatório:** grid sutil de fundo (`64px`), tipografia `72px`–`96px` bold/extrabold com `tabular-nums`, badge de categoria no topo (`ANÁLISIS FINANZASPRO • 01/06`), cards bento/glassmorphism e indicador de deslize elegante no rodapé.
2. **Onde Substituir os Slots de Imagem:**
   - **Slot Foto Mateo Rivas (Slide 1 do Template 01):** substituir a imagem mascarada com vinheta inferior por fotos locais salvas em `ativos_anuncios/banco_mateo/`.
   - **Slot Mockup da Planilha (Slide 5 de ambos os templates):** substituir a tela dentro da janela/bezel pela captura real correspondente em `./ativos/` (`demonstração planilha - vision geral.jpeg`, `presupuesto.jpeg`, `ingresos.jpeg` ou `resumen anual.jpeg`).
3. **Engenharia de Retenção — Roteiro Obrigatório de 6 Slides (Espanhol Neutro, tom analítico do Mateo Rivas):**
   - **Slide 1 (Capa / Gancho de Choque + Foto/Visual):** promessa específica ou erro financeiro caro + gatilho de curiosidade no rodapé (*"La mayoría comete el error del slide 3 →"* ou *"Casi nadie detecta la fuga del slide 4 →"*).
   - **Slide 2 (O Diagnóstico / Espelho):** números reais em dólares (antes vs. depois ou cronologia do mês) gerando identificação imediata.
   - **Slide 3 (A Quebra de Crença):** por que anotar tudo à mão, usar apps cheios de menus ou abrir planilhas em branco falha na semana 2.
   - **Slide 4 (O Mecanismo / Passo a Passo Visual):** gráfico nativo ou bento grid limpo mostrando a lógica na prática (50/30/20 ou corte de vazamentos).
   - **Slide 5 (A Prova Tangível — Mockup da Planilha):** print real da Planilha FinanzasPro dentro da moldura com callouts apontando para os resultados automáticos.
   - **Slide 6 (CTA de Conversão Irresistível):** destaque visual gigante para a palavra-chave do post (`PLANILLA`, `SISTEMA`, `CONTROL`, `METODO` ou `QUIERO`) + fechamento direto: *"Comenta **[PALABRA_CLAVE]** y te envío el acceso directo por DM ahora mismo 👇"*.
4. **Montagem, Exportação e Fila:**
   - Monte ou duplique os 6 slides no Paper via MCP (`create_artboard` / `write_html`) em `1080x1350`.
   - Exporte os 6 slides em `ativos_anuncios/carrossel_XX/slide_01.png` ... `slide_06.png` (ou direto em JPEG) e rode `python instagram_publisher.py --prepare-images` para gerar os JPEGs sRGB `1080x1350` (`<= 8 MB`) em `ativos_instagram/carrossel_XX/`.
   - Adicione a linha na fila de `historico_grupos.csv` (`canal=instagram`, `imagem_url` com as 6 URLs raw do GitHub separadas por `;`, `link_hotmart=https://go.hotmart.com/D108359728X`, `status=PENDENTE`) e valide com `python instagram_publisher.py --dry-run`.
