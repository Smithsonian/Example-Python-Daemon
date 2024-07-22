#!/usr/bin/env python
import logging
import sys
import time

import threading
import json

import systemd.daemon
import signal

default_smax_config = "/home/smauser/wsma_config/smax_config.json"

# Change these three lines per application
daemon_name = "Example-SMA-daemon"
from example_hardware_interface import ExampleHardwareInterface as HardwareInterface
default_config = "/home/smauser/wsma_config/example-smax-daemon/daemon_config.json"

READY = 'READY=1'
STOPPING = 'STOPPING=1'

from smax import SmaxRedisClient, join


class ExampleSmaxService:
    # Specify the path for a resource that we open and must close correctly
    # when the service is stopped
    FIFO = '/tmp/myservice_pipe'

    def __init__(self, config=default_config, smax_config=default_smax_config):
        """Service object initialization code"""
        self.logger = self._init_logger()
        
        # Configure SIGTERM behavior
        signal.signal(signal.SIGTERM, self._handle_sigterm)

        # A list of control keys
        self.control_keys = None

        # Read the hardware and SMAX configuration
        self.read_config(config, smax_config)
        self.logger.info('Read Config File')

        # The SMAXRedisClient instance
        self.smax_client = None
        
        # The simulated hardware class
        self.hardware = None

        # Log that we managed to create the instance
        self.logger.info(f'{daemon_name} instance created')
        
        # A time to delay between loops
        self.delay = 1.0

    def _init_logger(self):
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.DEBUG)
        stdout_handler = logging.StreamHandler()
        stdout_handler.setLevel(logging.DEBUG)
        stdout_handler.setFormatter(logging.Formatter('%(levelname)8s | %(message)s'))
        logger.addHandler(stdout_handler)
        file_handler = logging.FileHandler(f'{daemon_name.lower()}.log')
        file_handler.setLevel(logging.DEBUG)
        logger.addHandler(file_handler)
        return logger
    
    def read_config(self, config, smax_config=None):
        """Read the configuration file."""
        # Read the file
        with open(config) as fp:
            self._config = json.load(fp)
            fp.close()
        
        # If smax_config is given, update the hardware specific config file with the smax_config
        if smax_config:    
            with open(smax_config) as fp:
                s_config = json.load(fp)
                fp.close()
            self.logger.debug("Got smax_config")
            self.logger.debug(s_config)
            if "smax_table" in self._config["smax_config"]:
                smax_root = s_config["smax_table"]
                self._config["smax_config"]["smax_table"] = ":".join([smax_root, self._config["smax_config"]["smax_table"]])
                del s_config["smax_table"]
            self._config["smax_config"].update(s_config)
        
        # parse the _config dictionary and set up values
        self.smax_server = self._config["smax_config"]["smax_server"]
        self.smax_port = self._config["smax_config"]["smax_port"]
        self.smax_db = self._config["smax_config"]["smax_db"]
        self.smax_table = self._config["smax_config"]["smax_table"]
        self.smax_key = self._config["smax_config"]["smax_key"]
        
        self.logger.debug("SMAX Configuration:")
        self.logger.debug(f"\tSMAX Server: {self.smax_server}")
        self.logger.debug(f"\tSMAX Port  : {self.smax_port}")
        self.logger.debug(f"\tSMAx DB    : {self.smax_db}")
        self.logger.debug(f"\tSMAX Table : {self.smax_table}")
        self.logger.debug(f"\tSMAX Key   : {self.smax_key}")
        
        
        self.control_keys = self._config["smax_config"]["smax_control_keys"]
        self.logger.debug("Got control keys:")
        for k in self.control_keys.keys():
            self.logger.debug(f"\t {k} : {self.control_keys[k]}")
        
        self.logging_interval = self._config["logging_interval"]
        self.logger.debug(f"Logging Interval {self.logging_interval}")

    def start(self):
        """Code to be run before the service's main loop"""
        # Start up code

        # Create the hardware interface
        self.hardware = HardwareInterface(config=self._config, logger=self.logger)
        self.logger.info('Created hardware interface object')
        
        # Create the SMA-X interface
        # This snippet creates a connection to SMA-X that we have to close properly when the
        # service terminates
        if self.smax_client is None:
            self.smax_client = SmaxRedisClient(redis_ip=self.smax_server, redis_port=self.smax_port, redis_db=self.smax_db, program_name="example_smax_daemon")
        else:
            self.smax_client.smax_connect_to(self.smax_server, self.smax_port, self.smax_db)
        
        self.logger.info('SMA-X client connected to {self.smax_server}:{self.smax_port} DB:{self.smx_db}')

        # Register pubsub channels specified in config["smax_config"]["control_keys"] to the 
        # callbacks specified in the config.
        for k in self.control_keys.keys():
            self.smax_client.smax_subscribe(join(self.smax_table, self.smax_key, k), getattr(self.hardware, self.control_keys[k]))
        self.logger.info('Subscribed to pubsub notifications')

        # systemctl will wait until this notification is sent
        # Tell systemd that we are ready to run the service
        systemd.daemon.notify(READY)

        # Run the service's main loop
        self.run()

    def run(self):
        """Run the main service loop"""
        
        # Launch the logging thread as a daemon so that it can be shut down quickly
        self.logging_thread = threading.Thread(target=self.logging_loop, daemon=True, name='Logging')
        self.logging_thread.start()
        
        self.logger.info("Started logging thread")
        
        try:
            while True:
                time.sleep(self.delay)

        except KeyboardInterrupt:
            # Monitor for SIGINT, which we've set as the terminate signal in the
            # .service file
            self.logger.warning('SIGINT (keyboard interrupt) received...')
            self.stop()
            
    def logging_loop(self):
        """The loop that will run in the thread to carry out logging"""
        while True:
            self.logger.debug("tick")
            next_log_time = time.monotonic() + self.logging_interval
            try:
                self.smax_logging_action()
            except Exception as e:
                pass

            # Try to run on a regular schedule, but if smax_logging_action takes too long,
            # just wait logging_interval between finishing one smax_logging_action and starting next.
            curr_time = time.monotonic()
            if next_log_time > curr_time:
                time.sleep(next_log_time - curr_time)
            else:
                time.sleep(self.logging_interval)
        
    def smax_logging_action(self):
        """Run the code to write logging data to SMAX"""
        # Gather data
        self.logger.debug("In logging action")
        logged_data = self.hardware.logging_action()

        self.logger.debug("Received data")
        
        # write values to SMA-X
        for key in logged_data.keys():
            self.logger.info(f"key in logged_data.keys(): {key}")
            if ":" in key:
                ls = [self.smax_key]
                ls.extend(key.split(":")[0:-1])
                atab = ":".join(ls)
                skey = key.split(":")[-1]
            else:
                atab = self.smax_key
                skey = key
            self.smax_client.smax_share(f"{self.smax_table}:{atab}", skey, logged_data[key])
        self.logger.info(f'Wrote hardware data to SMAX ')
        
    def _handle_sigterm(self, sig, frame):
        self.logger.warning('SIGTERM received...')
        self.stop()

    def stop(self):
        """Clean up after the service's main loop"""
        # Tell systemd that we received the stop signal
        systemd.daemon.notify(STOPPING)

        # Clean up the hardware
        self.hardware.disconnect_hardware()

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
