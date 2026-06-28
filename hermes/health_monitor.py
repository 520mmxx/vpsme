#!/usr/bin/env python3
"""Hermes Gateway Platform Health Monitor

Periodically checks Telegram and QQ Bot connectivity every 72 hours.
If either bot is unresponsive, restarts the gateway service via s6.
"""

import asyncio
import httpx
import logging
import os
import signal
import time

CHECK_INTERVAL = 72 * 3600

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [health_monitor] %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("health_monitor")


async def check_telegram() -> bool:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        return True
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(f"https://api.telegram.org/bot{token}/getMe")
            data = r.json()
            if data.get("ok"):
                logger.info("Telegram OK: @%s", data["result"]["username"])
                return True
            else:
                logger.error("Telegram FAILED: %s", data.get("description", data))
                return False
    except Exception as e:
        logger.error("Telegram error: %s", e)
        return False


async def check_qqbot() -> bool:
    app_id = os.environ.get("QQ_APP_ID", "")
    client_secret = os.environ.get("QQ_CLIENT_SECRET", "")
    if not app_id or not client_secret:
        return True
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                "https://bots.qq.com/app/getAppAccessToken",
                json={"appId": app_id, "clientSecret": client_secret},
            )
            data = r.json()
            if data.get("access_token"):
                logger.info("QQ Bot OK")
                return True
            else:
                logger.error("QQ Bot FAILED: %s", data)
                return False
    except Exception as e:
        logger.error("QQ Bot error: %s", e)
        return False


def restart_gateway() -> None:
    logger.warning("Restarting gateway service...")
    ctrl = "/run/service/gateway-default/supervise/control"
    try:
        if os.path.exists(ctrl):
            with open(ctrl, "w") as f:
                f.write("t")
            logger.info("Sent restart signal via s6 control")
        else:
            pid_file = "/run/service/gateway-default/supervise/pid"
            if os.path.exists(pid_file):
                with open(pid_file) as f:
                    pid = int(f.read().strip())
                os.kill(pid, signal.SIGTERM)
                logger.info("Sent SIGTERM to gateway PID %d", pid)
            else:
                logger.error("Cannot find gateway s6 control or PID")
    except Exception as e:
        logger.error("Failed to restart gateway: %s", e)


async def main() -> None:
    logger.info("Started (interval: %dh)", CHECK_INTERVAL // 3600)
    while True:
        t0 = time.time()
        telegram_ok = await check_telegram()
        qq_ok = await check_qqbot()

        if not telegram_ok or not qq_ok:
            logger.warning(
                "FAILED — Telegram=%s QQ=%s (%.1fs)",
                telegram_ok, qq_ok, time.time() - t0,
            )
            restart_gateway()
        else:
            logger.info(
                "All OK (%.1fs) — next check in %dh",
                time.time() - t0, CHECK_INTERVAL // 3600,
            )

        await asyncio.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    asyncio.run(main())
