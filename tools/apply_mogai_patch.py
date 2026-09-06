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
# 2. Parser. {{墨:注}} must be recognized BEFORE punctuation conversion.
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
# ---------------------------------------------------------------------------
old_cfg = """#墨蓋版式微调：比例以一个正文标准字位的宽高为基准
my $mogai_box_width_ratio  = (defined $book{'mogai_box_width_ratio'}  and $book{'mogai_box_width_ratio'} ne '')  ? $book{'mogai_box_width_ratio'}  : 0.72;
my $mogai_box_height_ratio = (defined $book{'mogai_box_height_ratio'} and $book{'mogai_box_height_ratio'} ne '') ? $book{'mogai_box_height_ratio'} : 0.84;
my $mogai_box_y_shift      = (defined $book{'mogai_box_y_shift'}      and $book{'mogai_box_y_shift'} ne '')      ? $book{'mogai_box_y_shift'}      : -0.04;
my $mogai_text_y_shift     = (defined $book{'mogai_text_y_shift'}     and $book{'mogai_text_y_shift'} ne '')     ? $book{'mogai_text_y_shift'}     : 0.0;
my $mogai_font_scale       = (defined $book{'mogai_font_scale'}       and $book{'mogai_font_scale'} ne '')       ? $book{'mogai_font_scale'}       : 0.95;
"""
new_cfg = """#墨蓋版式微调：比例以一个正文标准字位的宽高为基准
my $mogai_box_width_ratio  = (defined $book{'mogai_box_width_ratio'}  and $book{'mogai_box_width_ratio'} ne '')  ? $book{'mogai_box_width_ratio'}  : 0.72;
my $mogai_box_height_ratio = (defined $book{'mogai_box_height_ratio'} and $book{'mogai_box_height_ratio'} ne '') ? $book{'mogai_box_height_ratio'} : 0.84;
my $mogai_box_y_shift      = (defined $book{'mogai_box_y_shift'}      and $book{'mogai_box_y_shift'} ne '')      ? $book{'mogai_box_y_shift'}      : -0.04;
my $mogai_text_y_shift     = (defined $book{'mogai_text_y_shift'}     and $book{'mogai_text_y_shift'} ne '')     ? $book{'mogai_text_y_shift'}     : 0.0;
my $mogai_font_scale       = (defined $book{'mogai_font_scale'}       and $book{'mogai_font_scale'} ne '')       ? $book{'mogai_font_scale'}       : 0.95;
# 实际字形最多占黑框多少比例；自动缩小可保证任何墨蓋字都不会越出本字位。
my $mogai_glyph_fill_ratio = (defined $book{'mogai_glyph_fill_ratio'} and $book{'mogai_glyph_fill_ratio'} ne '') ? $book{'mogai_glyph_fill_ratio'} : 0.78;
"""
if old_cfg in s:
    s = s.replace(old_cfg, new_cfg, 1)
    changed = True
elif "my $mogai_box_width_ratio" not in s:
    anchor = "my $fallback_bold_stroke_width = $book{'fallback_bold_stroke_width'} || 1.0;\n"
    if anchor not in s:
        raise SystemExit("mogai geometry config anchor not found")
    s = s.replace(anchor, anchor + "\n" + new_cfg, 1)
    changed = True
elif "my $mogai_glyph_fill_ratio" not in s:
    anchor = "my $mogai_font_scale       = (defined $book{'mogai_font_scale'}       and $book{'mogai_font_scale'} ne '')       ? $book{'mogai_font_scale'}       : 0.95;\n"
    if anchor not in s:
        raise SystemExit("mogai glyph fill config anchor not found")
    addition = "# 实际字形最多占黑框多少比例；自动缩小可保证任何墨蓋字都不会越出本字位。\nmy $mogai_glyph_fill_ratio = (defined $book{'mogai_glyph_fill_ratio'} and $book{'mogai_glyph_fill_ratio'} ne '') ? $book{'mogai_glyph_fill_ratio'} : 0.78;\n"
    s = s.replace(anchor, anchor + addition, 1)
    changed = True

