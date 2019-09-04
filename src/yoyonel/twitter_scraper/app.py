#!/usr/bin/env python
"""
    -u EmmanuelMacron Trump PyCon OpenGL Lyon Paris Marseille Bordeaux Toulouse

    --process run_twint_in_mono_thread -u EmmanuelMacron Trump PyCon -l 500

    # multiprocessing with linux shell and no database storing/saving.
    ╰─ time (twint -u EmmanuelMacron --limit 500 & twint -u Trump --limit 500 & twint -u PyCon --limit 500 & twint -u OpenGL --limit 500 & wait)
    ( twint -u EmmanuelMacron --limit 500 & twint -u Trump --limit 500 & twint -u)  28.56s user 2.92s system 103% cpu 30.502 total

    --process run_twint_with_asyncio -u EmmanuelMacron Trump PyCon OpenGL Lyon -l 500 --log_level info

    --process run_twint_with_asybncio --use_uvloop -u EmmanuelMacron Trump PyCon -l 500 --log_level info

    --process run_twint_with_multiprocessing -u EmmanuelMacron Trump PyCon -l 500  --log_level info
"""
import argparse
import asyncio
import builtins
import logging
import multiprocessing
import os
import queue
import signal
import sys
from collections import Counter
from contextlib import ExitStack
from dataclasses import dataclass, field
from functools import partial
from multiprocessing import Pool as MPPool
from threading import Event, Thread
from timeit import default_timer as timer
from typing import Any, Callable, Dict, List, Optional

import twint
from aiostream.stream import chunks as aio_chunks
from mock import patch
from twint.cli import main as twint_main

from yoyonel.twitter_scraper.tools.asyncio_tools import do_shutdown
from yoyonel.twitter_scraper.tools.fct_logger import init_logger
from yoyonel.twitter_scraper.tools.grouper import grouper_it

#

# RuntimeError: uvloop does not support Windows at the moment
try:
    import uvloop
except ImportError:
    pass

logger = logging.getLogger('twitter_scraper')

SIGNALS = [signal.SIGINT, signal.SIGTERM]


def mock_logger_debug(_, *__, **___):
    pass


# https://stackoverflow.com/questions/3024925/create-a-with-block-on-several-context-managers
# https://docs.python.org/3/library/contextlib.html#contextlib.ExitStack
ctx_managers_capture_outputs = [
    patch.object(logging, 'debug', mock_logger_debug),
    patch.object(builtins, 'print', mock_logger_debug)
]


def loop_store_tweets(
        queue_with_pb2_tweets: queue.Queue,
        func_is_time_to_exit: Callable[[], bool],
        func_apply_to_input: Callable[[Any], Any] = lambda i: i,
        nb_tweets_by_chunk: int = 50,
        reset_logger=None,
):
    if reset_logger:
        init_logger(reset_logger)

    def _stream_chunk_tweets():
        # https://anandology.com/python-practice-book/iterators.html
        @dataclass
        class GenPb2Tweets:
            queue: queue.Queue

            def __iter__(self):
                return self

            def __next__(self):
                while True:
                    try:
                        pb2_tweets = func_apply_to_input(self.queue.get(timeout=1.0))
                        break
                    except queue.Empty:
                        if func_is_time_to_exit():
                            raise StopIteration
                return pb2_tweets

        for _chunk_tweets in grouper_it(GenPb2Tweets(queue_with_pb2_tweets),
                                        nb_tweets_by_chunk):
            yield _chunk_tweets

    for chunk_tweets in _stream_chunk_tweets():
        tweets = [tweet for tweet in chunk_tweets]
        debug_infos = ", ".join(
            f"{user_name}#{counter}"
            for user_name, counter in Counter(
                [tweet.username.lower()
                 for tweet in tweets]).items()
        )
        logger.debug(
            f"gRPC: store {len(tweets)} tweets "
            f"from users=({debug_infos}) in db ...")

        # tweets from queue stored in database, so the queue task is done (for this chunk)
        queue_with_pb2_tweets.task_done()


def run_mono_thread_twint(twint_config: twint.Config):
    """

    Args:
        twint_config:

    Returns:

    """
    tweets_list = []

    twint_config.Store_object = True
    twint_config.Store_object_tweets_list = tweets_list
    twint.run.Search(twint_config)

    if not tweets_list:
        logger.error(f"No tweets found from twitter_user={twint_config.Username}")
        return

    # def _stream_tweets():
    #     for tweet in tweets_list:
    #         yield StorageService_pb2.StoreTweetsRequest(
    #             tweet=_convert_tweet_from_twint_to_pb2(tweet)
    #         )
    #
    # store_tweets_stream_response = MessageToDict(
    #     storage_rpc_stub.StoreTweetsStream(_stream_tweets()),
    #     including_default_value_fields=True
    # )
    # logger.debug(f"Response(StoreTweetsStream) = {store_tweets_stream_response}")


