# Deployment

Huong deploy hien tai:

```text
Windows machine
  |
  +-- Docker Desktop
  +-- GitHub Actions self-hosted runner
  +-- docker compose
```

## 1. Dieu kien

- Docker Desktop dang chay.
- `docker run hello-world` chay duoc.
- Repo da push len GitHub.
- File `deploy/docker.env` local da chay duoc.

## 2. Tao GitHub Secret

Vao:

```text
GitHub repo -> Settings -> Secrets and variables -> Actions -> New repository secret
```

Tao secret:

```text
DOCKER_ENV
```

Gia tri cua secret la toan bo noi dung file:

```text
deploy/docker.env
```

Khong dua `deploy/docker.env` len GitHub.

## 3. Cai Self-hosted Runner Tren Windows

Vao:

```text
GitHub repo -> Settings -> Actions -> Runners -> New self-hosted runner
```

Chon:

```text
Windows
```

Lam theo lenh GitHub hien thi de download, config va start runner.

Khi config runner, them label:

```text
rag-chatbot
```

Workflow yeu cau labels:

```text
self-hosted
Windows
rag-chatbot
```

Khuyen nghi chay runner tren may dang chay Docker Desktop.

## 4. Deploy

Deploy thu cong:

```text
GitHub -> Actions -> Deploy Windows Docker Compose -> Run workflow
```

Workflow se chay:

```powershell
docker compose build
docker compose up -d
```

Va kiem tra:

```text
http://127.0.0.1:8000/health/ready
```

## 5. Kiem Tra Sau Deploy

Tren may deploy:

```powershell
docker compose ps
docker compose logs -f backend
```

Mo app:

```text
http://127.0.0.1:8080
```

Health:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

## 6. Luu Y

- Khong chay `docker compose down -v` neu muon giu data/cache model.
- Sau khi BGE-M3 da duoc tai vao Docker volume, co the dat:

```env
EMBEDDING_LOCAL_FILES_ONLY=true
```

- Reranker nen de tat trong deploy local CPU:

```env
RERANKER_ENABLED=false
```

## 7. Sau Nay

Khi can deploy len server/cloud:

- Chuyen SQLite sang PostgreSQL.
- Tach worker indexing thanh service rieng.
- Dung registry image thay vi build tren may deploy.
- Dung HTTPS reverse proxy.
