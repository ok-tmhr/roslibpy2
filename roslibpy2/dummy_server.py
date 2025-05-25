import asyncio
import json

from websockets.asyncio.server import ServerConnection, serve


async def publish(websocket: ServerConnection):
    msg = {"op": "publish", "topic": "/chatter", "msg": {"data": "hello world"}}
    async for message in websocket:
        websocket.logger.info(message)
        await websocket.send(json.dumps(msg))


async def main(host="localhost", port=9090):
    async with serve(publish, host, port) as server:
        await server.serve_forever()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
