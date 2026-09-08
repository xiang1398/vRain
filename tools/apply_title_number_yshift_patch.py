#!/usr/bin/env python3
from pathlib import Path

path = Path("vrain.pl")
text = path.read_text(encoding="utf-8")

# Remove the accidental chapter-number Y-shift patch and restore the
# original vRain title/postfix rendering behavior.  This intentionally
# leaves pager_y untouched; page/leaf numbers are controlled separately.

# 1) Remove the config variable.
line = "my $title_number_y_shift = (defined $book{'title_number_y_shift'} and $book{'title_number_y_shift'} ne '') ? $book{'title_number_y_shift'} : 80; # 章次数字单独上移，正值向上\n"
text = text.replace(line, "")

# 2) Restore the original title_postfix block.
patched = """    my ($title_number_start, $title_number_len) = (-1, 0); # 章次数字在版心标题数组中的范围\n    if(defined $title_postfix) {\n        my $cid = ($if_text000 == 1) ? $tid-1 : $tid;\n        my $tpost = $title_postfix;\n        my $chapter_num = $zhnums{$cid};\n        if($cid != 0 and not ($if_text999 == 1 and $tid == $#dats)) {\n            my $post_prefix = $title_postfix;\n            $post_prefix =~ s/X.*$//; # X 之前的固定文字（如“卷”）不移动\n            $title_number_start = scalar(split //, $title.$post_prefix);\n            $title_number_len = scalar(split //, $chapter_num);\n        }\n        $tpost =~ s/X/$chapter_num/; #替换为卷章回数字\n        $tpost = '序' if($cid == 0);\t\n        $tpost = '附' if($if_text999 == 1 and $tid == $#dats);\t\t\n        @tpchars = split //, $title.$tpost;\n    } else {\n        @tpchars = split //, $title;\n    }\n"""
original = """    if(defined $title_postfix) {\n        my $cid = ($if_text000 == 1) ? $tid-1 : $tid;\n        my $tpost = $title_postfix;\n        $tpost =~ s/X/$zhnums{$cid}/; #替换为卷章回数字\n        $tpost = '序' if($cid == 0);\t\n        $tpost = '附' if($if_text999 == 1 and $tid == $#dats);\t\t\n        @tpchars = split //, $title.$tpost;\n    } else {\n        @tpchars = split //, $title;\n    }\n"""
if patched in text:
    text = text.replace(patched, original, 1)
elif "my ($title_number_start, $title_number_len)" in text:
    raise SystemExit("unexpected patched title_postfix block; refusing partial removal")

# 3) Remove the Y-shift from both page-center title rendering loops.
shift = "        $fy += $title_number_y_shift if($title_number_start >= 0 and $i >= $title_number_start and $i < $title_number_start+$title_number_len);\n"
text = text.replace(shift, "")

# Validation: none of the accidental patch symbols may remain.
for marker in ("title_number_y_shift", "title_number_start", "title_number_len"):
    if marker in text:
        raise SystemExit(f"failed to remove {marker}")

path.write_text(text, encoding="utf-8")
print("Removed chapter-number Y-shift patch; restored original title/postfix rendering.")
