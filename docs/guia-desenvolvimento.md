# Guia de desenvolvimento e integração

**Projeto:** Triagem Condominial — Squad 03

## 1. Estrutura proposta do projeto

A estrutura abaixo aproveita os arquivos já desenvolvidos pela equipe, acrescentando a infraestrutura de desenvolvimento e simplificando a organização do front-end.

```text
triagem-condominial/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── fila/
│   │   │   ├── ocorrencia/
│   │   │   └── ui/
│   │   ├── lib/
│   │   ├── routes/
│   │   └── test/
│   ├── public/
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
│
├── backend/
│   ├── lib/
│   │   ├── classificar.py
│   │   ├── salvar_ocorrencia.py
│   │   └── registrar_decisao.py
│   ├── main.py
│   ├── db.py
│   └── requirements.txt
│
├── database/
│   ├── migrations/
│   │   ├── versions/
│   │   └── env.py
│   ├── schema.sql
│   └── seed.sql
│
├── prototype/
│   └── prototipo v.1/
│
├── docs/
│   ├── CONTRATOS.md
│   ├── ambiente-local.md
│   └── guia-desenvolvimento.md
│
├── .github/
├── .env.example
├── .gitignore
├── alembic.ini
├── docker-compose.yml
├── CONTRATOS.md
└── README.md
```

**Observação:** esta é a estrutura desejada após a integração, não a estrutura atual da `develop`. Os arquivos estão distribuídos pelas branches da equipe.

### Sugestão de simplificação do front-end

Atualmente, o projeto React está em `frontend/condo-incident-compass/`.

Como o protótipo antigo será mantido em `prototype/prototipo v.1/`, sugerimos mover o conteúdo de `condo-incident-compass/` diretamente para `frontend/`.

Isso elimina uma pasta intermediária desnecessária e simplifica a execução:

```bash
cd frontend
npm install
npm run dev
```

**Essa alteração deve ser alinhada com o responsável pela PR #3**, que já está reorganizando o front-end, antes de modificar os arquivos.

## 2. Configuração do ambiente local

### Pré-requisitos

- Docker Desktop
- Python 3.12 (versão de referência)
- Node.js 20 ou superior

### PostgreSQL

Na raiz do repositório:

```powershell
Copy-Item .env.example .env
docker compose up -d
docker compose ps
```

Confira se `POSTGRES_DB` e `DATABASE_URL` apontam para o mesmo banco local.

### Migrations com Alembic

O projeto utiliza **Alembic** para versionar alterações na estrutura do PostgreSQL, mantendo os bancos dos desenvolvedores sincronizados.

As migrations ficam em:

```text
database/
└── migrations/
    ├── versions/
    ├── env.py
    └── script.py.mako
```

O arquivo `alembic.ini` fica na raiz do repositório.

**Comandos principais** (executados na raiz, com o ambiente virtual Python ativado):

```powershell
# Verificar a revisão atual do banco
python -m alembic current

# Consultar o histórico de migrations
python -m alembic history

# Aplicar migrations pendentes
python -m alembic upgrade head
```

**Orientações para a equipe:**

- Não alterar diretamente a estrutura do banco sem registrar a mudança em uma migration.
- Antes de criar uma migration, verificar se outro desenvolvedor já está trabalhando na mesma tabela.
- Não executar migrations em staging ou produção sem aprovação.
- Não modificar migrations que já foram aplicadas em ambientes compartilhados.
- A migration inicial será definida a partir do esquema SQL desenvolvido na `feature/db`, após alinhamento com os contratos do projeto.

**Importante:** o Alembic foi configurado na branch `chore/project-setup` e ainda precisa ser integrado à `develop`. Até lá, esses comandos dependem dos arquivos dessa branch.

### Back-end

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn main:app --reload
```

A documentação interativa da API estará em `http://localhost:8000/docs`, após a integração do `main.py`.

### Front-end

Após a reorganização proposta:

```powershell
cd frontend
npm install
npm run dev
```

Enquanto a reorganização não for aprovada, utilizar `frontend/condo-incident-compass/`.

## 3. Integração das funcionalidades

### Front-end

Preservar os componentes e as rotas já desenvolvidos. A integração com o back-end deve seguir os contratos aprovados, sem modificar desnecessariamente a interface existente.

### Back-end

A equipe já desenvolveu `backend/main.py`, `backend/db.py` e as funções em `backend/lib/`.

Esses arquivos precisam ser integrados respeitando as responsabilidades de cada módulo. Não criar implementações duplicadas de rotas ou regras de negócio.

As funções temporárias devem ser substituídas pelas implementações definitivas somente após validação.

### Banco de dados

Os arquivos `schema.sql` e `seed.sql` foram desenvolvidos originalmente em `sql/`. A proposta é organizá-los em `database/`, junto das migrations do Alembic.

Antes de realizar essa mudança, confirmar com o responsável pelo banco.

**Não executar migrations definitivas antes de alinhar o esquema com `CONTRATOS.md`.**

## 4. Fluxo de trabalho com Git

Criar uma branch a partir da `develop` atualizada:

```bash
git checkout develop
git pull origin develop
git checkout -b feature/minha-funcionalidade
```

Para incorporar as mudanças já aprovadas na `develop`:

```bash
git checkout develop
git pull origin develop
git checkout feature/minha-funcionalidade
git merge develop
```

Resolver eventuais conflitos preservando as alterações das duas partes.

Depois de validar o funcionamento, abrir um pull request para `develop` e solicitar revisão.

Não realizar merges diretamente nas branches compartilhadas.

## 5. Checklist antes do PR

- [ ] A funcionalidade existente continua funcionando.
- [ ] Não foram criados componentes, endpoints ou funções duplicadas.
- [ ] Os contratos entre front-end, back-end e banco foram respeitados.
- [ ] As dependências necessárias foram registradas.
- [ ] Arquivos `.env`, `.venv` e caches não foram versionados.
- [ ] As alterações foram testadas.
- [ ] O PR está direcionado à `develop` para revisão.

---

**Regra principal:** integrar o que cada colega já desenvolveu, preservando as funcionalidades e evitando mudanças estruturais sem alinhamento com o time.
