# Utilities to detect system parameters

import platform
import re

from .singleton import Singleton


# Class to detect system parameters
class PlatformInfo(Singleton):
    def __init__(self):
        self._os = platform.system()
        self._arch = platform.machine()
        self._version = platform.version()
        self._release = platform.release()
        if self._os == 'Linux':
            self._system = self._get_debian_system()
            self._id = self._system['ID']
            self._version = self._system['VERSION']
            self._distro = self._system['VERSION_CODENAME']
        elif self._os == 'Darwin':
            self._system = self._get_mac_system()
            self._id = self._system['ProductName']
            self._version = self._system['ProductUserVisibleVersion']
            self._distro = self._get_mac_codename(self._release)
        else:
            self._system = None
            self._id = 'Unknown'
            self._version = 'Unknown'
            self._distro = 'Unknown'
        self._python_version = platform.python_version()
    
    @staticmethod
    def _get_debian_system(self) -> dict:
        os_release = {}
        with open('/etc/os-release', 'r') as f:
            for line in f:
                if line.strip().startswith('#'):
                    continue
                key, value = line.strip().split('=')
                os_release[key] = value
        return os_release
    
    @staticmethod
    def _get_mac_system() -> dict:
        system_version = {}
        with open('/System/Library/CoreServices/SystemVersion.plist', 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('<key>'):
                    key = re.search(r'<key>(.*)</key>', line).group(1)
                elif line.startswith('<string>'):
                    value = re.search(r'<string>(.*)</string>', line).group(1)
                    system_version[key] = value
        return system_version
    
    @staticmethod
    def _get_mac_codename(release: str) -> str:
        releases = {
            '24': 'Sequoia',
            '23': 'Sonoma',
            '22': 'Ventura',
            '21': 'Monterey',
            '20': 'Big Sur',
            '19': 'Catalina',
            '18': 'Mojave',
            '17': 'High Sierra',
            '16': 'Sierra',
            '15': 'El Capitan',
            '14': 'Yosemite',
            '13': 'Mavericks',
            '12': 'Mountain Lion',
            '11': 'Lion',
            '10': 'Snow Leopard',
            '9': 'Leopard',
            '8': 'Tiger',
            '7': 'Panther',
            '6': 'Jaguar'
        }
        darwin_version = release.split('.')[0]
        return releases.get(darwin_version, 'Unknown')
    
    @property
    def os(self) -> str:
        return self._os
    
    @property
    def arch(self) -> str:
        return self._arch
    
    @property
    def version(self) -> str:
        return self._version
    
    @property
    def release(self) -> str:
        return self._release
    
    @property
    def id(self) -> str:
        return self._id
    
    @property
    def distro(self) -> str:
        return self._distro
    
    @property
    def system(self) -> dict:
        return self._system
    
    @property
    def python_version(self) -> str:
        return self._python_version
    
    def is_windows(self) -> bool:
        return self._os == 'Windows'
    
    def is_linux(self) -> bool:
        return self._os == 'Linux'
    
    def is_mac(self) -> bool:
        return self._os == 'Darwin'
    
    def is_debian(self) -> bool:
        return self._distro == 'debian'
    
    def is_ubuntu(self) -> bool:
        return self._distro == 'ubuntu'


_platform_info = PlatformInfo()
