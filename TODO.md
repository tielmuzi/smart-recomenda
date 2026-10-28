# Entregas do SmartRecomenda

## 1. Shell, rotas e identidade visual
- A aplicação navega corretamente entre início, busca, detalhes, preferências, favoritos, histórico, perfil, como recomendamos e administração.
- O shell responsivo contém marca SmartRecomenda, busca global, categorias, favoritos, perfil e rodapé com desenvolvedor e direitos reservados.
- A interface usa fundo azul-marinho/cinza-escuro, destaque `#6E8CFF`, cards arredondados, foco visível, estados de carregamento/erro/vazio/sucesso e adaptação a desktop/tablet/mobile.

## 2. Catálogo, busca e detalhes
- A API retorna conteúdos paginados e a busca aceita texto, categoria, gênero e ordenação.
- Cada card mostra capa, título, tipo, gêneros, nota somente quando disponível, favorito, detalhes e justificativa quando aplicável.
- A tela de detalhes exibe apenas metadados presentes na base, semelhantes, avaliação do usuário, favorito, interesse e explicação.
- Dados de demonstração são marcados como fictícios e o seed é idempotente.

## 3. Preferências, recomendações e explicabilidade
- O usuário consegue configurar, alterar e remover tipos, gêneros, idiomas, temas, bloqueios e diversidade.
- A API retorna recomendações calculadas por estratégia configurável, exclui bloqueados/duplicados, aplica fallback para usuário novo e oferece variedade.
- A fórmula `S(u,i)=0,6G+0,3A+0,1P` é implementada com normalização e redistribuição explícita quando não existem avaliações.
- Cada recomendação apresenta justificativa coerente com os sinais realmente usados e existe a área “Como recomendamos”.

## 4. Sessão, perfil, avaliações, favoritos e histórico
- Rotas privadas validam a sessão no backend e o perfil respeita propriedade por usuário.
- Avaliações de 1 a 5 podem ser criadas, alteradas e excluídas, uma por usuário/conteúdo.
- Favoritos podem ser adicionados, removidos, filtrados e persistidos.
- Histórico pode ser consultado, apagado e desativado conforme configuração.
- Perfil mostra dados básicos, preferências, privacidade e controles de dados sem expor segredos.

## 5. Administração e métricas
- Rotas administrativas exigem role verificada no backend.
- O painel permite CRUD de conteúdos/categorias, destaques, metadados ausentes e métricas agregadas.
- Métricas diferenciam dados de demonstração, sintéticos e reais e não apresentam resultados inventados como reais.

## 6. Segurança, documentação e testes
- Entradas são validadas, erros têm formato consistente, CORS/rate limiting são configurados e segredos ficam em ambiente.
- A documentação cobre arquitetura, SRP, Strategy, Observer, privacidade, riscos, viabilidade, trade-off, cronograma, endpoints, setup, migração, seed, testes e limitações.
- Existem testes funcionais, de segurança, algoritmo e desempenho, com limitações registradas.
- O projeto tem `.env.example`, `README.md`, `manus-routes.json`, migrações e build reproduzível.
