"""Background WebSocket adapter for the simulated device."""

import asyncio
import json
import logging
import queue
import threading
from enum import StrEnum

from websockets.asyncio.client import ClientConnection, connect

LOGGER = logging.getLogger(__name__)


class ConnectionStatus(StrEnum):
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"


class DeviceClient:
    """Exchange JSON messages without blocking the simulator render loop."""

    def __init__(
        self,
        url: str,
        *,
        device_id: str = "simulator-001",
        reconnect_seconds: float = 1.0,
    ) -> None:
        self.url = url
        self.device_id = device_id
        self.reconnect_seconds = reconnect_seconds
        self.status = ConnectionStatus.DISCONNECTED
        self.last_error: str | None = None
        self._outgoing: queue.Queue[dict[str, object]] = queue.Queue()
        self._incoming: queue.Queue[dict[str, object]] = queue.Queue()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._thread_main,
            name="buddy-device-websocket",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)

    def send(self, message: dict[str, object]) -> bool:
        """Queue a message only when a server connection is active."""
        if self.status is not ConnectionStatus.CONNECTED:
            return False
        self._outgoing.put(message)
        return True

    def receive_pending(self) -> list[dict[str, object]]:
        messages: list[dict[str, object]] = []
        while True:
            try:
                messages.append(self._incoming.get_nowait())
            except queue.Empty:
                return messages

    def _thread_main(self) -> None:
        asyncio.run(self._run())

    async def _run(self) -> None:
        while not self._stop.is_set():
            self.status = ConnectionStatus.CONNECTING
            try:
                async with connect(self.url) as websocket:
                    await websocket.send(
                        json.dumps(
                            {
                                "type": "DEVICE_CONNECTED",
                                "deviceId": self.device_id,
                                "deviceType": "SIMULATOR",
                            }
                        )
                    )
                    self.status = ConnectionStatus.CONNECTED
                    self.last_error = None
                    LOGGER.info("Simulator connected to %s", self.url)
                    await self._exchange(websocket)
            except Exception as exc:  # The adapter retries all connection failures.
                self.last_error = str(exc)
                LOGGER.debug("Simulator connection unavailable: %s", exc)
            finally:
                self.status = ConnectionStatus.DISCONNECTED

            if not self._stop.is_set():
                await asyncio.sleep(self.reconnect_seconds)

    async def _exchange(self, websocket: ClientConnection) -> None:
        while not self._stop.is_set():
            while True:
                try:
                    outgoing = self._outgoing.get_nowait()
                except queue.Empty:
                    break
                await websocket.send(json.dumps(outgoing))

            try:
                payload = await asyncio.wait_for(websocket.recv(), timeout=0.05)
            except TimeoutError:
                continue
            if not isinstance(payload, str):
                continue
            try:
                message = json.loads(payload)
            except json.JSONDecodeError:
                continue
            if isinstance(message, dict):
                self._incoming.put(message)
