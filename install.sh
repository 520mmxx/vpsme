#!/usr/bin/env bash
# ============================================================
# OpenDeepSeek 一键安装脚本（VPS / 服务器专用）
# 用法：
#   bash install.sh
#   bash install.sh --domain example.com --email admin@example.com
#   bash install.sh --no-nginx --no-tunnel
#   bash install.sh --help
# ============================================================
set -euo pipefail

# ════════════════════════════════════════════════════════════
# 颜色 / 输出工具
# ════════════════════════════════════════════════════════════
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m'

info()    { echo -e "${CYAN}  >>>${NC} $*"; }
ok()      { echo -e "${GREEN}  ✅${NC} $*"; }
warn()    { echo -e "${YELLOW}  ⚠️${NC}  $*"; }
err()     { echo -e "${RED}  ❌${NC} $*" >&2; }
die()     { err "$*"; exit 1; }
hr()      { echo -e "${BLUE}────────────────────────────────────────────────────────${NC}"; }
step()    { echo -e "${MAGENTA}[${1}/${TOTAL}]${NC} $2"; }

# ════════════════════════════════════════════════════════════
# 命令行参数解析
# ════════════════════════════════════════════════════════════
DOMAIN=""
EMAIL=""
INSTALL_NGINX=true
INSTALL_TUNNEL=true
INSTALL_DIR="/opt/opendeepseek"

usage() {
    cat <<EOF
用法: bash install.sh [选项]

选项:
  --domain DOMAIN    设置 Nginx 域名（自动配置 SSL）
  --email EMAIL      Let's Encrypt 邮箱（与 --domain 配合使用）
  --no-nginx        跳过 Nginx 安装和配置
  --no-tunnel       跳过 Cloudflare Tunnel 安装
  --dir PATH        安装目录（默认: /opt/opendeepseek）
  --help            显示此帮助信息
EOF
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --domain) DOMAIN="$2"; shift 2 ;;
        --email) EMAIL="$2"; shift 2 ;;
        --no-nginx) INSTALL_NGINX=false; shift ;;
        --no-tunnel) INSTALL_TUNNEL=false; shift ;;
        --dir) INSTALL_DIR="$2"; shift 2 ;;
        --help|-h) usage ;;
        *) die "未知参数: $1（使用 --help 查看帮助）" ;;
    esac
done

TOTAL=9

# ════════════════════════════════════════════════════════════
# 横幅
# ════════════════════════════════════════════════════════════
clear
echo -e "${BOLD}${BLUE}"
echo "  ██████╗ ██████╗ ███████╗███╗   ██╗██████╗ ███████╗███████╗██████╗ "
echo " ██╔═══██╗██╔══██╗██╔════╝████╗  ██║██╔══██╗██╔════╝██╔════╝██╔══██╗"
echo " ██║   ██║██████╔╝█████╗  ██╔██╗ ██║██║  ██║█████╗  █████╗  ██████╔╝"
echo " ██║   ██║██╔═══╝ ██╔══╝  ██║╚██╗██║██║  ██║██╔══╝  ██╔══╝  ██╔═══╝ "
echo " ╚██████╔╝██║     ███████╗██║ ╚████║██████╔╝███████╗███████╗██║     "
echo "  ╚═════╝ ╚═╝     ╚══════╝╚═╝  ╚═══╝╚═════╝ ╚══════╝╚══════╝╚═╝     "
echo -e "${NC}"
echo -e "${CYAN}         VPS 一键部署脚本  •  Linux x86_64${NC}"
echo -e "${CYAN}         文档: https://github.com/opendeepseek/opendeepseek${NC}"
hr

# ════════════════════════════════════════════════════════════
# Step 1: 系统要求检查
# ════════════════════════════════════════════════════════════
step 1 "检查系统环境..."

# 架构检查
ARCH=$(uname -m)
if [[ "$ARCH" != "x86_64" ]]; then
    die "仅支持 x86_64 架构，当前架构: $ARCH"
