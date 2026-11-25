# Proteca — site (Next.js)

Site do professor e tela da turma. Next.js 15 (App Router), TypeScript e Tailwind, exportado como site estático (`output: "export"` em `next.config.ts`). Os dados vêm da API FastAPI em `../backend`; o site não guarda nada além do token de login.

## Estrutura

```text
src/
├── app/
│   ├── (private)/    páginas com login: painel, sessões, ocorrências, dispositivos
│   ├── (public)/     login e tela da turma (`/turma/`), sem login
│   ├── layout.tsx
│   └── not-found.tsx
├── components/       peças reutilizáveis (AppShell, AuthGuard, Modal, StatusBadge, FieldError, ProtecaMascot...)
├── context/          AuthContext (token) e SchoolContext (dados da escola)
├── data/             fixtures.ts, dados de exemplo usados pelo mockService
├── features/         blocos por assunto: sessions (cards e Live), incidents (formulário e lista) e turma (código da turma)
├── services/         uma função por chamada à API; api.ts é o cliente base
└── types/            tipos alinhados aos schemas da API (index.ts e turma.ts)
Dockerfile            build do site e imagem nginx
nginx.conf            configuração do nginx dentro do container
```

| URL | Página | Login |
|---|---|---|
| `/login/` | login do professor | não |
| `/` | painel | sim |
| `/sessoes/`, `/sessoes/nova/` | lista e abertura de sessões | sim |
| `/sessoes/detalhe/?id=sess-01` | detalhe da sessão com o Live | sim |
| `/ocorrencias/`, `/ocorrencias/nova/` | lista e registro de ocorrências | sim |
| `/dispositivos/` | inventário | sim |
| `/turma/?codigo=AULA8B` | tela da turma | não |

O `mockService` ainda atende parte do `SchoolContext` (ocorrências, escola e turmas). Sessões, dispositivos, o Live e a tela da turma já chamam a API. O estado de cada tela está em `docs/status-entrega.md`.

A tela da turma é a única página sem login que muda sozinha. Ela pergunta à API a cada 4 s se há intervenção nova, troca o humor do mascote (acolhimento, curiosidade ou guardião) e toca a voz. O navegador só libera o som depois de um toque, por isso a tela tem o botão "Ativar o som". `services/turmaService.ts` faz essas chamadas sem token e sem cookies.

O export estático não gera páginas para rotas dinâmicas como `/sessoes/[id]`. Por isso o id da sessão e o código da turma vão na query string.

O token fica no `localStorage` (`proteca_token`). Sem token, o `AuthGuard` manda para `/login/`. Se a API responder 401, `services/api.ts` apaga o token e volta para `/login/?expirou=1`, que mostra o aviso de sessão expirada.

## Variáveis

| Variável | Exemplo | Uso |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000/api/v1` | Endereço da API. Termina em `/api/v1`, sem barra no final. |
| `NEXT_PUBLIC_BASE_PATH` | vazio | Só para publicar num subcaminho, como o GitHub Pages da Sprint 1. Fica vazio no Coolify. |

As duas são lidas no build: o Next.js grava o valor no JavaScript gerado. Mudar a URL da API exige um build novo. Nunca coloque chave ou senha numa variável `NEXT_PUBLIC_*`, porque ela vai para o navegador.

## Rodar em desenvolvimento

Precisa do Node 22 (a mesma versão do `Dockerfile`) e da API rodando em `http://localhost:8000`.

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

O site abre em http://localhost:3000. A API já aceita essa origem no CORS por padrão (`BACKEND_CORS_ORIGINS`). O login de demonstração é `professor@proteca.local`, com a senha configurada na API.

`npm run lint` roda o ESLint. `npm run build` também roda a checagem de tipos.

## Build estático e nginx

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1 npm run build   # gera out/
python3 -m http.server 3000 -d out                              # serve out/ para conferir
```

Em produção o site roda num container com nginx. O `Dockerfile` tem duas etapas:

1. `node:22-alpine` instala as dependências e roda `npm run build`. O build para com erro se `NEXT_PUBLIC_API_URL` não for passada.
2. `nginx:1.27-alpine` copia a pasta `out/` para `/usr/share/nginx/html` e escuta na porta 80.

```bash
docker build --build-arg NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1 -t proteca-site .
docker run --rm -p 8080:80 proteca-site
```

No Coolify, `NEXT_PUBLIC_API_URL` precisa estar marcada como variável de build, senão o valor não chega ao `npm run build`.

O que o `nginx.conf` faz:

- `try_files $uri $uri/ $uri.html =404` faz `/login` abrir `login/index.html`, já que o export usa `trailingSlash: true`.
- `absolute_redirect off` evita que o redirecionamento de `/login` para `/login/` troque `https` por `http` atrás do proxy do Coolify.
- Os arquivos de `/_next/static/` têm cache de um ano, porque o nome deles muda a cada build.
- A tela da turma abre em `/turma/?codigo=AULA8B`. O nginx só entrega `turma/index.html`; o código vai na query string e a API valida.
- Página não encontrada cai em `/404.html`.
