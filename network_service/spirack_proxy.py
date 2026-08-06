#!/usr/bin/env python3
"""Single-client TCP-to-UART conduit.

Bridges one TCP client at a time to a serial port, forwarding raw bytes in
both directions with no interpretation of the payload. The TCP connection's
lifetime acts as an exclusivity lock: while a client is connected it owns the
device, and a second client that connects meanwhile is sent ``BUSY`` and
disconnected. When the owner disconnects (cleanly or by dying), the OS tears
the socket down and the device is released for the next client.

On connect the server sends a single status line before entering pipe mode:

    OK\\n     -> you now own the device; everything after this is raw traffic
    BUSY\\n   -> someone else has it; the connection is then closed

The serial port is opened once at start-up and kept open for the life of the
process, so a new client connecting never toggles DTR and resets the
controller.

Configuration is read from the environment:

    UART_PORT       serial device, e.g. /dev/ttyUSB0        (required)
    UART_BAUD_RATE  serial baud rate, e.g. 1000000          (required)
    TCP_PORT        TCP port to listen on                   (required)
"""

from __future__ import annotations

import logging
import os
import selectors
import signal
import socket
import sys
import threading
from dataclasses import dataclass

import serial

BIND_HOST = "0.0.0.0"
BACKLOG = 8
SERIAL_READ_TIMEOUT = 0.1   # s; bounds a server-side serial read
SERIAL_WRITE_TIMEOUT = 2.0  # s; a stalled write is treated as device failure
CHUNK = 4096                # max bytes moved per pump step

log = logging.getLogger("uart-conduit")


@dataclass(frozen=True)
class Config:
    uart_port: str
    baud: int
    tcp_port: int


def load_config() -> Config:
    try:
        return Config(
            uart_port=os.environ["UART_PORT"],
            baud=int(os.environ["UART_BAUD_RATE"]),
            tcp_port=int(os.environ["TCP_PORT"]),
        )
    except KeyError as e:
        sys.exit(f"Missing required environment variable: {e.args[0]}")
    except ValueError as e:
        sys.exit(f"Invalid numeric environment variable: {e}")


class ConduitServer:
    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        self.stop = threading.Event()
        self.device_lock = threading.Lock()
        self.exit_code = 0
        self.ser: serial.Serial | None = None
        self.listener: socket.socket | None = None
        self._threads: set[threading.Thread] = set()
        self._threads_lock = threading.Lock()

    # -- lifecycle -------------------------------------------------------

    def open_serial(self) -> None:
        self.ser = serial.Serial(
            self.cfg.uart_port,
            self.cfg.baud,
            timeout=SERIAL_READ_TIMEOUT,
            write_timeout=SERIAL_WRITE_TIMEOUT,
        )
        log.info("Opened %s @ %d baud", self.cfg.uart_port, self.cfg.baud)

    def open_listener(self) -> None:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((BIND_HOST, self.cfg.tcp_port))
        s.listen(BACKLOG)
        s.settimeout(1.0)  # so accept() wakes periodically to check the stop flag
        self.listener = s
        log.info("Listening on %s:%d", BIND_HOST, self.cfg.tcp_port)

    def serve_forever(self) -> None:
        assert self.listener is not None
        while not self.stop.is_set():
            try:
                conn, addr = self.listener.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            t = threading.Thread(target=self._handle, args=(conn, addr), daemon=True)
            with self._threads_lock:
                self._threads.add(t)
            t.start()

    def shutdown(self) -> None:
        self.stop.set()
        if self.listener is not None:
            self.listener.close()
        with self._threads_lock:
            threads = list(self._threads)
        for t in threads:
            t.join(timeout=3.0)
        if self.ser is not None and self.ser.is_open:
            self.ser.close()
        log.info("Shutdown complete")

    # -- per-connection --------------------------------------------------

    def _handle(self, conn: socket.socket, addr) -> None:
        """
        This function gets called when someone tries to open a new connection. We need to figure out if anybody is using
        the device, or whether we can allow access.

        Args:
            conn: A socket for sending bytes back and forth.
            addr: The address of the connecting peer.
        """
        peer = "%s:%d" % addr
        try:
            conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            if not self.device_lock.acquire(blocking=False):
                log.info("BUSY  %s (device already in use)", peer)
                conn.close()
                return
            try:
                log.info("OWNER %s acquired the device", peer)
                self._pump(conn)
            finally:
                self.device_lock.release()
                log.info("FREE  %s released the device", peer)
        except serial.SerialException as e:
            log.error("Serial failure serving %s: %s -- shutting down", peer, e)
            self.exit_code = 1
            self.stop.set()
        except OSError as e:
            log.info("Connection error %s: %s", peer, e)
        finally:
            try:
                conn.close()
            except OSError:
                pass
            with self._threads_lock:
                self._threads.discard(threading.current_thread())

    def _pump(self, conn: socket.socket) -> None:
        """Forward bytes both ways until the client disconnects or we stop."""
        assert self.ser is not None
        sel = selectors.DefaultSelector()
        sel.register(conn, selectors.EVENT_READ, "sock")
        sel.register(self.ser.fileno(), selectors.EVENT_READ, "serial")
        try:
            while not self.stop.is_set():
                for key, _ in sel.select(timeout=1.0):
                    if key.data == "sock":
                        data = conn.recv(CHUNK)

                        # If data is None it means that the client closed the connection. We can do the same then.
                        if not data:
                            return
                        self.ser.write(data)
                    else:
                        n = self.ser.in_waiting
                        data = self.ser.read(n or 1)
                        if data:
                            conn.sendall(data)
        finally:
            sel.close()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        stream=sys.stdout,
    )
    server = ConduitServer(load_config())

    # First, grab a handle on the serial port. Obviously we'll get nowhere if the server cannot get exclusive access
    # to the serial port.
    try:
        server.open_serial()
    except serial.SerialException as e:
        sys.exit(f"Cannot open serial port: {e}")

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: server.stop.set())

    # Second, we may listen for connections coming from the outside.
    try:
        server.open_listener()
    except OSError as e:
        sys.exit(f"Cannot listen on TCP port {server.cfg.tcp_port}: {e}")

    try:
        server.serve_forever()
    finally:
        log.warning("Shutting down...")
        server.shutdown()
    sys.exit(server.exit_code)


if __name__ == "__main__":
    main()
