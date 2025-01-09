# String Util - Some useful string functions.

import urllib.parse


# URItoFileName - Convert the uri into a unique file name
def uri_to_file_name(uri: str) -> str:
    """
    This converts a URI into a safe filename. It quotes all unsafe characters
    and converts / to _ and removes the scheme identifier. The resulting
    file name should be unique and never occur again for a different file
    """
    parsed_uri = urllib.parse.urlparse(uri)
    # Nuke 'sensitive' parts of the URI
    sanitized_uri = parsed_uri._replace(username=None, password=None, fragment=None).geturl()
    # "\x00-\x20{}|\\\\^\\[\\]<>\"\x7F-\xFF";
    unsafe_chars = "\\|{}[]<>\"^~_=!@#$%^&*"
    # Quote all unsafe characters
    quoted_uri = urllib.parse.quote(sanitized_uri, safe=f"-_.{unsafe_chars}")
    # Replace / with _
    safe_file_name = quoted_uri.replace('/', '_')

    return safe_file_name