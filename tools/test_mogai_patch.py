#!/usr/bin/env python3
"""Static smoke test for the generated 墨蓋 implementation."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
s = (root / "vrain.pl").read_text(encoding="utf-8")

assert "my %mogai_map;" in s
assert "my $mogai_seq = 0;" in s
assert "\\{\\{墨[:：]([^{}])\\}\\}" in s
assert "exists $mogai_map{$char}" in s
assert "$mgfx->fillcolor('black');" in s
assert "-color => 'white'" in s
assert "$pcnt++ if($pcnt < $page_chars_num);" in s

# Critical regression check: markup must be tokenized before book.cfg punctuation
# replacement can turn ':' into '：' and then '。'.
parser_pos = s.index("\\{\\{墨[:：]([^{}])\\}\\}")
punct_pos = s.index("#标点符号替换", parser_pos)
assert parser_pos < punct_pos

# Geometry regression checks: the black block must no longer fill the whole
# standard cell. It is inset, referenced to the true cell bottom, and shifted
# slightly downward. These defaults remain overrideable from book.cfg.
assert "my $mogai_box_width_ratio" in s
assert "my $mogai_box_height_ratio" in s
assert "my $mogai_box_y_shift" in s
assert "my $mogai_text_y_shift" in s
assert "my $mogai_font_scale" in s
assert "my $cell_bottom = $by - $row_delta_y;" in s
assert "$mgfx->rect($box_x, $box_y, $box_w, $box_h);" in s
assert "$mgfx->rect($bx, $by, $cw, $rh);" not in s

print("OK: 墨蓋 parser and inset geometry smoke tests passed")