# ---------------------------------------------------------------------------
# 4. Glyph-bbox helper. PDF text coordinates use the glyph baseline, so center
# the actual ink bbox rather than the em square.
# ---------------------------------------------------------------------------
bbox_helper = r'''# get_glyph_bbox — 获取指定字号下字形的实际墨迹包围盒，用于墨蓋反白字精确居中
#   返回 xmin, ymin, xmax, ymax；单位与 PDF 字号在 72dpi 下对应
sub get_glyph_bbox {
    my ($font_file, $char, $size) = @_;

    my $face;
    if ($face_cache{$font_file}) {
        $face = $face_cache{$font_file};
    } else {
        my $freetype = Font::FreeType->new();
        $face = $freetype->face("fonts/$font_file");
        $face_cache{$font_file} = $face;
    }

    $face->set_char_size($size, $size, 72, 72);
    my $glyph = $face->glyph_from_char($char);
    return unless $glyph;
    my ($xmin, $ymin, $xmax, $ymax) = $glyph->outline_bbox();
    return unless defined $xmin and defined $ymin and defined $xmax and defined $ymax;
    return ($xmin, $ymin, $xmax, $ymax);
}

'''
if "sub get_glyph_bbox" not in s:
    anchor = "# get_glyph_height — 获取字体中参考字符的字形高度（已缩放至参考尺寸）\n"
    if anchor not in s:
        raise SystemExit("glyph bbox helper anchor not found")
    s = s.replace(anchor, bbox_helper + anchor, 1)
    changed = True

# ---------------------------------------------------------------------------
# 5. Renderer: one $pcnt, inset black box, white glyph centered by actual bbox.
# ---------------------------------------------------------------------------
old_center = """                my $mfsize = $fsize * $mogai_font_scale;
                my $deg = $fonts{$fn}->[2];
                my ($tx, $ty);
                my ($gxmin, $gymin, $gxmax, $gymax) = get_glyph_bbox($fn, $mchar, $mfsize);
                if(defined $gxmin and $deg == 0) {
                    my $glyph_w = $gxmax - $gxmin;
                    my $glyph_h = $gymax - $gymin;
                    # 文字的实际墨迹边界，而不是 em 方框，正好落在黑框中心。
                    $tx = $box_x + ($box_w - $glyph_w)/2 - $gxmin;
                    $ty = $box_y + ($box_h - $glyph_h)/2 - $gymin + $rh*$mogai_text_y_shift;
                } else {
                    # 极少数旋转字体/无 bbox 情况的保守回退。
                    $tx = $box_x + ($box_w-$mfsize)/2;
                    $ty = $box_y + ($box_h-$mfsize)/2 + $rh*$mogai_text_y_shift;
                }
                $vpage->text()->textlabel($tx, $ty, $vfonts{$fn}, $mfsize, $mchar,
                    -rotate => $deg, -color => 'white');
"""
new_center = """                my $mfsize = $fsize * $mogai_font_scale;
                my $deg = $fonts{$fn}->[2];
                my ($tx, $ty);
                my ($gxmin, $gymin, $gxmax, $gymax) = get_glyph_bbox($fn, $mchar, $mfsize);
                if(defined $gxmin and $deg == 0) {
                    my $glyph_w = $gxmax - $gxmin;
                    my $glyph_h = $gymax - $gymin;

                    # 字形若过大则先按实际墨迹边界等比缩小，使其始终留在自己的墨蓋框内。
                    my $max_w = $box_w * $mogai_glyph_fill_ratio;
                    my $max_h = $box_h * $mogai_glyph_fill_ratio;
                    my $fit = 1.0;
                    $fit = $max_w/$glyph_w if($glyph_w > $max_w and $max_w/$glyph_w < $fit);
                    $fit = $max_h/$glyph_h if($glyph_h > $max_h and $max_h/$glyph_h < $fit);
                    if($fit < 1.0) {
                        $mfsize *= $fit;
                        ($gxmin, $gymin, $gxmax, $gymax) = get_glyph_bbox($fn, $mchar, $mfsize);
                        $glyph_w = $gxmax - $gxmin;
                        $glyph_h = $gymax - $gymin;
                    }

                    # 文字的实际墨迹边界中心 = 黑框中心。
                    $tx = $box_x + ($box_w - $glyph_w)/2 - $gxmin;
                    $ty = $box_y + ($box_h - $glyph_h)/2 - $gymin + $rh*$mogai_text_y_shift;
                } else {
                    # 极少数旋转字体/无 bbox 情况也限制在黑框尺寸内。
                    my $max_em = (($box_w < $box_h) ? $box_w : $box_h) * $mogai_glyph_fill_ratio;
                    $mfsize = $max_em if($mfsize > $max_em);
                    $tx = $box_x + ($box_w-$mfsize)/2;
                    $ty = $box_y + ($box_h-$mfsize)/2 + $rh*$mogai_text_y_shift;
                }
                $vpage->text()->textlabel($tx, $ty, $vfonts{$fn}, $mfsize, $mchar,
                    -rotate => $deg, -color => 'white');
"""
if old_center in s:
    s = s.replace(old_center, new_center, 1)
    changed = True
elif "my $max_w = $box_w * $mogai_glyph_fill_ratio;" not in s:
    raise SystemExit("mogai fit-to-box anchor not found")

if changed:
    p.write_text(s, encoding="utf-8")
    print("patched/repaired vrain.pl 墨蓋 support (centered and constrained)")
else:
    print("vrain.pl already contains centered, constrained 墨蓋 support")
