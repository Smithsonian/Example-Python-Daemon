import logging
import os
import sys
import time
import datetime

import systemd.daemon

from smax import SmaxRedisClient

import random

class ExampleSmaxService:
    # Specify the path for a resource that we open and must close correctly
    # when the service is stopped
    FIFO = '/tmp/myservice_pipe'

    def __init__(self, delay=1, logging_interval=5):
        """Service object initialization code"""
        self.logger = self._init_logger()

        self.delay = delay
        self.logging_interval = logging_interval
        
        self.smax_server = "localhost"
        self.smax_port = 6379
        self.smax_db = 0
        # The SMAXRedisClient instance
        self.smax_client = None
        
        self._random_base = 0
        self._random_range = 1

        # Log that we managed to create the instance
        self.logger.info('Example-SMAX-Daemon instance created')

    def _init_logger(self):
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.DEBUG)
        stdout_handler = logging.StreamHandler()
        stdout_handler.setLevel(logging.DEBUG)
        stdout_handler.setFormatter(logging.Formatter('%(levelname)8s | %(message)s'))
        logger.addHandler(stdout_handler)
        return logger

    def start(self):
        """Code to be run before the service's main loop"""
        # Start up code

        # This snippet creates a connection to SMA-X that we haveclose properly when the
        # service terminates
        if self.smax_client is None:
            self.smax_client = SmaxRedisClient(redis_ip=self.smax_server, redis_port=self.smax_port, redis_db=self.smax_db, program_name="example_smax_daemon")
        else:
            self.smax_client.smax_connect_to(self.smax_server, self.smax_port, self.smax_db)
        
        self.logger.info('SMA-X client connected to {self.smax_server}:{self.smax_port} DB:{self.smx_db}')
        
        # Set default values for pubsub channels
        self.smax_client.smax_share("example_smax_daemon:logging_action", "random_base", self._random_base)
        self.smax_client.smax_share("example_smax_daemon:logging_action", "random_range", self._random_range)
        self.logger.info('Set initial values for pubsub values')

        # Register pubsub channels
        self.smax_client.smax_subscribe("example_smax_daemon:logging_action:random_base", self.smax_random_base_callback)
        self.smax_client.smax_subscribe("example_smax_daemon:logging_action:random_range", self.smax_random_range_callback)
        self.logger.info('Subscribed to pubsub notifications')

        # Set up the time for the next logging action
        self._next_log_time = time.monotonic() + self.logging_interval

        # systemctl will wait until this notification is sent
        # Tell systemd that we are ready to run the service
        systemd.daemon.notify(systemd.daemon.Notification.READY)

        # Run the service's main loop
        self.run()

    def run(self):
        """Run the main service loop"""
        try:
            while True:
                # Put the service's regular activities here
                self.smax_logging_action()
                time.sleep(self.logging_interval)

        except KeyboardInterrupt:
            # Monitor for SIGINT, which we've set as the terminate signal in the
            # .service file
            self.logger.warning('SIGINT (keyboard interrupt) received...')
            self.stop()

    def smax_logging_action(self):
        """Run the code to write logging data to SMAX"""
        # Gather data
        logging_data = random.uniform(self._random_base, self._random_base+self._random_range)

        # write value to SMA-X
        self.smax_client.smax_share("example_smax_daemon:logging_action", "random_data", logging_data)
        self.logger.info(f'Wrote {logging_data} to SMAX ')
        # Simulate a network delay
        time.sleep(random.uniform(0.01, 0.2))
        
        # read back value from SMA-X
        read_back = self.smax_client.smax_pull("example_smax_daemon:logging_action", "random_data")
        date = datetime.datetime.utcfromtimestamp(read_back.date)
        self.logger.info(f'Read back {read_back.data}, written at {date} from SMA-X')
        
    def smax_random_base_callback(self, message):
        """Run on a pubsub notifcation"""
        date = datetime.datetime.utcfromtimestamp(message.date)
        self.logger.info(f'Received PubSub notification for {message.origin} from {message.source} with data {message.data} at {date}')
        
        self._random_base = message.data
        
    def smax_random_range_callback(self, message):
        """Run on a pubsub notification"""
        date = datetime.datetime.utcfromtimestamp(message.date)
        self.logger.info(f'Received PubSub notification for {message.origin} from {message.source} with data {message.data} at {date}')
        
        self._random_range = message.data

    def stop(self):
        """Clean up after the service's main loop"""
        # Tell systemd that we received the stop signal
        systemd.daemon.notify(systemd.daemon.Notification.STOPPING)

        # Put the service's cleanup code here.
        self.logger.info('Cleaning up...')
        if self.smax_client:
            self.smax_client.smax_unsubscribe()
            self.smax_client.smax_disconnect()
            self.logger.info('SMA-X client disconnected')
        else:
            self.logger.error('SMA-X client not found, nothing to clean up')

        # Exit to finally stop the serivce
        sys.exit(0)


if __name__ == '__main__':
    # Do start up stuff
    service = ExampleSmaxService()
    service.start()
