# -*- coding: utf-8 -*-
"""Простой LAN-кооператив на TCP: один хост и один гость.

Архитектура намеренно лёгкая: оба игрока симулируют мир локально, хост
передаёт гостю снимок мира при подключении, а изменения тайлов и позиции
игроков синхронизируются небольшими JSON-сообщениями.
"""
from __future__ import annotations

import json
import queue
import socket
import threading
import time


def local_ip() -> str:
    """Возвращает локальный IPv4 для подключения по Wi-Fi/Ethernet."""
    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(0.4)
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        try:
            return socket.gethostbyname(socket.gethostname())
        except OSError:
            return "127.0.0.1"
    finally:
        if sock:
            sock.close()


class NetworkManager:
    MAX_MESSAGE = 32 * 1024 * 1024

    def __init__(self):
        self.role: str | None = None
        self.port = 0
        self.status = "idle"          # idle / connecting / waiting / connected / error
        self.error = ""
        self.local_host = local_ip()
        self.listening = False
        self.connected = False
        self.remote_name = ""
        self.remote_appearance: dict = {}
        self.remote_state: dict = {}
        self.remote_active = False
        self._sock: socket.socket | None = None
        self._listener: socket.socket | None = None
        self._running = False
        self._closing = False
        self._world_data: dict | None = None
        self._local_info: dict = {}
        self._send_lock = threading.Lock()
        self._event_queue: queue.Queue = queue.Queue()
        self._threads: list[threading.Thread] = []
        self._state_timer = 0.0
        self._state_interval = 0.1
        self._last_sent = (0.0, 0.0)

    # ------------------------------------------------------------------ запуск
    def bind_host(self, port: int) -> bool:
        self.close(notify=False)
        self.role = "host"
        self.port = int(port)
        self.error = ""
        self._closing = False
        self._event_queue = queue.Queue()
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind(("0.0.0.0", self.port))
            listener.listen(1)
            listener.settimeout(0.5)
        except OSError as exc:
            listener.close()
            self.status = "error"
            self.error = f"Не удалось открыть порт {port}: {exc}"
            self.role = None
            return False
        self._listener = listener
        self.listening = True
        self.status = "waiting"
        return True

    def launch_host(self, world_data: dict, local_info: dict):
        if self.role != "host" or not self._listener:
            return
        self._world_data = world_data
        self._local_info = dict(local_info)
        self._running = True
        thread = threading.Thread(target=self._accept_loop, name="tn-host", daemon=True)
        thread.start()
        self._threads.append(thread)
        self._event_queue.put(("listening", {
            "ip": self.local_host, "port": self.port,
        }))

    def join_async(self, host: str, port: int, local_info: dict):
        self.close(notify=False)
        self.role = "client"
        self.port = int(port)
        self.error = ""
        self.status = "connecting"
        self.local_host = host.strip() or "127.0.0.1"
        self._local_info = dict(local_info)
        self._closing = False
        self._event_queue = queue.Queue()
        self._running = True
        thread = threading.Thread(target=self._connect_loop,
                                  args=(self.local_host, self.port),
                                  name="tn-client", daemon=True)
        thread.start()
        self._threads.append(thread)

    # ------------------------------------------------------------------ потоки
    def _accept_loop(self):
        while self._running and self._listener:
            try:
                conn, addr = self._listener.accept()
            except socket.timeout:
                continue
            except OSError:
                if self._running and not self._closing:
                    self._event_queue.put(("error", "Сервер остановлен"))
                break
            if not self._running:
                conn.close()
                break
            try:
                conn.settimeout(0.5)
                conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            except OSError:
                pass
            self._sock = conn
            self.connected = True
            self.listening = False
            self.status = "connected"
            self.remote_active = True
            welcome = {
                "type": "welcome",
                "world": self._world_data,
                "name": self._local_info.get("name", "Хост"),
                "appearance": self._local_info.get("appearance", {}),
                "x": self._local_info.get("x", 0),
                "y": self._local_info.get("y", 0),
                "hp": self._local_info.get("hp", 100),
                "max_hp": self._local_info.get("max_hp", 100),
                "time_of_day": self._local_info.get("time_of_day", 0.22),
                "day": self._local_info.get("day", 1),
            }
            if not self._send_obj(welcome):
                self._drop_connection()
                continue
            self._event_queue.put(("connected", {"addr": f"{addr[0]}:{addr[1]}"}))
            self._recv_loop(conn)
            if self._running and not self._closing:
                self.listening = True
                self.status = "waiting"

    def _connect_loop(self, host: str, port: int):
        conn = None
        try:
            conn = socket.create_connection((host, port), timeout=7.0)
            conn.settimeout(0.5)
            conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self._sock = conn
            welcome = self._recv_one(conn, timeout=24.0)
            if not welcome or welcome.get("type") != "welcome":
                raise ValueError("Сервер не прислал данные мира")
            host_info = {
                "name": welcome.get("name", "Хост"),
                "appearance": welcome.get("appearance", {}),
                "x": welcome.get("x", 0),
                "y": welcome.get("y", 0),
                "hp": welcome.get("hp", 100),
                "max_hp": welcome.get("max_hp", 100),
            }
            self._set_remote(host_info)
            self.connected = True
            hello = {
                "type": "hello",
                "name": self._local_info.get("name", "Гость"),
                "appearance": self._local_info.get("appearance", {}),
            }
            if not self._send_obj(hello):
                raise OSError("Не удалось отправить приветствие")
            self.remote_active = True
            self.status = "connected"
            self._event_queue.put(("joined", {"welcome": welcome, "host": host}))
            self._recv_loop(conn)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            if not self._closing:
                self.error = str(exc)
                self.status = "error"
                self._event_queue.put(("error", self.error))
                self._event_queue.put(("disconnected", self.error))
        finally:
            self.connected = False
            self.remote_active = False
            if conn:
                try:
                    conn.close()
                except OSError:
                    pass
            self._sock = None
            self._running = False

    def _recv_loop(self, conn: socket.socket):
        buffer = bytearray()
        reason = "Соединение закрыто"
        while self._running and not self._closing:
            try:
                chunk = conn.recv(65536)
            except socket.timeout:
                continue
            except OSError:
                reason = "Сетевая ошибка"
                break
            if not chunk:
                break
            buffer.extend(chunk)
            if len(buffer) > self.MAX_MESSAGE:
                reason = "Слишком большое сообщение"
                break
            while b"\n" in buffer:
                raw, _, rest = buffer.partition(b"\n")
                buffer = bytearray(rest)
                if not raw:
                    continue
                try:
                    msg = json.loads(raw.decode("utf-8"))
                except (ValueError, UnicodeDecodeError):
                    continue
                if not self._handle_remote_message(msg):
                    self.connected = False
                    self.remote_active = False
                    try:
                        conn.close()
                    except OSError:
                        pass
                    self._event_queue.put(("disconnected", "Игрок покинул игру"))
                    return
        self.connected = False
        self.remote_active = False
        try:
            conn.close()
        except OSError:
            pass
        if self._sock is conn:
            self._sock = None
        if not self._closing:
            if self.role == "host":
                self.listening = self._running
                self.status = "waiting" if self._running else "idle"
            else:
                self.status = "idle"
            self._event_queue.put(("disconnected", reason))

    def _handle_remote_message(self, msg: dict) -> bool:
        kind = msg.get("type")
        if kind == "hello":
            self._set_remote(msg)
        elif kind == "state":
            self._set_remote(msg)
        elif kind == "bye":
            return False
        self._event_queue.put(("message", msg))
        return True

    def _set_remote(self, data: dict):
        if data.get("name"):
            self.remote_name = str(data["name"])[:32]
        appearance = data.get("appearance")
        if isinstance(appearance, dict):
            self.remote_appearance = dict(appearance)
        state = {
            "x": float(data.get("x", self.remote_state.get("x", 0))),
            "y": float(data.get("y", self.remote_state.get("y", 0))),
            "hp": int(data.get("hp", self.remote_state.get("hp", 100))),
            "max_hp": int(data.get("max_hp", self.remote_state.get("max_hp", 100))),
            "facing": int(data.get("facing", self.remote_state.get("facing", 1))),
            "moving": bool(data.get("moving", False)),
        }
        self.remote_state = state

    # ------------------------------------------------------------------ отправка
    def _send_obj(self, obj: dict) -> bool:
        sock = self._sock
        if not sock or not self.connected:
            return False
        try:
            raw = (json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
            with self._send_lock:
                sock.sendall(raw)
            return True
        except OSError:
            return False

    def send_state(self, info: dict):
        if not self.connected:
            return
        payload = {
            "type": "state",
            "name": info.get("name", "Игрок"),
            "appearance": info.get("appearance", {}),
            "x": round(float(info.get("x", 0)), 1),
            "y": round(float(info.get("y", 0)), 1),
            "hp": int(info.get("hp", 100)),
            "max_hp": int(info.get("max_hp", 100)),
            "facing": int(info.get("facing", 1)),
            "moving": bool(info.get("moving", False)),
        }
        self._send_obj(payload)

    def send_tile(self, x: int, y: int, tile: int):
        if self.connected:
            self._send_obj({"type": "tile", "x": int(x), "y": int(y), "tile": int(tile)})

    def send_chat(self, text: str):
        text = " ".join(str(text).split())[:120]
        if self.connected and text:
            self._send_obj({"type": "chat", "text": text})

    # ------------------------------------------------------------------ обновление
    def update(self, dt: float, local_info: dict | None = None):
        if self.connected and local_info is not None:
            self._state_timer -= dt
            if self._state_timer <= 0:
                self._state_timer = self._state_interval
                self.send_state(local_info)

    def poll(self) -> list[tuple[str, object]]:
        events = []
        while True:
            try:
                events.append(self._event_queue.get_nowait())
            except queue.Empty:
                break
        return events

    def _recv_one(self, conn: socket.socket, timeout=8.0) -> dict | None:
        old_timeout = conn.gettimeout()
        conn.settimeout(timeout)
        buffer = bytearray()
        started = time.monotonic()
        try:
            while b"\n" not in buffer:
                if time.monotonic() - started > timeout:
                    raise socket.timeout("Таймаут подключения")
                chunk = conn.recv(65536)
                if not chunk:
                    return None
                buffer.extend(chunk)
                if len(buffer) > self.MAX_MESSAGE:
                    raise ValueError("Слишком большой снимок мира")
            raw = bytes(buffer).split(b"\n", 1)[0]
            return json.loads(raw.decode("utf-8"))
        finally:
            try:
                conn.settimeout(old_timeout or 0.5)
            except OSError:
                pass

    def _drop_connection(self):
        sock = self._sock
        self._sock = None
        self.connected = False
        self.remote_active = False
        if sock:
            try:
                sock.close()
            except OSError:
                pass

    def close(self, notify=True):
        self._closing = True
        self._running = False
        if notify and self.connected and self._sock:
            try:
                with self._send_lock:
                    raw = (json.dumps({"type": "bye"}, ensure_ascii=False) + "\n").encode("utf-8")
                    self._sock.sendall(raw)
            except OSError:
                pass
        sock = self._sock
        listener = self._listener
        self._sock = None
        self._listener = None
        if sock:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                sock.close()
            except OSError:
                pass
        if listener:
            try:
                listener.close()
            except OSError:
                pass
        self.connected = False
        self.listening = False
        self.remote_active = False
        self.remote_name = ""
        self.remote_state = {}
        self.remote_appearance = {}
        self.status = "idle"
        self.role = None
        self._world_data = None
        self._local_info = {}
        self._threads = [t for t in self._threads if t.is_alive()]
        self._closing = False

    @property
    def active(self) -> bool:
        return self.role is not None and (self.connected or self.listening or
                                          self.status == "connecting")

    def status_text(self) -> str:
        if self.status == "connecting":
            return "Подключение..."
        if self.status == "waiting":
            return f"Сервер ждёт игрока: {self.local_host}:{self.port}"
        if self.status == "connected":
            return f"Подключено: {self.remote_name or 'игрок'}"
        if self.status == "error":
            return self.error or "Сетевая ошибка"
        return "Сеть не активна"
