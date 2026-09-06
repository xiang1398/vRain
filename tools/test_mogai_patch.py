#!/usr/bin/env python3
"""Static smoke test for the generated 墨蓋 implementation.
The workflow applies tools/apply_mogai_patch.py before this test, so this script
must inspect the already-patched vrain.pl rather than invoke the patcher again.
"""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
s = (root / "vrain.pl").read_text(encoding="utf-8")

assert "my %mogai_map;" in s
assert "my $mogai_seq = 0;" in s
assert "\\{\\{墨:([^{}])\\}\\}" in s
assert "exists $mogai_map{$char}" in s
assert "$mgfx->fillcolor('black');" in s
assert "-color => 'white'" in s
assert "$pcnt++ if($pcnt < $page_chars_num);" in s

print("OK: 墨蓋 patch static smoke test passed")
