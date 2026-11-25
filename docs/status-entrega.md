# Status das entregas — Proteca

Atualizado em 24/11/2026.

- Site: https://app.163.176.54.212.sslip.io
- API: https://api.163.176.54.212.sslip.io/docs
- Repositório: https://github.com/plreis/proteca
- Arquitetura e diagramas: `docs/arquitetura.md`. Decisões: `docs/decisoes.md` e `docs/adr/`.

Os critérios de cada sprint abaixo foram copiados do enunciado (`Trabalho Final Web 26-2.pdf`).

## Sprint 1 — concluída (review em 04/11)

| Critério do enunciado | Situação | Onde ver |
|---|---|---|
| Descrição com problema, usuários e papel da IA | Feita | `README.md` |
| Componentes com responsabilidade clara, sem duplicação | Feitos | `frontend/src/components/`, `frontend/src/features/` |
| Estrutura de pastas coerente com o Next.js | Feita | `frontend/src/app/` |
| Dados mockados verossímeis | Feitos; trocados pela API na Sprint 3 | — |
| Uso consistente da biblioteca de CSS | Tailwind em todas as telas | `frontend/tailwind.config.ts` |
| Versão estática exportada e disponível | GitHub Pages | https://plreis.github.io/proteca/ |

## Sprint 2 — concluída (review em 11/11, API publicada depois)

Na review de 11/11 a API ainda não estava publicada. Em 18/11 corrigimos o código (import faltando, rotas com 500, modelo do Gemini desativado) e depois publicamos no Coolify.

| Critério do enunciado | Situação | Onde ver |
|---|---|---|
| API por URL pública, com `/docs` | Feito | https://api.163.176.54.212.sslip.io/docs |
| Código organizado em módulos | Feito | `backend/app/{routers,schemas,models,repositories,services,auth,core}` |
| Schemas Pydantic alinhados ao frontend | Feito | `backend/app/schemas/`, `frontend/src/types/index.ts` |
| Códigos HTTP e mensagens de erro adequados | Feito: 401, 404, 409, 422 e 503 na voz | `backend/app/core/errors.py`, `backend/tests/` |
| IA com papel real no fluxo do usuário | Feito: Live da sessão e voz do Proteca | `POST /sessions/{id}/live`, `POST /ia/voz` |
| Chaves em variáveis de ambiente | Feito: `GEMINI_API_KEY` e `SECRET_KEY` só no Coolify | `backend/.env.example` |

## Sprint 3 — revisada em 23/11