def run_twint_in_mono_thread(twint_configs):
    # # Init gRPC services Storage
    # storage_rpc_stub = rpc_init_stub(twitter_analyzer_storage_addr,
    #                                  twitter_analyzer_storage_port,
    #                                  StorageService_pb2_grpc.StorageServiceStub,
    #                                  service_name='[twint-mono_thread] twitter analyzer storage')
    for twint_config in twint_configs:
        run_mono_thread_twint(twint_config)


def loop_consume_tweets_from_twint_mp(
        queue_sync_with_twint: queue.Queue,
        # twitter_analyzer_storage_addr,
        # twitter_analyzer_storage_port,
        event_twint_worker_is_finish,
        nb_tweets_by_chunk,
        log_level: Optional[str] = None
):
    """
    AttributeError: Can't pickle local object '...'
    https://github.com/ouspg/trytls/issues/196#issuecomment-239676366

    https://github.com/grpc/grpc/tree/master/examples/python/multiprocessing
    https://github.com/grpc/grpc/blob/master/examples/python/multiprocessing/client.py

    Args:
        queue_sync_with_twint:
        # twitter_analyzer_storage_addr:
        # twitter_analyzer_storage_port:
        event_twint_worker_is_finish:
        nb_tweets_by_chunk:
        log_level:

    Returns:

    """

    # # init gRPC stub to access to Storage service(r)
    # storage_rpc_stub = rpc_init_stub(
    #     twitter_analyzer_storage_addr, twitter_analyzer_storage_port,
    #     StorageService_pb2_grpc.StorageServiceStub,
    #     service_name='[twint-multiprocessing] twitter analyzer storage'
    # )

    def _func_exit_loop():
        #
        # To create code that needs to wait for all queued tasks to be
        # completed, the preferred technique is to use the join() method.
        # return (event_twint_worker_is_finish.is_set()
        #         and queue_sync_with_twint.qsize() == 0)
        return event_twint_worker_is_finish.is_set()

    loop_store_tweets(queue_sync_with_twint,
                      # storage_rpc_stub,
                      func_is_time_to_exit=_func_exit_loop,
                      # func_apply_to_input=_convert_tweet_from_twint_to_pb2,
                      nb_tweets_by_chunk=nb_tweets_by_chunk,
                      reset_logger=log_level)


def worker_on_twint_run_search(_twint_config, use_capture_printouts: bool = False):
    with ExitStack() as stack:
        for mgr in ctx_managers_capture_outputs if use_capture_printouts else []:
            stack.enter_context(mgr)
        # Patch the entry point "append" for twint's store object container.
        # The patch connect append to put, and allow to use multiprocessing.Queue
        setattr(_twint_config.Store_object_tweets_list, "append",
                _twint_config.Store_object_tweets_list.put)
        twint.run.Search(_twint_config)


def run_twint_with_multiprocessing(
        twint_configs,
        # twitter_analyzer_storage_addr,
        # twitter_analyzer_storage_port,
        nb_tweets_by_chunk=20,
        log_level: Optional[str] = None
):
    """

    Args:
        twint_configs:
        # twitter_analyzer_storage_addr:
        # twitter_analyzer_storage_port:
        nb_tweets_by_chunk:
        log_level:

    Returns:

    """
    mp_manager = multiprocessing.Manager()
    mp_queue = mp_manager.Queue()
    mp_event_twint_worker_is_finish = mp_manager.Event()

    mp_consumers = multiprocessing.Process(
        target=loop_consume_tweets_from_twint_mp,
        kwargs={
            'queue_sync_with_twint': mp_queue,
            'event_twint_worker_is_finish': mp_event_twint_worker_is_finish,
            # 'twitter_analyzer_storage_addr': twitter_analyzer_storage_addr,
            # 'twitter_analyzer_storage_port': twitter_analyzer_storage_port,
            'nb_tweets_by_chunk': nb_tweets_by_chunk,
            'log_level': log_level,
        }
    )
    # This is critical! The consumer function has an infinite loop
    # Which means it will never exit unless we set daemon to true
    mp_consumers.daemon = True
    mp_consumers.start()

    # for each twint config (i.e twint tweets producer)
    # link to the same multiprocessing queue
    for twint_config in twint_configs:
        twint_config.Store_object = True
        twint_config.Store_object_tweets_list = mp_queue

    # Init a multiprocessing pool for all twint configs (producers)
    # Launch worker on search (tweets) method
    mp_pool = MPPool(len(twint_configs))
    _ = mp_pool.map(
        partial(worker_on_twint_run_search,
                use_capture_printouts=True),  # argument apply to all calls
        twint_configs  # map on all twint configurations
    )
    mp_pool.close()
    # wait until all producers finish
    mp_pool.join()
    # set the event (flag) to notify all consumers that twint producers are finished
    mp_event_twint_worker_is_finish.set()
    # wait until all consumers finished
    mp_consumers.join()

    assert mp_queue.qsize() == 0


