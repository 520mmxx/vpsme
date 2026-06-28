# 🏗️ 系统架构文档

> 完整架构说明：容器拓扑、数据流、网络策略、自动修复机制

---

## 一、网络拓扑

```mermaid
graph TB
    subgraph Internet
        USERS[用户浏览器 / 手机]
        TG[Telegram API<br/>api.telegram.org]
        QQ[QQ Bot API<br/>api.sgroup.qq.com]
    end

    subgraph DNS
        CNAME[CNAME 记录<br/>domain → tunnel-id.cfargotunnel.com]
        CF_IP[Cloudflare Edge<br/>104.21.46.97<br/>172.67.137.88]
    end

    subgraph VPS_SERVER["VPS 服务器 (38.252.8.200)"]
        subgraph NET["网络层"]
            direction LR
            WARP["sing-box WARP<br/>WireGuard 隧道<br/>allowed_ips: 0.0.0.0/0"]
            TUN["cloudflared tunnel<br/>ID: 5363ecdd"]
            NGINX_SYS["system nginx<br/>端口 14333"]
        end

        subgraph DOCKER["Docker 容器"]
            NGINX_D["🐳 nginx<br/>80 / 443 SSL"]
            
            subgraph FRONTEND["前端层"]
                WEBUI["Open WebUI<br/>端口 3000<br/>UI / 知识库 / 多模态"]
                ONBOARD["Onboarding Portal<br/>端口 7070"]
            end

            subgraph GATEWAY["网关层"]
                HERMES["Hermes Gateway<br/>端口 8642<br/>Telegram + QQ Bot"]
                BRIDGE["Smart Bridge<br/>端口 8770<br/>路由 + OCR"]
                LLMPROXY["LLM Proxy<br/>端口 8000<br/>模型映射]
            end

            subgraph UPSTREAM["上游代理层"]
                GSPARK["genspark-proxy<br/>端口 7056<br/>→ genspark.ai"]
                KIRO["kiro-gateway<br/>端口 7057<br/>多模型路由"]
                POOL["proxy-pool<br/>端口 7777"]
            end

            subgraph MONITOR["运维层"]
                HEALTH["🩺 health_monitor<br/>72h 循环检测"]
                OLLAMA["ollama<br/>端口 11434"]
            end
        end
    end

    USERS -->|https://domain.com| CNAME
    CNAME --> CF_IP
    CF_IP -->|TLS 隧道| TUN
    TUN --> NGINX_D
    NGINX_D -->|/v1/*| LLMPROXY
    NGINX_D -->|/*| WEBUI
    TG -->|polling| HERMES
    QQ -->|wss://| HERMES
    WEBUI --> BRIDGE --> HERMES
    WEBUI --> LLMPROXY
    HERMES --> LLMPROXY
    
    LLMPROXY --> GSPARK
    LLMPROXY --> KIRO
    GSPARK -->|HTTP| WARP -->|加密| INTERNET
    
    subgraph INTERNET["互联网"]
        GENSPARK["genspark.ai<br/>上游 AI API"]
    end
    
    HEALTH -.->|每 72h| HERMES
    HEALTH -.->|掉线重启| TUN
```

---

## 二、容器拓扑

```mermaid
flowchart LR
    subgraph DOCKER_HOST["Docker Host (network_mode: host)"]
        direction TB
        NGX["nginx<br/>80/443"]
        GP["genspark-proxy<br/>7056"]
        BP["bigbat<br/>7055"]
        KG["kiro-gateway<br/>7057"]
        PP["proxy-pool<br/>7777"]
        HM["hermes<br/>8642"]
        OLL["ollama<br/>11434"]
    end

    subgraph DOCKER_BRIDGE["Docker Bridge Network (opendeepseek-network)"]
        LP["llm-proxy<br/>8000"]
        HB["hermes-bridge<br/>8765"]
        WU["open-webui<br/>8080"]
        SX["searxng<br/>8080"]
    end

    NGX --> LP
    LP --> GP
    LP --> KG
    HM --> LP
    HB --> HM
    WU --> HB
    WU --> LP
    WU --> SX
```

---

## 三、数据流

