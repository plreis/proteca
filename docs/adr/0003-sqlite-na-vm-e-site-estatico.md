# ADR 0003 — SQLite num volume da VM e site estático

- **Status:** aceita
- **Data:** 24/11/2026
- **Substitui:** na ADR 0001, as linhas de Banco (Supabase) e de Frontend (build `standalone`)

A API e o site rodam no Coolify de uma VM Ampere da Oracle Cloud (Always Free). Os dados ficam em SQLite, acessado só pelo SQLModel, num arquivo dentro de um volume persistente do Coolify montado em `/app/data`, e não no Postgres do Supabase. O enunciado recomenda banco hospedado porque o disco das plataformas gratuitas é apagado a cada reinício; na nossa VM o volume sobrevive a reinícios e redeploys, e assim não dependemos de um serviço externo nem do pooler de conexões. O site é exportado como estático e servido por nginx, porque não usa nada que exija um servidor Node.

## Consequências

- Sem o volume montado em `/app/data`, cada redeploy apaga o banco, exatamente como acontecia com a memória.
- Voltar para Postgres é trocar `DATABASE_URL`: nenhuma parte do código fala com o banco sem passar pelo SQLModel.
- O backup é uma cópia do arquivo `proteca.db`.
- `NEXT_PUBLIC_API_URL` continua sendo lida no build do site.
