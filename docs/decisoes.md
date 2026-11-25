# Registro de decisões — Proteca

Decisões que afetam os dois membros da dupla são tomadas juntas e anotadas aqui. Quando a decisão muda a arquitetura ou o escopo, ela também vira uma ADR em `docs/adr/`. Os termos seguem o `GLOSSARY.md`.

## Decididas

| Data | Decisão | Por quê | Registro |
|---|---|---|---|
| até 04/11 | Tema 12: segurança, controle e uso pedagógico dos dispositivos fornecidos pelo governo | Problema real das escolas que receberam Chromebooks e tablets, e dá para atacar sem vigiar estudantes | — |
| depois de 04/11 | Dupla Pedro Lucas dos Reis Silva (RA 2272040) e Henrique Cois Farjado Gau (RA 2369133) | Pedro fez a Sprint 1 sozinho porque a turma tinha número ímpar; depois a disciplina passou a exigir duplas | — |
| Sprint 1 | Frontend em Next.js e backend em Python/FastAPI | O enunciado fala em "uma única linguagem", mas detalha a stack Next.js + FastAPI + SQLModel + JWT. Seguimos a stack detalhada | — |
| 18/11 | Coolify na VM da equipe para a API e o site, com HTTPS em `sslip.io` | Os dois serviços ficam no mesmo lugar, com segredos fora do repositório e sem depender de plano gratuito de terceiros | [ADR 0001](adr/0001-stack-e-hospedagem.md) |
| 18/11 | Sem captura de tela, sem fotos, sem painel multitela e sem índice de desatenção | Guardar imagem de estudante é o próprio risco que o tema aponta, e não daria tempo de terminar até 30/11 | [ADR 0002](adr/0002-escopo-e-privacidade.md) |
| 18/11 | Nenhum dado de estudante; a ocorrência aponta para o dispositivo e a sessão; o Gemini recebe só o objetivo e contagens | Cumprir LGPD, ECA e ECA Digital sem precisar de consentimento de cada estudante | [ADR 0002](adr/0002-escopo-e-privacidade.md) |
| 18/11 | Nada entra na `main` sem PR revisado pelo outro | Quem revisa precisa saber explicar o código na review | `docs/plano-sprints-tarefas.md` |
| 23/11 | Rodízio de modelos do Gemini: 4 modelos de texto e 4 de voz, tentados em ordem | Um modelo sozinho às vezes responde 503 (sobrecarregado) ou 429 (cota esgotada). Os `lite` vêm primeiro porque a cota gratuita deles é de 500 requisições por dia, contra 20 dos `flash` | PR #26, `backend/app/core/config.py` |
| 23/11 | Se nenhum modelo de texto responde, a API devolve a orientação de reserva; se nenhum modelo de voz responde, o site usa a voz do navegador | O Live e a voz não podem travar a aula por falta de cota | PR #26 |
| 24/11 | SQLite num volume persistente da VM (`/app/data`) no lugar do Postgres do Supabase; site exportado como estático e servido por nginx | Na nossa VM o volume sobrevive a reinício e redeploy, e não dependemos de serviço externo nem de pooler. O site não usa nada que precise de servidor Node | [ADR 0003](adr/0003-sqlite-na-vm-e-site-estatico.md) |
| 24/11 | Tela da turma pública, aberta pelo código da turma, sem login, sem cookies e sem enviar nada à API | Consentimento pedido pelo professor não é livre, e abaixo de 12 anos a LGPD exige o responsável. Um site também não enxerga outras abas | [ADR 0004](adr/0004-tela-da-turma-sem-coleta.md) |
| 24/11 | Gestor fora do escopo desta entrega; o professor é o único papel com acesso | O código não tem regra diferente para o gestor, e funcionalidade pela metade não é pontuada | [ADR 0004](adr/0004-tela-da-turma-sem-coleta.md) |
| 24/11 | Fala do Proteca: a intervenção ganha o campo `speech`, curto, em primeira pessoa e dirigido à turma | Mensagem e pergunta escritas para leitura ficam longas e estranhas quando lidas em voz alta | `GLOSSARY.md` |
| 24/11 | Voz Puck no TTS, e o modelo de voz recebe só a fala | Na primeira versão o modelo lia em voz alta a instrução de tom junto com a fala. Agora o tom vem só da voz escolhida, e a Puck é animada, o que combina com um mascote que convida em vez de dar bronca. A anterior, Kore, é mais firme | `GEMINI_TTS_VOICE`, PR #27 |
| 24/11 | Sem divisão fixa de tarefas: cada um pega o item que puder da lista em `docs/status-entrega.md` | Faltam poucos dias e os itens dependem uns dos outros. O enunciado exige que os dois saibam explicar qualquer parte | `docs/status-entrega.md` |

