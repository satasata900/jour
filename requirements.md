# Requirements

## System
- Docker Desktop (Compose v2)
- Node.js 20.x (for local development)
- Python 3.11.x (for local development)

## Services (Docker)
- backend (FastAPI)
- agents (LangChain multi-agent)
- db (PostgreSQL 16)
- redis (Redis 7)
- whatsapp-service (Baileys)
- telegram-service (Telethon)

## Node Packages (whatsapp-service)
- @whiskeysockets/baileys
- pino
- qrcode-terminal

## Python Packages (telegram-service)
- telethon
- httpx

## Python Packages (agent-service)
- fastapi
- uvicorn
- SQLAlchemy
- psycopg2-binary
- langchain-core

## Environment
- POSTGRES_USER
- POSTGRES_PASSWORD
- POSTGRES_DB
- BACKEND_INGEST_URL
- WA_LOG_LEVEL
- WA_PHONE_NUMBER (optional)
- TG_API_ID
- TG_API_HASH
- TG_PHONE_NUMBER
- TG_SESSION_NAME (optional)
- TG_LOG_LEVEL (optional)
- TG_INCLUDE_PRIVATE (optional)
- TG_LOG_GROUPS (optional)
- TG_CODE (optional)
- TG_PASSWORD (optional)
- AGENTS_BASE_URL (optional)
