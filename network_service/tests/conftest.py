import os, socket, select, threading
import pytest
from network_service.spirack_proxy import ConduitServer, Config

@pytest.fixture
def pseudo_serial_port():
    """
    Opens a PTY that can stand in for a serial port. This is a fixture, so it can
    be used as an argument for tests or other fixtures.
    """

    master_fd, slave_fd = os.openpty()
    yield master_fd, os.ttyname(slave_fd)
    os.close(master_fd); os.close(slave_fd)

@pytest.fixture
def server(pseudo_serial_port):
    """
    Creates a ConduitServer (from `spirack_proxy.py`) that talks to a pseudo serial
    port. It listens on a port

    Args:
        device:

    Returns:

    """
    import random

    port_number = random.randint(1024, 65535)

    master_fd, slave_name = pseudo_serial_port
    srv = ConduitServer(Config(uart_port=slave_name, baud=9600, tcp_port=port_number))
    srv.open_serial()
    srv.open_listener()

    # We start the server on a different thread, then we yield the connection information
    # and join back with the other thread once the yield-caller is done.
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield srv, port_number, master_fd

    # The caller is done, we can shut down the server and clean up the thread.
    srv.shutdown()
    t.join(timeout=3)
