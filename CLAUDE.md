# Rodanegócios — guia para o Claude Code

Plataforma web para organizar **rodadas de negócios** entre empresas (compradoras e vendedoras):
cadastro de empresas e interesses, eventos, geração automática de rodadas/mesas, agendas e relatórios
para impressão. Desenvolvedor: Eloi. Responda sempre em português. Visão geral e pontos de atenção:
ver `README.md`.

## Stack e comandos

- Python + Django 6.0, Django REST Framework + `simplejwt`, `django-localflavor` (CNPJ), WhiteNoise, gunicorn.
- Banco: SQLite local (`db.sqlite3`); **produção = Postgres do Railway** via `DATABASE_URL` (`dj-database-url`).
- Windows, VS Code, ambiente virtual em `venv/` (Claude Code roda em Git Bash):
  - Rodar: `venv/Scripts/python manage.py runserver`
  - Verificar: `venv/Scripts/python manage.py check` e `venv/Scripts/python manage.py makemigrations --check --dry-run`
  - Testes: `venv/Scripts/python manage.py test`
- Segredos no `.env` — nunca ler, exibir ou commitar. Variáveis lidas: `SECRET_KEY`, `DEBUG`, `DATABASE_URL`.
  O `settings.py` **não** carrega o `.env`; só lê o ambiente do processo.

## Estrutura

- `rodanegocios/` — settings, urls raiz, wsgi/asgi.
- `core/` — app principal: models, views (`views.py`, ~2100 linhas), forms, templates, `templatetags/`,
  `services/matchmaking.py` (geração das rodadas), `utils.py`, `middleware.py`.
- `api/` — API REST somente leitura (agendas, empresas, eventos, rodadas, mesas) + `/api/token/` (JWT).
- `dados*.json`, `db.sqlite3` — cargas antigas versionadas; **não são usados em produção**.

## Regras do projeto (não quebrar)

- Acesso: `RodanegociosProtectionMiddleware` exige login e a permissão `core.pode_acessar_rodanegocios`
  (rotas livres: login, esqueci/redefinir senha, troca de senha, `/admin`, `/api`).
- **A API exige JWT** (`REST_FRAMEWORK` em `settings.py`, `IsAuthenticated` por padrão). Só `/api/token/` e
  `/api/token/refresh/` ficam livres. Não reabrir a API sem pedido explícito.
- `RelacionamentoEmpresa`: `empresa_a` deve ser COMPRADOR e `empresa_b` VENDEDOR; o matchmaking evita
  pares com relação prévia ou que já se encontraram.
- `core/services/matchmaking.py` é sensível: qualquer mudança no algoritmo exige teste antes e depois.

## Deploy (Railway)

- Dois serviços: app `rodanegocios` (GitHub, deploy a cada `git push`) e **Postgres** (volume próprio).
- `Procfile`: `migrate` e depois `gunicorn` na porta `$PORT`. O domínio público (*Settings → Networking*)
  deve apontar para a **mesma porta** que o gunicorn mostra no log (hoje 8080) — senão dá
  "Application failed to respond".
- Variáveis do app: `SECRET_KEY` (longa e aleatória), `DEBUG` (não `True`), `DATABASE_URL` (referência ao
  Postgres, rede privada). O host `postgres.railway.internal` só resolve dentro do Railway.
- Carga/ajuste de dados em produção: rodar no **console do app** (`railway ssh` ou aba Console), onde a
  conexão é a rede privada. Pelo TCP Proxy público a conexão caiu em cargas longas (foi removido).
- PowerShell: variável de ambiente é `$env:NOME = '...'` (não `export`); `export` só no Git Bash.

## Como trabalhar

- Uma tarefa por sessão. Para mudanças grandes, apresente um plano antes de editar.
- Nova funcionalidade vem com testes (Django `TestCase`). Antes de dizer que terminou: `check`,
  `makemigrations --check` e `test` verdes.
- Migrations: nunca editar uma já aplicada; criar nova. Antes de migration em tabela com dados, fazer cópia
  do banco; em produção, conferir o backup do Postgres.
- Nunca rodar `flush`, apagar `db.sqlite3` ou mexer no banco de produção sem pedir confirmação.
- **Dados reais** (empresas, representantes, usuários): não exportar, imprimir nem commitar. O dump local
  `dump_rodanegocios.json` está no `.gitignore`; quem roda `dumpdata`/`loaddata` é o Eloi.
- Commits pequenos, em português. O Eloi faz os commits e o `git push`, salvo pedido explícito.
- Comentários e docstrings em português, no estilo já usado no código.

## Estado atual (atualizar ao fim de cada sessão)

- **09/10/2026:** projeto estava sem documentação; criados `README.md` (análise) e este `CLAUDE.md`.
  - ✅ **API protegida** com JWT (`REST_FRAMEWORK`); 4 testes em `api/tests.py`; confirmado em produção
    (401 sem token).
  - ✅ **Banco de produção migrado do SQLite do contêiner para Postgres do Railway** (3 usuários, 153
    empresas, 910 mesas, conferidos por SQL). `Procfile` com `migrate` + `$PORT`. TCP Proxy removido.
  - Ponto 2 (dados reais no Git: `db.sqlite3`, `dados*.json`) **mantido por decisão do Eloi**; já não são
    usados em produção.
- Pontos de atenção ainda abertos (ver README): versão do Python (`.python-version` 3.11 × Django 6 ≥ 3.12);
  `STATICFILES_STORAGE` removido do Django (usar `STORAGES`; WhiteNoise com manifest provavelmente
  inativo); domínio e `SECRET_KEY` de reserva fixos no código; tela `configuracoes` quebra com
  `Configuracao` vazia; `Rodada.inicio_ro/fim_ro` com `default=timezone.now` em `TimeField`; `views.py`
  muito grande; arquivos soltos na raiz (`estrutura_pastas.txt`).
- Cobertura de testes: só os 4 de `api/tests.py`. `core` (views, matchmaking, middleware) sem testes.
- Próximas sessões sugeridas: testes do `core` e do matchmaking → versão do Python e `STORAGES` →
  tela de configurações → divisão do `views.py`.
