# Arquitetura do SmartRecomenda

O frontend React consome a API FastAPI por uma camada de serviços tipada. A API concentra validação, autorização, regras de recomendação e persistência. O repositório atual usa o módulo `sqlite3` como camada equivalente a um ORM para manter o MVP leve, com `DATABASE_URL` como ponto de evolução para o banco gerenciado MySQL-compatible ou PostgreSQL/Supabase externo.

## Responsabilidades

- **Controller/API:** traduz HTTP em chamadas de serviço e valida payloads Pydantic.
- **Service:** coordena catálogo, perfil, preferências, favoritos, avaliações e métricas.
- **Repository:** funções de acesso SQL com queries parametrizadas e limites.
- **Recommendation Engine:** calcula score, aplica exclusões/diversidade e produz a explicação.
- **Observer:** `recommendation_events` registra a geração sem acoplar a interface ao cálculo.
- **Strategy:** a implementação MVP expõe `HybridStrategy` como composição de afinidade, avaliação e popularidade; a pasta `recommendations` é o ponto de extensão para PopularityStrategy e ContentBasedStrategy independentes.

## Fluxo de segurança

O modo demonstrativo usa o identificador isolado `demo-alexandre` e o cabeçalho `X-Smart-User` apenas para testes locais. Em produção, esse ponto é substituído pelo adaptador Manus OAuth, validando `webdev_app_session`, JWT HS256, `MANUS_JWT_SECRET`, `MANUS_PROJECT_ID` e o `openId` resolvido. Nenhum token ou senha é persistido no frontend.