@dataclass
class GRPCAsyncIOTwint:
    twint_configs: List[twint.Config] = field(init=True)

    use_capture_printouts: bool = field(init=True, default=True)

    # AsyncIO Queue for processing twint tweet to gRPC tweet
    aio_queue_with_twint_tweets: asyncio.Queue = field(default_factory=asyncio.Queue, init=False)
    # Queue for GRPC
    # queue_with_pb2_tweets: queue.Queue = field(default_factory=queue.Queue, init=False)
    # Queue for Twint
    queue_link_to_twint: queue.Queue = field(default_factory=queue.Queue, init=False)
    # https://docs.python.org/3/library/threading.html#event-objects
    # https://docs.python.org/3/library/threading.html#threading.Event
    # 1 event for each twitter user (i.e twint config)
    event_twint_finished: Dict[twint.Config, Event] = field(default_factory=dict, init=False)

    @staticmethod
    def _is_finished(gprc_asyncio_twint: 'GRPCAsyncIOTwint') -> bool:
        """
        Condition to stop main runner (loop):
            - no more tweets from twint (for all users)
            - no items (in processing) in queues:
                - queue_for_twint
                - queue_for_pb2

        Args:
            gprc_asyncio_twint:

        Returns:

        """
        flags = (all([event.is_set() for event in gprc_asyncio_twint.event_twint_finished.values()]),
                 gprc_asyncio_twint.queue_link_to_twint.empty(),
                 # gprc_asyncio_twint.queue_with_pb2_tweets.empty()
                 )
        # flags_explains = ('no more tweets from twint (from all users)',
        #                   'no items in queue_for_twint',
        #                   'no items in queue_for_pb2')
        # debug_msg_flags = ", ".join([
        #     f"{flags_explains}={flags}"
        #     for flags, flags_explains in zip(flags, flags_explains)
        # ])
        # logger.debug(f"flags: {debug_msg_flags}")
        return all(flags)

    def worker_twint(self, config: twint.Config):
        # new event loop just for twint (containerized in separate thread)
        event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(event_loop)
        twint.run.Search(config)
        self.event_twint_finished[config].set()
        logger.debug(f"Twint worker (user={config.Username}) finished !")

    async def producer_twint_tweets(self, twint_config: twint.Config):
        # https://stackoverflow.com/questions/3487434/overriding-append-method-after-inheriting-from-a-python-list
        class QueuedList:
            def __init__(self, _queue):
                self._q_twint_tweet = _queue

            def append(self, item):
                self._q_twint_tweet.put(item)

        # 1 centralized queue to communicate between twint and our application
        twint_config.Store_object = True
        twint_config.Store_object_tweets_list = QueuedList(self.queue_link_to_twint)

        t = Thread(target=self.worker_twint, args=(twint_config,))
        t.start()

        async def loop_on_tweets_from_twint():
            while True:
                try:
                    twint_tweet = self.queue_link_to_twint.get(timeout=1.0)
                except queue.Empty:
                    # Condition to stop producer: no more tweets from twint
                    if self.event_twint_finished[twint_config].is_set():
                        break
                    continue
                await self.aio_queue_with_twint_tweets.put(twint_tweet)
                # https://stackoverflow.com/questions/41871046/suspend-coroutine-and-return-to-caller?noredirect=1&lq=1
                # https://github.com/python/cpython/blob/44cd86bbdddb1f7b05deba2c1986a1e98f992429/Lib/asyncio/tasks.py#L611-L627
                # sleep(0) does [...] a simple yield. In fact they have a private __sleep0() function there with that yield statement.
                await asyncio.sleep(0.0)

        # on 'twint' package, using mock/patches to intercept (intermediate) results from:
        #   - logs: twint use default logger directly from logging package
        #   - printout: print tweets results (to stdout)
        with ExitStack() as stack:
            for mgr in ctx_managers_capture_outputs if self.use_capture_printouts else []:
                stack.enter_context(mgr)
            await loop_on_tweets_from_twint()

    async def consumer_twint_tweets(self):
        async def gen_twint_tweets():
            while True:
                twint_tweet = await self.aio_queue_with_twint_tweets.get()
                yield twint_tweet

        # https://github.com/vxgmichel/aiostream/issues/12
        # https://stackoverflow.com/questions/37280141/lazy-iterators-generators-with-asyncio
        # https://www.python.org/dev/peps/pep-0525/#example
        async with aio_chunks(gen_twint_tweets(), 25).stream() as aio_chunk_twint_tweets_streamer:
            async for chunk_twint_tweets in aio_chunk_twint_tweets_streamer:
                tweets = chunk_twint_tweets
                debug_infos = ", ".join(
                    f"{user_name}#{counter}"
                    for user_name, counter in Counter(
                        [tweet.username.lower() for tweet in tweets]).items())
                logger.debug(
                    f"gRPC: store {len(tweets)} tweets "
                    f"from users=({debug_infos}) in db ...")

    async def do_run(self, event_loop, delay=1.0):
        while True:
            if GRPCAsyncIOTwint._is_finished(self):
                break
            await asyncio.sleep(delay=delay)

        results = await do_shutdown(event_loop)
        logger.debug('finished awaiting cancelled tasks, results: {0}'.format(results))

    def run_with_asyncio(self,
                         # storage_rpc_stub: Optional[StorageServiceServicer],
                         nb_consumers: int = 1):
        """

        Args:
            # storage_rpc_stub:
            nb_consumers:

        Returns:

        """
        # t = Thread(target=loop_store_tweets,
        #            kwargs={
        #                'queue_with_pb2_tweets': self.queue_with_pb2_tweets,
        #                # 'storage_rpc_stub': storage_rpc_stub,
        #                'func_is_time_to_exit': lambda: GRPCAsyncIOTwint._is_finished(self),
        #                'nb_tweets_by_chunk': 25 * 2})
        # t.start()

        loop = asyncio.get_event_loop()

        # Producer(s)
        for twint_config in self.twint_configs:
            logger.info(f"Create producer twint_tweet for user={twint_config.Username}")
            self.event_twint_finished[twint_config] = Event()
            loop.create_task(self.producer_twint_tweets(twint_config))

        # Consumer(s)
        logger.info(f"Create {nb_consumers} consumers ...")
        for _ in range(nb_consumers):
            loop.create_task(self.consumer_twint_tweets())

        loop.run_until_complete(self.do_run(loop))


