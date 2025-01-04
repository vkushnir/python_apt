# Configuration Class
# Implemented from original C++ code in https://salsa.debian.org/apt-team/apt
# It was originally written by Jason Gunthorpe <jgg@debian.org>.
# ######################################################################
#  This class provides a configuration file and command line parser
#  for a tree-oriented configuration environment.
#  Each configuration name is given as a fully scoped string such as
#      Foo::Bar
#  And has associated with it a text string. The Configuration class only
#  provides storage and lookup for this tree, other classes provide
#  configuration file formats (and parsers/emitters if needed).
#
#  Most things can get by quite happily with,
#     get("Foo::Bar")
#
#  A special extension, support for ordered lists is provided by using the
#  special syntax, "block::list::" the trailing :: designates the
#  item as a list. To access the list you must use the tree function on
#  "block::list".
#
#   #####################################################################

import os
from .platformutil import _platform_info as platform
from .singleton import Singleton

class Configuration(Singleton):
    """
    Configuration class
    """
    def __init__(self) -> None:
        self._data = {}
    
    def _set(self, data: dict, tags: list, value: int | str | bool) -> None:
        """
        :param dict: data
        :param tags: list of tags
        :param value: a value to set
        :return:
        :TODO implement mechanics for array for 'foo::bar::'
        """
        if tags[0] not in data:
            data[tags[0]] = {}
        if len(tags) == 1:
            data[tags[0]]['_value'] = value
        else:
            self._set(data[tags[0]], tags[1:], value)
    
    def set(self, full_tag: str, value: int | str | bool) -> None:
        """
        Set a value to tree
        """
        self._set(self._data, full_tag.split('::'), value)
    
    def set_many(self, data: dict[str, int | str | bool]) -> None:
        """
        Set many values to tree
        """
        for key, value in data.items():
            self.set(key, value)
    
    def get(self, full_tag: str, default: None | int | str | bool = None) -> None | int | str | bool:
        """
        Get a value from tree
        :TODO implement mechanics for array for 'foo::bar'
        """
        tags = full_tag.split('::')
        data = self._data
        for tag in tags:
            if tag not in data:
                return default
            data = data[tag]
        return data["_value"] if "_value" in data else default
    
    def find_file(self, name: str, default: str = None) -> str:
        """
        Directories are stored as the base dir in the Parent node and the
        sub directory in sub nodes with the final node being the end filename
        """
        tags = name.split('::')
        data = self._data
        values = []
        for tag in tags:
            if tag not in data:
                values.append(default)
                break
            data = data[tag]
            values.append(data["_value"])
        return os.path.normcase(os.path.normpath(os.path.join(*values)))
    
    def find_dir(self, name: str, default: str = None) -> str:
        """
        This is like findfile except the result is terminated in a /
        """
        return self.find_file(name, default) + os.sep


# Initialize the Configuration class
_config = Configuration()

# General APT things
# if etc directory exists in current directory, set it as default else set root directory
if os.path.isdir(os.path.join(os.path.curdir, 'etc')):
    _config.set("Dir", os.path.curdir)
else:
    _config.set("Dir", "/")
# Set current system parameters
_config.set("APT::ID", platform.id)
_config.set("APT::Platform", platform.os)
_config.set("APT::Distro", platform.distro)
_config.set("APT::Architecture", platform.arch)
_config.set("APT::PackageType", "deb")
_config.set("APT::Component", "main")
# State
_config.set_many({
    "Dir::State": "var/lib/apt/",
    "Dir::State::lists": "lists/",
    "Dir::State::cdroms": "cdroms.list"
})
# Cache
_config.set_many({
    "Dir::Cache": "var/cache/apt/",
    "Dir::Cache::archives": "archives/",
    "Dir::Cache::srcpkgcache": "srcpkgcache.bin",
    "Dir::Cache::pkgcache": "pkgcache.bin"
})
# Configuration
_config.set_many({
    "Dir::Etc": "etc/apt/",
    "Dir::Boot": "boot",
    "Dir::Usr": "usr",
    "Dir::Etc::sourcelist": "sources.list",
    "Dir::Etc::sourceparts": "sources.list.d"
})
# State
_config.set_many({
    "Dir::Log": "var/log/apt/",
    "Dir::Log::Terminal": "term.log",
    "Dir::Log::History": "history.log",
    "Dir::Log::Planner": "eipp.log.xz"
})
#
_config.set_many({
    "Acquire::IndexTargets::deb::Packages::MetaKey": "$(COMPONENT)/binary-$(ARCHITECTURE)/Packages",
    "Acquire::IndexTargets::deb::Packages::flatMetaKey": "Packages",
    "Acquire::IndexTargets::deb::Packages::ShortDescription": "Packages",
    "Acquire::IndexTargets::deb::Packages::Description": "$(RELEASE)/$(COMPONENT) $(ARCHITECTURE) Packages",
    "Acquire::IndexTargets::deb::Packages::flatDescription": "$(RELEASE) Packages",
    "Acquire::IndexTargets::deb::Packages::Optional": False,
    "Acquire::IndexTargets::deb::Translations::MetaKey": "$(COMPONENT)/i18n/Translation-$(LANGUAGE)",
    "Acquire::IndexTargets::deb::Translations::flatMetaKey": "$(LANGUAGE)",
    "Acquire::IndexTargets::deb::Translations::ShortDescription": "Translation-$(LANGUAGE)",
    "Acquire::IndexTargets::deb::Translations::Description": "$(RELEASE)/$(COMPONENT) ANGUAGE)",
    "Acquire::IndexTargets::deb::Translations::flatDescription": "$(RELEASE) Translation-$(LANGUAGE)",
    "Acquire::IndexTargets::deb-src::Sources::MetaKey": "$(COMPONENT)/source/Sources",
    "Acquire::IndexTargets::deb-src::Sources::flatMetaKey": "Sources",
    "Acquire::IndexTargets::deb-src::Sources::ShortDescription": "Sources",
    "Acquire::IndexTargets::deb-src::Sources::Description": "$(RELEASE)/$(COMPONENT) Sources",
    "Acquire::IndexTargets::deb-src::Sources::flatDescription": "$(RELEASE) Sources",
    "Acquire::IndexTargets::deb-src::Sources::Optional": False
})
# Compression types
_config.set_many({
    "Acquire::CompressionTypes::xz": "xz",
    "Acquire::CompressionTypes::bz2": "bzip2",
    "Acquire::CompressionTypes::lzma": "lzma",
    "Acquire::CompressionTypes::gz": "gzip",
    "Acquire::CompressionTypes::lz4": "lz4",
    "Acquire::CompressionTypes::zst": "zstd"
})