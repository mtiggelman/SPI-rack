# Network service for SPI rack hardware
In the Spin Qubit labs at the University of Copenhagen we found it to be a nuisance that we'd need to jump through
various hoops to share our SPI rack devices. This subdirectory contains a very thin network wrapper around a USB port,
along with some SPI Rack-specific niceties that you may use.

## Protocol
Essentially, the SPI rack unit uses a UART based protocol to talk to the different units inside the rack. What this 
little utility does is to wrap such a UART connection inside a TCP flow.

## Configuration
The configuration is done in environment variables (for easy deployment with Docker, although it's not _required_):

- `UART_PORT` denotes what port to connect to, e.g. `COM3` or `/dev/ttyACM0`.
- `UART_BAUD_RATE` denotes the baud rate. `115200` is known to be working, and the TuDelft docs suggest `9600`.  
- `TCP_PORT` denotes what TCP port to bind to. Confer with your IT department what's accessible.

## Running the server side

### Bare-bones (not recommended)
Running the server bare-bones is done like so:

```bash
UART_PORT=/dev/ttyACM0 UART_BAUD_RATE=115200 TCP_PORT=10101 python network_service/spirack_proxy.py
```

You can also put the environment variables in an `.env` file and source that. Ask your AI agent how to do that if 
you're interested.

### Docker
If you intend to run this in a lab, Docker can provide you some nice guarantees like restarting the instance if 
something goes wrong, and seamlessly running many instances of the same service, in case you have more than one SPI 
Rack.

First, build the Docker image by running:

```bash
docker build -t spirack-service network_service
```

Then, once that's done you may run the container like this:

```bash
docker run \
  -d \
  -e UART_PORT=/dev/ttyACM0 \
  -e UART_BAUD_RATE=115200 \
  -e TCP_PORT=10000 \
  -p 10000:10000 \
  --device=/dev/ttyACM0:/dev/ttyACM0 \
  --restart unless-stopped \
  spirack-service
```

The `-d` daemonizes the running container which means you don't see log statements and so on. Use `docker ps` to see 
what's currently running:

```
(.venv) ➜  SPI-rack git:(feat/networked-spi-rack) ✗ docker ps
CONTAINER ID   IMAGE                 COMMAND                  CREATED              STATUS                PORTS                                                             NAMES
db9e99f48175   spirack-service       "python spirack_prox…"   About a minute ago   Up About a minute     0.0.0.0:10000->10000/tcp, [::]:10000->10000/tcp                   distracted_lewin
```

You can see that there's one instance of `spirack-service` running with container ID `db9e99f48175`. To get the flow of 
logs:

```
(.venv) ➜  SPI-rack git:(feat/networked-spi-rack) ✗ docker logs -f db9e99f48175
2026-08-06 12:20:53,899 INFO Opened /dev/ttyACM0 @ 115200 baud
2026-08-06 12:20:53,899 INFO Listening on 0.0.0.0:10000
```

And to stop the container:
```
(.venv) ➜  SPI-rack git:(feat/networked-spi-rack) ✗ docker kill db9e99f48175
db9e99f48175
```

## Connecting the client side
Thanks to PySerial's support for `socket://` connections we don't actually have to modify it at all. Instantiate your
`SPI_Rack` device passing `socket://<ip or hostname>:<port>` in the `port=` property and you should be good.

```python
# Import parts of the SPI Rack library
from spirack import SPI_rack, D5a_module

# Instantiate the controller module
spi = SPI_rack(port="socket://127.0.0.1:10000", timeout=1)
# Unlock the controller for communication to happen
spi.unlock()

# Instantiate the D5a module using the controller module
# and the correct module address
D5a = D5a_module(spi, module=2)
# Set the output of DAC 1 to the desired voltage
D5a.set_voltage(0, voltage=2.1)
```
