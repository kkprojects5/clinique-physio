"""The data dictionary describes every column and matches the code."""

from scripts.data_dictionary import OUTPUT, render


def test_data_dictionary_is_up_to_date():
    expected = render()  # also fails if a column has no description

    # Compare without line-ending differences (Git may use CRLF on Windows).
    actual = OUTPUT.read_text(encoding="utf-8").replace("\r\n", "\n")
    assert actual == expected, (
        "docs/data-dictionary.md is out of date: run 'python -m scripts.data_dictionary' in api/"
    )