fi
ok "架构: $ARCH"

# OS 检查
if [[ "$(uname -s)" != "Linux" ]]; then
    die "仅支持 Linux 系统，当前系统: $(uname -s)"
fi

# 检测发行版
DISTRO=""
PKG_MANAGER=""
if command -v apt-get &>/dev/null; then
    DISTRO="debian"
    PKG_MANAGER="apt"
elif command -v dnf &>/dev/null; then
    DISTRO="fedora"
    PKG_MANAGER="dnf"
elif command -v yum &>/dev/null; then
    DISTRO="centos"
    PKG_MANAGER="yum"
else
    die "不支持的 Linux 发行版（仅支持 Debian/Ubuntu/CentOS/Fedora）"
fi
ok "发行版: $DISTRO"

# root / sudo 检查
if [[ $EUID -ne 0 ]]; then
    if command -v sudo &>/dev/null; then
        warn "当前不是 root 用户，脚本将使用 sudo 提权"
        SUDO="sudo"
    else
        die "请以 root 用户运行，或安装 sudo"
    fi
else
    SUDO=""
fi
ok "权限: $([[ $EUID -eq 0 ]] && echo 'root' || echo 'sudo 可用')"

# ════════════════════════════════════════════════════════════
# Step 2: 安装 Docker + Docker Compose Plugin
# ════════════════════════════════════════════════════════════
step 2 "安装 Docker 环境..."

install_docker() {
    info "检测到 Docker 未安装，开始安装..."
    if [[ "$DISTRO" == "debian" ]]; then
        $SUDO apt-get update -qq
        $SUDO apt-get install -y -qq ca-certificates curl
        $SUDO install -m 0755 -d /etc/apt/keyrings
        $SUDO curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
        $SUDO chmod a+r /etc/apt/keyrings/docker.asc
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo \"$VERSION_CODENAME\") stable" | $SUDO tee /etc/apt/sources.list.d/docker.list > /dev/null
        $SUDO apt-get update -qq
        $SUDO apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin
    elif [[ "$DISTRO" == "centos" || "$DISTRO" == "fedora" ]]; then
        $SUDO $PKG_MANAGER install -y yum-utils
        $SUDO yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
        $SUDO $PKG_MANAGER install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    fi
    $SUDO systemctl enable docker --now
}

if command -v docker &>/dev/null; then
    ok "Docker 已安装 ($(docker --version 2>/dev/null || echo '?'))"
else
    install_docker
    ok "Docker 安装完成 ($(docker --version))"
fi

if docker compose version &>/dev/null; then
    ok "Docker Compose Plugin 可用"
else
    # 尝试安装 compose plugin
    if [[ "$DISTRO" == "debian" ]]; then
        $SUDO apt-get install -y -qq docker-compose-plugin 2>/dev/null || true
    fi
    if ! docker compose version &>/dev/null; then
        die "Docker Compose Plugin 安装失败，请手动安装: $SUDO apt-get install docker-compose-plugin"
    fi
    ok "Docker Compose Plugin 已安装"
fi

# 确保 docker 可用（非 root 用户可能需重新登录）
if ! docker info &>/dev/null; then
    warn "Docker 守护进程未运行，尝试启动..."
    $SUDO systemctl start docker || die "无法启动 Docker 守护进程"
    ok "Docker 已启动"
fi

# ════════════════════════════════════════════════════════════
# Step 3: 安装必需工具（git, curl, openssl）
# ════════════════════════════════════════════════════════════
step 3 "安装必需工具..."

MISSING=()
for tool in git curl openssl; do
    if ! command -v "$tool" &>/dev/null; then
        MISSING+=("$tool")
    fi
done

