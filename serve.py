# serve.py
import os, sys, asyncio, signal, contextlib, logging
from aiohttp import web

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
PORT = int(os.environ.get("PORT", "10000"))
MAIN = os.environ.get("MAIN_SCRIPT", "Main.py")

async def health(_):
    return web.Response(text="ok")

async def start_http():
    app = web.Application()
    app.router.add_get("/health", health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logging.info(f"HTTP on :{PORT}")
    try:
        while True:
            await asyncio.sleep(3600)
    finally:
        with contextlib.suppress(Exception):
            await runner.cleanup()

async def run_bot_forever():
    while True:
        logging.info(f"starting {MAIN} …")
        try:
            proc = await asyncio.create_subprocess_exec(sys.executable, MAIN)
            rc = await proc.wait()
            logging.warning(f"{MAIN} exited rc={rc}; restart in 1s")
        except Exception as e:
            logging.exception(f"failed to exec {MAIN}: {e}")
        await asyncio.sleep(1)  # не дёргать в цикле

async def main():
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(sig, stop.set)

    t_http = asyncio.create_task(start_http(), name="http")
    t_bot  = asyncio.create_task(run_bot_forever(), name="bot")

    await stop.wait()
    for t in (t_http, t_bot):
        t.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await asyncio.gather(t_http, t_bot)

if __name__ == "__main__":
    asyncio.run(main())
