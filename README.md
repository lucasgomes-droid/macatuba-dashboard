# Dashboard Operacional / BI — Macatuba

Repositório do dashboard operacional/BI da unidade Macatuba (ICC), alimentado
pelos dados reais do AppSheet "ICC - Gestão Operacional".

## Por que a arquitetura mudou (histórico rápido)

1. Primeira tentativa: scraper Playwright rodando no meu ambiente de nuvem →
   bloqueado pela rede do próprio ambiente (não alcança appsheet.com).
2. Segunda tentativa: rodar esse mesmo scraper no computador do usuário →
   recusado ("TEM QUE SER WEB N LOCAL").
3. Arquitetura atual: nada roda local nem depende de guardar senha/sessão
   num servidor. A coleta usa a extensão Claude in Chrome, já logada na
   conta real do usuário, disparada por uma tarefa agendada — o mesmo
   processo manual que gerou a análise técnica (fixtures/), só que
   repetido automaticamente. Cada execução grava um JSON atualizado neste
   repositório; o site (GitHub Pages) lê esse JSON.

```
Tarefa agendada (a cada N min)
    |
    v
Sessão do Claude usa a extensão Chrome do usuário (já logada)
para ler Pedidos / Recebimentos / Veículos no AppSheet
    |
    v
Normaliza (scraper/parser.py) -> grava data/latest.json
    |
    v
git commit + push (token do usuário, escopo repo)
    |
    v
GitHub Pages serve o frontend, que lê data/latest.json
e atualiza a tela a cada 10s (sem reload)
```

## Limitação real de intervalo

O agendador de tarefas usado aqui normalmente não aceita menos que ~1h em
alguns planos, e mesmo quando aceita minutos, cada execução tem custo (abre
sessão, navega, lê 3 telas). Por isso o intervalo real vai ficar mais perto
de alguns minutos a algumas dezenas de minutos, não 10 segundos — o mesmo
compromisso já combinado antes (Etapa 1, seção "Decisões confirmadas").

## Estrutura

- `backend/db.py` — schema SQLite de referência (uso local/futuro; a versão
  "web" grava direto em JSON, ver `data/latest.json`).
- `scraper/parser.py` — normalização dos campos (kg→t, limpeza), testada
  contra dados reais (`fixtures/test_parser.py`).
- `fixtures/` — dados reais capturados manualmente do AppSheet, usados como
  base de teste (não são dados inventados).
- `data/latest.json` — snapshot mais recente, atualizado pela tarefa
  agendada.
- `docs/` — frontend estático publicado via GitHub Pages.