```mermaid
sequenceDiagram
    participant User as 用户浏览器
    participant CF as Cloudflare
    participant Nginx as Nginx
    participant LP as LLM Proxy
    participant GP as genspark-proxy
    participant GS as genspark.ai
    participant HB as Hermes Bridge
    participant HG as Hermes Gateway
    participant TG as Telegram Bot
    participant QQ as QQ Bot

    rect rgb(200, 230, 255)
        Note over User,GS: 普通聊天（Open WebUI 网页）
        User->>CF: HTTPS 请求
        CF->>Nginx: 解密 + 转发
        Nginx->>HB: /v1/chat/completions
        HB->>LP: 轻量路由
        LP->>GP: 模型映射
        GP->>GS: API 请求
        GS-->>GP: 流式响应
        GP-->>LP: 转发
        LP-->>HB: 转发
        HB-->>Nginx: 响应
        Nginx-->>CF: 加密
        CF-->>User: 显示结果
    end

    rect rgb(230, 255, 230)
        Note over User,QQ: 机器人对话
        TG->>HG: 轮询新消息
        HG->>LP: 处理请求
        LP->>GP: AI 推理
        GP-->>LP: 结果
        LP-->>HG: 回复
        HG-->>TG: 发送消息

        QQ->>HG: WebSocket 消息
        HG->>LP: 处理请求
        LP->>GP: AI 推理
        GP-->>LP: 结果
        LP-->>HG: 回复
        HG-->>QQ: 发送消息
    end

    rect rgb(255, 230, 230)
        Note over User,QQ: 健康检查（每 72h）
        HM->>TG: GET /getMe
        HM->>QQ: POST /getAppAccessToken
        alt 失败
            HM->>HG: 重启信号 (s6)
        end
    end
```

---

## 四、自动修复流程

```mermaid
stateDiagram-v2
    [*] --> Running: 容器启动
    
    Running --> CheckFailed: 72h 健康检查失败
    Running --> OK: 检查通过
    
    CheckFailed --> Restarting: s6 发送 SIGTERM
    
    Restarting --> Connecting: 进程退出
    Connecting --> Reconnected: Telegram 重连
    Connecting --> Reconnected: QQ WebSocket 重连
    
    Reconnected --> Running: 全部平台就绪
    
    OK --> Running: 继续运行
    Running --> Crashed: 进程崩溃
    
    Crashed --> Restarting: s6 自动拉起（<1s）
    
    note right of Restarting
        Docker restart: unless-stopped
        s6 监督: 自动拉起
        健康监视器: 72h 深度检测
    end note
```

---

## 五、端口映射表

| 端口 | 服务 | 协议 | 绑定 | 说明 |
|------|------|------|------|------|
| 80 | Nginx | HTTP | host | Cloudflare 代理入口 |
| 443 | Nginx | HTTPS/SSL | host | Cloudflare 代理入口 |
| 3000 | Open WebUI | HTTP | 0.0.0.0 | 用户界面 |
| 8000 | LLM Proxy | HTTP | 127.0.0.1 | OpenAI 兼容 API |
| 8642 | Hermes Gateway | HTTP | host | Agent API |
| 8770 | Hermes Bridge | HTTP | 127.0.0.1 | Smart Bridge |
| 7056 | genspark-proxy | HTTP | host | 上游代理 |
| 7057 | kiro-gateway | HTTP | 127.0.0.1 | 多模型路由 |
| 7777 | proxy-pool | HTTP | host | 代理池 |
| 11434 | ollama | HTTP | host | 本地 LLM |
| 14333 | system nginx | HTTP | host | sing-box 内部 |

---

## 六、镜像依赖图

```mermaid
graph TD
    genspark-proxy --> proxy-pool
    llm-proxy --> genspark-proxy
    llm-proxy --> kiro-gateway
    hermes --> llm-proxy
    hermes-bridge --> hermes
    hermes-bridge --> llm-proxy
    open-webui --> hermes-bridge
    open-webui --> llm-proxy
    open-webui --> searxng
    nginx --> llm-proxy
    nginx --> open-webui
    health_monitor -.-> hermes
```

---

## 七、安全边界

```mermaid
flowchart LR
    subgraph PUBLIC["公网"]
        CF["Cloudflare<br/>DDoS 防护<br/>WAF 规则"]
    end

    subgraph EDGE["边缘"]
        TUN["Tunnel<br/>加密通道"]
        direction LR
        CF --> TUN
    end

    subgraph VPS["VPS 内部"]
        direction TB
        NG["Nginx<br/>SSL 终止"]
        FW["127.0.0.1 绑定<br/>防火墙规则"]
        ENV["环境变量<br/>密钥隔离"]
        GI[".gitignore<br/>排除密钥文件"]
        
        TUN --> NG
        NG --> FW
    end

    subgraph APP["应用层"]
        API["API Key 认证<br/>Bearer Token"]
        ISO["容器隔离<br/>只读挂载"]
        
        FW --> API
        API --> ISO
    end
```

---

## 八、技术栈

| 层 | 技术 | 版本 |
|----|------|------|
| 运行时 | Python 3.13 | 容器内 |
| 容器编排 | Docker Compose | v2 |
| 反向代理 | nginx | latest |
| 隧道 | cloudflared | latest |
| 代理/VPN | sing-box + WARP | latest |
| Agent 框架 | Hermes Agent | v2026.6.5 |
| AI 代理 | genspark-proxy | 自制 |
| 多模型路由 | kiro-gateway | v0.8 |
| 用户界面 | Open WebUI | latest |
| 搜索引擎 | SearXNG | latest |
| 本地 LLM | ollama | latest |
