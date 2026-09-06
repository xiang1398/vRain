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

# Markup parsing must precede punctuation conversion.
parser_pos = s.index("\\{\\{墨[:：]([^{}])\\}\\}")
punct_pos = s.index("#标点符号替换", parser_pos)
assert parser_pos < punct_pos

# Inset black-box geometry.
assert "my $mogai_box_width_ratio" in s
assert "my $mogai_box_height_ratio" in s
assert "my $mogai_box_y_shift" in s
assert "my $mogai_text_y_shift" in s
assert "my $mogai_font_scale" in s
assert "my $mogai_glyph_fill_ratio" in s
assert "my $cell_bottom = $by - $row_delta_y;" in s
assert "$mgfx->rect($box_x, $box_y, $box_w, $box_h);" in s
assert "$mgfx->rect($bx, $by, $cw, $rh);" not in s

# White 墨蓋 glyph is centered by actual FreeType ink bbox and automatically
# scaled down if necessary, so it cannot invade a neighboring body-text cell.
assert "sub get_glyph_bbox" in s
assert "my ($gxmin, $gymin, $gxmax, $gymax) = get_glyph_bbox($fn, $mchar, $mfsize);" in s
assert "my $max_w = $box_w * $mogai_glyph_fill_ratio;" in s
assert "my $max_h = $box_h * $mogai_glyph_fill_ratio;" in s
assert "$mfsize *= $fit;" in s
assert "$tx = $box_x + ($box_w - $glyph_w)/2 - $gxmin;" in s
assert "$ty = $box_y + ($box_h - $glyph_h)/2 - $gymin + $rh*$mogai_text_y_shift;" in s
assert "? $book{'mogai_text_y_shift'}     : 0.0;" in s

print("OK: 墨蓋 stays one-cell, centered, inset, and glyph-constrained")
