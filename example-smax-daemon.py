import logging
import os
import sys
import time

import systemd.daemon

import random

class ExampleSmaxService:
    # Specify the path for a resource that we open and must close correctly
    # when the service is stopped
    FIFO = '/tmp/myservice_pipe'

    def __init__(self, delay=1, logging_interval=5):
        """Service object initialization code"""
        self.logger = self._init_logger()
        self._scheduler = sched.scheduler(time.time, time.sleep)

        self.delay = delay
        self.logging_interval = logging_interval

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

        # This snippet creates a pipe that we have to close properly when the
        # service terminates
        if not os.path.exists(ExampleService.FIFO):
            os.mkfifo(ExampleService.FIFO)
        self.fifo = os.open(ExampleService.FIFO, os.O_RDWR | os.O_NONBLOCK)
        self.logger.info('Named pipe set up')
        # Wait a bit
        time.sleep(self.delay)

        # Set up the time for the next logging action
        self._next_log_time = datetime.now() + self.logging_interval

        # systemctl will wait until this notification is sent
        # Tell systemd that we are ready to run the service
        systemd.daemon.notify('READY=1')

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
            self.logger.warning('Keyboard interrupt (SIGINT) received...')
            self.stop()

    def smax_logging_action(self):
        """Run the code to write logging data to SMAX"""
        # Gather data
        logging_data = random.randrange(12.1, 14.2)

        # write code to SMA-X
        self.logger.info(f'Pretending to Write {logging_data} to SMAX ')
        # Simulate a network delay
        time.sleep(random.randrange(0.01, 0.2))


    def stop(self):
        """Clean up after the service's main loop"""
        # Tell systemd that we received the stop signal
        systemd.daemon.notify('STOPPING=1')

        # Put the service's cleanup code here.
        self.logger.info('Cleaning up...')
        if os.path.exists(ExampleService.FIFO):
            os.close(self.fifo)
            os.remove(ExampleService.FIFO)
            self.logger.info('Named pipe removed')
        else:
            self.logger.error('Named pipe not found, nothing to clean up')

        # Exit to finally stop the serivce
        sys.exit(0)


if __name__ == '__main__':
    # Do start up stuff
    service = ExampleSmaxService()
    service.start()
