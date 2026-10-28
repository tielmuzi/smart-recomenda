# Plano de implementação — SmartRecomenda

## Objetivo e escopo

Construir uma aplicação web full-stack funcional para descoberta personalizada de filmes, séries, músicas e notícias demonstrativas. O MVP terá navegação real, recomendações calculadas no backend, justificativas verificáveis, preferências, avaliações, favoritos, histórico, busca, perfil/privacidade, painel administrativo e documentação acadêmica. O produto não será tratado como landing page nem como protótipo estático.

A implementação prioriza o fluxo principal e a demonstração acadêmica dos conceitos de Design Thinking, requisitos, APIs, recomendação, arquitetura modular, SOLID, Strategy, Observer, segurança, privacidade, riscos, viabilidade e testes. Funcionalidades avançadas — integrações com catálogos externos, recuperação de senha por e-mail, notificações reais e ML treinado — ficam explicitamente fora do MVP, mas com pontos de extensão documentados.

## Decisões de plataforma e tecnologia

- **Frontend:** React + TypeScript + Vite, com CSS modular/variáveis de design e componentes acessíveis.
- **Backend:** Python + FastAPI + Pydantic + SQLAlchemy, concentrando regras de negócio, autorização e recomendação.
- **Persistência:** SQLAlchemy usando `DATABASE_URL`; no desenvolvimento local, SQLite como fallback automático; no WebDev, o banco gerenciado MySQL-compatible provisionado pelo projeto. O modelo permanece compatível com PostgreSQL/Supabase quando uma URL externa for configurada, sem gravar credenciais no código.
- **Autenticação:** Manus OAuth, por ser o mecanismo padrão seguro do ambiente quando nenhum provedor foi escolhido. A aplicação utilizará o cookie `webdev_app_session`, validará o JWT com `MANUS_JWT_SECRET`, resolverá o usuário pela identidade Manus e não armazenará senhas. O perfil poderá guardar nome/e-mail retornados pela identidade e preferências separadamente.
- **Servidor/preview:** FastAPI escutará em `0.0.0.0:3000`, servirá a API `/api/v1/*` e o build estático do React. Durante o desenvolvimento, o frontend será compilado e o servidor será reiniciado conforme necessário; o Preview continuará sendo acessado por rotas relativas.
- **Migrações:** scripts SQLAlchemy/SQL idempotentes e tabela de controle de versão; seed demonstrativo reaplicável por identificador estável, sem sobrescrever edições do usuário.
- **Testes:** Pytest para backend/algoritmo e testes de contrato/fluxo; checagem TypeScript e build do frontend.

## Arquitetura e fluxo de dados

O navegador consome a camada `frontend/src/services/api.ts`. A API FastAPI valida entradas com Pydantic, autentica o usuário, encaminha a operação ao service apropriado e persiste através de repositories. O `RecommendationService` escolhe uma estratégia (`PopularityStrategy`, `ContentBasedStrategy` ou `HybridStrategy`) e retorna itens com componentes de score e explicação gerados pelos mesmos critérios usados no cálculo. Eventos internos do domínio notificam invalidação/atualização de recomendações sem acoplar controllers a efeitos colaterais.

A autenticação de rotas privadas será obrigatória para preferências, avaliações, favoritos, histórico e perfil; conteúdos públicos e catálogo demonstrativo poderão ser consultados sem login. Operações administrativas exigirão role verificada no backend. Respostas de erro terão formato consistente, limites de paginação e mensagens compreensíveis; logs não registrarão tokens, cookies ou dados pessoais desnecessários.

## Modelo de dados

Entidades principais: `profiles`, `contents`, `categories`, `preferences`, `ratings`, `favorites`, `interactions`, `recommendation_events` e `roles`. Serão usadas chaves estáveis, FKs, índices de busca, unicidade para uma avaliação/favorito por usuário e conteúdo, validação de categoria/tipo e timestamps. Interações terão opção de registro desativado e remoção pelo próprio usuário. Dados de demonstração serão marcados com `is_demo=true`; notícias demonstrativas serão identificadas como fictícias na interface.

## Recomendação explicável

A implementação inicial utilizará a fórmula configurável:

