#!/usr/bin/env python3
from pathlib import Path

p = Path("vrain.pl")
s = p.read_text(encoding="utf-8")

# The feature branch commits the generated vrain.pl.  Subsequent CI runs must
# therefore accept an already-patched file instead of trying to patch it twice.
if (
    "my %mogai_map;" in s
    and "my $mogai_seq = 0;" in s
    and "exists $mogai_map{$char}" in s
    and "$mgfx->fillcolor('black');" in s
):
    print("vrain.pl already contains 墨蓋 support")
    raise SystemExit(0)

old = "my @dats = ('');\n"
new = """my @dats = ('');
# 墨蓋内部标记表。每个标记本身只占一个正文标准字位。
my %mogai_map;
my $mogai_seq = 0;
"""
if old not in s:
    raise SystemExit("global anchor not found")
s = s.replace(old, new, 1)

old = """        s/\\@/ /g; #@代表空格\n\n    \tmy $tmpstr = $_; #保存基础处理后原始文本\n"""
new = """        s/\\@/ /g; #@代表空格

        # 墨蓋：{{墨:X}} -> 单个私用区标记；因此段末补空格计算仍按一个字位处理。
        s/\\{\\{墨:([^{}])\\}\\}/
            my $key = chr(0xE000 + ($mogai_seq++ % 0x1900));
            $mogai_map{$key} = $1;
            $key;
        /gex;

    \tmy $tmpstr = $_; #保存基础处理后原始文本
"""
if old not in s:
    raise SystemExit("parser anchor not found")
s = s.replace(old, new, 1)

old = """        my $char = shift @chars;\n        #特殊符号标识\n"""
new = """        my $char = shift @chars;

        # 墨蓋：白纸印刷用黑底白字反白效果。
        if(ord($char) >= 0xE000 and ord($char) <= 0xF8FF and exists $mogai_map{$char}) {
            $pcnt++ if($pcnt < $page_chars_num);
            if($pcnt <= $page_chars_num) {
                my $mchar = $mogai_map{$char};
                my $fn = get_font($mchar, \\@tfns);
                if(not $fn) { $mchar = '□'; $fn = get_font($mchar, \\@tfns); }
                my $fsize = $fonts{$fn}->[0];
                $fsize *= $font_scale{$fn} if $if_font_metric_adjust;
                my ($bx, $by) = @{$pos_l[$pcnt]};

                my $mgfx = $vpage->gfx();
                $mgfx->fillcolor('black');
                $mgfx->rect($bx, $by, $cw, $rh);
                $mgfx->fill();

                my $tx = $bx + ($cw-$fsize)/2;
                my $ty = $by;
                my $deg = $fonts{$fn}->[2];
                $vpage->text()->textlabel($tx, $ty, $vfonts{$fn}, $fsize, $mchar,
                    -rotate => $deg, -color => 'white');
                @last = @{$pos_l[$pcnt]};
                $last_char = $mchar;
            }
            goto RCHARS if($pcnt == $page_chars_num);
            next;
        }

        #特殊符号标识
"""
if old not in s:
    raise SystemExit("renderer anchor not found")
s = s.replace(old, new, 1)

p.write_text(s, encoding="utf-8")
print("patched vrain.pl with 墨蓋 support")
