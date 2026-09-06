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
# 3. Configurable 墨蓋 geometry.
# Ratios are relative to one standard body-text cell.  Defaults intentionally
# leave white space around the black block and move it slightly downward.
# ---------------------------------------------------------------------------
geometry_cfg = """#墨蓋版式微调：比例以一个正文标准字位的宽高为基准
my $mogai_box_width_ratio  = (defined $book{'mogai_box_width_ratio'}  and $book{'mogai_box_width_ratio'} ne '')  ? $book{'mogai_box_width_ratio'}  : 0.72;
my $mogai_box_height_ratio = (defined $book{'mogai_box_height_ratio'} and $book{'mogai_box_height_ratio'} ne '') ? $book{'mogai_box_height_ratio'} : 0.84;
my $mogai_box_y_shift      = (defined $book{'mogai_box_y_shift'}      and $book{'mogai_box_y_shift'} ne '')      ? $book{'mogai_box_y_shift'}      : -0.04;
my $mogai_text_y_shift     = (defined $book{'mogai_text_y_shift'}     and $book{'mogai_text_y_shift'} ne '')     ? $book{'mogai_text_y_shift'}     : -0.04;
my $mogai_font_scale       = (defined $book{'mogai_font_scale'}       and $book{'mogai_font_scale'} ne '')       ? $book{'mogai_font_scale'}       : 0.95;
"""
if "my $mogai_box_width_ratio" not in s:
    anchor = "my $fallback_bold_stroke_width = $book{'fallback_bold_stroke_width'} || 1.0;\n"
    if anchor not in s:
        raise SystemExit("mogai geometry config anchor not found")
    s = s.replace(anchor, anchor + "\n" + geometry_cfg, 1)
    changed = True

# ---------------------------------------------------------------------------
# 4. Renderer: black ground + white glyph, consuming exactly one $pcnt.
#    The box is centered horizontally inside the cell, vertically referenced to
#    the actual cell bottom (pos_y includes row_delta_y), then nudged downward.
# ---------------------------------------------------------------------------
old_renderer = """        # 墨蓋：白纸印刷用黑底白字反白效果。
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
"""

new_renderer = """        # 墨蓋：白纸印刷用黑底白字反白效果。黑框不填满整字位，四周留白并略向下移。
        if(ord($char) >= 0xE000 and ord($char) <= 0xF8FF and exists $mogai_map{$char}) {
            $pcnt++ if($pcnt < $page_chars_num);
            if($pcnt <= $page_chars_num) {
                my $mchar = $mogai_map{$char};
                my $fn = get_font($mchar, \\@tfns);
                if(not $fn) { $mchar = '□'; $fn = get_font($mchar, \\@tfns); }
                my $fsize = $fonts{$fn}->[0];
                $fsize *= $font_scale{$fn} if $if_font_metric_adjust;
                my ($bx, $by) = @{$pos_l[$pcnt]};

                # @pos_l 的 y 已包含 row_delta_y，因此先还原标准字位的真正下沿。
                my $box_w = $cw * $mogai_box_width_ratio;
                my $box_h = $rh * $mogai_box_height_ratio;
                my $box_x = $bx + ($cw - $box_w)/2;
                my $cell_bottom = $by - $row_delta_y;
                my $box_y = $cell_bottom + ($rh - $box_h)/2 + $rh*$mogai_box_y_shift;

                my $mgfx = $vpage->gfx();
                $mgfx->fillcolor('black');
                $mgfx->rect($box_x, $box_y, $box_w, $box_h);
                $mgfx->fill();

                my $mfsize = $fsize * $mogai_font_scale;
                my $tx = $box_x + ($box_w-$mfsize)/2;
                my $ty = $by + $rh*$mogai_text_y_shift;
                my $deg = $fonts{$fn}->[2];
                $vpage->text()->textlabel($tx, $ty, $vfonts{$fn}, $mfsize, $mchar,
                    -rotate => $deg, -color => 'white');
                @last = @{$pos_l[$pcnt]};
                $last_char = $mchar;
            }
            goto RCHARS if($pcnt == $page_chars_num);
            next;
        }
"""

if old_renderer in s:
    s = s.replace(old_renderer, new_renderer, 1)
    changed = True
elif "my $box_w = $cw * $mogai_box_width_ratio;" not in s:
    old = """        my $char = shift @chars;\n        #特殊符号标识\n"""
    if old not in s:
        raise SystemExit("renderer anchor not found")
    s = s.replace(old, "        my $char = shift @chars;\n\n" + new_renderer + "\n        #特殊符号标识\n", 1)
    changed = True

if changed:
    p.write_text(s, encoding="utf-8")
    print("patched/repaired vrain.pl 墨蓋 support (inset geometry)")
else:
    print("vrain.pl already contains repaired 墨蓋 support (inset geometry)")
