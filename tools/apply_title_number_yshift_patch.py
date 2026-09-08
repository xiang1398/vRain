#!/usr/bin/env python3
from pathlib import Path

path = Path("vrain.pl")
text = path.read_text(encoding="utf-8")

# 1) Add a configurable Y shift for chapter-number glyphs only.
needle = "my ($title_font_size, $title_font_color, $title_y, $title_ydis) = ($book{'title_font_size'}, $book{'title_font_color'}, $book{'title_y'}, $book{'title_ydis'});\n"
insert = needle + "my $title_number_y_shift = (defined $book{'title_number_y_shift'} and $book{'title_number_y_shift'} ne '') ? $book{'title_number_y_shift'} : 80; # 章次数字单独上移，正值向上\n"
if "my $title_number_y_shift" not in text:
    if needle not in text:
        raise SystemExit("title config anchor not found")
    text = text.replace(needle, insert, 1)

# 2) Track exactly which characters in title+postfix are the Chinese chapter number.
old = """    if(defined $title_postfix) {\n        my $cid = ($if_text000 == 1) ? $tid-1 : $tid;\n        my $tpost = $title_postfix;\n        $tpost =~ s/X/$zhnums{$cid}/; #替换为卷章回数字\n        $tpost = '序' if($cid == 0);\t\n        $tpost = '附' if($if_text999 == 1 and $tid == $#dats);\t\t\n        @tpchars = split //, $title.$tpost;\n    } else {\n        @tpchars = split //, $title;\n    }\n"""
new = """    my ($title_number_start, $title_number_len) = (-1, 0); # 章次数字在版心标题数组中的范围\n    if(defined $title_postfix) {\n        my $cid = ($if_text000 == 1) ? $tid-1 : $tid;\n        my $tpost = $title_postfix;\n        my $chapter_num = $zhnums{$cid};\n        if($cid != 0 and not ($if_text999 == 1 and $tid == $#dats)) {\n            my $post_prefix = $title_postfix;\n            $post_prefix =~ s/X.*$//; # X 之前的固定文字（如“卷”）不移动\n            $title_number_start = scalar(split //, $title.$post_prefix);\n            $title_number_len = scalar(split //, $chapter_num);\n        }\n        $tpost =~ s/X/$chapter_num/; #替换为卷章回数字\n        $tpost = '序' if($cid == 0);\t\n        $tpost = '附' if($if_text999 == 1 and $tid == $#dats);\t\t\n        @tpchars = split //, $title.$tpost;\n    } else {\n        @tpchars = split //, $title;\n    }\n"""
if "my ($title_number_start, $title_number_len)" not in text:
    if old not in text:
        raise SystemExit("title postfix block anchor not found")
    text = text.replace(old, new, 1)

# 3) Shift only the chapter-number glyphs in BOTH title-rendering loops.
anchor = "        my ($fx, $fy) = ($canvas_width/2-$fs/2, $title_y-$fs*$i*$title_ydis);\n"
replacement = anchor + "        $fy += $title_number_y_shift if($title_number_start >= 0 and $i >= $title_number_start and $i < $title_number_start+$title_number_len);\n"
existing = text.count("$fy += $title_number_y_shift if($title_number_start")
if existing == 0:
    count = text.count(anchor)
    if count != 2:
        raise SystemExit(f"expected 2 title-render anchors, found {count}")
    text = text.replace(anchor, replacement)
elif existing != 2:
    raise SystemExit(f"unexpected existing patched-loop count: {existing}")

path.write_text(text, encoding="utf-8")
print("Patched vrain.pl: chapter-number glyphs only are shifted upward.")
print("Default title_number_y_shift=80; override in book.cfg as needed.")
