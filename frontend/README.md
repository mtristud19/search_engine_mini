# Signals frontend

React + TypeScript + Vite editorial frontend for this Django REST API.

## Run locally

1. Start the Django stack on port `8000`.
2. Run `npm install` and `npm run dev` from this directory.

## Environment modes

`VITE_API_BASE_URL` is deliberately `/api` in both committed modes, so the
browser never needs a backend origin or secret. The web server/proxy owns the
backend connection.

| File | Used by | Purpose |
| --- | --- | --- |
| `.env.development` | `npm run dev` | Vite proxies `/api` to `VITE_API_PROXY_TARGET` (default `http://localhost:8000`). |
| `.env.production` | `npm run build` | Uses `/api`; the Compose Nginx service proxies it to Django. |
| `.env*.example` | Reference | Safe values for new environments. |

For machine-specific overrides, create `.env.local`, `.env.development.local`,
or `.env.production.local`; these files are ignored by Git. Do not place
passwords, tokens, or private backend settings in any `VITE_*` variable.

For a separately deployed frontend, set a public API origin only when CORS and
CSRF configuration has been intentionally added to Django.

The editor uses the backend's existing Basic authentication contract. It keeps its encoded Authorization value in `sessionStorage` only, never in localStorage, and clears it on sign-out. A cookie/session login endpoint would be a better production authentication contract.

## Docker Compose

Build and start the full stack, including the production frontend:

```sh
docker compose up --build
```

Open `http://localhost:5173`. Nginx serves the Vite build, falls back to
`index.html` for direct React routes, and proxies `/api/` to the Django `web`
service on the internal Compose network.

## Supported backend contract

Public: `documents`, `categories`, Elasticsearch `search`, and `similar` documents. Editor: document CRUD and category reads. No server endpoints exist for tags, authors, media, metrics, user session login, article slugs, or images, so those are intentionally not presented as working features.
