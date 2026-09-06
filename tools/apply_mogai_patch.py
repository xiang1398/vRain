#!/usr/bin/env python3
from pathlib import Path

p = Path("vrain.pl")
s = p.read_text(encoding="utf-8")

old = """        s/\\@/ /g; #@代表空格\n\n    \tmy $tmpstr = $_; #保存基础处理后原始文本\n"""
new = """        s/\\@/ /g; #@代表空格\n\n        # 墨蓋：{{墨:X}} 在正文中占一个标准字位。先转换成单字符私用区标记，\n        # 并保存标记与显示字符的对应关系，避免段末补空格计算把标记本身算入长度。\n        state $mogai_seq = 0;\n        state %mogai_map;\n        s/\\{\\{墨:([^{}])\\}\\}/\n            my $key = chr(0xE000 + ($mogai_seq++ % 0x1900));\n            $mogai_map{$key} = $1;\n            $key;\n        /gex;\n\n    \tmy $tmpstr = $_; #保存基础处理后原始文本\n"""
if old not in s:
    raise SystemExit("input parser anchor not found")
s = s.replace(old, new, 1)

old = """        my $char = shift @chars;\n        #特殊符号标识\n"""
new = """        my $char = shift @chars;\n\n        # 墨蓋：黑底白字。私用区标记本身正好占一个正文标准字位。\n        # 白纸印刷用，因此采用传统墨蓋的反白效果：实黑方块 + 白色大字。\n        if(ord($char) >= 0xE000 and ord($char) <= 0xF8FF and exists $mogai_map{$char}) {\n            $pcnt++ if($pcnt < $page_chars_num);\n            if($pcnt <= $page_chars_num) {\n                my $mchar = $mogai_map{$char};\n                my $fn = get_font($mchar, \\@tfns);\n                if(not $fn) { $mchar = '□'; $fn = get_font($mchar, \\@tfns); }\n                my $fsize = $fonts{$fn}->[0];\n                $fsize *= $font_scale{$fn} if $if_font_metric_adjust;\n                my ($bx, $by) = @{$pos_l[$pcnt]};\n\n                my $mgfx = $vpage->gfx();\n                $mgfx->fillcolor('black');\n                $mgfx->rect($bx, $by, $cw, $rh);\n                $mgfx->fill();\n\n                my $tx = $bx + ($cw-$fsize)/2;\n                my $ty = $by;\n                my $deg = $fonts{$fn}->[2];\n                $vpage->text()->textlabel($tx, $ty, $vfonts{$fn}, $fsize, $mchar,\n                    -rotate => $deg, -color => 'white');\n                @last = @{$pos_l[$pcnt]};\n                $last_char = $mchar;\n            }\n            goto RCHARS if($pcnt == $page_chars_num);\n            next;\n        }\n\n        #特殊符号标识\n"""
if old not in s:
    raise SystemExit("render anchor not found")
s = s.replace(old, new, 1)

# state requires feature support on older Perl versions.
old = "use utf8;\n"
new = "use utf8;\nuse feature 'state';\n"
if old not in s:
    raise SystemExit("use utf8 anchor not found")
s = s.replace(old, new, 1)

p.write_text(s, encoding="utf-8")
print("patched vrain.pl with 墨蓋 support")
