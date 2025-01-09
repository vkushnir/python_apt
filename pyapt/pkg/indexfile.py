# Interpretation of the indexfile.cc/h files from the C++ APT library

import os.path
from enum import StrEnum


from .contrib.configuration import _config as config
from .contrib.strutil import uri_to_file_name


class OptionKeys(StrEnum):
    """
    List of keys that can be used in the Options.
    """
    SITE = "SITE"  # The site from which the index file was downloaded
    RELEASE = "RELEASE"  # The release of the index file
    COMPONENT = "COMPONENT"  # Component (main, contrib, non-free)
    LANGUAGE = "LANGUAGE"  # Language (en, fr, etc.)
    ARCHITECTURE = "ARCHITECTURE"  # Architecture (amd64, i386, etc.)
    BASE_URI = "BASE_URI"
    REPO_URI = "REPO_URI"
    CREATED_BY = "CREATED_BY"
    TARGET_OF = "TARGET_OF"
    FILENAME = "FILENAME"
    EXISTING_FILENAME = "EXISTING_FILENAME"
    PDIFFS = "PDIFFS"
    COMPRESSIONTYPES = "COMPRESSIONTYPES"
    DEFAULTENABLED = "DEFAULTENABLED"
    SOURCESENTRY = "SOURCESENTRY"
    BY_HASH = "BY_HASH"
    KEEPCOMPRESSEDAS = "KEEPCOMPRESSEDAS"
    FALLBACK_OF = "FALLBACK_OF"
    IDENTIFIER = "IDENTIFIER"
    ALLOW_INSECURE = "ALLOW_INSECURE"
    ALLOW_WEAK = "ALLOW_WEAK"
    ALLOW_DOWNGRADE_TO_INSECURE = "ALLOW_DOWNGRADE_TO_INSECURE"
    INRELEASE_PATH = "INRELEASE_PATH"
    SHADOWED = "SHADOWED"
    
    
class IndexTarget:
    """
    Information about an index file.
    """
        
    def __init__(self, meta_key: str, short_desc: str, long_desc: str, uri: str,
                 is_optional: bool, keep_compressed: bool,
                 options: dict[str, int | str | bool]):
        """
        :type uri: str A URI from which the index file can be downloaded.
        :type long_desc: str A description of the index file.
        :type short_desc: str A shorter description of the index file.
        :type meta_key: str The key by which this index file should be looked up within the meta index file.
        :type is_optional: bool Is it okay if the file isn't found in the meta index.
        :type keep_compressed: bool If the file is downloaded compressed, do not unpack it.
        :type options: Dict[str, str] Options with which this target was created.
        Beware: Not all of these options are intended for public use
        """
        self.meta_key = meta_key
        self.short_desc = short_desc
        self.long_desc = long_desc
        self.uri = uri
        self.is_optional = is_optional
        self.keep_compressed = keep_compressed
        self.options = options
    
    def option(self, key: str) -> str:
        """
        Get the value of an option by its key.
        """
        # TODO: Release mechanics from cpp code for FILENAME, EXISTING_FILENAME
        """
              case FILENAME:
              {
             auto const M = Options.find("FILENAME");
             if (M == Options.end())
                return _config->FindDir("Dir::State::lists") + URItoFileName(URI);
             return M->second;
              }
              case EXISTING_FILENAME:
             std::string const filename = Option(FILENAME);
             std::vector<std::string> const types = VectorizeString(Option(COMPRESSIONTYPES), ' ');
             for (std::vector<std::string>::const_iterator t = types.begin(); t != types.end(); ++t)
             {
                if (t->empty())
                   continue;
                std::string const file = (*t == "uncompressed") ? filename : (filename + "." + *t);
                if (FileExists(file))
                   return file;
             }
        """
        if key == OptionKeys.FILENAME:
            return self.options.get(key, config.FindDir("Dir::State::lists") + uri_to_file_name(self.uri))
        elif key == OptionKeys.EXISTING_FILENAME:
            filename = self.option(OptionKeys.FILENAME)
            types = self.option(OptionKeys.COMPRESSIONTYPES).split(" ")
            for t in types:
                if t == "":
                    continue
                file = filename if t == "uncompressed" else f"{filename}.{t}"
                if os.path.isfile(file):
                    return file
        return self.options.get(key, "")
    
    def option_bool(self, key: OptionKeys) -> bool:
        """
        Get the value of an option by its key as a boolean.
        """
        return self.options.get(key, 'false').lower() in ["true", "yes", "1"]
    
    def format(self, template: str) -> str:
        """
        Format the template string with the options of this target.
        """
        for key, value in self.options.items():
            template = template.replace(f"$({key})", value)
        template = template.replace("$(METAKEY)", self.meta_key)
        template = template.replace("$(SHORTDESC)", self.short_desc)
        template = template.replace("$(DESCRIPTION)", self.long_desc)
        template = template.replace("$(URI)", self.uri)
        template = template.replace("$(FILENAME)", self.option(OptionKeys.FILENAME))
        return template
        
    def __str__(self):
        return self.format("IndexTarget({meta_key}, {short_desc}, {long_desc}, {uri}, {is_optional}, {keep_compressed}, {options})")