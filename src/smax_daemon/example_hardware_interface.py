from collections.abc import MutableMapping
import types
import threading
import smax

from example_smax_hardware import ExampleHardware

leaf_keys = [
    "function",
    "attribute",
    "type"
]
leaf_keys.extend(smax.optional_metadata)



def flatten_logged_data(dictionary, parent_key="", separator=":"):
    """Flatten the logged data dictionary to dictionary keyed by SMA-X table:key strings"""
    items = []
    for key, value in dictionary.items():
        new_key = parent_key + separator + key if parent_key else key
        if isinstance(value, MutableMapping):
            # Detect if we have a leaf node
            if value is None or len(value) == 0 or any(key for key in leaf_keys if key in value.keys()):
                items.append((new_key, value))
            else:
                items.extend(flatten_logged_data(value, new_key, separator=separator).items())
        else:
            items.append((new_key, value))
    return dict(items)


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
            
        self.connect_hardware()
        
    def __getattr__(self, name):
        """Override __getattr__ so that we can pass requests for attributes to the
        wrapped hardware class.
        
        This allows automatic access to all the attributes of the hardware that are not explicitly
        overriden in this interface class.
        
        This implementation is a little wasteful, as a direct call for
        an unimplemented attribute will end up calling self.__getattribute__() twice, and raising
        AttributeError twice. But we don't intend to use it that way."""
        try:
            return self.__getattribute__(name)
        except AttributeError:
            return self._hardware.__getattribute__(name)
            
    def configure(self, config):
        """Configure the daemon and hardware"""
        
        if 'config' in config.keys():
            self._hardware_config = config['config']
            
        if 'logged_data' in config.keys():
            self._hardware_data = flatten_logged_data(config['logged_data'])
            
        if self._hardware and self._hardware_config:
            with self._hardware_lock:
                try:   
                    self._hardware.configure(self._hardware_config)
                except AttributeError:
                    pass

    def connect_hardware(self):
        """Create and initialize hardware communication object."""
        try:
            with self._hardware_lock:
                self._hardware = ExampleHardware(config=self._hardware_config)
                self._hardware_error = "None"
                if self._hardware and self._hardware_config:
                    try:   
                        self._hardware.configure(self._hardware_config)
                    except AttributeError:
                        pass
                
        except Exception as e: # Hardware connection errors
            self._hardware = None
            self._hardware_error = repr(e)
            self.logger.error(f"Failed to connect to hardware with error {e}.")
            
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
                        self.logger.debug(f"attempting to get key {data}")
                        # Check this first, or later tests throw exceptions
                        if self._hardware_data[data] is None:
                            attribute = data.replace(":", ".")
                        elif "attribute" in self._hardware_data[data]:
                            attribute = self._hardware_data[data]["attribute"]
                        elif "function" in self._hardware_data[data]:
                            attribute = self._hardware_data[data]["function"]
                        else:
                            attribute = data.replace(":", ".")
                        self.logger.debug(f"attempting to get data {attribute}")
                        reading = self.__getattr__(attribute.split(".")[0])
                        # If this is a compound key, push down to the leaf attribute
                        if len(attribute.split(".")) > 1:
                            for d in attribute.split(".")[1:]:
                                reading = reading.__getattr__(d)
                        # If this is a method, call it to get the value
                        if type(reading) is types.MethodType:
                            if "args" in self._hardware_data[data].keys():
                                args = self._hardware_data[data]["args"]
                                if type(args) is not list:
                                    args = [args]
                                self.logger.debug(f"calling {reading} with arguments {args}.")
                                reading = reading(*args)
                            else:
                                self.logger.debug(f"calling {reading}")
                                reading = reading()
                        logged_data[data] = reading
                        self.logger.info(f'Got data for hardware {data}: {reading}')
                logged_data['comm_status'] = "good"
                logged_data['comm_error'] = "None"
            except Exception as e: # Except hardware connection errors
                self._hardware = None
                self.logger.debug(f'HardwareInterface.logging_action: connection error {e}')
                logged_data = {'comm_status':'connection error'}
                logged_data['comm_error'] = repr(e)
        else:
            logged_data = {'comm_status':"connection error",
                           'comm_error':"Not Connected"}
        
        return logged_data
    
    @property
    def random_base_minus_one(self):
        """Get the random base and return a value 1 lower"""
        return self._hardware.random_base - 1

    def random_range_plus_one(self):
        """Get the random range and return a value 1 higher"""
        return self._hardware.random_range + 1
        
    def set_random_base_callback(self, message):
        """Callback to be triggered on Pub/Sub for random base value"""
        if self.logger:
            date = message.timestamp
            self.logger.info(f'Received callback notification for {message.smaxname} from {message.origin} with data {message.data} at {date}')
        
        newbase = message.data
        
        if self._hardware:
            try:
                with self._hardware_lock:
                    self._hardware.random_base = newbase
            except Exception as e: # Except hardware errors
                self._hardware_error = repr(e)
                if self.logger:
                    self.logger.error(f'Attempt by {message.origin} to set random_base to {newbase} failed with {self._hardware_error}')
                
        if self.logger:
            self.logger.status(f'{message.origin} set random_range to {newbase}')
            
    def set_random_range_callback(self, message):
        """Callback to be triggered on Pub/Sub for random base value"""
        if self.logger:
            date = message.timestamp
            self.logger.info(f'Received callback notification for {message.smaxname} from {message.origin} with data {message.data} at {date}')
        
        newrange = message.data
        
        if self._hardware:
            try:
                with self._hardware_lock:
                    self._hardware.random_range = newrange
            except Exception as e: # Except hardware errors
                self._hardware_error = repr(e)
                if self.logger:
                    self.logger.error(f'Attempt by {message.origin} to set random_range to {newrange} failed with {self._hardware_error}')
                
        if self.logger:
            self.logger.status(f'{message.origin} set random_range to {newrange}')