def run_twint_with_asyncio(twint_configs,
                           # twitter_analyzer_storage_addr, twitter_analyzer_storage_port
                           ):
    # # Init gRPC services Storage
    # storage_rpc_stub = rpc_init_stub(twitter_analyzer_storage_addr,
    #                                  twitter_analyzer_storage_port,
    #                                  StorageService_pb2_grpc.StorageServiceStub,
    #                                  service_name='[twint-asyncio] twitter analyzer storage')
    #
    gprc_asyncio_twint = GRPCAsyncIOTwint(twint_configs)
    # 1 consumer
    gprc_asyncio_twint.run_with_asyncio(
        # storage_rpc_stub,
        nb_consumers=1)


def run_twint_with_cli(twint_configs):
    # https://stackoverflow.com/questions/18160078/how-do-you-write-tests-for-the-argparse-portion-of-a-python-module
    for twint_config in twint_configs:
        with patch('twint.cli.argparse._sys.argv',
                   ['twint',
                    '-u', twint_config.Username,
                    '--limit', str(twint_config.Limit)
                    ]):
            twint_main()


def process(args: argparse.Namespace):
    def _signal_handler(_sig, _):
        """ Empty signal handler used to override python default one """
        logger.info("sig: {} intercepted. Closing application.".format(_sig))
        # https://stackoverflow.com/questions/73663/terminating-a-python-script
        sys.exit()

    # Signals HANDLER (to exit properly)
    for sig in SIGNALS:
        signal.signal(sig, _signal_handler)

    twint_configs = []
    for twitter_user in args.twitter_users:
        twint_config = twint.Config()
        twint_config.Username = twitter_user
        twint_config.Limit = args.twint_limit  # bug with the Limit parameter not working only factor of 25 tweets
        twint_config.Debug = args.twint_debug
        twint_configs.append(twint_config)

    # twitter_analyzer_storage_host = (args.twitter_analyzer_storage_addr,
    #                                  args.twitter_analyzer_storage_port)
    logger.info("Using processing: <%s>", args.processor)
    if args.processor == 'run_twint_in_mono_thread':
        run_twint_in_mono_thread(twint_configs,
                                 # *twitter_analyzer_storage_host
                                 )
    elif args.processor == 'run_twint_with_asyncio':
        run_twint_with_asyncio(twint_configs,
                               # *twitter_analyzer_storage_host
                               )
    elif args.processor == 'run_twint_with_multiprocessing':
        run_twint_with_multiprocessing(twint_configs,
                                       # *twitter_analyzer_storage_host,
                                       log_level=args.log_level)
    elif args.processor == 'run_twint_with_cli':
        run_twint_with_cli(twint_configs)


