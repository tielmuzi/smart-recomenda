# SmartRecomenda

> Descubra o que combina com você.

Aplicação acadêmica demonstrativa de recomendação personalizada e explicável para filmes, séries, músicas e notícias fictícias. O MVP possui interface responsiva, API FastAPI, persistência, busca, preferências, favoritos, ratings, histórico, administração e documentação.

## Pré-requisitos

Node.js 22+, pnpm 10+, Python 3.11+ e pip. O modo local usa SQLite automaticamente. O ambiente WebDev fornece `DATABASE_URL` para o banco gerenciado; uma URL PostgreSQL/Supabase externa pode ser configurada quando disponível.

## Instalação rápida

```bash
pnpm install
pnpm setup
cp .env.example .env
```

O comando `pnpm setup` cria o ambiente virtual `.venv` e instala as dependências do backend automaticamente em Windows, Linux e macOS.

## Execução local

Para rodar o frontend e a API em modo de desenvolvimento:

```bash
cp .env.example .env
pnpm dev
```

Isso inicia o Vite em `http://localhost:3000` e a API em `http://localhost:8000` em paralelo.

Por padrão, `DEMO_ACCESS=true` habilita uma conta compartilhada de visitante acadêmico e o site abre sem pedir login. Não é necessário configurar `AUTH_*` para a avaliação local.

Configure `AUTH_CLIENT_ID`, `AUTH_PORTAL_URL`, `AUTH_API_URL` e `AUTH_JWT_SECRET` no `.env` para habilitar o login. Em Manus, os valores de plataforma `MANUS_PROJECT_ID`, `MANUS_OAUTH_PORTAL_URL`, `MANUS_OAUTH_API_URL` e `MANUS_JWT_SECRET` também são aceitos como aliases. Para uso local, a URL de callback precisa estar permitida pelo projeto Manus:

```text
http://localhost:3000/api/v1/auth/callback
```

O frontend encaminha `/api` à API durante o desenvolvimento, então o callback usa a mesma origem pública do Vite.

Para validar rapidamente a integridade do projeto antes de entregar:

```bash
pnpm verify
```

Para servir a versão compilada do frontend junto com a API em um único listener:

```bash
cp .env.example .env
APP_ENV=production APP_HOST=0.0.0.0 APP_PORT=8000 pnpm start
```

A API e o frontend compilado ficam no mesmo listener. O endpoint `/health` verifica prontidão; `/docs` expõe OpenAPI; `/manus-routes.json` é um manifesto estático em `frontend/public` durante o build.

## Deploy real (Docker)

O projeto também já está preparado para empacotamento em container:

```bash
docker build -t smartrecomenda .
docker run --rm -p 8000:8000 --env-file .env smartrecomenda
```

Ou com compose:

```bash
docker compose up --build
```

A imagem compila o frontend, inicia a API em produção e serve a aplicação estática a partir da pasta `dist/` com fallback SPA. O Compose persiste o SQLite em um volume Docker e executa a API como usuário sem privilégios. Para publicação, altere `FRONTEND_URL`, `AUTH_CALLBACK_URL` e `CORS_ORIGINS` para o domínio HTTPS real antes de subir o container.

## Deploy Vercel + Railway

O repositório inclui configuração para Vercel (frontend estático com fallback SPA e proxy same-origin em `api/[...path].js`) e Railway (API via Dockerfile, health check e porta dinâmica `PORT`).

1. Publique o repositório no Git e crie um projeto Railway apontando para a raiz. Railway usa `railway.json` e o `Dockerfile`; gere um domínio público HTTPS para o serviço.
2. No Railway, crie um volume montado em `/app/data` e configure. O container corrige automaticamente a permissão desse volume antes de iniciar a API, então o processo da aplicação continua rodando como usuário sem privilégios:

   ```text
   APP_ENV=production
   DEMO_ACCESS=true
   DATABASE_URL=sqlite:////app/data/smartrecomenda.db
   FRONTEND_URL=https://SEU-APP.vercel.app
   CORS_ORIGINS=https://SEU-APP.vercel.app
   AUTH_CLIENT_ID=...
   AUTH_PORTAL_URL=...
   AUTH_API_URL=...
   AUTH_JWT_SECRET=...
   AUTH_CALLBACK_URL=https://SEU-APP.vercel.app/api/v1/auth/callback
   ADMIN_OPEN_IDS=...
   ```

   Mantenha `AUTH_COOKIE_SECURE=true` e `AUTH_COOKIE_SAMESITE=none` em produção. O volume é necessário porque a base SQLite precisa sobreviver a novos deploys e reinícios.
3. Crie o projeto Vercel a partir do mesmo repositório, com a raiz do projeto na raiz do repositório e o framework Vite. Configure `RAILWAY_API_URL` com a origem pública do serviço Railway, por exemplo `https://smartrecomenda-api.up.railway.app` (sem `/api`).
4. Publique no Vercel e atualize `FRONTEND_URL`, `CORS_ORIGINS` e `AUTH_CALLBACK_URL` no Railway com o domínio final (incluindo domínio customizado, se houver). Cadastre o callback idêntico no provedor Manus.
5. Faça novo deploy do Railway e do Vercel; valide `/health` diretamente no Railway, `/api/health` no Vercel, login/logout e navegação direta para rotas como `/favoritos`.

