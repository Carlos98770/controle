# LGR Studio

Aplicação web para análise do Lugar Geométrico das Raízes, com frontend React/Vite e API FastAPI.

## Estrutura

```text
frontend/  interface React/Vite e visualização em LaTeX/KaTeX
backend/   API FastAPI e cálculos numéricos
```

## Executar localmente

Backend:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn main:app --app-dir backend --reload
```

Frontend:

```bash
cd frontend
cp .env.example .env.local
npm ci
npm run dev
```

Acesse `http://localhost:5173`. A API fica disponível em `http://localhost:8000/docs`.

No campo **Ponto de teste**, informe uma coordenada como `1 + 5j`. Para analisar
automaticamente os dois pontos conjugados, use `1 +- 5j` (também é aceito `1 ± 5j`).
As chamadas antigas da API, com `pointReal` e `pointImag`, continuam válidas.

O frontend usa Node.js `22.12+` (versão registrada em `frontend/.nvmrc`).

Se o arquivo `frontend/.env.local` não existir ou `VITE_API_URL` estiver vazio, o Vite usa o proxy local de `vite.config.js`.

## Deploy na Vercel

O deploy recomendado usa dois projetos Vercel ligados ao mesmo repositório Git:

```text
lgr-api   → diretório backend
lgr-web   → diretório frontend
```

### Projeto da API

Ao importar o repositório na Vercel, configure:

```text
Root Directory: backend
Framework Preset: FastAPI (ou Other, se o preset não aparecer)
Build Command: vazio
Output Directory: vazio
```

A Vercel detecta `main.py`, `requirements.txt` e a variável FastAPI `app` automaticamente. Depois do deploy, teste:

```text
https://SEU-BACKEND.vercel.app/api/health
https://SEU-BACKEND.vercel.app/docs
```

Na aba **Environment Variables** do projeto da API, cadastre:

```text
FRONTEND_ORIGINS=https://SEU-FRONTEND.vercel.app
```

O backend também permite previews `*.vercel.app` por meio do CORS configurado em `backend/main.py`.

### Projeto do frontend

Crie um segundo projeto a partir do mesmo repositório e configure:

```text
Root Directory: frontend
Framework Preset: Vite
Install Command: npm ci
Build Command: npm run build
Output Directory: dist
```

Na aba **Environment Variables**, cadastre:

```text
VITE_API_URL=https://SEU-BACKEND.vercel.app
```

A aplicação chamará automaticamente `https://SEU-BACKEND.vercel.app/api/analyze`.

Os arquivos `frontend/vercel.json` e `backend/vercel.json` já deixam essas configurações registradas no projeto.

### Deploy pela CLI

Também é possível executar:

```bash
npm install -g vercel
cd frontend
vercel --prod
cd ../backend
vercel --prod
```

Na primeira execução, escolha o projeto correto e mantenha cada diretório como um projeto Vercel separado.

## Docker

O Docker Compose continua disponível para desenvolvimento local e execução conjunta:

```bash
docker compose up --build
```

Os arquivos Docker não são necessários no deploy tradicional da Vercel.

## Variáveis de ambiente

Os arquivos `.env` reais são ignorados pelo Git. Use estes modelos:

```text
frontend/.env.example
backend/.env.example
```

Nunca coloque tokens, senhas ou chaves privadas no frontend: variáveis `VITE_*` ficam visíveis no navegador.

## Referências

- [Deploy de Vite na Vercel](https://vercel.com/docs/frameworks/frontend/vite)
- [Deploy de FastAPI na Vercel](https://vercel.com/docs/frameworks/backend/fastapi)
- [Runtime Python da Vercel](https://vercel.com/docs/functions/runtimes/python)
