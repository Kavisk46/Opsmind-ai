from core.filenames import sanitize_filename


def test_leaves_a_normal_filename_unchanged():
    assert sanitize_filename("Q3 Report.pdf") == "Q3 Report.pdf"


def test_strips_unix_style_directory_traversal():
    assert sanitize_filename("../../etc/passwd") == "passwd"


def test_strips_windows_style_directory_traversal():
    assert sanitize_filename("..\\..\\evil.pdf") == "evil.pdf"


def test_strips_a_leading_absolute_path():
    assert sanitize_filename("/etc/passwd") == "passwd"


def test_replaces_control_characters():
    # \r\n specifically matters: an unsanitized copy of this could inject
    # extra headers into the download endpoint's Content-Disposition
    # response later (see core/filenames.py's module docstring).
    result = sanitize_filename("evil\r\nSet-Cookie: pwned=1.pdf")
    assert "\r" not in result
    assert "\n" not in result


def test_replaces_null_bytes():
    assert "\x00" not in sanitize_filename("notes\x00.pdf")


def test_replaces_characters_forbidden_on_windows():
    result = sanitize_filename('weird:name*file?.txt')
    for char in ':*?':
        assert char not in result


def test_empty_result_falls_back_to_a_safe_default():
    assert sanitize_filename("///") == "file"


def test_empty_input_falls_back_to_a_safe_default():
    assert sanitize_filename("") == "file"


def test_preserves_the_extension():
    assert sanitize_filename("../weird/../path/report.final.docx") == "report.final.docx"
