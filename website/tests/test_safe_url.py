import pytest 
from website.utils import rebuild_safe_url


@pytest.mark.parametrize("input_url,expected", [
    # Test case with credentials and encoded control characters in the path.
    (
        "https://user:pass@example.com/%0a:%0dsome-path?query=test#ekdes",
        "https://example.com/some-path"
    ),
    # Test case with multiple slashes in the path.
    (
        "https://example.com//multiple///slashes",
        "https://example.com/multiple/slashes"
    ),
    # Test case with no modifications needed.
    (
        "https://example.com/normal/path",
        "https://example.com/normal/path"
    ),
    # Test with CRLF characters.
    (
        "https://example.com/%0d%0a",
        "https://example.com/"
    ),
])
def test_rebuild_safe_url(input_url, expected):
    result = rebuild_safe_url(input_url)
    assert result == expected
