#!/usr/bin/env python3
from pathlib import Path

p = Path("vrain.pl")
s = p.read_text(encoding="utf-8")
changed = False

# ---------------------------------------------------------------------------
# 1. Global map: one private-use token == one normal body-text position.
# ---------------------------------------------------------------------------
if "my %mogai_map;" not in s:
    old = "my @dats = ('');\n"
    new = """my @dats = ('');
# 墨蓋内部标记表。每个标记本身只占一个正文标准字位。
my %mogai_map;
my $mogai_seq = 0;
"""
    if old not in s:
        raise SystemExit("global anchor not found")
    s = s.replace(old, new, 1)
    changed = True

# ---------------------------------------------------------------------------
# 2. Parser.
# IMPORTANT: {{墨:注}} must be recognized BEFORE punctuation conversion.
# book.cfg commonly converts ':' -> '：' and then '：' -> '。'; parsing after
# that stage produced the literal blue '{ 墨。注 }' seen in test PDFs.
# ---------------------------------------------------------------------------
old_parser = """        # 墨蓋：{{墨:X}} -> 单个私用区标记；因此段末补空格计算仍按一个字位处理。
        s/\\{\\{墨:([^{}])\\}\\}/
            my $key = chr(0xE000 + ($mogai_seq++ % 0x1900));
            $mogai_map{$key} = $1;
            $key;
        /gex;

"""
if old_parser in s:
    s = s.replace(old_parser, "", 1)
    changed = True

new_parser = """        # 墨蓋：必须先于标点替换处理，否则 ':' 会被 book.cfg 改写。
        # 同时接受 ASCII 冒号和全角冒号，输入 {{墨:注}} / {{墨：注}} 均可。
        s/\\{\\{墨[:：]([^{}])\\}\\}/
            die "墨蓋标记过多（私用区已用尽）\\n" if $mogai_seq >= 0x1900;
            my $key = chr(0xE000 + $mogai_seq++);
            $mogai_map{$key} = $1;
            $key;
        /gex;

"""
parser_anchor = "        $_ = decode('utf-8', $_);\n"
if new_parser not in s:
    if parser_anchor not in s:
        raise SystemExit("decode/parser anchor not found")
    s = s.replace(parser_anchor, parser_anchor + new_parser, 1)
    changed = True

# ---------------------------------------------------------------------------
# 3. Renderer: black ground + white glyph, consuming exactly one $pcnt.
# ---------------------------------------------------------------------------
if "exists $mogai_map{$char}" not in s:
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
    changed = True

if changed:
    p.write_text(s, encoding="utf-8")
    print("patched/repaired vrain.pl 墨蓋 support")
else:
    print("vrain.pl already contains repaired 墨蓋 support")
