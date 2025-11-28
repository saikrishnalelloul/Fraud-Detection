<div align="center">

# Fraud Detection Dashboard

Real-time payments monitoring pipeline combining streaming analytics, statistical anomaly detection, and domain heuristics with a polished React dashboard.

</div>

## Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Getting Started](#getting-started)
   - [1. Clone the repository](#1-clone-the-repository)
   - [2. Start the backend stack](#2-start-the-backend-stack)
   - [3. Start the frontend](#3-start-the-frontend)
- [Environment Variables](#environment-variables)
- [Key Endpoints](#key-endpoints)
- [Project Structure](#project-structure)
- [Operational Notes](#operational-notes)
- [Troubleshooting](#troubleshooting)
- [Roadmap Ideas](#roadmap-ideas)

## Overview
The project simulates a card-payments fraud monitoring system. Synthetic transactions are streamed through Kafka, enriched and scored by a Python consumer that blends an Isolation Forest model with rule-based heuristics (amount spikes, geographic velocity, velocity bursts). Results are persisted to SQLite and surfaced through a React dashboard that visualizes totals, status distribution, and detailed verdicts for user-provided scenarios.

## Features
- **Streaming pipeline**: Kafka producer and consumer containers continuously generate and score transactions.
- **Hybrid detection**: Isolation Forest anomaly scoring augmented with rule rules (`amount_spike`, `geo_velocity`, `high_velocity`, `huge_amount`, `model_anomaly`).
- **Explainable insights**: `fraud_reason` metadata is stored in SQLite and displayed in the UI.
- **Interactive validation**: Frontend lookup lets analysts probe a specific `user_id` and `amount`, returning live history context.
- **Dashboard polish**: Responsive layout with live status indicator, donut chart distribution, and sortable table.
- **Containerized backend**: Docker Compose orchestrates Zookeeper, Kafka, producer, consumer, and Flask API with a shared volume for SQLite.

## Architecture
```
┌─────────┐     ┌─────────┐     ┌──────────────┐
│Producer │ ──▶ │  Kafka  │ ──▶ │ Consumer     │
│(Python) │     │ Broker  │     │ (rules + ML) │
└─────────┘     └─────────┘     └──────┬───────┘
                                                            │
                                                            ▼
                                                    SQLite DB
                                                            │
                                                            ▼
                                          ┌──────────────────┐
                                          │ Flask REST API   │
                                          └────────┬─────────┘
                                                       │
                                                       ▼
                                          React Dashboard (frontend)
```

## Prerequisites
- Docker Desktop 4.x or newer (includes Docker Compose v2)
- Node.js 18+ and npm (for running the React frontend)
- (Optional) Python 3.10+ if you plan to run backend services outside Docker

## Getting Started

### 1. Clone the repository
```bash
git clone https://github.com/<your-user>/fraud-detection.git
cd fraud-detection
```

### 2. Start the backend stack
The main `docker-compose.yml` handles Zookeeper, Kafka, producer, consumer, and Flask API.

```bash
docker compose up --build
```

This command will:
- build backend images (producer, consumer, API)
- provision Zookeeper and Kafka
- seed the SQLite database (`transactions_data` docker volume)
- expose the API on `http://localhost:5000`

> **Tip:** The first build may take a few minutes while Python dependencies install.

### 3. Start the frontend

```bash
cd frontend
npm install
npm start
```

The React development server runs on `http://localhost:3000` and proxies API calls to the Flask service.

## Environment Variables
The backend reads these variables (defaults shown):

| Variable | Default | Description |
|----------|---------|-------------|
| `KAFKA_BROKER` | `kafka:9092` within Docker | Kafka bootstrap server |
| `TRANSACTIONS_DB_PATH` | `/app/data/transactions.db` | SQLite file location (shared volume) |
| `DATABASE_URL` | _(unused placeholder)_ | Reserved for future DB integrations |

Front-end specific configuration lives in `.env` (create if needed). By default it calls the API at `http://127.0.0.1:5000`.

## Key Endpoints

| Method | Route | Description |
|--------|-------|-------------|
| `GET` | `/` | Health message for quick status checks |
| `GET` | `/transactions?n=20` | Returns `{ items, meta }` with recent transactions plus aggregate totals |
| `POST` | `/predict` | Scores a single transaction payload (used primarily by producer/legacy clients) |
| `POST` | `/validate-transaction` | Evaluates a hypothetical transaction using latest user history and rule heuristics |

Example validation payload:
```json
{
   "user_id": "1087",
   "amount": 1500,
   "location": "Hyderabad"
}
```

## Project Structure
```
backend/
   app.py                 # Flask API exposing transaction and validation endpoints
   kafka_consumer_worker.py# Kafka consumer + detection logic
   kafka_producer.py      # Synthetic transaction generator
   fraud_rules.py         # Shared rule evaluation helpers and descriptions
   fraud_model.py         # Isolation Forest training utilities
   database.py            # SQLite helpers (shared volume aware)
   init_db.py             # Ensures schema exists before consumer starts
   Dockerfile.*           # Docker build configurations

frontend/
   src/App.js             # React dashboard (filters, charts, validation panel)
   src/App.css            # Dashboard styling
   package.json           # React app metadata

docker-compose.yml       # Orchestrates backend services + shared volume
```

## Operational Notes
- **Data volume**: Transactions persist in the `transactions_data` Docker volume. Remove with `docker volume rm fraud-detection-project_transactions_data` if you want a clean slate.
- **Hot reload**: The React dev server supports hot module replacement; the Flask API inside Docker requires a rebuild or container restart for backend code changes.
- **Fraud rules**: Reasons stored in `fraud_reason` include `amount_spike`, `large_amount`, `geo_velocity`, `high_velocity`, `huge_amount`, and `model_anomaly` labels. They appear as tooltips in the status column.
- **Manual validation**: The dashboard’s “Sync table results” toggle controls whether the transaction table filters mirror the lookup fields.

## Troubleshooting
- **Dashboard shaking/scroll jumps**: Make sure the backend is running so `/transactions` returns consistent payloads. UI layout has built-in guardrails to avoid jitter, but dramatic data swings can still shuffle the table.
- **Kafka not ready**: If the consumer logs `NoBrokersAvailable`, wait a few seconds for Kafka to finish booting or restart with `docker compose restart consumer`.
- **Port conflicts**: Ensure ports `5000`, `3000`, `2181`, and `29092` are free before starting the stack.
- **Stale data**: Delete the Docker volume noted above to reset the dataset.

## Roadmap Ideas
- Swap SQLite for PostgreSQL or another managed store.
- Add authentication and role-based dashboards.
- Integrate batch evaluation or back-testing UI for historical datasets.
- Expand the model training pipeline with scheduled retraining notebooks.
- Produce alert webhooks or Slack notifications when specific fraud rules fire.

---

Happy detecting! 🚀 Feel free to open issues or pull requests as you build on top of this foundation.
