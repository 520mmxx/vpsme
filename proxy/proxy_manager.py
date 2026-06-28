import asyncio
import json
import logging
import os
from collections import defaultdict
from datetime import datetime, timezone

import aiohttp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("proxy-manager")

PROXY_API_URL = os.environ.get("PROXY_API_URL", "")
LISTEN_HOST = os.environ.get("LISTEN_HOST", "0.0.0.0")
LISTEN_PORT = int(os.environ.get("LISTEN_PORT", "7777"))
FETCH_INTERVAL = int(os.environ.get("FETCH_INTERVAL", "300"))


class ProxyPool:
    def __init__(self):
        self.proxies: list[str] = []
        self.index = 0
        self.stats: dict[str, dict] = defaultdict(
            lambda: {"uses": 0, "errors": 0, "last_used": None}
        )
        self.last_fetch: datetime | None = None

    async def fetch_proxies(self) -> None:
        if not PROXY_API_URL:
            logger.warning("PROXY_API_URL is not set")
            return
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(PROXY_API_URL, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    text = await resp.text()
                    lines = text.strip().split("\n")
                    new_proxies = [line.strip() for line in lines if line.strip()]
                    if new_proxies:
                        self.proxies = new_proxies
                        self.last_fetch = datetime.now(timezone.utc)
                        logger.info("Fetched %d proxies: %s", len(new_proxies), new_proxies[:3])
                    else:
                        logger.warning("API returned empty proxy list")
        except Exception as e:
            logger.error("Failed to fetch proxies: %s", e)

    def get_proxy(self) -> str | None:
        if not self.proxies:
            return None
        proxy = self.proxies[self.index % len(self.proxies)]
        self.index += 1
        self.stats[proxy]["uses"] += 1
        self.stats[proxy]["last_used"] = datetime.now(timezone.utc).isoformat()
        return proxy

    def record_error(self, proxy: str) -> None:
        self.stats[proxy]["errors"] += 1

    def health(self) -> dict:
        return {
            "status": "ok" if self.proxies else "no_proxies",
            "pool_size": len(self.proxies),
            "total_uses": sum(s["uses"] for s in self.stats.values()),
            "total_errors": sum(s["errors"] for s in self.stats.values()),
            "last_fetch": self.last_fetch.isoformat() if self.last_fetch else None,
            "proxy_api_url": PROXY_API_URL,
        }


pool = ProxyPool()


async def pipe(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    try:
        while True:
            data = await asyncio.wait_for(reader.read(65536), timeout=300)
            if not data:
                break
            writer.write(data)
            await writer.drain()
    except (asyncio.TimeoutError, ConnectionResetError, BrokenPipeError, ConnectionError):
        pass
    except Exception:
        pass


async def handle_client(
    reader: asyncio.StreamReader, writer: asyncio.StreamWriter
) -> None:
    peername = writer.get_extra_info("peername")
    try:
        data = await asyncio.wait_for(reader.readuntil(b"\r\n"), timeout=30)
    except (asyncio.TimeoutError, asyncio.IncompleteReadError, ConnectionError):
        writer.close()
        return

    first_line = data.decode("utf-8", errors="replace").strip()
    parts = first_line.split(" ", 2)

    if len(parts) < 2:
        writer.close()
        return

    method = parts[0]
    target = parts[1]

    if method == "GET" and target in ("/health", "/health/"):
        body = json.dumps(pool.health(), ensure_ascii=False).encode()
        resp = (
            f"HTTP/1.1 200 OK\r\n"
            f"Content-Type: application/json\r\n"
            f"Content-Length: {len(body)}\r\n"
            f"Connection: close\r\n\r\n"
        ).encode() + body
        try:
            writer.write(resp)
            await writer.drain()
        except Exception:
            pass
        writer.close()
        return

    if method != "CONNECT":
        try:
            writer.write(b"HTTP/1.1 405 Method Not Allowed\r\n\r\n")
            await writer.drain()
        except Exception:
            pass
        writer.close()
        return

    host, _, port_str = target.partition(":")
    try:
        port = int(port_str) if port_str else 443
    except ValueError:
        port = 443

    proxy_addr = pool.get_proxy()
    if not proxy_addr:
        logger.warning("No proxies available for %s", peername)
        try:
            writer.write(b"HTTP/1.1 503 Service Unavailable\r\n\r\n")
            await writer.drain()
        except Exception:
            pass
        writer.close()
        return

    try:
        proxy_host, proxy_port_str = proxy_addr.split(":")
        proxy_port = int(proxy_port_str)
    except (ValueError, IndexError):
        pool.record_error(proxy_addr)
        writer.close()
        return

    upstream_reader = None
    upstream_writer = None
    try:
        upstream_reader, upstream_writer = await asyncio.wait_for(
            asyncio.open_connection(proxy_host, proxy_port), timeout=10
        )

        connect_req = f"CONNECT {host}:{port} HTTP/1.1\r\nHost: {host}:{port}\r\n\r\n"
        upstream_writer.write(connect_req.encode())
        await upstream_writer.drain()

        resp_header = await asyncio.wait_for(
            upstream_reader.readuntil(b"\r\n\r\n"), timeout=15
        )
        status_line = resp_header.split(b"\r\n")[0].decode()
        if "200" not in status_line:
            pool.record_error(proxy_addr)
            logger.warning("Upstream proxy %s rejected CONNECT: %s", proxy_addr, status_line)
            writer.write(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
            await writer.drain()
            upstream_writer.close()
            writer.close()
            return

        writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
        await writer.drain()

        logger.info(
            "Tunnel established %s -> %s via %s -> %s:%s",
            peername, target, proxy_addr, host, port
        )

        await asyncio.gather(
            pipe(reader, upstream_writer),
            pipe(upstream_reader, writer),
        )
    except asyncio.TimeoutError:
        logger.error("Timeout connecting via proxy %s", proxy_addr)
        pool.record_error(proxy_addr)
        try:
            writer.write(b"HTTP/1.1 504 Gateway Timeout\r\n\r\n")
            await writer.drain()
        except Exception:
            pass
    except (ConnectionRefusedError, ConnectionError, OSError) as e:
        logger.error("Connection error via proxy %s: %s", proxy_addr, e)
        pool.record_error(proxy_addr)
        try:
            writer.write(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
            await writer.drain()
        except Exception:
            pass
    except Exception as e:
        logger.error("Unexpected error via proxy %s: %s", proxy_addr, e)
        pool.record_error(proxy_addr)
    finally:
        try:
            if upstream_writer:
                upstream_writer.close()
        except Exception:
            pass
        try:
            writer.close()
        except Exception:
            pass


async def periodic_fetch() -> None:
    await pool.fetch_proxies()
    while True:
        await asyncio.sleep(FETCH_INTERVAL)
        await pool.fetch_proxies()


async def main() -> None:
    server = await asyncio.start_server(handle_client, LISTEN_HOST, LISTEN_PORT)
    logger.info("Proxy manager listening on %s:%s", LISTEN_HOST, LISTEN_PORT)

    async with server:
        await asyncio.gather(
            server.serve_forever(),
            periodic_fetch(),
        )


if __name__ == "__main__":
    asyncio.run(main())
