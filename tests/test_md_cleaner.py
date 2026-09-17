from doc_title_renamer.md_cleaner import clean_markdown


def test_clean_markdown_normalizes_whitespace_and_cjk_spacing() -> None:
    markdown = "　見\t 積　書　 ABC  123　\n  次 の 行  "

    assert clean_markdown(markdown) == "見積書 ABC 123\n次の行"


def test_clean_markdown_preserves_two_blank_lines_but_compresses_three() -> None:
    assert clean_markdown("a\n\n\nb") == "a\n\n\nb"
    assert clean_markdown("a\n\n\n\nb") == "a\n\nb"


def test_clean_markdown_removes_noise_and_invisible_characters() -> None:
    markdown = "件\u200b名\x00\n----------\n……………\n本文"

    assert clean_markdown(markdown) == "件名\n\n本文"


def test_clean_markdown_collapses_consecutive_markitdown_images() -> None:
    markdown = (
        "![表紙](Picture1.jpg)\n\n"
        "![ロゴ](Picture2.jpg)\n"
        "![写真](Picture3.jpg)\n"
        "本文"
    )

    assert clean_markdown(markdown) == "![表紙](Picture1.jpg)\n本文"


def test_clean_markdown_keeps_separated_markitdown_images() -> None:
    markdown = "![表紙](Picture1.jpg)\n説明文\n![図](Picture2.jpg)"

    assert clean_markdown(markdown) == markdown


def test_clean_markdown_applies_nfkc_without_reformatting_markdown() -> None:
    assert clean_markdown("＃ 見出し\n｜Ａ｜Ｂ｜") == "# 見出し\n|A|B|"
