# Guia Completo de Deploy: Render / Fly.io + Neon PostgreSQL

Este guia descreve o passo a passo detalhado para colocar a aplicação **Privio Commitments** em produção na nuvem utilizando o **Neon** (PostgreSQL Serverless) e o **Render** ou **Fly.io**.

---

## 1. 🐘 Configuração do PostgreSQL no Neon

O [Neon](https://neon.tech) é um banco PostgreSQL Serverless escalável e gratuito.

### Passo a passo:
1. Crie uma conta gratuita em [neon.tech](https://neon.tech).
2. Clique em **"Create Project"** e defina:
   - **Project name**: `privio-db`
   - **Postgres version**: `16` (ou mais recente)
   - **Region**: Escolha a região mais próxima dos servidores de deploy (ex: `US East (Ohio / us-east-2)` para Render/Fly.io).
3. Após a criação, no painel principal do Neon (Dashboard):
   - Localize a caixa **"Connection Details"**.
   - Selecione a opção **"Pooled connection"** (recomendado para serverless).
   - Copie a **Connection String** gerada. Ela terá o formato:
     ```
     postgresql://alex:AbC123dEf@ep-cool-mountain-123456-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require
     ```
   *(Nota: O Privio converte automaticamente o prefixo para `postgresql+psycopg://` internamente, então você pode colar a URL exatamente como copiada do Neon).*

---

## 2. 🚀 Opção A: Deploy no Render (Recomendado)

O [Render](https://render.com) oferece hospedagem web gratuita e suporte nativo ao arquivo de infraestrutura [`render.yaml`](file:///Users/alanviana/Projects/privio_v1/render.yaml).

### Método 1: Deploy com Blueprint (Automático via `render.yaml`)

1. Suba o código do projeto para um repositório no **GitHub** ou **GitLab**.
2. Acesse o [Render Dashboard](https://dashboard.render.com/).
3. Clique em **"New +"** $\rightarrow$ **"Blueprint"**.
4. Conecte seu repositório Git. O Render detectará automaticamente o arquivo `render.yaml`.
5. Preencha a variável `DATABASE_URL` com a string copiada do Neon.
6. Clique em **"Apply"**. O Render irá:
   - Instalar o `uv` e sincronizar todas as dependências com `uv sync --frozen --no-dev`.
   - Gerar credenciais seguras para `EDITOR_PASS` e `VIEWER_PASS`.
   - Iniciar o servidor FastAPI com Uvicorn.
   - Criar as tabelas no PostgreSQL na inicialização.

---

### Método 2: Deploy Manual no Render (Web Service)

1. No [Render Dashboard](https://dashboard.render.com/), clique em **"New +"** $\rightarrow$ **"Web Service"**.
2. Conecte seu repositório Git.
3. Configure os seguintes campos:
   - **Name**: `privio-commitments`
   - **Region**: Mesma do seu Neon (ex: `Ohio (US East)`)
   - **Branch**: `main`
   - **Runtime**: `Python 3`
   - **Build Command**:
     ```bash
     curl -LsSf https://astral.sh/uv/install.sh | sh && export PATH="$HOME/.local/bin:$PATH" && uv sync --frozen --no-dev
     ```
   - **Start Command**:
     ```bash
     export PATH="$HOME/.local/bin:$PATH" && uv run uvicorn app.main:app --host 0.0.0.0 --port $PORT
     ```
   - **Instance Type**: `Free`
4. Na seção **"Environment Variables"**, adicione:
   | Chave | Valor |
   |---|---|
   | `DATABASE_URL` | *Sua connection string do Neon* |
   | `ENVIRONMENT` | `production` |
   | `DEBUG` | `false` |
   | `EDITOR_USER` | `editor` |
   | `EDITOR_PASS` | *Sua senha forte de editor* |
   | `VIEWER_USER` | `viewer` |
   | `VIEWER_PASS` | *Sua senha forte de viewer* |
5. Clique em **"Create Web Service"**.

---

## 3. 🛸 Opção B: Deploy no Fly.io

O [Fly.io](https://fly.io) executa a aplicação empacotada no Dockerfile otimizado multi-stage em qualquer região global.

### Passo a passo com Fly CLI:

1. Instale o Fly CLI (`flyctl`) se ainda não possuir:
   ```bash
   # macOS
   brew install flyctl

   # Linux
   curl -L https://fly.io/install.sh | sh
   ```

2. Faça login na sua conta:
   ```bash
   fly auth login
   ```

3. Inicialize a aplicação (usando o [`fly.toml`](file:///Users/alanviana/Projects/privio_v1/fly.toml) e [`Dockerfile`](file:///Users/alanviana/Projects/privio_v1/Dockerfile)):
   ```bash
   fly launch --no-deploy
   ```

4. Configure as variáveis secretas (incluindo o Neon):
   ```bash
   fly secrets set \
     DATABASE_URL="postgresql://alex:AbC123dEf@ep-cool-mountain-123456-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require" \
     EDITOR_USER="editor" \
     EDITOR_PASS="sua_senha_segura_editor" \
     VIEWER_USER="viewer" \
     VIEWER_PASS="sua_senha_segura_viewer"
   ```

5. Faça o deploy:
   ```bash
   fly deploy
   ```

6. Abra sua aplicação no navegador:
   ```bash
   fly open
   ```

---

## 4. ✅ Verificação pós-deploy

Após o deploy concluir, teste:
- **Health Check**: `https://sua-app.onrender.com/health` (deve retornar `{"status":"ok"}`)
- **Swagger / OpenAPI**: `https://sua-app.onrender.com/docs` (autentique com HTTP Basic Auth)
- **Dashboard Web (Jinja2 + HTMX)**: `https://sua-app.onrender.com/?lang=pt`