| Critério do enunciado | Situação | Onde ver |
|---|---|---|
| Site público consumindo a API real | Parcial: login, sessões, dispositivos e Live usam a API. Ocorrências, escola e turmas ainda vêm do `mockService` na `main`; a branch `ajustes-rique` resolve (#11) | `frontend/src/context/SchoolContext.tsx` |
| Login funcional, token nas requisições protegidas | Feito | `frontend/src/context/AuthContext.tsx`, `frontend/src/services/api.ts` |
| JWT protegendo escrita e dados sensíveis | Feito: só `/auth/token` e `/health` ficam abertas | `backend/app/main.py`, `backend/tests/test_auth.py` |
| Estados de carregamento e erro na interface | Feito no login, sessões, dispositivos e Live. Sessão expirada volta ao login com aviso (PR #27) | `frontend/src/features/sessions/AIDemoCard.tsx` |
| URL da API e CORS por variável de ambiente | Feito | `NEXT_PUBLIC_API_URL` (build do site), `BACKEND_CORS_ORIGINS` (API) |

Depois da review entraram o rodízio de modelos do Gemini e a voz do Proteca (PR #26). Com o PR #27 a API tem 48 testes no pytest.

As issues #4 (API no Coolify), #8 (Live pela rota da sessão) e #9 (Dockerfile e deploy do site) já foram feitas, mas continuam abertas.

## Sprint 4 — em andamento (review e entrega em 30/11)

A review é um pitch de até 2 minutos para membros externos.

| Critério do enunciado | Situação | Issue |
|---|---|---|
| Modelos SQLModel coerentes, com tipos e relacionamentos | Em andamento na branch `sprint-4/persistencia-e-turma`: 10 tabelas, diagrama em `docs/arquitetura.md` | #13, #15 |
| Dados mantidos após reiniciar a API | Depende do volume `/app/data` no Coolify e do teste de reinício | #16 |
| Fluxo principal sem erros críticos em produção | Revisão final depois dos merges | #19 |
| Manual do usuário claro, focado nos fluxos principais | A fazer | #18 |
| Pitch de até 2 minutos focado no usuário final | Roteiro pronto, falta ensaiar | #19 |

A #13 ainda fala em Supabase no título. A ADR 0003 trocou o banco por SQLite num volume da VM.

Entrega no Moodle até 30/11:

| Arquivo | Conteúdo | Issue |
|---|---|---|
| Documentação (PDF) | Dupla, descrição do sistema, README e link do repositório | #17 |
| Manual do usuário (PDF) | Guia para o professor, com telas do site publicado | #18 |
| Código (ZIP) | Pastas `frontend/` e `backend/` | #17 |

## O que falta até 30/11

Ninguém é dono fixo de um item. Quem pegar um item marca o nome ao lado e abre o PR. Decisões que afetam os dois vão para `docs/decisoes.md`.

### Código e produção

- [ ] Resolver os 2 conflitos da `ajustes-rique` com a `main` (`frontend/src/context/SchoolContext.tsx` e `frontend/src/services/liveGuidanceService.ts`) e fazer o merge. Isso tira o `mockService` e fecha a #11.
- [ ] Revisar e fazer o merge do PR #27 (sessão expirada volta ao login; a voz não lê mais a instrução).
- [ ] Persistência com SQLModel: modelos, repositório SQL no lugar do de memória e carga inicial com o usuário professor (#13, #14, #15).
- [ ] `/api/v1/health` mostrar o armazenamento real. Hoje responde `"storage": "memory"` fixo.
- [ ] Coolify: volume persistente montado em `/app/data` na API (ADR 0003). Conferir se o usuário `proteca` (uid 1000) do container consegue escrever nessa pasta.
- [ ] Tela da turma (ADR 0004): rotas `POST/DELETE /sessions/{id}/turma`, `GET /turma/{codigo}` e `GET /turma/{codigo}/voz`, página `/turma/?codigo=AULA8B` com o mascote e botão "Mostrar para a turma" no Live. Sem issue; abrir uma ou citar no PR.
- [ ] `GEMINI_TTS_VOICE=Puck` no Coolify. O padrão no código ainda é `Kore`.
- [ ] Teste de reinício em produção: criar uma sessão e uma ocorrência, reiniciar a API e fazer um redeploy pelo Coolify, conferir que as duas continuam lá. Tirar print para a documentação (#16).
- [ ] Fluxo completo em produção sem erro: login, abrir sessão, registrar ocorrência, Live, mostrar para a turma, mudar a ocorrência até encerrada, encerrar a sessão (#19).
- [ ] Proteção da `main`: workflow de CI com `pytest` e build do site em todo PR, e regra exigindo PR, uma revisão e CI verde antes do merge.
- [ ] Fechar as issues #4, #8 e #9 com o link do commit ou PR que resolveu cada uma.

### Documentos e entrega

- [ ] Atualizar o `README.md` da raiz: banco SQLite (ADR 0003), Gestor fora do escopo (ADR 0004), links de produção no topo e rotas da tela da turma (#17).
- [ ] Manual do usuário em PDF com prints do site publicado: login, abrir sessão, registrar ocorrência, Live, mostrar para a turma, encerrar ocorrência e sessão (#18).
- [ ] Documentação em PDF: dupla, descrição do sistema, README e link do repositório. O enunciado não considera links externos, então o PDF precisa trazer o conteúdo e não só o link (#17).
- [ ] ZIP só com `frontend/` e `backend/`, sem `node_modules`, `.next`, `out`, `.venv` e `.env`. `git archive --format=zip -o proteca.zip HEAD frontend backend` gera o ZIP só com o que está versionado (#17).
- [ ] Pitch ensaiado pelo menos duas vezes com cronômetro, com o notebook e o tablet, trocando quem fala cada parte em um dos ensaios (#19).
- [ ] Decidir os itens de "Para decidir juntos" em `docs/decisoes.md`, principalmente o (a) e o (b), antes do ensaio.
- [ ] Enviar os três arquivos no Moodle até 30/11 (#19).