## Para decidir juntos

### (a) Como apresentamos o Proteca no pitch?

**Recomendação:** como uma camada pedagógica que complementa o filtro e o gerenciamento de dispositivos da SEED. O filtro bloqueia sites; o Proteca ajuda o professor a mediar o que acontece na sala. No futuro ele pode virar um módulo desse ecossistema. Ele ajuda sem dados pessoais porque trabalha com registros factuais do professor por dispositivo (número de patrimônio) e com sinais agregados da sessão.

**Por quê:** evita a comparação com o filtro, que não é o que fazemos. Também responde logo a primeira dúvida de quem é de fora: "isso vigia o aluno?".

**Cuidado:** não dizer que existe integração com a SEED. Nunca conversamos com eles; "pode virar um módulo" é proposta, não fato.

### (b) Quem opera qual aparelho e quem fala o quê no pitch?

**Recomendação:** uma pessoa fica no notebook projetado (abre o Live e clica em "Mostrar para a turma"). A outra entrega o tablet à banca, ajuda a abrir a tela da turma com o código `AULA8B` e explica a parte de privacidade. As falas do problema e do fecho ficam com quem estiver livre naquele momento. Em um dos ensaios, trocamos os papéis.

**Por quê:** o enunciado dá desconto se um dos dois não souber explicar uma parte. Trocar no ensaio garante que qualquer um segura o pitch se algo der errado.

**Decidir até:** o primeiro ensaio, no máximo em 29/11.

### (c) Reenviamos alguma entrega no Moodle?

**Contexto:** a entrega da Sprint 1 no Moodle tem só o nome do Pedro e aponta para `github.com/plreis/PROJETO_FINAL_DEV_WEB` e `plreis.github.io/PROJETO_FINAL_DEV_WEB/`. O link do repositório ainda redireciona para `plreis/proteca`, mas o do GitHub Pages dá 404.

**Recomendação:** se a tarefa da Sprint 1 ainda aceitar envio, reenviar com a dupla e os links atuais. Se não aceitar, não insistir: deixar a dupla e os links atuais no PDF da documentação final e avisar o professor na review de 30/11.

### (d) Adesão de dispositivos e sinal de foco entram como próximo passo?

**Recomendação:** sim, mas só como próximo passo no pitch e na documentação, sem código nesta entrega. Antes de qualquer código é preciso decidir com a escola qual base legal da LGPD vale para isso. O consentimento do estudante não serve (ADR 0004). O sinal guardaria só contagens por sessão, nunca endereço de site nem conteúdo da tela.

**Por quê:** a rota `/telemetry` já existe e o Live já conta eventos de foco perdido, então o caminho técnico é curto. O que falta é a decisão sobre dados de crianças e adolescentes, e essa não é nossa.

### (e) Qual seria o papel de gestor no futuro?

**Recomendação:** manter fora desta entrega. Se voltar, o gestor só leria o inventário e as ocorrências de todas as turmas, sem acesso ao Live nem à tela da turma. Isso pede regra por perfil no backend: hoje o `UserRole.GESTOR` existe no schema, mas nenhuma rota trata ele de forma diferente.

**Junto com isso:** tirar "professores e gestores" do `README.md`, para o texto bater com a ADR 0004. Se a banca perguntar, a resposta é "papel futuro, fora do escopo desta entrega".
