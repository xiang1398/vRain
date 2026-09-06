#!/usr/bin/env python3
"""Convert a rendered Wikisource 《論語註疏》 chapter to vRain markup.

The converter is intentionally conservative:
  * 經文 remains large text.
  * Parenthetical 集解 text becomes {{墨:注}}【...】.
  * A 疏 paragraph and its following ○注/○正義 paragraphs are merged into
    one {{墨:疏}}【...】 block.
  * Modern editorial punctuation and quote/book-title marks are removed.
  * ○ section markers inside 疏 are preserved.
  * One Analects chapter is emitted as one physical input line so vRain does
    not force every clause to the top of a new column.

By default the script fetches the rendered HTML through the Wikisource
MediaWiki API using only Python's standard library.  It can also process a
saved HTML file, which is useful for reproducible/offline work.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

DEFAULT_PAGE = "論語註疏/卷01"
DEFAULT_TITLE = "學而第一"
API = "https://zh.wikisource.org/w/api.php"
USER_AGENT = "vRain-mogai-converter/0.1 (personal scholarly typesetting)"

# Deliberately keep ○/〇 because they are structural markers inside 疏.
EDITORIAL_PUNCT = str.maketrans("", "", "，。；：！？、,.!?;:「」『』“”‘’《》〈〉﹁﹂﹃﹄　 \t\r\n")
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}


class ParagraphExtractor(HTMLParser):
    """Collect textual content of <p> elements from MediaWiki rendered HTML."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_p = False
        self.depth = 0
        self.buf: list[str] = []
        self.paragraphs: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag == "p" and not self.in_p:
            self.in_p = True
            self.depth = 1
            self.buf = []
            return
        if not self.in_p:
            return
        if tag == "br":
            self.buf.append("\n")
            return
        if tag not in VOID_TAGS:
            self.depth += 1

    def handle_endtag(self, tag: str) -> None:
        if not self.in_p:
            return
        if tag == "p":
            text = "".join(self.buf).strip()
            if text:
                self.paragraphs.append(text)
            self.in_p = False
            self.depth = 0
            self.buf = []
            return
        if tag not in VOID_TAGS and self.depth > 1:
            self.depth -= 1

    def handle_data(self, data: str) -> None:
        if self.in_p:
            self.buf.append(data)