`S(u,i) = 0,6 × G(u,i) + 0,3 × A(u,i) + 0,1 × P(i)`

- `G`: sobreposição normalizada entre gêneros/temas/tipos/idiomas preferidos e metadados do conteúdo.
- `A`: afinidade derivada das avaliações do usuário para gêneros/tipos semelhantes; quando não houver avaliações, redistribuir explicitamente o peso para `G` e `P` e indicar isso na explicação.
- `P`: popularidade normalizada somente como sinal de descoberta, nunca como sinônimo de qualidade.

O serviço excluirá bloqueados e duplicados, evitará itens já avaliados quando houver alternativas, aplicará diversidade por categoria/gênero e fornecerá fallback popular para usuários novos. Cada item terá uma explicação estruturada, por exemplo: “Recomendado porque você selecionou ficção científica” ou “Semelhante a conteúdos que você avaliou positivamente”. A página “Como recomendamos” explicará pesos, limites e controles. Métricas de Precision@K, Recall@K, NDCG@K e diversidade serão calculadas apenas quando houver relevância adequada e serão identificadas como dados de demonstração ou medição real.

## Módulos e estrutura do projeto

```text
smartrecom/
├── app.config.ts
├── plan.md
├── TODO.md
├── README.md
├── .env.example
├── package.json / pnpm-lock.yaml
├── frontend/
│   ├── src/components/       # cards, navegação, filtros, estados e controles acessíveis
│   ├── src/pages/            # início, busca, detalhes, preferências, favoritos, histórico, perfil, admin
│   ├── src/layouts/          # shell público/privado/admin
│   ├── src/services/         # cliente HTTP e sessão
│   ├── src/hooks/            # dados de sessão, catálogo e mutations
│   ├── src/types/            # contratos compartilhados do frontend
│   ├── src/utils/            # formatação, validação e acessibilidade
│   └── public/manus-routes.json
├── backend/
│   ├── app/main.py           # criação FastAPI e serving do frontend
│   ├── app/api/              # controllers/routers HTTP
│   ├── app/core/             # settings, segurança, erros e dependências
│   ├── app/models/           # modelos SQLAlchemy
│   ├── app/schemas/          # DTOs Pydantic
│   ├── app/repositories/     # acesso a dados
│   ├── app/services/         # perfil, catálogo, ratings, favoritos, admin
│   ├── app/recommendations/  # Strategy, score, diversidade e explicações
│   ├── app/events/           # Observer/event bus interno
│   ├── migrations/           # versões idempotentes do esquema
│   └── tests/                # funcional, segurança, recomendação e desempenho
├── scripts/                  # migrate, seed_demo e métricas
└── docs/
    ├── architecture.md
    ├── privacy.md
    ├── risks.md
    ├── feasibility.md
    ├── testing.md
    └── academic-report.md
```

## Direção visual

- **Movimento:** *Editorial digital / dark data lounge*: uma interface de curadoria com atmosfera noturna e precisão de ferramenta profissional.
- **Princípios:** (1) descoberta com foco, (2) transparência antes do encantamento, (3) densidade organizada, (4) controles sempre próximos da decisão.
- **Filosofia de cor:** azul-marinho quase preto cria concentração; superfícies azul-ardósia separam camadas; o azul elétrico “Sinal Smart” (`#6E8CFF`) marca ações de descoberta; verde confirma uma decisão concluída e vermelho fica restrito a destruição/alertas.
- **Paradigma de layout:** shell assimétrico com rail lateral contextual e faixas horizontais de curadoria; detalhes abrem em página própria para preservar contexto, com trilha de navegação e painel de justificativa lateral em telas amplas.
- **Elementos de assinatura:** marca “S” formada por dois arcos orbitais, chips de motivo com ícone de radar, e uma linha fina de “sinal de afinidade” que conecta score, gênero e explicação.
- **Interação e animação:** ações devem confirmar no lugar, com transições de 160–220 ms, entrada suave dos cards e redução respeitada via `prefers-reduced-motion`; favoritos e avaliações têm retorno imediato, mas estado de carregamento e erro continuam visíveis.
- **Tipografia:** `Space Grotesk` para títulos e wordmark, `Inter` para leitura, controles e tabelas; escala com títulos fortes, rótulos compactos e corpo confortável.
- **Essência da marca:** “Uma bússola pessoal para decidir o que vale seu próximo intervalo.” Personalidade: criteriosa, curiosa, acolhedora.
- **Voz:** direta, inteligente e sem promessas exageradas. Exemplos: “Menos rolagem. Mais acertos.” e “Este sinal veio das suas preferências — não de uma caixa-preta.”
- **Wordmark/logo:** wordmark `SmartRecomenda` com o “S” orbitado por dois arcos e um pequeno ponto elétrico, construído como SVG acessível para evitar dependência de imagem externa.
- **Cor proprietária:** `#6E8CFF`, “Sinal Smart”, um azul-violeta luminoso usado com parcimônia para tornar descoberta e personalização reconhecíveis.

