# AgentGuard Web

React dashboard for the AgentGuard demo product.

## Setup

```bash
cd apps/web
npm install
```

## Run

From the repository root:

```bash
make demo
```

Or run the services separately:

```bash
python3 scripts/run_api.py
npm --prefix apps/web run dev
```

Open `http://127.0.0.1:5173`.

## Verify

```bash
npm --prefix apps/web test
npm --prefix apps/web run build
npm --prefix apps/web audit
```
