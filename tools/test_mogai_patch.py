#!/usr/bin/env python3
"""Static smoke test for tools/apply_mogai_patch.py.
Does not require PDF::Builder or fonts; it patches a temporary copy and checks invariants.
"""
from pathlib import Path
import subprocess
import tempfile
import shutil

root = Path(__file__).resolve().parents[1]
source = root / "vrain.pl"
patcher = root / "tools" / "apply_mogai_patch.py"

with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    shutil.copy2(source, td / "vrain.pl")
    subprocess.run(["python3", str(patcher)], cwd=td, check=True)
    s = (td / "vrain.pl").read_text(encoding="utf-8")

    assert "my %mogai_map;" in s
    assert "my $mogai_seq = 0;" in s
    assert "\\{\\{墨:([^{}])\\}\\}" in s
    assert "exists $mogai_map{$char}" in s
    assert "$mgfx->fillcolor('black');" in s
    assert "-color => 'white'" in s
    assert "$pcnt++ if($pcnt < $page_chars_num);" in s

print("OK: 墨蓋 patch static smoke test passed")
