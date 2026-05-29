# Nginx Reverse Proxy — Architecture

## Overview

A three-container Docker application where Nginx acts as the single entry point, routing traffic to either the frontend static server or the Flask backend API — all on an isolated Docker network.

---

## Container Layout

```mermaid
graph TD
    Browser["🌐 Browser\nhttp://localhost"]

    subgraph Docker Network: app-net
        Nginx["Nginx\n:80\nnginx:alpine"]
        Frontend["Frontend\n:3000\nnginx:alpine\nstatic HTML"]
        Backend["Backend\n:5000\npython:alpine\nFlask"]
    end

    Browser -->|"HTTP :80"| Nginx
    Nginx -->|"location /\nproxy_pass :3000"| Frontend
    Nginx -->|"location /api\nproxy_pass :5000"| Backend
```

---

## Request Routing

```mermaid
flowchart LR
    Client(["Client"])

    Client -->|"GET /"| Nginx
    Client -->|"GET /api/hello"| Nginx
    Client -->|"GET /api/health"| Nginx
    Client -->|"PUT /api/items/:id"| Nginx
    Client -->|"DELETE /api/items/:id"| Nginx

    Nginx -->|"location /"| Frontend["Frontend :3000"]
    Nginx -->|"location /api"| Backend["Backend :5000"]
```

---

## API Endpoints

```mermaid
graph LR
    subgraph GET
        H1["GET /api/hello\n→ {message}"]
        H2["GET /api/health\n→ {status, service, version}"]
    end
    subgraph PUT
        H3["PUT /api/items/:id\n→ {message, id, data}"]
    end
    subgraph DELETE
        H4["DELETE /api/items/:id\n→ {message, id}"]
    end

    Backend["Flask Backend"] --> H1
    Backend --> H2
    Backend --> H3
    Backend --> H4
```

---

## Docker Compose Service Graph

```mermaid
graph TD
    nginx["nginx\nimage: nginx:alpine\nports: 80:80"]
    frontend["frontend\nbuild: ./frontend"]
    backend["backend\nbuild: ./backend"]
    net(["app-net\nbridge network"])

    nginx -->|depends_on| frontend
    nginx -->|depends_on| backend

    nginx --- net
    frontend --- net
    backend --- net
```

---

## File Structure

```mermaid
graph TD
    root["nginx-proxy/"]

    root --> dc["docker-compose.yml"]
    root --> nginxDir["nginx/"]
    root --> feDir["frontend/"]
    root --> beDir["backend/"]

    nginxDir --> nc["nginx.conf\nReverse proxy rules"]

    feDir --> fdf["Dockerfile\nnginx:alpine"]
    feDir --> dcf["default.conf\nlisten :3000"]
    feDir --> html["index.html\nDark dashboard UI"]

    beDir --> bdf["Dockerfile\npython:alpine + Flask"]
    beDir --> py["app.py\n5 API endpoints"]
```

---

## Traffic Flow — Sequence

```mermaid
sequenceDiagram
    participant Browser
    participant Nginx
    participant Frontend
    participant Backend

    Browser->>Nginx: GET /
    Nginx->>Frontend: proxy_pass http://frontend:3000/
    Frontend-->>Nginx: 200 HTML page
    Nginx-->>Browser: 200 HTML page

    Browser->>Nginx: GET /api/hello
    Nginx->>Backend: proxy_pass http://backend:5000/api/hello
    Backend-->>Nginx: 200 {"message": "Hello from backend"}
    Nginx-->>Browser: 200 {"message": "Hello from backend"}

    Browser->>Nginx: GET /api/health
    Nginx->>Backend: proxy_pass http://backend:5000/api/health
    Backend-->>Nginx: 200 {"status": "ok", ...}
    Nginx-->>Browser: 200 {"status": "ok", ...}

    Browser->>Nginx: PUT /api/items/1
    Nginx->>Backend: proxy_pass http://backend:5000/api/items/1
    Backend-->>Nginx: 200 {"message": "Item 1 updated", ...}
    Nginx-->>Browser: 200 {"message": "Item 1 updated", ...}

    Browser->>Nginx: DELETE /api/items/1
    Nginx->>Backend: proxy_pass http://backend:5000/api/items/1
    Backend-->>Nginx: 200 {"message": "Item 1 deleted", "id": 1}
    Nginx-->>Browser: 200 {"message": "Item 1 deleted", "id": 1}
```

---

## Key Design Points

- **Single exposed port** — only Nginx is published on host port `80`. Frontend and Backend are not reachable from outside Docker.
- **Docker internal DNS** — Nginx resolves `frontend` and `backend` by service name; no hardcoded IPs.
- **Read-only config mount** — `nginx.conf` is mounted as `:ro` so the container cannot modify it.
- **No data layer** — all API responses are stateless; PUT and DELETE echo back the request without persisting anything.