if [[ ${#MISSING[@]} -gt 0 ]]; then
    info "安装缺失工具: ${MISSING[*]}"
    if [[ "$DISTRO" == "debian" ]]; then
        $SUDO apt-get install -y -qq "${MISSING[@]}"
    else
        $SUDO $PKG_MANAGER install -y "${MISSING[@]}"
    fi
fi
ok "工具检查完成"

# ════════════════════════════════════════════════════════════
# Step 4: 克隆仓库
# ════════════════════════════════════════════════════════════
step 4 "克隆项目代码..."

REPO_URL="https://github.com/opendeepseek/opendeepseek.git"

if [[ -d "$INSTALL_DIR" ]]; then
    warn "目录已存在: $INSTALL_DIR"
    echo ""
    echo "  请选择操作："
    echo "    1) 覆盖（删除后重新 clone）[默认]"
    echo "    2) 更新（git pull）"
    echo "    3) 跳过"
    echo "    4) 退出"
    read -rp "  请输入选项 [1-4]: " DIR_CHOICE
    case "${DIR_CHOICE:-1}" in
        2)
            info "更新已有代码..."
            cd "$INSTALL_DIR" && git pull
            ok "代码已更新"
            ;;
        3)
            info "跳过 clone，使用已有目录"
            ;;
        4)
            info "退出安装"
            exit 0
            ;;
        1|"")
            info "删除旧目录: $INSTALL_DIR"
            rm -rf "$INSTALL_DIR"
            ;;
    esac
fi

if [[ ! -d "$INSTALL_DIR" ]]; then
    # 检查是否私有仓库
    PRIVATE_REPO=false
    read -rp "  是否为私有仓库？需要 GitHub Token？[y/N]: " IS_PRIVATE
    if [[ "$IS_PRIVATE" =~ ^[Yy]$ ]]; then
        PRIVATE_REPO=true
        read -rsp "  请输入 GitHub Token: " GH_TOKEN
        echo ""
        REPO_URL="https://${GH_TOKEN}@github.com/opendeepseek/opendeepseek.git"
    fi

    # 尝试 clone，带重试
    CLONE_OK=false
    for i in 1 2 3; do
        if git clone --depth=1 "$REPO_URL" "$INSTALL_DIR" 2>/dev/null; then
            CLONE_OK=true
            break
        fi
        if [[ $i -lt 3 ]]; then
            warn "clone 失败（尝试 $i/3），5 秒后重试..."
            sleep 5
        fi
    done

    if [[ "$CLONE_OK" != true ]]; then
        die "clone 失败，请检查：1) 网络连接  2) GitHub Token 是否正确  3) 仓库是否存在"
    fi
    ok "代码已克隆到 $INSTALL_DIR"
fi

cd "$INSTALL_DIR"

# ════════════════════════════════════════════════════════════
# Step 5: 生成 .env 配置文件
# ════════════════════════════════════════════════════════════
step 5 "生成 .env 配置文件..."

if [[ -f ".env" ]]; then
    warn ".env 已存在"
    read -rp "  是否重新生成？[y/N]: " REGEN_ENV
    if [[ ! "$REGEN_ENV" =~ ^[Yy]$ ]]; then
        info "保留现有 .env"
    else
        REGEN_ENV="yes"
    fi
else
    REGEN_ENV="yes"
fi

if [[ "$REGEN_ENV" == "yes" ]]; then
    # 先用 setup.sh 生成基础配置
    if [[ -f "./setup.sh" ]]; then
        chmod +x ./setup.sh

        # 非交互式：直接生成 .env（通过简单模式）
        # 但如果 setup.sh 没有静默模式，我们就手动创建
        if [[ -f ".env.example" ]]; then
            cp .env.example .env.tmp
            info "请编辑 .env 文件，填入你的 API Key 等配置"
            echo ""
            echo "  最少需要修改："
            echo "    OPDS_LLM_API_KEY=your-api-key-here  →  你的真实 API Key"
            echo ""
            read -rp "  是否现在用 vim 编辑 .env？[y/N]: " EDIT_NOW
            if [[ "$EDIT_NOW" =~ ^[Yy]$ ]]; then
                ${EDITOR:-vi} .env.tmp
            fi
            # 检查是否修改了关键字段
            if grep -q "your-api-key-here" .env.tmp; then
                warn "API Key 仍是占位符，请稍后手动编辑 .env"
            fi
            mv .env.tmp .env
        else
            # 极简生成
            HERMES_API_KEY=$(openssl rand -hex 32 2>/dev/null || head -c 32 /dev/urandom | base64 | tr -d '=+/')
            WEBUI_SECRET_KEY=$(openssl rand -hex 32 2>/dev/null || head -c 32 /dev/urandom | base64 | tr -d '=+/')
            read -rsp "请输入你的 LLM API Key: " API_KEY
            echo ""
            cat > .env <<ENVEOF
