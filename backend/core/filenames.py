import re

# Control characters (0x00-0x1F, 0x7F — includes \r and \n, the pair that
# matters most: a raw CRLF in a filename could otherwise inject extra
# headers into the Content-Disposition response on the download endpoint)
# plus path separators and characters Windows itself forbids in a
# filename. Replacing rather than rejecting outright — an upload with an
# odd filename is still a valid file the user should be able to store,
# just under a cleaned-up name.
_UNSAFE_CHARS = re.compile(r'[\x00-\x1f\x7f\\/:*?"<>|]')


def sanitize_filename(filename: str) -> str:
    """Cleans a client-supplied filename before it's ever persisted or
    shown back to a user.

    This is NOT what prevents path traversal on disk — the actual bytes
    are always written under a random UUID-derived storage key (see
    DocumentService.upload_document), never this name directly, so a
    malicious filename can never make the server read or write outside
    its intended directory. This function exists for a narrower reason:
    the ORIGINAL filename IS displayed to the user and IS sent back
    verbatim in the download endpoint's Content-Disposition header, so it
    must never be able to carry a CRLF-injection or control-character
    payload, and stripping directory components means a name like
    "../../etc/passwd" displays as the harmless "passwd" rather than
    something that reads as a path.
    """
    # Normalize to forward slashes first so both "../evil.pdf" and
    # "..\\evil.pdf" (a Windows-style path a client could still send)
    # are treated identically, then take only the final path segment.
    last_segment = filename.replace("\\", "/").rsplit("/", 1)[-1]
    cleaned = _UNSAFE_CHARS.sub("_", last_segment).strip()
    return cleaned or "file"
