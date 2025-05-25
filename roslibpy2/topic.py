import asyncio
import json
from collections import UserDict
from types import CoroutineType, TracebackType
from typing import Any, Callable, TypeAlias

from websockets.asyncio.client import connect

ROSMessage: TypeAlias = dict[str, Any]


class ROSMessageType(UserDict):
    pass


def create_message(op: str, /, **optional: Any):
    option = {key: value for key, value in optional.items() if value is not None}
    return json.dumps({"op": op, **option})


class Ros:
    def __init__(self, host="localhost", port=9090) -> None:
        self.host = host
        self.port = port
        self._topics: list[str] = []
        self._connect = connect(f"ws://{self.host}:{self.port}")
        self._count = -1

    async def __aenter__(self):
        return await self._connect.__aenter__()

    async def __aexit__(
        self,
        exec_type: type[BaseException],
        exec_value: BaseException,
        traceback: TracebackType,
    ):
        await self._connect.__aexit__(exec_type, exec_value, traceback)

    def add_node(self, name: str):
        node_id = name + str(self._count)
        self._topics.append(node_id)
        return node_id

    def remove_node(self, name: str):
        self._topics.remove(name)

    @property
    def count(self):
        self._count += 1
        return self._count


async def create_timer(period: float, callback: CoroutineType):
    while True:
        await asyncio.sleep(period)
        await callback


async def publish(ros: Ros, message: dict, topic: str, message_type: str | None):
    topic_id = ros.add_node(topic)
    async with ros as websocket:
        await websocket.send(
            json.dumps(
                {
                    "op": "advertise",
                    "id": topic_id,
                    "topic": topic,
                    **({} if message_type is None else {"type": message_type}),
                }
            )
        )

        while True:
            print("publish message", message)
            await websocket.send(
                json.dumps(
                    {
                        "op": "publish",
                        "id": topic_id,
                        "topic": topic,
                        "msg": message,
                    }
                )
            )
            await asyncio.sleep(1)


async def subscribe(
    ros: Ros,
    topic: str,
    message_type: str | None,
    callback: Callable[[ROSMessage], None],
):
    topic_id = ros.add_node(topic)
    async with ros as websocket:
        await websocket.send(
            json.dumps(
                {
                    "op": "subscribe",
                    "id": topic_id,
                    "topic": topic,
                    **({} if message_type is None else {"type": message_type}),
                }
            )
        )

        while True:
            msg = await websocket.recv()
            match json.loads(msg):
                case {"msg": x}:
                    callback(x)


class Topic:
    def __init__(
        self,
        ros: Ros,
        name: str,
        message_type: str | None,
    ) -> None:
        self.ros = ros
        self.name = name
        self.message_type = message_type
        self._topic_id: str | None = None
        self._event: asyncio.Event | None = None

    async def subscribe(self, callback: Callable[..., None]):
        op = self.subscribe.__name__
        self._topic_id = ".".join(
            (self.subscribe.__name__, self.name, str(self.ros.count))
        )
        self._event = asyncio.Event()

        async with self as websocket:
            await websocket.send(
                create_message(
                    op, id=self._topic_id, type=self.message_type, topic=self.name
                )
            )

            while not self._event.is_set():
                match json.loads(await websocket.recv()):
                    case {"msg": x}:
                        callback(x)

            await websocket.send(
                create_message("un" + op, id=self._topic_id, topic=self.name)
            )

    def unsubscribe(self):
        if self._event:
            self._event.set()

    async def __aenter__(self):
        return await self.ros.__aenter__()

    async def __aexit__(
        self,
        exec_type: type[BaseException],
        exec_value: BaseException,
        traceback: TracebackType,
    ):
        self.unsubscribe()
        self._topic_id = None
        self._event = None
        await self.ros.__aexit__(exec_type, exec_value, traceback)


async def main():
    def callback(msg: ROSMessageType):
        print(msg)

    ros = Ros()
    sub = Topic(ros, "/chatter", "std_msgs/msg/String")

    for _ in range(2):
        task = asyncio.create_task(sub.subscribe(callback))
        await asyncio.sleep(5)
        sub.unsubscribe()
        await task


if __name__ == "__main__":
    asyncio.run(main())
