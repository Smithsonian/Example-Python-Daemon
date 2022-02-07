import logging
import os
import sys
import time
import systemd.daemon

class MyService:
    FIFO = '/tmp/myservice_pipe'

    def __init__(self, delay=5):
        # Put service start up code here
        self.logger = self._init_logger()
        self.delay = delay
        if not os.path.exists(MyService.FIFO):
            os.mkfifo(MyService.FIFO)
        self.fifo = os.open(MyService.FIFO, os.O_RDWR | os.O_NONBLOCK)
        self.logger.info('MyService instance created')

    def _init_logger(self):
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.DEBUG)
        stdout_handler = logging.StreamHandler()
        stdout_handler.setLevel(logging.DEBUG)
        stdout_handler.setFormatter(logging.Formatter('%(levelname)8s | %(message)s'))
        logger.addHandler(stdout_handler)
        return logger

    def run(self):
        try:
            while True:
                # Put the daemon's main loop here
                time.sleep(self.delay)
                self.logger.info('Tick')
        except KeyboardInterrupt:
            self.logger.warning('Keyboard interrupt (SIGINT) received...')
            self.stop()

    def stop(self):
        # Put the daemon's cleanup code here.
        self.logger.info('Cleaning up...')
        if os.path.exists(MyService.FIFO):
            os.close(self.fifo)
            os.remove(MyService.FIFO)
            self.logger.info('Named pipe removed')
        else:
            self.logger.error('Named pipe not found, nothing to clean up')
        sys.exit(0)


if __name__ == '__main__':
    # Do start up stuff
    service = MyService()
    time.sleep(5)
    # systemctl will wait until this notification is sent
    systemd.daemon.notify('READY=1')
    # Run the daemon
    service.run()
