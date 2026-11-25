# Arquitetura do Proteca

Atualizado em 24/11/2026. Os termos seguem o `GLOSSARY.md`. O motivo de cada escolha está em `docs/adr/`.

O que ainda está na branch `sprint-4/persistencia-e-turma` (banco SQLite e tela da turma) aparece marcado com **(Sprint 4)**.

| Parte | Tecnologia | Onde roda |
|---|---|---|
| Site do professor e tela da turma | Next.js 15 exportado como estático, TypeScript, Tailwind | nginx num container do Coolify |
| API | Python 3.12, FastAPI, Pydantic v2, SQLModel | container do Coolify, porta 8000 |
| Banco **(Sprint 4)** | SQLite, arquivo `proteca.db` | volume persistente do Coolify em `/app/data` |
| Login | JWT emitido pela API, senha com Argon2 | API |
| IA de texto e de voz | Gemini, chamado só pela API | Google |

Produção:

- Site: https://app.163.176.54.212.sslip.io
- API: https://api.163.176.54.212.sslip.io (Swagger em `/docs`, saúde em `/api/v1/health`)

## 1. Implantação

```mermaid
flowchart TB
    subgraph sala["Sala de aula"]
        prof["Navegador do professor<br/>notebook, com login"]
        turma["Tela da turma<br/>tablet ou projetor, sem login"]
    end

    subgraph vm["VM Ampere na Oracle Cloud, com Coolify e HTTPS"]
        site["Site estático<br/>nginx, porta 80"]
        api["API FastAPI<br/>uvicorn, porta 8000"]
        db[("SQLite<br/>/app/data/proteca.db<br/>volume persistente")]
    end

    subgraph google["Google AI"]
        gtexto["Gemini texto<br/>4 modelos em rodízio"]
        gtts["Gemini TTS<br/>modelos de voz em rodízio"]
    end

    prof -->|"baixa as páginas"| site
    turma -->|"baixa /turma/"| site
    prof -->|"JSON com Bearer JWT"| api
    turma -->|"rotas públicas /turma, a cada 4 s"| api
    api --> db
    api -->|"objetivo e contagens"| gtexto
    api -->|"fala do Proteca"| gtts
```