OPDS_LLM_PROVIDER=custom
OPDS_LLM_BASE_URL=http://127.0.0.1:8000/v1
OPDS_LLM_API_KEY=${API_KEY:-your-api-key-here}
OPDS_LLM_MODEL=GPT-5.4
OPDS_LLM_PRO_MODEL=GPT-5.5 Pro
HERMES_INFERENCE_PROVIDER=custom
DEFAULT_MODEL=GPT-5.4
HERMES_API_KEY=${HERMES_API_KEY}
WEBUI_SECRET_KEY=${WEBUI_SECRET_KEY}
ENVEOF
        fi
        ok ".env 已生成"
    else
        die "setup.sh 不存在，项目不完整"
    fi
fi

# ════════════════════════════════════════════════════════════
# Step 6: 配置 Nginx（可选）
# ════════════════════════════════════════════════════════════
step 6 "配置 Nginx..."

if [[ "$INSTALL_NGINX" == true ]] && [[ -n "$DOMAIN" ]]; then
    info "安装 Nginx + 配置 SSL..."

    # 安装 nginx
    if ! command -v nginx &>/dev/null; then
        if [[ "$DISTRO" == "debian" ]]; then
            $SUDO apt-get install -y -qq nginx
        else
            $SUDO $PKG_MANAGER install -y nginx
        fi
    fi

    # 检查 nginx 模板目录
    if [[ -d "config/nginx" ]]; then
        # 使用项目自带的 nginx 模板
        if [[ -f "config/nginx/opendeepseek.conf" ]]; then
            $SUDO cp config/nginx/opendeepseek.conf /etc/nginx/sites-available/opendeepseek.conf 2>/dev/null || \
            $SUDO cp config/nginx/opendeepseek.conf /etc/nginx/conf.d/opendeepseek.conf 2>/dev/null || true
            # 替换域名占位符
            if [[ -n "$DOMAIN" ]]; then
                $SUDO sed -i "s/__DOMAIN__/$DOMAIN/g" /etc/nginx/sites-available/opendeepseek.conf 2>/dev/null || true
                $SUDO sed -i "s/__DOMAIN__/$DOMAIN/g" /etc/nginx/conf.d/opendeepseek.conf 2>/dev/null || true
            fi
        fi
    else
        # 生成默认 nginx 配置
        $SUDO tee /etc/nginx/sites-available/opendeepseek.conf > /dev/null <<NGINXEOF
server {
    listen 80;
    server_name ${DOMAIN};
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name ${DOMAIN};

    ssl_certificate     /etc/letsencrypt/live/${DOMAIN}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${DOMAIN}/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_buffering off;
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
    }
}
NGINXEOF
        $SUDO ln -sf /etc/nginx/sites-available/opendeepseek.conf /etc/nginx/sites-enabled/
    fi

    # 安装 SSL 证书
    if [[ -n "$EMAIL" ]]; then
        if ! command -v certbot &>/dev/null; then
            if [[ "$DISTRO" == "debian" ]]; then
                $SUDO apt-get install -y -qq certbot python3-certbot-nginx
            else
                $SUDO $PKG_MANAGER install -y certbot python3-certbot-nginx
            fi
        fi
        info "申请 Let's Encrypt SSL 证书..."
        $SUDO certbot --nginx --non-interactive --agree-tos --email "$EMAIL" -d "$DOMAIN" || \
            warn "SSL 证书申请失败，请稍后手动运行: certbot --nginx -d $DOMAIN"
    else
        warn "未提供 --email，跳过 SSL 自动申请"
        warn "请稍后手动运行: certbot --nginx -d $DOMAIN"
    fi

    $SUDO systemctl enable nginx --now || true
    $SUDO nginx -t && $SUDO systemctl reload nginx || warn "Nginx 配置有误，请手动检查"
    ok "Nginx 配置完成"
