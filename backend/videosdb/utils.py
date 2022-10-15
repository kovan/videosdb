import socket
import time
import anyio
import logging


logger = logging.getLogger(__name__)


class QuotaExceeded(Exception):
    pass


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


# class ExceptionFilter:
#     def __init__(self, exception_type_to_filter, exception):
#         self.ex_type = exception_type_to_filter
#         self.exception = exception
#         self.to_handle_exceptions = []
#         self.to_handle_exceptions_iter = iter(self.to_handle_exceptions)
#         self.unhandled_exceptions = []

#         if type(exception) == anyio.ExceptionGroup:
#             for e in exception.exceptions:
#                 if type(e) == self.ex_type:
#                     self.to_handle_exceptions.append(e)
#                 else:
#                     self.unhandled_exceptions.append(e)

#         else:
#             if type(exception) == self.ex_type:
#                 self.to_handle_exceptions.append(exception)
#             else:
#                 self.unhandled_exceptions.append(exception)

#     def __iter__(self):
#         return

#     def __next__(self):
#         next(self.to_handle_exceptions_iter)
#         for e in self.unhandled_exceptions:
#             raise e


def my_handler(my_type, e, handler):
    if type(e) == anyio.ExceptionGroup:
        unhandled = []
        for ex in e.exceptions:
            if isinstance(e, my_type):
                handler(ex)
            else:
                unhandled.append(ex)
        if unhandled:
            raise anyio.ExceptionGroup(unhandled)

    elif isinstance(e, my_type):
        handler(e)
    else:
        raise e


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
