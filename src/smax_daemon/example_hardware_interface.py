import datetime
import types
import threading

from example_smax_hardware import ExampleHardware

class ExampleHardwareInterface:
    """An example daemon interface for communicating with a piece of hardware."""
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
        self._hardware_error = "disconnected"
        
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
                        # We do this next checl so that we can get values from methods as 
                        # well as attribute values.
                        # This also suggests that arguments could be
                        # defined in the configuration json for self._hardware_data
                        # and passed to the method call. Keyword arguments
                        # would be simplest.
                        self.logger.debug(f"Attribute {data}: {type(reading)}")
                        if type(reading) is types.MethodType:
                            reading = self._hardware.__getattribute__(data)()
                        logged_data[data] = reading
                        self.logger.info(f'Got data for hardware {data}: {reading}')
                logged_data['comm_status'] = "good"
                logged_data['comm_error'] = "None"
            except Exception as e: # Except hardware connection errors
                self._hardware = None
                logged_data = {'comm_status':'connection error'}
                logged_data['comm_error'] = repr(e)
        else:
            logged_data = {'comm_status':"connection error",
                           'comm_error':"Not Connected"}
        
        return logged_data
        
    def set_random_base_callback(self, message):
        """Callback to be triggered on Pub/Sub for random base value"""
        if self.logger:
            date = message.timestamp
            self.logger.info(f'Received callback notification for {message.smaxname} from {message.origin} with data {message.data} at {date}')
        
        newbase = message.data
        
        self.logger.warning(f'{message.origin} set random_base to {newbase}')
        
        if self._hardware:
            try:
                with self._hardware_lock:
                    self._hardware.random_base = newbase
            except Exception as e: # Except hardware errors
                self._hardware_error = repr(e)
            
    def set_random_range_callback(self, message):
        """Callback to be triggered on Pub/Sub for random base value"""
        if self.logger:
            date = message.timestamp
            self.logger.info(f'Received callback notification for {message.smaxname} from {message.origin} with data {message.data} at {date}')
        
        newrange = message.data
        
        self.logger.warning(f'{message.origin} set random_range to {newrange}')
        
        if self._hardware:
            try:
                with self._hardware_lock:
                    self._hardware.random_range = newrange
            except Exception as e: # Except hardware errors
                self._hardware_error = repr(e)