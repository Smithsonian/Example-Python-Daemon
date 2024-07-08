import logging
import os
import sys
import time
import datetime
import threading

import systemd.daemon

default_config = "/home/smauser/wsma_config/hardware/hardware_config.json"
default_smax_config = "/home/smauser/wsma_config/smax_config.json"

READY = 'READY=1'
STOPPING = 'STOPPING=1'

from smax import SmaxRedisClient

from example_smax_hardware import ExampleHardware

class ExampleHardwareInterface:
    """An example daemon for communicating with a piece of hardware."""
    def __init__(self, config=None):
        """Create a new daemon class that carries out monitoring and control of a simulated
        piece of hardware. 
        
        Pass the initial config to the hardware object if given.
        
        Keyword Arguments:
            config (dict) : dictionary of config values for the hardware and daemon"""
        self._hardware = None
        self._hardware_config = None
        self._hardware_lock = threading.Lock()
        
        # Logging interval in seconds
        self.logging_interval = 5.0
        
        if config:
            self.configure(config)
            
    def configure(self, config):
        """Configure the daemon and hardware"""
        if 'logging_interval' in config.keys():
            self.logging_interval = config['logging_interval']
        
        if 'config' in config.keys():
            self._hardware_config = config['config']
            
        if self._hardware and self._hardware_config:
            with self._hardware_lock:
                self._hardware.configure(self._hardware_config)

    def connect_hardware(self):
        """Create and initialize hardware communication object."""
        try:
            with self._hardware_lock:
                self._hardware = ExampleHardware.ExampleHardware(config=self._hardware_config)
        except: # Hardware connection errors
            self._hardware = None
        
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
                logged_data['comm_error'] = e.msg
        else:
            logged_data = {'comm_status':'connection error'}
        
        return logged_data
        
    def set_random_base_callback(self, msg):
        """Callback to be triggered on Pub/Sub for random base value"""
        newbase = msg.data
        
        if self._hardware:
            try:
                with self._hardware_lock:
                    self._hardware.base = newbase
            except: # Except hardware errors
                pass
            
    def set_random_range_callback(self, msg):
        """Callback to be triggered on Pub/Sub for random base value"""
        newrange = msg.data
        
        if self._hardware:
            try:
                with self._hardware_lock:
                    self._hardware.range = newrange
            except: # Except hardware errors
                pass
        

class ExampleSmaxService:
    # Specify the path for a resource that we open and must close correctly
    # when the service is stopped
    FIFO = '/tmp/myservice_pipe'

    def __init__(self, config=default_config, smax_config=default_smax_config):
        """Service object initialization code"""
        self.logger = self._init_logger()

        # Read the hardware and SMAX configuration
        self.read_config(config, smax_config)

        # The SMAXRedisClient instance
        self.smax_client = None
        
        # The simulated hardware class
        self.hardware = None

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
        
        control_keys = {}
        for k in self._config["smax_config"].keys():
            if k.endswith('control_key'):
                control_keys[k] = self._config["smax_config"][k]
                             
        self.logging_interval = self._config["logging_interval"]
        self.serial_server = self._config["serial_server"]

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
        systemd.daemon.notify(READY)

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
        systemd.daemon.notify(STOPPING)

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
