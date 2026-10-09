# Rodanegócios

Plataforma web para organizar **rodadas de negócios** entre empresas: cadastro de empresas (compradoras e vendedoras) com seus interesses, montagem de eventos e geração automática das rodadas/mesas (quem se reúne com quem e quando), com agendas e relatórios para impressão.
Desenvolvedor: Eloi. Este README foi criado em 09/10/2026, a partir da análise do código existente — o projeto já vinha sendo usado antes de haver documentação.

## Stack

- Python + Django 6.0 (`requirements.txt`), Django REST Framework + `simplejwt` (API),
  `django-localflavor` (campo CNPJ), `whitenoise` (estáticos), `gunicorn`.
- Banco: **SQLite** local (`db.sqlite3`); em produção usa `DATABASE_URL` (via `dj-database-url`,
  `psycopg2-binary` instalado para Postgres) quando a variável existe.
- Templates Django + CSS próprio (`core/static/core/css/style.css`). Sem framework JS.
- Hospedagem: **Railway** (`Procfile`: `gunicorn rodanegocios.wsgi:application`). Domínio em
  `settings.py` (`ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS`).
- Windows, VS Code, ambiente virtual em `venv/`.

## Comandos

- Rodar: `venv/Scripts/python manage.py runserver`
- Verificar: `venv/Scripts/python manage.py check` e `venv/Scripts/python manage.py makemigrations --check --dry-run`
- Testes: `venv/Scripts/python manage.py test` (**ainda não há testes** — `core/tests.py` e `api/tests.py` estão vazios)
- Segredos no `.env` (nunca commitar nem expor). Variáveis lidas: `SECRET_KEY`, `DEBUG`, `DATABASE_URL`.

## Estrutura

- `rodanegocios/` — settings, urls raiz, wsgi/asgi.
- `core/` — app principal: models, views (`views.py`, ~2100 linhas), forms, templates, `templatetags/`,
  `services/matchmaking.py` (algoritmo de geração das rodadas), `utils.py`, `middleware.py`.
- `api/` — API REST somente de leitura (agendas, empresas, eventos, rodadas, mesas) + token JWT.
- `dados*.json`, `db.sqlite3` — cargas e dump de dados usados na migração para o Railway.

## Modelo de dados (`core/models.py`)

- `Categoria` → `Interesse` (N interesses por categoria); `Empresa` ↔ `Interesse` (N:N).
- `Empresa` (modalidade **COMPRADOR** ou **VENDEDOR**, CNPJ único opcional) → `Endereco`, `Representante` (1:N).
- `Evento` ↔ `Empresa` por `EmpresaEvento` (flag `participa`); `Evento` → `Rodada` (nome, duração 15/20/30 min,
  início/fim) → `Mesa` (número, comprador, vendedor).
- `RelacionamentoEmpresa` — vínculo prévio comprador↔vendedor (cliente/fornecedor/parceiro/já negociaram),
  usado para **evitar** pares que já se conhecem.
- `Configuracao` (e-mail de recuperação, identificador do usuário; define a permissão
  `core.pode_acessar_rodanegocios`) e `TokenResetSenha` (token UUID com validade de 30 min).

## Fluxo principal

1. Cadastrar categorias/interesses e empresas (manual ou por importação — `empresa_importar`,
   `representante_importar`).
2. Criar o evento e marcar as empresas participantes (`evento_participantes`).
3. Ver o **ranking de afinidades** (interesses em comum) e gerar as rodadas
   (`rodadas_gerar` → `matchmaking.gerar_pares_para_rodada`): respeita limite de mesas, evita encontros
   repetidos e empresas com relação prévia, garante mínimo de participações por vendedor e usa afinidade
   para desempatar.
4. Conferir/editar rodadas e mesas, painel da rodada, relatórios (inscritos, repetições, rodadas por
   comprador, empresas relacionadas) e **agendas** por empresa, com versão para impressão.

## Acesso

`RodanegociosProtectionMiddleware` (`core/middleware.py`) redireciona para `/login` quem não está autenticado
ou não tem a permissão `core.pode_acessar_rodanegocios`. Rotas livres: login, esqueci/redefinir senha,
troca de senha, `/admin` e tudo sob `/api`. Recuperação de senha por token individual (e-mail em console
em desenvolvimento: `EMAIL_BACKEND` = console).

## Estado atual (09/10/2026) e pontos de atenção

Levantamento só de leitura; **nenhuma alteração de código foi feita**. `check` e `makemigrations --check`
limpos. Banco local: 153 empresas, 153 representantes, 2 eventos, 26 rodadas, 910 mesas, 13 categorias,
284 interesses, 3 usuários. Pontos a tratar (a combinar antes de mexer):

1. ✅ **Corrigido em 09/10/2026 (aguardando commit/deploy):** `REST_FRAMEWORK` em `settings.py` agora exige JWT (`IsAuthenticated`) em toda a API; `/api/token/` segue livre. 4 testes novos em `api/tests.py`. Clientes que consumiam a API sem login precisam passar a enviar `Authorization: Bearer <token>`. *Problema original:* todos os `permission_classes = [IsAuthenticated]` de `api/views.py` estão
   comentados, e o middleware libera `/api` — dados de empresas, agendas e mesas ficam públicos.
2. **Dados no Git:** `db.sqlite3` e `dados*.json` estão versionados (o `.gitignore` tem `db.sqlite3`
   comentado). Contêm dados reais de empresas/representantes (e hashes de senha dos usuários).
3. **Banco no Railway:** confirmar se produção usa `DATABASE_URL` (Postgres) ou o SQLite do contêiner —
   se for SQLite sem volume, os dados se perdem a cada deploy (ver `/app/db.sqlite3` no console do Railway).
4. **Versão do Python:** `.python-version` diz 3.11.0, mas Django 6.0 exige Python ≥ 3.12; conferir a versão
   realmente usada no venv/Railway. (O próprio `.python-version` consta no `.gitignore`.)
5. **Estáticos:** `STATICFILES_STORAGE` foi removido do Django (usar `STORAGES`); o WhiteNoise com manifest
   provavelmente não está ativo.
6. **Configuração fixa no código:** domínio do Railway em `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS`;
   `SECRET_KEY` com valor *fallback* (`fallback-dev-key`) se a variável faltar; e-mail pessoal como
   padrão de `Configuracao.email_recuperacao`.
7. **`configuracoes`:** `Configuracao.objects.first()` retorna `None` (tabela vazia hoje) — salvar a tela
   dá erro (`AttributeError`).
8. **Sem testes automatizados** e `views.py` muito grande (2100 linhas), sem separação em módulos.
9. `Rodada.inicio_ro/fim_ro` usam `default=timezone.now` em `TimeField` (retorna datetime) — frágil.
10. Documentos soltos na raiz: `dados.json`, `dados_limpo*.json`, `estrutura_pastas.txt` (vazio/corrompido).

## Próximos passos sugeridos

1. Decidir com o Eloi a ordem dos pontos de atenção (sugestão: 1, 2 e 3 primeiro — segurança e dados).
2. Criar `CLAUDE.md` com as regras do projeto e escrever os primeiros testes (acesso, API, geração de rodadas).
3. Só então alterações de código, em commits pequenos, com `check`, `makemigrations --check` e `test` verdes.
