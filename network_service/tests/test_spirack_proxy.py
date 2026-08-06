import pytest
import os, socket, select, threading
from network_service.spirack_proxy import ConduitServer, Config

def _read(fd, n, timeout=1.0):      # so a bug fails fast instead of hanging
    assert select.select([fd], [], [], timeout)[0], "no serial data"
    return os.read(fd, n)

def _connect(port):
    s = socket.create_connection(("127.0.0.1", port), timeout=1); s.settimeout(1)
    return s

def test_owner_pipes_both_ways(server):
    _, port, master = server
    c = _connect(port)

    c.sendall(b"ping")
    assert _read(master, 4) == b"ping"

    os.write(master, b"pong")
    assert c.recv(4) == b"pong"

def test_second_client_is_refused(server):
    _, port, master = server
    first = _connect(port)
    first.sendall(b"x")
    _read(master, 1)   # prove first owns it before opening second

    second = _connect(port)
    assert second.recv(1) == b""            # busy -> connection dropped
