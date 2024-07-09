import logging
import os
import sys
import time
import datetime
import threading
import json

import systemd.daemon
import signal

default_config = "/home/smauser/wsma_config/hardware/hardware_config.json"
default_smax_config = "/home/smauser/wsma_config/smax_config.json"

READY = 'READY=1'
STOPPING = 'STOPPING=1'

from smax import SmaxRedisClient, join

from example_smax_hardware import ExampleHardware

class ExampleHardwareInterface:
    """An example daemon for communicating with a piece of hardware."""
    def __init__(self, config=None, logger=None):
        """Create a new daemon class that carries out monitoring and control of a simulated
        piece of hardware. 
        
        Pass the initial config to the hardware object if given.
        
        Keyword Arguments:
            config (dict) : dictionary of config values for the hardware and daemon"""
        self._hardware = None
        self._hardware_config = None
        self._hardware_lock = threading.Lock()
        self._hardware_error = 'No connection attempted'
        self._hardware_data = {}
        
        self.logger = logger
        
        if config:
            self.configure(config)
            
    def configure(self, config):
        """Configure the daemon and hardware"""
        
        if 'config' in config.keys():
            self._hardware_config = config['config']
            
        if 'logged_data' in config.keys():
            self._hardware_data = config['logged_data']
            
        if self._hardware and self._hardware_config:
            with self._hardware_lock:
                self._hardware.configure(self._hardware_config)

    def connect_hardware(self):
        """Create and initialize hardware communication object."""
        try:
            with self._hardware_lock:
                self._hardware = ExampleHardware(config=self._hardware_config)
                self._hardware_error = "None"
                if self._hardware_config:
                    self._hardware.configure(self._hardware_config)
                
        except Exception as e: # Hardware connection errors
            self._hardware = None
            self._hardware_error = repr(e)
            
    def disconnect_hardware(self):
        self._hardware = None
        self._harwarre_error = "disconnected"
        
    def logging_action(self):
        """Get logging data from hardware and share to SMA-X"""
        # check for hardware connection, and connect if not present
        # This will automatically retry the connection every logging_interval
        # We could instead set up a connection retrying loop, but this
        # seems like it would work for most things, and will provide
        # feedback to the 
        if self._hardware is None:
            self.connect_hardware()
        
        if self._hardware:
            try:
                with self._hardware_lock:
                    logged_data = {}
                    # do logging gets
                    for data in self._hardware_data.keys():
                        reading = self._hardware.__getattribute__(data)
                        logged_data[data] = reading
                        self.logger.info(f'Got data for hardware {data}: {reading}')
                logged_data['comm_status'] = "good"
                logged_data['comm_error'] = "None"
            except Exception as e: # Except hardware connection errors
                self._hardware = None
                logged_data = {'comm_status':'connection error'}
                logged_data['comm_error'] = repr(e)
        else:
            logged_data = {'comm_status':'connection error',
                           'comm_error':self._hardware_error}
        
        return logged_data
        
    def set_random_base_callback(self, message):
        """Callback to be triggered on Pub/Sub for random base value"""
        if self.logger:
            date = datetime.datetime.fromtimestamp(message.date)
            self.logger.info(f'Received callback notification for {message.origin} from {message.source} with data {message.data} at {date}')
        
        newbase = message.data
        
        if self._hardware:
            try:
                with self._hardware_lock:
                    self._hardware.base = newbase
            except Exception as e: # Except hardware errors
                self._hardware_error = repr(e)
            
    def set_random_range_callback(self, message):
        """Callback to be triggered on Pub/Sub for random base value"""
        if self.logger:
            date = datetime.datetime.fromtimestamp(message.date)
            self.logger.info(f'Received callback notification for {message.origin} from {message.source} with data {message.data} at {date}')
        
        newrange = message.data
        
        if self._hardware:
            try:
                with self._hardware_lock:
                    self._hardware.range = newrange
            except Exception as e: # Except hardware errors
                self._hardware_error = repr(e)
        

class ExampleSmaxService:
    # Specify the path for a resource that we open and must close correctly
    # when the service is stopped
    FIFO = '/tmp/myservice_pipe'

    def __init__(self, config=default_config, smax_config=default_smax_config):
        """Service object initialization code"""
        self.logger = self._init_logger()
        
        # Configure SIGTERM behavior
        signal.signal(signal.SIGTERM, self._handle_sigterm)

        # Read the hardware and SMAX configuration
        self.read_config(config, smax_config)

        # A list of control keys
        self.control_keys = None

        # The SMAXRedisClient instance
        self.smax_client = None
        
        # The simulated hardware class
        self.hardware = None

        # Log that we managed to create the instance
        self.logger.info('Example-SMAX-Daemon instance created')
        
        # A time to delay between loops
        self.delay = 1.0

    def _init_logger(self):
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.DEBUG)
        stdout_handler = logging.StreamHandler()
        stdout_handler.setLevel(logging.DEBUG)
        stdout_handler.setFormatter(logging.Formatter('%(levelname)8s | %(message)s'))
        logger.addHandler(stdout_handler)
        return logger
    
    def read_config(self, config, smax_config=None):
        """Read the configuration file."""
        # Read the file
        with open(config) as fp:
            self._config = json.load(fp)
            fp.close()
        
        # If smax_config is given, update the compressor specific config file with the smax_config
        if smax_config:    
            with open(smax_config) as fp:
                s_config = json.load(fp)
                fp.close()
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
        
        self.control_keys = self._config["smax_config"]["control_keys"]
                             
        self.logging_interval = self._config["logging_interval"]

    def start(self):
        """Code to be run before the service's main loop"""
        # Start up code

        # Create the hardware interface
        self.hardware = ExampleHardwareInterface(config=self._config)
        
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
        for k in self.control_keys:
            self.smax_client.smax_subscribe(join(self.smax_table, self.smax_key, k), getattr(self._hardware, self.control_keys[k]))
        self.logger.info('Subscribed to pubsub notifications')

        # systemctl will wait until this notification is sent
        # Tell systemd that we are ready to run the service
        systemd.daemon.notify(READY)

        # Run the service's main loop
        self.run()

    def run(self):
        """Run the main service loop"""
        
        # Launch the logging thread as a daemon so that it can be shut down quickly
        self.logging_thread = threading.Thread(target=self.logging_loop, args=(self.logging_interval), daemon=True, name='Logging')
        self.logging_thread.start()
        
        try:
            while True:
                time.sleep(self.delay)

        except KeyboardInterrupt:
            # Monitor for SIGINT, which we've set as the terminate signal in the
            # .service file
            self.logger.warning('SIGINT (keyboard interrupt) received...')
            self.stop()
            
    def logging_loop(self, interval):
        """The loop that will run in the thread to carry out logging"""
        while True:
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
        logged_data = self.hardware.logging_action()

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