else
    if [[ "$INSTALL_NGINX" == true ]]; then
        info "未指定 --domain，跳过 Nginx 配置"
        info "稍后可通过 bash install.sh --domain your.domain.com --email you@email.com 补配置"
    else
        info "已跳过 Nginx 安装（--no-nginx）"
    fi
fi

# ════════════════════════════════════════════════════════════
# Step 7: 配置 Cloudflare Tunnel（可选）
# ════════════════════════════════════════════════════════════
step 7 "配置 Cloudflare Tunnel..."

if [[ "$INSTALL_TUNNEL" == true ]]; then
    if command -v cloudflared &>/dev/null; then
        ok "cloudflared 已安装"
        read -rp "  是否配置 Cloudflare Tunnel？[y/N]: " SETUP_TUNNEL
        if [[ "$SETUP_TUNNEL" =~ ^[Yy]$ ]]; then
            info "请登录 Cloudflare 并创建 Tunnel..."
            cloudflared tunnel login || warn "cloudflared login 失败"
            read -rp "  请输入 Tunnel Name: " TUNNEL_NAME
            if [[ -n "$TUNNEL_NAME" ]]; then
                cloudflared tunnel create "$TUNNEL_NAME" || true
                # 生成配置文件
                $SUDO mkdir -p /etc/cloudflared
                $SUDO tee /etc/cloudflared/config.yml > /dev/null <<TUNNELCFG
tunnel: ${TUNNEL_NAME}
credentials-file: /root/.cloudflared/${TUNNEL_NAME}.json

ingress:
  - hostname: ${DOMAIN:-opendeepseek.example.com}
    service: http://localhost:3000
  - service: http_status:404
TUNNELCFG
                $SUDO systemctl enable cloudflared --now 2>/dev/null || \
                    warn "请手动安装 cloudflared systemd 服务"
                ok "Cloudflare Tunnel 配置完成"
            fi
        else
            info "跳过 Cloudflare Tunnel 配置"
        fi
    else
        info "cloudflared 未安装"
        read -rp "  是否安装 Cloudflare Tunnel (cloudflared)？[y/N]: " INSTALL_CF
        if [[ "$INSTALL_CF" =~ ^[Yy]$ ]]; then
            info "安装 cloudflared..."
            if [[ "$DISTRO" == "debian" ]]; then
                $SUDO curl -fsSL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb -o /tmp/cloudflared.deb
                $SUDO dpkg -i /tmp/cloudflared.deb
            else
                $SUDO curl -fsSL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.rpm -o /tmp/cloudflared.rpm
                $SUDO rpm -i /tmp/cloudflared.rpm
            fi
            ok "cloudflared 已安装"
        else
            info "跳过 Cloudflare Tunnel"
        fi
    fi
else
    info "已跳过 Cloudflare Tunnel（--no-tunnel）"
fi

# ════════════════════════════════════════════════════════════
# Step 8: 设置 Systemd 自启服务
# ════════════════════════════════════════════════════════════
step 8 "设置 Systemd 自启服务..."

SERVICE_SRC="scripts/opendeepseek-auto.service"
SERVICE_DST="/etc/systemd/system/opendeepseek-auto.service"

