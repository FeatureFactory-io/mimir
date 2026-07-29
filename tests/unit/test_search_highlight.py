"""Unit tests for search term highlighting."""

import pytest

from methodology.utils.search_highlight import highlight_search_term


class TestHighlightSearchTerm:
    def test_wraps_case_insensitive_match(self):
        result = highlight_search_term("React Frontend Development", "react")
        assert '<mark class="mm-search-highlight">React</mark>' in result

    def test_escapes_html_before_wrapping(self):
        result = highlight_search_term("<script>alert(1)</script> React", "React")
        assert "<script>" not in result
        assert "&lt;script&gt;" in result
        assert '<mark class="mm-search-highlight">React</mark>' in result

    def test_empty_query_returns_escaped_text(self):
        result = highlight_search_term("Plain text", "")
        assert result == "Plain text"

    def test_none_text_returns_empty(self):
        result = highlight_search_term(None, "React")
        assert result == ""