## Superfícies do MVP

1. **Início:** saudação, busca, categorias, recomendados, motivos, alta, novidades, explorar, filtros e estados vazios.
2. **Busca:** consulta ao backend, filtros, ordenação, paginação e feedback para zero resultados.
3. **Detalhes:** metadados disponíveis, avaliação/favorito, interesse, semelhantes e explicação.
4. **Preferências:** tipos, gêneros, idiomas, temas, bloqueios e diversidade com salvar/editar/remover.
5. **Favoritos, histórico e perfil:** CRUD real, privacidade, retenção e controles de exclusão.
6. **Como recomendamos:** fórmula, sinais, limitações e trade-off velocidade × precisão.
7. **Administração:** CRUD de conteúdos/categorias, destaques, metadados ausentes, métricas agregadas e erros sem dados sensíveis.
8. **Acesso:** estado conectado via Manus OAuth e estado desconectado com CTA; nenhuma credencial fictícia será exibida.

## Segurança, privacidade e acessibilidade

Aplicar autorização no backend, checagem de propriedade por `openId`, proteção contra acesso horizontal/vertical, validação Pydantic, CORS restrito, rate limiting simples por rota, headers seguros sem bloquear o iframe do Preview, cookies com `SameSite=None; Secure` quando aplicável, variáveis apenas por ambiente e política de privacidade em linguagem clara. Não coletar dados sensíveis nem afirmar conformidade integral com LGPD/WCAG: a documentação registrará os critérios efetivamente verificados. O frontend usará HTML semântico, labels, foco visível, navegação por teclado, contraste e `alt` relevante.

## Documentação e entrega

README cobrindo pré-requisitos, instalação, variáveis, migração, seed, inicialização, testes, endpoints e limitações. O relatório acadêmico reunirá requisitos, persona, arquitetura, SOLID/Strategy/Observer, algoritmo, UX, riscos, viabilidade, trade-off, métricas e cronograma de oito semanas. A matriz de riscos terá probabilidade, impacto, prioridade, mitigação, responsável e risco residual. Os números de custo e desempenho serão classificados como estimativas, valores verificados ou não cotados; nenhum gráfico receberá dados inventados como reais.

## Build e validação

Antes do primeiro servidor: configurar diagnóstico TypeScript no WebDev, instalar dependências com política de scripts revisada e publicar `manus-routes.json` com todas as rotas. Depois: executar migração e seed, build frontend, testes Pytest, lint/typecheck, iniciar FastAPI em `0.0.0.0:3000`, verificar `/health` e `/manus-routes.json`, revisar código e corrigir diagnósticos. O checkpoint será salvo no repositório canônico após os checks. Publicação só será considerada concluída se houver confirmação explícita; caso contrário, a entrega apontará o Preview.

## Limitações declaradas

O ambiente WebDev provisiona um banco MySQL-compatible, não PostgreSQL; a camada SQLAlchemy mantém portabilidade e aceita uma URL PostgreSQL/Supabase externa se o responsável fornecer essa integração. Manus OAuth substitui armazenamento próprio de senha. Catálogo e notícias são dados demonstrativos marcados como fictícios; métricas de qualidade serão placeholders até existirem avaliações/relevância suficientes e não serão apresentadas como medições reais. Integrações de terceiros e notificações reais não fazem parte da primeira entrega.
