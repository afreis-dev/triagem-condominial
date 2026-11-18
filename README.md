# Triagem do Síndico

Ferramenta para síndicos profissionais com muitos condomínios. Cada ocorrência que chega é classificada com prioridade, categoria, responsável sugerido e motivo. O síndico confirma só o que é urgente, aprova o resto em lote e toda decisão fica registrada.

Projeto da Squad 03 no bootcamp.

## Stack

| Camada | Tecnologia |
|---|---|
| Front | React + TypeScript (TanStack Start e Vite), interfaces criadas com o Lovable |
| Back | Python (FastAPI) |
| Banco | PostgreSQL. Neon em staging e produção, Postgres local com Docker no desenvolvimento (em montagem) |
| Hospedagem | A definir |

## Estrutura do repositório

| Pasta ou arquivo | O que é |
|---|---|
| `frontend/condo-incident-compass/` | Front oficial |
| `prototype/prototipo v.1/` | Protótipo navegável, só de referência |
| `backend/lib/` | Funções do servidor. Por enquanto são versões de teste |
| `CONTRATOS.md` | Contrato de cada função: entrada, saída e erros |

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

O servidor FastAPI e o banco local entram aqui quando forem para a `develop`.

Variáveis de ambiente, como a `DATABASE_URL`, ficam num `.env` local. O `.env` nunca vai para o repositório.

## Como trabalhamos

- `main`: só versões aprovadas. Ninguém envia alteração direto para ela.
- `develop`: branch de integração, onde o time trabalha.
- Cada tarefa vai numa branch criada a partir da `develop`, com nome como `feature/formulario` ou `docs/readme`.
- O pull request é aberto para a `develop`, não para a `main`.
- Quando uma tela estiver funcionando, a `develop` vai para a `main` por pull request.
- Commits no formato `tipo: o que mudou (SQU-00)`, com `feat`, `fix`, `docs` ou `chore`.

## Como pedir revisão de um pull request

1. Envie a branch: `git push -u origin feature/minha-tarefa`.
2. Abra o pull request para a `develop`: `gh pr create --base develop`, ou pelo botão do GitHub.
3. Escreva o que mudou e coloque o código da issue do Linear.
4. Em Reviewers, peça a revisão da Cinthia (`cinthiamartins-nr`).
5. Faça o merge só depois da aprovação. Depois dele, atualize sua branch com `git pull origin develop`.

## Contratos

As funções do servidor seguem o `CONTRATOS.md`. Se o contrato mudar, o arquivo muda no mesmo pull request.