if [[ -f "$SERVICE_SRC" ]]; then
    # 替换工作目录为实际安装目录
    $SUDO cp "$SERVICE_SRC" "$SERVICE_DST"
    $SUDO sed -i "s|WorkingDirectory=.*|WorkingDirectory=${INSTALL_DIR}|" "$SERVICE_DST"
    $SUDO systemctl daemon-reload
    $SUDO systemctl enable opendeepseek-auto.service
    ok "opendeepseek-auto.service 已启用（开机自启）"
else
    warn "未找到 $SERVICE_SRC，手动创建服务..."
    $SUDO tee "$SERVICE_DST" > /dev/null <<SERVICEEOF
[Unit]
Description=OpenDeepSeek Auto Start
Requires=docker.service
After=docker.service network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=${INSTALL_DIR}
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SERVICEEOF
    $SUDO systemctl daemon-reload
    $SUDO systemctl enable opendeepseek-auto.service
    ok "opendeepseek-auto.service 已创建并启用"
fi

# ════════════════════════════════════════════════════════════
# Step 9: 启动服务 + 健康检查
# ════════════════════════════════════════════════════════════
step 9 "启动 Docker Compose 服务..."

cd "$INSTALL_DIR"

# 构建并启动
info "构建 hermes-bridge 镜像..."
$SUDO docker compose build hermes-bridge 2>/dev/null || warn "hermes-bridge 构建失败，将使用已有镜像"

info "启动所有服务..."
$SUDO docker compose up -d || die "docker compose up 失败"

ok "服务已启动"

# 健康检查
info "等待服务就绪..."
TOTAL_CHECKS=3
PASSED=0

check_service() {
    local name="$1"
    local url="$2"
    local max_wait="$3"
    local ready=0
    for i in $(seq 1 $((max_wait / 2))); do
        if curl -fsS "$url" &>/dev/null; then
            ready=1
            break
        fi
        sleep 2
    done
    if [[ "$ready" -eq 1 ]]; then
        ok "$name 就绪 ($url)"
        return 0
    else
        warn "$name 在 ${max_wait}秒 内未就绪 ($url)"
        return 1
    fi
}

check_service "Open WebUI" "http://localhost:3000" 30 && PASSED=$((PASSED + 1))
check_service "Hermes" "http://localhost:8642/health" 60 && PASSED=$((PASSED + 1))
check_service "GenSpark Proxy" "http://localhost:7056/v1/models" 30 && PASSED=$((PASSED + 1))

# ════════════════════════════════════════════════════════════
# 完成
# ════════════════════════════════════════════════════════════
echo ""
hr
if [[ "$PASSED" -ge 2 ]]; then
    echo -e "${GREEN}${BOLD}"
    echo "  🎉 OpenDeepSeek 安装完成！"
    echo -e "${NC}"
else
    echo -e "${YELLOW}${BOLD}"
    echo "  ⚠️  OpenDeepSeek 安装完成（部分服务未就绪）"
    echo -e "${NC}"
fi
echo ""
echo -e "  ${CYAN}本地访问${NC}    http://localhost:3000"
echo -e "  ${CYAN}Hermes API${NC}  http://localhost:8642"
if [[ -n "$DOMAIN" ]]; then
    echo -e "  ${CYAN}公网访问${NC}    https://${DOMAIN}"
fi
echo ""
echo -e "  ${BOLD}常用命令：${NC}"
echo -e "    查看日志:    $SUDO docker compose logs -f"
echo -e "    停止服务:    $SUDO docker compose down"
echo -e "    重启服务:    $SUDO docker compose restart"
echo -e "    更新代码:    cd ${INSTALL_DIR} && git pull && $SUDO docker compose up -d"
echo ""
echo -e "  ${YELLOW}📝 后续步骤：${NC}"
echo -e "    1. 编辑 .env 完善配置:  ${EDITOR:-vi} ${INSTALL_DIR}/.env"
echo -e "    2. 配置域名:    bash install.sh --domain your.domain.com --email you@email.com"
echo -e "    3. 配置 SSL:    certbot --nginx -d your.domain.com"
echo ""
hr
exit 0