def build_parser(parser=None, **argparse_options):
    """
    Args:
        parser (argparse.ArgumentParser):
        **argparse_options (dict):
    Returns:
    """
    if parser is None:
        parser = argparse.ArgumentParser(**argparse_options)

    argparse_default = "(default=%(default)s)."

    # TODO: grab parser from twint lib and getting all options available (by inheritance)
    parser.add_argument('-p', '--processor',
                        dest='processor',
                        type=str,
                        choices=['run_twint_in_mono_thread',
                                 'run_twint_with_asyncio',
                                 'run_twint_with_multiprocessing',
                                 'run_twint_with_cli'],
                        default='run_twint_with_asyncio',
                        help=f"Processor to use to grab tweets from twinter. {argparse_default}")
    parser.add_argument('-u', '--twitter_users',
                        dest='twitter_users',
                        nargs='+',
                        type=str,
                        required=True,
                        help="Twitter user.")

    parser.add_argument("-l", "--twint_limit",
                        dest="twint_limit",
                        type=int,
                        required=False,
                        default=100,
                        help=f"Twint limit for scrapping tweets. {argparse_default}")

    parser.add_argument("--twint_debug",
                        dest="twint_debug",
                        action="store_true",
                        help="Activate Debug mode for twint (printout results in logs).")

    parser.add_argument("--use_uvloop",
                        action="store_true",
                        help="Activate using uvloop for asyncio event loop [OPTIMIZATION]")

    # # GRPC SERVICES
    # # - STORAGE
    # parser.add_argument("--twitter_analyzer_storage_addr",
    #                     default=os.environ.get('TWITTER_ANALYZER_STORAGE_SERVICE_HOST',
    #                                            'localhost'),
    #                     type=str,
    #                     help=f"{argparse_default}")
    # parser.add_argument("--twitter_analyzer_storage_port",
    #                     default=int(os.environ.get('TWITTER_ANALYZER_STORAGE_PORT',
    #                                                '50052')),
    #                     type=int,
    #                     help=f"{argparse_default}",
    #                     metavar='')

    parser.add_argument(
        '-ll', '--log_level',
        type=str, required=False, default='debug',
        choices=['debug', 'warning', 'info', 'error', 'critical'],
        help=f"The logger filter level. {argparse_default}",
    )
    parser.add_argument(
        '-lf', '--log_file',
        type=str, required=False,
        help="The path to the file into which the logs will be streamed. "
        f"{argparse_default}",
    )

    parser.add_argument("-v", "--verbose",
                        action="store_true", default=False,
                        help="increase output verbosity (enable 'DEBUG' level log). "
                        f"{argparse_default}")

    return parser


def parse_arguments(args=None):
    """
    Returns:
        argparse.Namespace:
    """
    return build_parser().parse_args(args)


def main(args=None):
    start = timer()

    # Deal with inputs (stdin, parameters, etc ...)
    args = parse_arguments(args)

    init_logger(args.log_level)

    if args.use_uvloop:
        if os.name == 'nt':
            logger.warning("Can't use uvloop on Windows platform.")
        else:
            logger.info("Install uvloop replacement of the built-in asyncio event loop")
            uvloop.install()

    # https://docs.python.org/3/library/asyncio-dev.html#asyncio-debug-mode
    if os.environ.get(" PYTHONASYNCIODEBUG", False):
        # activate debug mode
        asyncio.get_event_loop().set_debug(True)
        logging.getLogger("asyncio").setLevel(logging.WARNING)

    process(args)

    end = timer()
    logger.info(f"Time elapsed: {end - start}")


if __name__ == '__main__':
    main()
    sys.exit(0)
