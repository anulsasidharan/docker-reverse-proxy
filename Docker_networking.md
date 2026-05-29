# Docker Networking — Nginx Reverse Proxy

## Overview

Docker networking in this project separates **external traffic** (what the host machine and browser can reach) from **internal traffic** (container-to-container communication invisible to the outside world).

---

## Big Picture — External vs Internal

```mermaid
graph TB
    subgraph HOST["Host Machine"]
        Browser["🌐 Browser"]
        HostPort["Host Port :80"]
    end

    subgraph DOCKER["Docker Engine"]
        subgraph APPNET["app-net  (bridge network)"]
            Nginx["nginx\n172.20.0.2:80"]
            Frontend["frontend\n172.20.0.3:3000"]
            Backend["backend\n172.20.0.4:5000"]
        end
    end

    Browser -->|"HTTP request"| HostPort
    HostPort -->|"port mapping\n80 → 80"| Nginx
    Nginx -->|"internal DNS\nfrontend:3000"| Frontend
    Nginx -->|"internal DNS\nbackend:5000"| Backend

    style HOST fill:#1a1a2e,stroke:#4a4a8a,color:#e2e8f0
    style DOCKER fill:#0d1117,stroke:#30363d,color:#e2e8f0
    style APPNET fill:#1e2330,stroke:#2d3448,color:#e2e8f0
```

> **Note:** IP addresses shown are illustrative. Docker assigns them dynamically from the bridge subnet.

---

## External Networking — Host to Docker

Only one port is published to the host. The frontend and backend are fully isolated from the host network.

```mermaid
graph LR
    subgraph Internet["External / Host"]
        Browser["Browser"]
        CurlTool["curl / API client"]
    end

    subgraph DockerPublished["Published Ports"]
        P80["0.0.0.0:80"]
    end

    subgraph DockerInternal["Docker Internal (not reachable from host)"]
        P3000["frontend:3000 ❌"]
        P5000["backend:5000 ❌"]
    end

    Browser -->|"✅ reachable"| P80
    CurlTool -->|"✅ reachable"| P80
    Browser -. "❌ blocked" .-> P3000
    Browser -. "❌ blocked" .-> P5000
```

---

## Internal Networking — Container DNS Resolution

Docker's embedded DNS server automatically registers each service name as a hostname inside `app-net`. No `/etc/hosts` editing or IP hardcoding is needed.

```mermaid
sequenceDiagram
    participant Nginx
    participant DockerDNS as Docker DNS\n(embedded resolver)
    participant Frontend
    participant Backend

    Note over Nginx: Request arrives for /
    Nginx->>DockerDNS: resolve "frontend"
    DockerDNS-->>Nginx: 172.20.0.3
    Nginx->>Frontend: TCP connect → 172.20.0.3:3000

    Note over Nginx: Request arrives for /api
    Nginx->>DockerDNS: resolve "backend"
    DockerDNS-->>Nginx: 172.20.0.4
    Nginx->>Backend: TCP connect → 172.20.0.4:5000
```

---

## Network Isolation Model

```mermaid
graph TD
    subgraph default_bridge["default bridge (docker0)\nnot used"]
        DB["isolated — no containers here"]
    end

    subgraph appnet["app-net (user-defined bridge)"]
        N["nginx"]
        F["frontend"]
        B["backend"]

        N <-->|"DNS + TCP"| F
        N <-->|"DNS + TCP"| B
        F <-.->|"no direct route\n(not needed)"| B
    end

    Host["Host eth0\n:80 only"] -->|port publish| N
```

User-defined bridge networks (like `app-net`) provide:
- **Automatic DNS** — containers resolve each other by service name.
- **Isolation** — containers on `app-net` cannot communicate with containers on other networks unless explicitly connected.
- **No link flags needed** — unlike the legacy default bridge, no `--link` required.

---

## Port Mapping Detail

```mermaid
graph LR
    subgraph Host
        H80["0.0.0.0:80\n(all interfaces)"]
    end

    subgraph Nginx Container
        C80["eth0:80\n(container NIC)"]
    end

    subgraph Frontend Container
        C3000["eth0:3000\n(internal only)"]
    end

    subgraph Backend Container
        C5000["eth0:5000\n(internal only)"]
    end

    H80 -->|"iptables NAT rule\nadded by Docker"| C80
    C80 -->|"proxy_pass\nhttp://frontend:3000"| C3000
    C80 -->|"proxy_pass\nhttp://backend:5000"| C5000
```

---

## docker-compose.yml — Network Declarations

```mermaid
graph TD
    DC["docker-compose.yml"]

    DC --> SVC["services:"]
    SVC --> SN["nginx → networks: [app-net]"]
    SVC --> SF["frontend → networks: [app-net]"]
    SVC --> SB["backend → networks: [app-net]"]

    DC --> NET["networks:"]
    NET --> AN["app-net:\n(driver: bridge — default)"]

    AN -->|"creates"| BridgeNIC["Docker bridge NIC\nbr-xxxxxxxx"]
    SN & SF & SB -->|"attached to"| BridgeNIC
```

---

## Inbound Packet Journey

```mermaid
flowchart TD
    A["Browser sends\nGET http://localhost/api/hello"]
    B["Host kernel receives packet\non port 80"]
    C["Docker iptables NAT rule\nDNAT → nginx container IP:80"]
    D["Nginx evaluates\nlocation /api block"]
    E["Nginx resolves 'backend'\nvia Docker DNS → 172.20.0.4"]
    F["Nginx opens TCP connection\nto backend:5000"]
    G["Flask handles request\nreturns JSON"]
    H["Response travels back\nthrough Nginx to browser"]

    A --> B --> C --> D --> E --> F --> G --> H
```

---

## What Is and Isn't Exposed

| Resource | Exposed to Host | Exposed on app-net |
|---|---|---|
| `nginx` port 80 | ✅ Yes — mapped to host :80 | ✅ Yes |
| `frontend` port 3000 | ❌ No | ✅ Yes (nginx only) |
| `backend` port 5000 | ❌ No | ✅ Yes (nginx only) |
| Container-to-container DNS | N/A | ✅ Automatic |

---

## Key Takeaways

- **One public surface** — only port 80 on Nginx is reachable from outside Docker.
- **Service-name DNS** — Docker's built-in resolver means `proxy_pass http://backend:5000` works without any IP configuration.
- **Bridge isolation** — `app-net` is a private L2 segment; traffic between containers never leaves the Docker host.
- **iptables integration** — Docker automatically manages NAT rules for published ports; no manual firewall config needed.
- **depends_on order** — Nginx waits for `frontend` and `backend` to start before itself, preventing failed proxy connections on cold start.
