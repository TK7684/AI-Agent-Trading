# Docker Infrastructure Setup

## Quick Start

### Prerequisites
- Docker Desktop installed and running
- pnpm package manager

### 1. Start the Infrastructure

```bash
# Start all services (PostgreSQL, Redis, pgAdmin, Prometheus, Grafana)
docker-compose up -d

# Check services are running
docker-compose ps
```

### 2. Install Dependencies

```bash
# Install PostgreSQL dependencies
pnpm add @neondatabase/serverless

# or use postgres-js for local connections
pnpm add postgres drizzle-orm
```

### 3. Run Database Migrations

```bash
# Generate and run migrations
pnpm db:push
```

### 4. Access Services

| Service | URL | Credentials |
|---------|-----|-------------|
| PostgreSQL | localhost:5432 | crypto_user / crypto_pass_2024 |
| Redis | localhost:6379 | - |
| pgAdmin | http://localhost:5050 | admin@crypto.local / admin |
| Prometheus | http://localhost:9090 | - |
| Grafana | http://localhost:3001 | admin / admin |

### 5. Stop Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (WARNING: deletes data)
docker-compose down -v
```

## Free Cloud Hosting Options

### Neon (PostgreSQL)
- Sign up: https://neon.tech
- Free tier: 0.5GB storage, 300 hours compute/month
- Connection string format: `postgresql://user:password@ep-xxx.region.aws.neon.tech/neondb`

### Railway
- Sign up: https://railway.app
- Free tier: $5 credit/month
- Supports PostgreSQL, Redis, and app hosting

### Render
- Sign up: https://render.com
- Free tier available with limitations

### Self-hosted VPS
- Hetzner: $3.50/month
- DigitalOcean: $4/month
- Or use your own hardware

## Troubleshooting

### PostgreSQL Connection Issues
```bash
# Check logs
docker-compose logs postgres

# Restart PostgreSQL
docker-compose restart postgres
```

### Port Conflicts
Edit `docker-compose.yml` to change port mappings if needed.

### Data Persistence
Data is stored in Docker volumes. Use `docker-compose down` (without -v) to preserve data.
