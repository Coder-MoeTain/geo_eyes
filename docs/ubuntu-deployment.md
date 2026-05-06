# Ubuntu Deployment Guide

## 1. System prerequisites

- Ubuntu 22.04+
- Docker Engine + Docker Compose plugin
- NVIDIA drivers + container toolkit (for GPU profile)

## 2. Install dependencies

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-plugin git
sudo usermod -aG docker $USER
```

Relogin after group change.

## 3. Deploy

```bash
git clone <your-repo-url> geoeye-ai
cd geoeye-ai
cp .env.example .env
docker compose up --build -d
```

## 4. Optional GPU worker

```bash
docker compose --profile gpu up -d worker-gpu
```

## 5. Health checks

- API health: `curl http://localhost:8000/health`
- OpenAPI docs: `http://localhost:8000/docs`
- Frontend: `http://localhost:5173`
