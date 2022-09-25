import socket
import time
import anyio
import logging


logger = logging.getLogger(__name__)


def wait_for_port(port: int, host: str = 'localhost', timeout: float = 30.0):
    """Wait until a port starts accepting TCP connections.
    Args:
        port: Port number.
        host: Host address on which the port should exist.
        timeout: In seconds. How long to wait before raising errors.
    Raises:
        TimeoutError: The port isn't accepting connection after time specified in `timeout`.
    """
    logger.debug("waiting for port %s:%s to be open", port, host)
    start_time = time.perf_counter()
    while True:
        try:
            with socket.create_connection((host, port), timeout=timeout):
                break
        except OSError as ex:
            time.sleep(0.01)
            if time.perf_counter() - start_time >= timeout:
                raise TimeoutError('Waited too long for the port {} on host {} to start accepting '
                                   'connections.'.format(port, host)) from ex


def _contains_exceptions(exception_types, exception):
    if type(exception) == anyio.ExceptionGroup:
        for e in exception.exceptions:
            if type(e) in exception_types:
                return True
    elif type(exception) in exception_types:
        return True

    return False


def put_item_at_front(seq, item):
    if not item:
        return seq
    # start from where we left:
    try:
        i = seq.index(item)
        seq = seq[i:] + seq[:i]
    except ValueError:
        pass
    return seq
