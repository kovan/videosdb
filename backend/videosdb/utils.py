
import socket
import time
from typing import Callable, Type
import anyio
import logging
import os
import sys
import inspect
logger = logging.getLogger(__name__)


class QuotaExceeded(Exception):
    pass


def get_module_path():
    frame = inspect.currentframe()
    file = inspect.getabsfile(frame)  # type: ignore
    return os.path.dirname(file)


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


def my_handler(my_type: Type[Exception], e: Exception, handler: Callable):
    catched = False
    logger.debug("Exception happened: %s" % str(e))
    if isinstance(e, anyio.ExceptionGroup):
        unhandled = []
        for ex in e.exceptions:
            if isinstance(e, my_type):
                catched = True
                handler(ex)
            else:
                unhandled.append(ex)
        if unhandled:
            raise anyio.ExceptionGroup(unhandled)

    elif isinstance(e, my_type):
        catched = True
        handler(e)
    else:
        raise e

    return catched


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


def json_schema_validation(db):
    pass
