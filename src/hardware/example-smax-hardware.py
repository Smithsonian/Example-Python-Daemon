# A simple class to simulate a hardware object that a daemon can interact with
#
# Includes delays so that race conditions can be examined
#
# This code is deliberately not threaded and blocks to simulate
# I/O delays

import random
import time

class ExampleHardware:
    def __init__(self, config=None):
        """Create a simulated hardware object that returns random numbers in a certain range.
        
        Keyword Arguments:
            config (dict) : a dictionary that sets the initial configuration."""
        
        self._random_base = 0.0
        self._random_range = 1.0
        
        # How much to delay changing a value
        self._config_delay = None
        # How much to delay the output of a number
        self._delay = None
        
        if config:
            self.configure(config)
            
    def configure(self, config):
        """Configure the random number generator with a dictionary
        keyed by the private attributes to set."""
        
        for k in config.keys():
            # no type checking or anything complex
            setattr(self, "_"+k, config[k])
        
        time.sleep(self._config_delay)
        
    def random_value(self):
        """Return a random number"""
        time.sleep(self._delay)
        return random.uniform(self._random_base, self._random_base+self._random_range)
    
    @property
    def base(self):
        """Getter for random base"""
        return self._random_base
    
    @base.setter
    def base(self, base):
        """Set the base for the random number"""
        time.sleep(self._config_delay)
        self._random_base = base
    
    @property
    def range(self):
        """Getter for random range"""
        return self._random_range
    
    @range.setter
    def range(self, range):
        """Set the range of the random number"""
        time.sleep(self._config_delay)
        self._random_range = range