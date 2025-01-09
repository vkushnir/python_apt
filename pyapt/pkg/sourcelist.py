# SourceList - Manage a list of sources
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Implementation sourcelist.h, sourcelist.cc from original project https://salsa.debian.org/apt-team/apt
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

import os.path
import logging
from . import Singleton
from . import _config

class SourceList(Singleton):
    def __init__(self):
        self.src_list = []
        self._main = None
        self._parts = None
        
    def reset(self) -> None:
        self.__init__()
        
    def read_main_list(self) -> None:
        """
        SourceList::ReadMainList - Read the main source list from etc
        :param self:
        :return:
        """
        self.reset()
        self._main = _config.find_file("Dir::Etc::sourcelist")
        self._parts = _config.find_dir("Dir::Etc::sourceparts")
       
        if os.path.isfile(self._main):
            self.read_append(self._main)
        elif not os.path.isdir(self._parts):
            logging.warning(f"Unable to read {self._parts}")
        
        if os.path.isdir(self._parts):
            self.read_source_dir(self._parts)
        elif (self._main is not None) & (os.path.isfile(self._main) is None):
            logging.warning(f"Unable to read {self._main}")
        
        for url in _config.get("APT::SourcesList", []):
            self.src_append(url)
            
    def read_append(self, fn: str):
        pass
    
    def read_source_dir(self, dir):
        pass
    
    def src_append(self, url: str) -> None:
        pass
    
    # Type::FixupURI - Normalize the URI and check it..
    @staticmethod
    def fixup_uri(self, uri: str) -> str:
        """
        Normalize the URI and check it.
        """
        # Make sure that the URI is / postfixed
        if not uri.endswith('/'):
            uri += '/'
        return uri.replace('$(ARCH)', _config.get("APT::Architecture"))
    
    def parse_line(self, list, line, cur_line, fn):
        """
        Parse a line from the source list.
        """
        
# Initialize the SourcesList class
_sources = SourceList()