O proxy Vercel mantém API e sessão sob a mesma origem do navegador, encaminhando `Cookie`, `Set-Cookie`, `Origin` e redirects ao Railway. `VITE_API_BASE_URL` fica vazio nesse arranjo. Não exponha `AUTH_JWT_SECRET` ou credenciais do provedor em variáveis `VITE_*`; apenas `RAILWAY_API_URL` deve existir como variável de ambiente de build/runtime da Vercel.

## Migração e seed

O backend executa o esquema idempotente e carrega dados fictícios identificados como demonstração na inicialização. Os contratos SQL estão em `backend/migrations/001_initial.sql` e `backend/migrations/002_recommendation_indexes.sql`. Para rodar manualmente a API:

```bash
node scripts/run-python.mjs -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

## Testes

```bash
pytest -q backend/tests
pnpm typecheck
pnpm build
```

## Acesso acadêmico e autenticação

Por padrão, a autenticação está desabilitada no código (`AUTH_ENABLED = False` em `backend/app/main.py`) e a aplicação abre diretamente com o perfil compartilhado “Visitante acadêmico”. Para reativar o login, altere essa constante para `True`, configure as variáveis `AUTH_*` e faça um novo deploy. Com a autenticação desabilitada, as credenciais OAuth existentes não são usadas e todas as rotas funcionam no modo visitante; preferências e interações continuam compartilhadas nesse perfil.

O login Manus opcional usa autorização de código, verificação de `state` e nonce vinculado ao navegador. O backend troca o código no servidor e busca a identidade antes de criar uma sessão. Nenhum access token do provedor é guardado. Cadastre o callback exato na configuração OAuth do projeto Manus; localhost só funciona se o provedor o permitir.

Quando o login opcional está configurado, o cookie é `webdev_app_session` (HTTP-only, HS256, com expiração); esse nome é mantido para compatibilidade com o Preview Manus. Configure `AUTH_CALLBACK_URL` com a URL HTTPS pública terminada em `/api/v1/auth/callback`, `FRONTEND_URL`, `CORS_ORIGINS` e `ADMIN_OPEN_IDS` (lista de `openId`s). `AUTH_COOKIE_SAMESITE=none` requer `AUTH_COOKIE_SECURE=true`; a proteção de origem também é aplicada a chamadas de alteração de dados.

Rotas de autenticação: `GET /api/v1/auth/config`, `GET /api/v1/auth/login`, `GET /api/v1/auth/callback`, `GET /api/v1/auth/me` e `POST /api/v1/auth/logout`.

## Recomendações e sinais persistidos

Cada perfil recebe recomendações com afinidade explícita (preferências), afinidade aprendida (avaliações, favoritos e visualizações), qualidade média e popularidade. A ponderação central é `0.44E + 0.34H + 0.10Q + 0.12P`; notas baixas reduzem os gêneros relacionados, itens avaliados/vistos perdem posição para reduzir repetição e “Não recomendar novamente” exclui o item daquele perfil. Preferências, avaliações, favoritos, visualizações e itens ocultos alimentam o perfil individualmente; qualidade média e popularidade do catálogo são agregados compartilhados. O histórico de navegação pode ser apagado sem remover notas e favoritos.

Ao abrir detalhes, a interface persiste uma visualização; ações de favorito, avaliação e ocultação também são gravadas no SQLite. `/api/v1/admin/metrics` entrega métricas agregadas dos últimos 30 dias, série diária de sete dias, conteúdos mais ativos e atividades recentes para o painel administrativo.

## Principais endpoints

`GET /api/v1/contents`, `GET /api/v1/contents/{id}`, `GET /api/v1/recommendations`, `GET/PUT /api/v1/preferences`, `GET /api/v1/favorites`, `POST /api/v1/favorites/{id}`, `POST /api/v1/ratings/{id}`, `POST/GET/DELETE /api/v1/interactions`, `GET /api/v1/profile`, `GET/POST /api/v1/admin/*`.

## Segurança e limites

As rotas personalizadas exigem uma sessão JWT válida e não confiam em IDs de usuário enviados pelo cliente. A aplicação não cria mais um usuário demonstrativo autenticado por padrão. Os dados do catálogo continuam fictícios e devem ser identificados como demonstração. O ambiente WebDev tem banco MySQL-compatible; o repositório mantém uma camada SQLite e não afirma compatibilidade operacional com PostgreSQL sem testar a URL/driver escolhido. Capas usam URLs remotas; uma versão publicada deve verificar licenças e armazenar assets duráveis.

## Documentos

- `plan.md`: decisões de implementação e design.
- `docs/architecture.md`: módulos e padrões.
- `docs/academic-report.md`: riscos, viabilidade, trade-off e cronograma.
- `privacy.md`: política do modo demonstrativo.
- `TODO.md`: entregas e critérios.
