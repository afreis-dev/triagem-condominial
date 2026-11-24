# Triagem do Síndico

Ferramenta para síndicos profissionais com muitos condomínios. Cada ocorrência que chega é classificada com prioridade, categoria, responsável sugerido e motivo. O síndico confirma só o que é urgente, aprova o resto em lote e toda decisão fica registrada.

Projeto da Squad 03 no bootcamp.

## Stack

| Camada | Tecnologia |
|---|---|
| Front | React + TypeScript (TanStack Start e Vite), interfaces criadas com o Lovable |
| Back | Python (FastAPI) |
| Banco | PostgreSQL. Neon em staging e produção, Postgres local com Docker no desenvolvimento |
| Hospedagem | A definir |

## Estrutura do repositório

| Pasta ou arquivo | O que é |
|---|---|
| `frontend/condo-incident-compass/` | Front oficial |
| `prototype/prototipo v.1/` | Protótipo navegável, só de referência |
| `backend/lib/` | Funções do servidor. Por enquanto são versões de teste |
| `CONTRATOS.md` | Contrato de cada função: entrada, saída e erros |
| `docker-compose.yml` e `database/` | Postgres local com Docker e migrations (Alembic) |
| `docs/guia-desenvolvimento.md` | Passo a passo para configurar o ambiente local e integrar as partes |

## Como começar

```bash
git clone git@github.com:afreis-dev/triagem-condominial.git
cd triagem-condominial
git checkout develop
```

### Front

Precisa de Node.js 20 ou mais novo.

```bash
cd frontend/condo-incident-compass
npm install
npm run dev
```

O front abre em `http://localhost:8080`. As rotas são `/c/aurora` (formulário do condomínio), `/fila` e `/ocorrencia/1`.

Outros comandos: `npm run test` roda os testes, `npm run lint` confere o código e `npm run build` gera a versão de produção. Quem usa Bun pode trocar `npm install` por `bun install` e `npm run` por `bun run`.

### Back

Precisa de Python 3.12 ou mais novo. As funções de `backend/lib/` rodam sem banco. Para testar uma delas:

```bash
cd backend
python -c "from lib.classificar import classificar; print(classificar('cheiro de gás no bloco B'))"
```

Para subir o banco local com Docker, o servidor FastAPI e as migrations, siga o `docs/guia-desenvolvimento.md`.

As configurações de ambiente ficam no `.env` da raiz do projeto.

A variável `APP_ENV` define o ambiente utilizado:
- `development`: utiliza `DATABASE_URL_DEV` (PostgreSQL local).
- `production`: utiliza `DATABASE_URL_PROD` (PostgreSQL remoto).

O backend e o Alembic compartilham essa configuração. O `.env` nunca deve ser enviado ao repositório.

## Como trabalhamos

- `main`: só versões aprovadas.
- `develop`: branch de integração, onde o time trabalha.
- Ninguém envia alteração direto para a `main` nem para a `develop`. Tudo entra por pull request.
- Commits no formato `tipo: o que mudou (SQU-00)`, com `feat`, `fix`, `docs` ou `chore`.

## Da tarefa ao pull request

1. Atribua a tarefa a você no Linear e mova para "In Progress".
2. Crie uma branch a partir da `develop`, com nome como `feature/formulario` ou `docs/readme`: `git checkout develop`, `git pull` e `git checkout -b feature/minha-tarefa`.
3. Desenvolva e suba a branch no GitHub: `git push -u origin feature/minha-tarefa`.
4. Abra o pull request para a `develop`: `gh pr create --base develop`, ou pelo botão do GitHub. Escreva o que mudou e coloque o código da issue do Linear.
5. Mova a tarefa para "In Review" no Linear.

## Revisão e merge

A revisão dos pull requests e o merge na `develop` ficam só com os mentores do bootcamp. Quem abre o pull request não dá merge. Depois que um mentor mergear, atualize sua branch com `git pull origin develop`.

## Contratos

As funções do servidor seguem o `CONTRATOS.md`. Se o contrato mudar, o arquivo muda no mesmo pull request.
