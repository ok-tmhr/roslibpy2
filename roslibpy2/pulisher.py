import asyncio
import json
import uuid
from types import TracebackType
from typing import Any

from websockets.asyncio.client import ClientConnection, connect


def create_message(op: str, /, **optional: Any):
    option = {key: value for key, value in optional.items() if value is not None}
    return json.dumps({"op": op, **option})


class Ros:
    def __init__(self, host="localhost", port=9090) -> None:
        self.host = host
        self.port = port
        self._connect = connect(f"ws://{self.host}:{self.port}")
        self._connection: ClientConnection | None = None

    async def __aenter__(
        self,
    ):
        self._connection = await self._connect
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ):
        await self.disconnect()
        self._connection = None

    async def connect(self):
        self._connection = await self._connect

    async def disconnect(self):
        if self._connection:
            await self._connection.close()

    async def send(self, msg):
        if self._connection:
            await self._connection.send(msg)

    async def receive(self):
        if self._connection:
            return await self._connection.recv()
        raise Exception


class Publisher:
    def __init__(self, ros: Ros, topic: str, message_type: str) -> None:
        self.ros = ros
        self.topic = topic
        self.message_type = message_type
        self._uid = str(uuid.uuid4())

    async def advertise(self):
        await self.ros.send(
            create_message(
                "advertise", id=self._uid, topic=self.topic, type=self.message_type
            )
        )

    async def unadvertise(self):
        await self.ros.send(
            create_message("unadvertise", id=self._uid, topic=self.topic)
        )

    async def publish(self, msg):
        await self.ros.send(
            create_message("publish", id=self._uid, topic=self.topic, msg=msg)
        )

    async def __aenter__(self):
        await self.advertise()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ):
        await self.unadvertise()


class Subscription:
    def __init__(self, ros: Ros, topic: str, message_type: str) -> None:
        self.ros = ros
        self.topic = topic
        self.message_type = message_type
        self._uid = str(uuid.uuid4())
        self._task: asyncio.Task | None = None
        self._event = asyncio.Event()

    async def subscribe(self, callback):
        self._event.clear()

        await self.ros.send(
            create_message(
                "subscribe", id=self._uid, topic=self.topic, type=self.message_type
            )
        )

        async def _subscribe():
            while not self._event.is_set():
                data = await self.ros.receive()
                match json.loads(data):
                    case {"msg": x}:
                        callback(x)

        self._task = asyncio.create_task(_subscribe())

    async def unsubscribe(self):
        self._event.set()
        if self._task:
            await self._task
        await self.ros.send(
            create_message("unsubscribe", id=self._uid, topic=self.topic)
        )

    async def __aenter__(self):
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ):
        await self.unsubscribe()


async def main():
    def callback(msg):
        print(msg)

    ros, ros2 = Ros(), Ros()
    async with ros:
        sub = Subscription(ros, "/chatter", "std_msgs/msg/String")
        sub2 = Subscription(ros2, "/chatter2", "std_msgs/msg/String")
        async with asyncio.TaskGroup() as tg:
            t1 = tg.create_task(sub.subscribe(callback))
            t2 = tg.create_task(sub2.subscribe(callback))
            await asyncio.sleep(5)

            await sub.unsubscribe()
            await sub2.unsubscribe()


if __name__ == "__main__":
    asyncio.run(main())