def fetch_rendered_html(page: str) -> str:
    query = urllib.parse.urlencode(
        {
            "action": "parse",
            "page": page,
            "prop": "text",
            "format": "json",
            "formatversion": "2",
        }
    )
    req = urllib.request.Request(f"{API}?{query}", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.load(resp)
    try:
        return payload["parse"]["text"]
    except KeyError as exc:
        raise RuntimeError(f"Wikisource API response did not contain rendered text: {payload}") from exc


def extract_paragraphs(html: str) -> list[str]:
    parser = ParagraphExtractor()
    parser.feed(html)
    return parser.paragraphs


def clean_text(text: str) -> str:
    """Remove modern editorial punctuation while retaining textual characters."""
    text = text.translate(EDITORIAL_PUNCT)
    # Parentheses should have been structurally consumed in main text.  They
    # can occur editorially in 疏; remove any that remain.
    text = text.replace("（", "").replace("）", "").replace("(", "").replace(")", "")
    return text


def split_parenthetical(text: str) -> list[tuple[bool, str]]:
    """Return (is_note, text) segments, supporting nested full/ASCII parens."""
    result: list[tuple[bool, str]] = []
    buf: list[str] = []
    depth = 0
    opener_for: list[str] = []

    def flush(is_note: bool) -> None:
        nonlocal buf
        if buf:
            result.append((is_note, "".join(buf)))
            buf = []

    pairs = {"（": "）", "(": ")"}
    closers = set(pairs.values())

    for ch in text:
        if ch in pairs:
            if depth == 0:
                flush(False)
            else:
                buf.append(ch)
            opener_for.append(pairs[ch])
            depth += 1
            continue
        if ch in closers and depth:
            expected = opener_for[-1]
            if ch != expected:
                # Preserve malformed punctuation rather than silently losing it.
                buf.append(ch)
                continue
            depth -= 1
            opener_for.pop()
            if depth == 0:
                flush(True)
            else:
                buf.append(ch)
            continue
        buf.append(ch)

    if depth:
        raise ValueError(f"unbalanced parenthesis in paragraph: {text}")
    flush(False)
    return result


def main_paragraph_to_markup(text: str) -> str:
    chunks: list[str] = []
    for is_note, segment in split_parenthetical(text):
        segment = clean_text(segment)
        if not segment:
            continue
        if is_note:
            chunks.append(f"{{{{墨:注}}}}【{segment}】")
        else:
            chunks.append(segment)
    return "".join(chunks)


def is_shu_start(text: str) -> bool:
    t = text.lstrip()
    return t.startswith("疏") or t.startswith("〈疏")


def is_shu_continuation(text: str) -> bool:
    t = text.lstrip()
    return t.startswith("○注") or t.startswith("〇注") or t.startswith("○正義") or t.startswith("〇正義")


def shu_piece(text: str, first: bool) -> str:
    t = text.strip()
    if t.startswith("〈") and t.endswith("〉"):
        t = t[1:-1]
    if first and t.startswith("疏"):
        t = t[1:]
    return clean_text(t)


def trim_to_chapter(paragraphs: list[str]) -> list[str]:
    """Drop navigation/provenance paragraphs preceding the actual chapter."""
    for i, p in enumerate(paragraphs):
        t = p.lstrip()
        if "疏正義曰" in t or t.startswith("子曰") or t.startswith("有子曰"):
            return paragraphs[i:]
    raise ValueError("could not locate the beginning of 《學而》 content")


def convert_paragraphs(paragraphs: list[str], title: str = DEFAULT_TITLE) -> str:
    paragraphs = trim_to_chapter(paragraphs)
    out: list[str] = [title]
    chapter_main: list[str] = []
    shu: list[str] = []

    def flush_chapter() -> None:
        nonlocal chapter_main, shu
        if not chapter_main and not shu:
            return
        body = "".join(chapter_main)
        if shu:
            shu_text = "".join(shu)
            body += f"{{{{墨:疏}}}}【{shu_text}】"
        if body:
            out.append(body)
        chapter_main = []
        shu = []

    for p in paragraphs:
        p = p.strip()
        if not p:
            continue

        if is_shu_start(p):
            # A new 疏 following 經 belongs to that chapter.  A leading 疏
            # before the first 經 (the chapter-level preface) stands alone.
            if shu:
                flush_chapter()
            shu = [shu_piece(p, first=True)]
            continue

        if shu and is_shu_continuation(p):
            shu.append(shu_piece(p, first=False))
            continue

        # Any non-疏 paragraph after a completed 疏 starts the next chapter.
        if shu:
            flush_chapter()

        converted = main_paragraph_to_markup(p)
        if converted:
            chapter_main.append(converted)

    flush_chapter()
    return "\n".join(out) + "\n"


def parse_args(argv: list[str]) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Convert Wikisource 論語註疏 to vRain 墨蓋 markup")
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--input-html", type=Path, help="saved rendered HTML instead of fetching Wikisource")
    src.add_argument("--input-text", type=Path, help="plain text with one source paragraph per line")
    ap.add_argument("--page", default=DEFAULT_PAGE, help=f"Wikisource page title (default: {DEFAULT_PAGE})")
    ap.add_argument("--title", default=DEFAULT_TITLE, help=f"title line in output (default: {DEFAULT_TITLE})")
    ap.add_argument("-o", "--output", type=Path, help="output file; stdout if omitted")
    return ap.parse_args(argv)


def run(argv: list[str]) -> int:
    args = parse_args(argv)
    if args.input_text:
        paragraphs = [line.strip() for line in args.input_text.read_text(encoding="utf-8").splitlines() if line.strip()]
    else:
        if args.input_html:
            html = args.input_html.read_text(encoding="utf-8")
        else:
            html = fetch_rendered_html(args.page)
        paragraphs = extract_paragraphs(html)

    output = convert_paragraphs(paragraphs, title=args.title)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
        print(f"wrote {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(run(sys.argv[1:]))
