#!/usr/bin/env python3
from pathlib import Path
import importlib.util

root = Path(__file__).resolve().parents[1]
mod_path = root / "tools" / "wikisource_lunyu_to_vrain.py"
spec = importlib.util.spec_from_file_location("lunyu_conv", mod_path)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)

paragraphs = [
    "〈疏正義曰：「甲乙。」〉",
    "子曰：「甲乙。」（某曰：「丙丁。」）",
    "「戊己。」（某曰：「庚辛。」）",
    "疏「子曰甲乙」至「戊己」。○正義曰：「壬癸。」",
    "○注「某曰丙丁」。○正義曰：「子丑。」",
    "有子曰：「寅卯。」（某曰：「辰巳。」）",
    "疏「有子曰」至「寅卯」。○正義曰：「午未。」",
]

out = mod.convert_paragraphs(paragraphs)
lines = out.strip().splitlines()

assert lines[0] == "學而第一"
assert lines[1] == "{{墨:疏}}【正義曰甲乙】"
assert lines[2] == (
    "子曰甲乙{{墨:注}}【某曰丙丁】"
    "戊己{{墨:注}}【某曰庚辛】"
    "{{墨:疏}}【子曰甲乙至戊己○正義曰壬癸○注某曰丙丁○正義曰子丑】"
)
assert lines[3] == (
    "有子曰寅卯{{墨:注}}【某曰辰巳】"
    "{{墨:疏}}【有子曰至寅卯○正義曰午未】"
)
assert "，" not in out and "。" not in out and "「" not in out

html = "<div><p>子曰：「甲。」（某曰：「乙。」）</p><p>疏「子曰」至「甲」。○正義曰：「丙。」</p></div>"
ps = mod.extract_paragraphs(html)
assert ps == ["子曰：「甲。」（某曰：「乙。」）", "疏「子曰」至「甲」。○正義曰：「丙。」"]

print("OK: 論語註疏 converter smoke test passed")