Os dois containers rodam na mesma VM, atrás do proxy HTTPS do Coolify (Let's Encrypt em domínios `sslip.io`). O navegador baixa o site do nginx e chama a API direto. Só a API fala com o Gemini, então a chave nunca chega ao navegador.

## 2. Proteca Live

```mermaid
sequenceDiagram
    autonumber
    actor P as Professor
    participant S as Site do professor
    participant A as API FastAPI
    participant B as Banco
    participant G as Gemini texto

    P->>S: clica em "Ler o momento da aula"
    S->>A: POST /api/v1/sessions/sess-01/live com JWT
    A->>B: lê a sessão aberta, as ocorrências e a telemetria
    A->>A: conta os sinais agregados
    loop modelo por modelo, até um responder
        A->>G: objetivo da aula e sinais agregados
        G-->>A: JSON da orientação, ou erro 503, 429 ou tempo esgotado
    end
    alt algum modelo respondeu
        A-->>S: orientação com o nome do modelo e is_mock false
    else nenhum respondeu, ou não há chave
        A->>A: aplica as regras fixas
        A-->>S: orientação de reserva, model local-fallback e is_mock true
    end
    S-->>P: nível de atenção, padrão observado, 2 sugestões e a intervenção
```

O site manda só o id da sessão. A API monta os sinais a partir do banco e tenta os modelos na ordem de `GEMINI_MODEL` e `GEMINI_FALLBACK_MODELS`. Se todos falham, a orientação de reserva sai das regras de `_fallback` em `services/ai_guidance.py`.

| Ordem | Modelo de texto | Modelo de voz (TTS) |
|---|---|---|
| 1 | `gemini-3.5-flash-lite` | `gemini-3.8-flash-tts` |
| 2 | `gemini-3.1-flash-lite` | `gemini-3.8-flash-lite-tts` |
| 3 | `gemini-3.8-flash` | `gemini-3.1-flash-tts-preview` |
| 4 | `gemini-3.6-flash` | `gemini-2.5-flash-preview-tts` |

Os `lite` vêm primeiro porque a cota gratuita deles é de 500 requisições por dia, contra 20 dos `flash`.

O que vai para o Gemini de texto e o que fica na API:

| Vai | Não vai |
|---|---|
| Objetivo da aula | Descrição das ocorrências |
| Dispositivos ativos, eventos de foco perdido, alertas de segurança | Número de patrimônio ou id de dispositivo |
| Ocorrências abertas, total e por categoria | Nome do professor |
| Minutos desde o início da sessão | Qualquer dado de estudante (não existe no sistema) |

## 3. Mostrar para a turma (Sprint 4)

```mermaid
sequenceDiagram
    autonumber
    actor P as Professor
    participant S as Site do professor
    participant A as API FastAPI
    participant B as Banco
    participant V as Gemini TTS
    participant T as Tela da turma

    loop a cada 4 s
        T->>A: GET /api/v1/turma/AULA8B
        A-->>T: objetivo da aula, sem intervenção
    end
    Note over T: Proteca em espera
    P->>S: clica em "Mostrar para a turma"
    S->>A: POST /api/v1/sessions/sess-01/turma com JWT e a intervenção
    A->>B: grava broadcast_intervention e broadcast_at
    A-->>S: intervenção enviada
    par em segundo plano
        A->>V: fala do Proteca, modelo por modelo
        V-->>A: áudio
    end
    T->>A: GET /api/v1/turma/AULA8B
    A-->>T: humor, título, mensagem e fala
    T->>T: troca o humor do mascote e mostra a mensagem
    T->>A: GET /api/v1/turma/AULA8B/voz
    alt áudio pronto
        A-->>T: audio/wav
        T->>T: toca a voz do Proteca
    else nenhum modelo de voz respondeu
        A-->>T: erro
        T->>T: lê a fala com a voz do navegador em pt-BR
    end
```

O professor decide o que a turma vê. A API grava a intervenção na sessão e já pede o áudio em segundo plano, para a tela não ficar esperando a síntese. A tela da turma só manda o código: ela pergunta a cada 4 s se há intervenção nova e, quando há, troca o humor do mascote (acolhimento, curiosidade ou guardião) e toca a voz.

O navegador do tablet só toca áudio depois de um toque na tela. Por isso a tela da turma tem o botão "Ativar o som", que precisa ser tocado uma vez.

| Rota | Quem chama | Login | O que faz |
|---|---|---|---|
| `POST /api/v1/sessions/{id}/turma` | site do professor | JWT | grava a intervenção enviada e dispara a síntese da voz |
| `DELETE /api/v1/sessions/{id}/turma` | site do professor | JWT | tira a intervenção da tela da turma |
| `GET /api/v1/turma/{codigo}` | tela da turma | não | devolve o objetivo da aula e a intervenção enviada, se houver |
| `GET /api/v1/turma/{codigo}/voz` | tela da turma | não | devolve o WAV da fala do Proteca |

As rotas públicas não recebem nada além do código e não usam cookies. Elas não devolvem dispositivos, ocorrências nem nome de professor (ADR 0004).

## 4. Banco (Sprint 4)

```mermaid
erDiagram
    User {
        string id PK
        string username UK "e-mail de login"
        string full_name
        string role "professor"
        string hashed_password "Argon2"
        bool disabled
    }

    School ||--o{ Classroom : "tem"
    School ||--o{ Device : "tem no inventário"
    Classroom ||--o{ LessonSession : "tem"
    LessonSession ||--o{ SessionDevice : "vincula"
    Device ||--o{ SessionDevice : "participa de"
    LessonSession ||--o{ SessionAction : "histórico"
    LessonSession ||--o{ Incident : "tem"
    Incident ||--o{ IncidentAction : "histórico"
    LessonSession ||--o{ TelemetryEvent : "recebe"
    Device |o..o{ Incident : "citado em"
    Device ||..o{ TelemetryEvent : "origem"

    School {
        string id PK
        string name
        string city
    }
    Classroom {
        string id PK
        string school_id FK
        string name "8º Ano B"
        string grade
    }
    Device {
        string id PK
        string school_id FK
        string patrimonio UK
        string type "chromebook, tablet ou notebook"
        string model
        string status "disponivel, em_uso ou manutencao"
    }
    LessonSession {
        string id PK
        string classroom_id FK
        string teacher_name
        string objective
        string status "aberta ou encerrada"
        datetime started_at
        datetime ended_at
        string closing_justification
        string class_code UK "código da turma"
        json broadcast_intervention "intervenção enviada"
        datetime broadcast_at
    }
    SessionDevice {
        string session_id PK, FK
        string device_id PK, FK
    }
    SessionAction {
        string id PK
        string session_id FK
        datetime timestamp
        string action
        string author
        string note
    }
    Incident {
        string id PK
        string session_id FK
        string device_id FK "opcional"
        string category
        string description
        string status "aberta, em_analise ou encerrada"
        datetime created_at
        string closing_justification
    }
    IncidentAction {
        string id PK
        string incident_id FK
        datetime timestamp
        string action
        string author
        string note
    }
    TelemetryEvent {
        string id PK
        string session_id FK
        string device_id FK
        string event_type "foco_perdido, foco_recuperado ou alerta"
        datetime occurred_at
        int duration_seconds
    }
```

A escola é a raiz. A sessão liga a turma aos dispositivos pela tabela `SessionDevice`, porque o mesmo dispositivo passa por várias sessões no mesmo dia. `SessionAction` e `IncidentAction` guardam quem fez o quê e quando. `User` só guarda quem faz login. O diagrama mostra os campos principais, e nenhuma tabela tem campo de estudante.

## 5. Estados

### Sessão de aula

```mermaid
stateDiagram-v2
    [*] --> aberta : professor abre com turma, objetivo e dispositivos
    aberta --> encerrada : professor encerra com justificativa
    encerrada --> [*]
```

Com a sessão aberta funcionam o Live, o registro de ocorrência e o código da turma. Ao encerrar, a API libera os dispositivos que estavam em uso, e o código da turma deixa de abrir. Um Live ou uma ocorrência em sessão encerrada recebe 409.

### Ocorrência

```mermaid
stateDiagram-v2
    state "em análise" as em_analise
    [*] --> aberta : professor registra numa sessão aberta
    aberta --> em_analise : professor analisa
    em_analise --> aberta : volta para aberta
    aberta --> encerrada : encerra com justificativa
    em_analise --> encerrada : encerra com justificativa
    encerrada --> aberta : professor reabre
```

Cada mudança entra no histórico da ocorrência. Encerrar sem justificativa dá 422, e uma transição fora do diagrama dá 409. A tabela de transições está em `INCIDENT_TRANSITIONS`, no repositório.

### Dispositivo

```mermaid
stateDiagram-v2
    state "disponível" as disponivel
    state "em uso" as em_uso
    state "manutenção" as manutencao
    [*] --> disponivel : cadastro no inventário
    disponivel --> em_uso : vinculado ao abrir uma sessão
    em_uso --> disponivel : sessão encerrada
    disponivel --> manutencao : professor marca manutenção
    manutencao --> disponivel : volta da manutenção
```

O estado `em uso` só muda pela sessão: pedir `em_uso` pela rota de status dá 422, e mandar para manutenção um dispositivo em uso dá 409. Abrir uma sessão com um dispositivo que não está disponível também dá 409.

## 6. Onde fica cada regra

| Regra | Arquivo |
|---|---|
| Rotas, uma por recurso | `backend/app/routers/` |
| Contratos de entrada e saída | `backend/app/schemas/` |
| Tabelas SQLModel | `backend/app/models/` |
| Transições de sessão, ocorrência e dispositivo | `backend/app/repositories/` |
| Sinais agregados do Live | `backend/app/services/session_signals.py` |
| Rodízio de modelos e orientação de reserva | `backend/app/services/ai_guidance.py` |
| Voz do Proteca em rodízio | `backend/app/services/voice.py` |
| JWT e senha | `backend/app/auth/` |
| Variáveis de ambiente | `backend/app/core/config.py` |
| Cliente HTTP, token e volta ao login no 401 | `frontend/src/services/api.ts` |
| Proteção das páginas com login | `frontend/src/components/AuthGuard.tsx` |
