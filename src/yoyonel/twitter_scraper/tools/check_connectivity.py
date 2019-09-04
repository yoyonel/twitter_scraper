try:
    import grpc
except ImportError:
    raise ModuleNotFoundError("grpc is needed in order to "
                              "launch RPC server (`pip install .[grpc]`)")


def check_connectivity(
        channel,
        block=True,
        timeout_seconds=None,
        timeout_raise=True,
):
    """
    Check if a gRPC channel is reachable. If :attr:`block` is True and :attr:`timeout_seconds` is None, this function
    wont return until the channel is reachable.

    :param channel: The gRPC channel to check connectivity
    :type channel: grpc.Channel

    :param block: Block until the channel is reachable, or :attr:`timeout_seconds` is elapsed
    :type block: bool

    :param timeout_seconds: Timeout while waiting for reachability. Use `None` for no timeout
    :type timeout_seconds: int

    :param timeout_raise: Raise an exception if a timeout is reached
    :type timeout_raise: bool

    :return: If block is True, returns True if the channel is reachable, False otherwise. If block is False, returns
             a future
    :rtype: bool | grpc.Future

    >>> type(check_connectivity(block=False))
    <class 'grpc._utilities._ChannelReadyFuture'>

    >>> check_connectivity(block=True, timeout_seconds=0.1)
    Traceback (most recent call last):
        ...
    grpc.FutureTimeoutError

    >>> check_connectivity(block=True, timeout_seconds=0.1, timeout_raise=False)
    """
    # https://grpc.io/grpc/python/grpc.html#grpc.ChannelConnectivity
    # https://grpc.io/grpc/python/grpc.html
    # https://github.com/grpc/grpc/issues/9987
    future = grpc.channel_ready_future(channel)  # type: grpc.Future

    if block:
        # Wait until the channel is connected
        try:
            future.result(timeout=timeout_seconds)
        except grpc.FutureTimeoutError as e:
            if timeout_raise:
                raise e

            return False

        return True

    return future
