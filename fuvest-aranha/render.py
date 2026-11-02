#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Animação "A aranha e a teia" (FUVEST – Questão 59)

Contagem das combinações de 2 e 4 bolinhas pretas usando só ideias do Fundamental II:
  * 2 patas -> lados + diagonais do octógono (d = n(n-3)/2) - diâmetros = 8 + 20 - 4 = 24
  * 4 patas -> 8 formatos que fazem a aranha andar, cada um girado nas 8 posições = 64
  * Total: 24 + 64 = 88

Uso:
  python3 render.py                       # renderiza o vídeo completo (aranha_fuvest_q59.mp4)
  python3 render.py --timeline            # mostra o tempo de início de cada cena
  python3 render.py --sheet 10 20 30 40 --out prev.png   # folha de conferência (2x2) com quadros
Requer: pycairo, ffmpeg (com libx264) e a fonte Inter instalada.
"""
import argparse
import math
import os
import subprocess
import sys
import tempfile

import cairo

W, H, FPS = 1920, 1080, 30
TAU = 2 * math.pi
HERE = os.path.dirname(os.path.abspath(__file__))


# ----------------------------------------------------------------------------
# Cores
# ----------------------------------------------------------------------------
def hexc(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


BG = hexc('#FBFAF6')
INK = hexc('#1E2230')
MUTED = hexc('#737A8C')
OCT = hexc('#A8A398')
WEBC = hexc('#CFCABE')
BODY = hexc('#9C9C9C')
WHITE = hexc('#FFFFFF')
BLUE = hexc('#2F6FDE')
GREEN = hexc('#12A27A')
GREEN_D = hexc('#0A5E46')
RED = hexc('#E03131')
ARROWC = hexc('#E8590C')
AMBER = hexc('#F59F00')
PURPLE = hexc('#7048E8')


def mix(c1, c2, f):
    f = clamp(f)
    return tuple(a + (b - a) * f for a, b in zip(c1, c2))


def rgba(ctx, c, a=1.0):
    ctx.set_source_rgba(c[0], c[1], c[2], clamp(a))


# ----------------------------------------------------------------------------
# Tempo / suavização
# ----------------------------------------------------------------------------
def clamp(x, lo=0.0, hi=1.0):
    return lo if x < lo else hi if x > hi else x


def smooth(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def P(t, a, d=0.5):
    """Progresso suavizado (0..1) de algo que começa em a e dura d."""
    if d <= 0:
        return 1.0 if t >= a else 0.0
    return smooth((t - a) / d)


def win(t, a, b, fi=0.4, fo=0.4):
    """Visível a partir de a; some a partir de b (b=None: fica até o fim)."""
    v = P(t, a, fi)
    if b is not None:
        v = min(v, 1 - P(t, b, fo))
    return v


def pop(t, a, d=0.35):
    """Escala com leve 'salto' para elementos que surgem."""
    x = clamp((t - a) / d)
    if x <= 0:
        return 0.0
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


def bump(t, a, d=0.4):
    x = (t - a) / d
    return math.sin(math.pi * x) if 0 < x < 1 else 0.0


# ----------------------------------------------------------------------------
# Texto
# ----------------------------------------------------------------------------
FACES = {
    'regular': cairo.ToyFontFace('Inter', cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL),
    'semibold': cairo.ToyFontFace('Inter SemiBold', cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL),
    'bold': cairo.ToyFontFace('Inter', cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD),
}


def setfont(ctx, size, weight):
    ctx.set_font_face(FACES[weight])
    ctx.set_font_size(size)


def tw(ctx, s, size, weight='regular', spacing=0):
    setfont(ctx, size, weight)
    return ctx.text_extents(s).x_advance + spacing * max(0, len(s) - 1)


def text(ctx, s, x, y, size=34, color=INK, a=1.0, weight='regular', align='left', spacing=0, scale=1.0):
    """Escreve s com o 'meio' das maiúsculas na altura y."""
    w = tw(ctx, s, size, weight, spacing)
    if a <= 0.002 or not s or scale <= 0:
        return w
    x0 = x - (0 if align == 'left' else w / 2 if align == 'center' else w)
    if scale != 1.0:
        ctx.save()
        ax = x0 + (0 if align == 'left' else w / 2 if align == 'center' else w)
        ctx.translate(ax, y)
        ctx.scale(scale, scale)
        ctx.translate(-ax, -y)
    setfont(ctx, size, weight)
    rgba(ctx, color, a)
    by = y + size * 0.36
    if spacing == 0:
        ctx.move_to(x0, by)
        ctx.show_text(s)
    else:
        cx = x0
        for ch in s:
            ctx.move_to(cx, by)
            ctx.show_text(ch)
            cx += ctx.text_extents(ch).x_advance + spacing
    ctx.new_path()
    if scale != 1.0:
        ctx.restore()
    return w


def runs_w(ctx, items, size):
    w = 0
    for it in items:
        if it[0] == 'frac':
            _, num, den, col, wt = it
            fs = size * 0.8
            w += max(tw(ctx, num, fs, wt), tw(ctx, den, fs, wt)) + size * 0.34
        else:
            s, col, wt = it
            w += tw(ctx, s, size, wt)
    return w


def runs(ctx, items, x, y, size, a=1.0, align='left', scale=1.0):
    """Texto com trechos de cores/pesos diferentes. Item: (txt, cor, peso) ou ('frac', num, den, cor, peso)."""
    w = runs_w(ctx, items, size)
    if a <= 0.002 or scale <= 0:
        return w
    x0 = x - (0 if align == 'left' else w / 2 if align == 'center' else w)
    if scale != 1.0:
        ctx.save()
        ax = x0 + w / 2
        ctx.translate(ax, y)
        ctx.scale(scale, scale)
        ctx.translate(-ax, -y)
    cx = x0
    for it in items:
        if it[0] == 'frac':
            _, num, den, col, wt = it
            fs = size * 0.8
            fw = max(tw(ctx, num, fs, wt), tw(ctx, den, fs, wt))
            mid = cx + size * 0.17 + fw / 2
            bar_y = y + 0.08 * size
            text(ctx, num, mid, bar_y - 0.13 * size - 0.37 * fs, fs, col, a, wt, 'center')
            text(ctx, den, mid, bar_y + 0.13 * size + 0.37 * fs, fs, col, a, wt, 'center')
            rgba(ctx, col, a)
            ctx.set_line_width(max(2.5, size * 0.055))
            ctx.set_line_cap(cairo.LINE_CAP_BUTT)
            ctx.move_to(cx + size * 0.1, bar_y)
            ctx.line_to(cx + size * 0.24 + fw, bar_y)
            ctx.stroke()
            cx += fw + size * 0.34
        else:
            s, col, wt = it
            cx += text(ctx, s, cx, y, size, col, a, wt)
    if scale != 1.0:
        ctx.restore()
    return w


# ----------------------------------------------------------------------------
# Formas
# ----------------------------------------------------------------------------
def circle(ctx, x, y, r):
    ctx.new_sub_path()
    ctx.arc(x, y, max(0.1, r), 0, TAU)


def rrect(ctx, x, y, w, h, r):
    r = min(r, w / 2, h / 2)
    ctx.new_sub_path()
    ctx.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    ctx.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    ctx.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    ctx.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
    ctx.close_path()


def box(ctx, x, y, w, h, color, a=1.0, fill_a=0.08, lw=3, r=18):
    if a <= 0:
        return
    rrect(ctx, x, y, w, h, r)
    rgba(ctx, color, a * fill_a)
    ctx.fill_preserve()
    rgba(ctx, color, a)
    ctx.set_line_width(lw)
    ctx.stroke()


def chip(ctx, x, y, label, color, a=1.0, size=24):
    w = tw(ctx, label, size, 'bold', 2) + 30
    if a > 0:
        rrect(ctx, x, y - size * 0.85, w, size * 1.7, size * 0.5)
        rgba(ctx, color, a)
        ctx.fill()
        text(ctx, label, x + 15, y, size, WHITE, a, 'bold', spacing=2)
    return w


def xmark(ctx, x, y, s, color=RED, a=1.0, lw=None):
    if a <= 0:
        return
    rgba(ctx, color, a)
    ctx.set_line_width(lw or max(2, s * 0.28))
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.move_to(x - s * 0.5, y - s * 0.5)
    ctx.line_to(x + s * 0.5, y + s * 0.5)
    ctx.move_to(x + s * 0.5, y - s * 0.5)
    ctx.line_to(x - s * 0.5, y + s * 0.5)
    ctx.stroke()


def nomove(ctx, x, y, s, a=1.0):
    """Marca de 'a aranha não se move'."""
    if a <= 0:
        return
    circle(ctx, x, y, s * 1.3)
    rgba(ctx, WHITE, 0.85 * a)
    ctx.fill_preserve()
    rgba(ctx, RED, 0.16 * a)
    ctx.fill_preserve()
    rgba(ctx, RED, a)
    ctx.set_line_width(max(1.5, s * 0.12))
    ctx.stroke()
    xmark(ctx, x, y, s * 1.1, RED, a, lw=max(2, s * 0.26))


def arrow(ctx, x0, y0, ang, length, color=ARROWC, width=10, prog=1.0, a=1.0):
    L = length * prog
    if L < 1 or a <= 0:
        return
    head = width * 2.5
    ux, uy = math.cos(ang), math.sin(ang)
    tipx, tipy = x0 + ux * L, y0 + uy * L
    hl = min(head, L)
    bx, by = tipx - ux * hl, tipy - uy * hl
    rgba(ctx, color, a)
    ctx.set_line_width(width)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.move_to(x0, y0)
    ctx.line_to(bx + ux, by + uy)
    ctx.stroke()
    px, py = -uy, ux
    hw = hl * 0.62
    ctx.move_to(tipx, tipy)
    ctx.line_to(bx + px * hw, by + py * hw)
    ctx.line_to(bx - px * hw, by - py * hw)
    ctx.close_path()
    ctx.fill()


# ----------------------------------------------------------------------------
# Geometria do octógono / aranha
# ----------------------------------------------------------------------------
CX, CY, R = 520, 575, 315
VR = 15  # raio da bolinha na ponta da pata
PX = 1070  # margem esquerda do painel da direita


def ang_of(k):
    return -math.pi / 2 + k * math.pi / 4


def at(ang, r, cx=CX, cy=CY):
    return cx + r * math.cos(ang), cy + r * math.sin(ang)


def vpos(k, r=R, cx=CX, cy=CY):
    return at(ang_of(k), r, cx, cy)


def resultant(ks):
    x = sum(math.cos(ang_of(k)) for k in ks)
    y = sum(math.sin(ang_of(k)) for k in ks)
    return math.atan2(y, x), math.hypot(x, y)


def moves(ks):
    return resultant(ks)[1] > 1e-6


def rotated(ks, j):
    return tuple(sorted((k + j) % 8 for k in ks))


def period(ks):
    s = set(ks)
    for j in range(1, 9):
        if set(rotated(ks, j)) == s:
            return j
    return 8


def litmarker(ctx, x, y, lv, glow, a=1.0, r=VR):
    if lv <= 0 or a <= 0:
        return
    k = r / VR
    circle(ctx, x, y, r + 16 * lv * k)
    rgba(ctx, glow, 0.22 * lv * a)
    ctx.fill()
    circle(ctx, x, y, r + 4 * k)
    rgba(ctx, glow, lv * a)
    ctx.fill()
    circle(ctx, x, y, r - 1)
    rgba(ctx, INK, lv * a)
    ctx.fill()


def vdot(ctx, x, y, lit=0.0, glow=AMBER, a=1.0, r=VR):
    if a <= 0:
        return
    circle(ctx, x, y, r)
    rgba(ctx, WHITE, a)
    ctx.fill_preserve()
    rgba(ctx, INK, a)
    ctx.set_line_width(3)
    ctx.stroke()
    litmarker(ctx, x, y, lit, glow, a, r)


def web(ctx, a, cx=CX, cy=CY, R=R):
    if a <= 0:
        return
    rgba(ctx, WEBC, a)
    ctx.set_line_width(1.6)
    n = 16
    rmax = R * 1.2
    for i in range(n):
        ang = -math.pi / 2 + i * TAU / n
        ctx.move_to(*at(ang, R * 0.28, cx, cy))
        ctx.line_to(*at(ang, rmax, cx, cy))
    ctx.stroke()
    for rr in (0.42, 0.56, 0.70, 0.84, 0.98, 1.12):
        r = R * rr
        for i in range(n):
            a0 = -math.pi / 2 + i * TAU / n
            a1 = a0 + TAU / n
            p0 = at(a0, r, cx, cy)
            p1 = at(a1, r, cx, cy)
            q = at((a0 + a1) / 2, r * 0.9, cx, cy)
            c1 = (p0[0] + 2 / 3 * (q[0] - p0[0]), p0[1] + 2 / 3 * (q[1] - p0[1]))
            c2 = (p1[0] + 2 / 3 * (q[0] - p1[0]), p1[1] + 2 / 3 * (q[1] - p1[1]))
            ctx.move_to(*p0)
            ctx.curve_to(c1[0], c1[1], c2[0], c2[1], p1[0], p1[1])
        ctx.stroke()


def spider(ctx, cx=CX, cy=CY, R=R, body_a=1.0, legs_a=1.0, tips_a=1.0, lit=None, glow=AMBER, tip_r=VR):
    lit = lit or {}
    s = R / 315.0
    if legs_a > 0:
        for k in range(8):
            ang = ang_of(k)
            ux, uy = math.cos(ang), math.sin(ang)
            knee = R * 0.60
            ctx.set_line_cap(cairo.LINE_CAP_BUTT)
            rgba(ctx, INK, legs_a)
            ctx.set_line_width(12 * s)
            ctx.move_to(*at(ang, R * 0.28, cx, cy))
            ctx.line_to(*at(ang, knee, cx, cy))
            ctx.stroke()
            p0 = at(ang, knee, cx, cy)
            p1 = at(ang, R - tip_r, cx, cy)
            ctx.set_line_width(12 * s)
            ctx.move_to(*p0)
            ctx.line_to(*p1)
            ctx.stroke()
            rgba(ctx, WHITE, legs_a)
            ctx.set_line_width(6 * s)
            ctx.move_to(p0[0] + ux * 3, p0[1] + uy * 3)
            ctx.line_to(p1[0] - ux * 1, p1[1] - uy * 1)
            ctx.stroke()
            px, py = -uy, ux
            rgba(ctx, INK, legs_a)
            ctx.set_line_width(5 * s)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.move_to(p0[0] + px * 15 * s, p0[1] + py * 15 * s)
            ctx.line_to(p0[0] - px * 15 * s, p0[1] - py * 15 * s)
            ctx.stroke()
    if body_a > 0:
        circle(ctx, cx, cy, R * 0.30)
        rgba(ctx, BODY, body_a)
        ctx.fill_preserve()
        rgba(ctx, INK, body_a)
        ctx.set_line_width(4 * s)
        ctx.stroke()
    if tips_a > 0:
        for k in range(8):
            vdot(ctx, *vpos(k, R, cx, cy), lit.get(k, 0.0), glow, tips_a, tip_r)


def octagon(ctx, prog=1.0, a=1.0, color=OCT, width=3.5):
    if a <= 0 or prog <= 0:
        return
    total = 8 * clamp(prog)
    rgba(ctx, color, a)
    ctx.set_line_width(width)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.move_to(*vpos(0))
    full = int(total)
    for i in range(1, full + 1):
        ctx.line_to(*vpos(i % 8))
    frac = total - full
    if frac > 0 and full < 8:
        p0 = vpos(full)
        p1 = vpos((full + 1) % 8)
        ctx.line_to(p0[0] + (p1[0] - p0[0]) * frac, p0[1] + (p1[1] - p0[1]) * frac)
    ctx.stroke()


def numbers(ctx, a=1.0, hl=None):
    if a <= 0:
        return
    for k in range(8):
        x, y = vpos(k, R + 50)
        on = hl is not None and k in hl
        text(ctx, str(k + 1), x, y, 32 if on else 30, INK if on else MUTED, a, 'bold' if on else 'semibold', 'center')


def segment(ctx, i, j, color, prog=1.0, width=6, a=1.0, dash=None):
    if prog <= 0 or a <= 0:
        return
    x0, y0 = vpos(i)
    x1, y1 = vpos(j)
    rgba(ctx, color, a)
    ctx.set_line_width(width)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    if dash:
        ctx.set_dash(dash)
    ctx.move_to(x0, y0)
    ctx.line_to(x0 + (x1 - x0) * prog, y0 + (y1 - y0) * prog)
    ctx.stroke()
    if dash:
        ctx.set_dash([])


def center_body(ctx, a=1.0, r=24):
    if a <= 0:
        return
    circle(ctx, CX, CY, r)
    rgba(ctx, BODY, 0.6 * a)
    ctx.fill_preserve()
    rgba(ctx, INK, 0.55 * a)
    ctx.set_line_width(3)
    ctx.stroke()


def oct_view(ctx, base_a=1.0, oct_prog=1.0, segs=(), lit=None, movers=(), arrow_spec=None,
             nomove_a=0.0, num_a=1.0, num_hl=None):
    """Desenha o octógono com segmentos, patas acesas, seta ou 'não se move'."""
    if base_a <= 0:
        return
    octagon(ctx, oct_prog, base_a)
    for s in segs:
        i, j, col, prog, width, a = s[:6]
        dash = s[6] if len(s) > 6 else None
        segment(ctx, i, j, col, prog, width, a * base_a, dash)
    center_body(ctx, base_a)
    if arrow_spec:
        ang, prog, a = arrow_spec
        arrow(ctx, *at(ang, 30), ang, R * 0.5, ARROWC, 11, prog, a * base_a)
    if nomove_a > 0:
        nomove(ctx, CX, CY, 30, nomove_a * base_a)
    lit = lit or {}
    for k in range(8):
        lv, gc = lit.get(k, (0.0, AMBER))
        vdot(ctx, *vpos(k), lv, gc, base_a)
    for ang, lv, gc in movers:
        litmarker(ctx, *at(ang, R), lv, gc, base_a)
    numbers(ctx, num_a * base_a, num_hl)


def mini(ctx, x, y, r, lit, segc=None, a=1.0, s=1.0, ring=None):
    """Miniatura: octógono com as patas acesas e o resultado (seta ou X)."""
    if a <= 0 or s <= 0:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    pts = [at(ang_of(k), r, 0, 0) for k in range(8)]
    if ring:
        rc, ra = ring
        if ra > 0:
            circle(ctx, 0, 0, r * 1.32)
            rgba(ctx, rc, 0.15 * ra * a)
            ctx.fill_preserve()
            rgba(ctx, rc, ra * a)
            ctx.set_line_width(4)
            ctx.stroke()
    rgba(ctx, OCT, a)
    ctx.set_line_width(max(1.5, r * 0.045))
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.move_to(*pts[0])
    for p in pts[1:]:
        ctx.line_to(*p)
    ctx.close_path()
    ctx.stroke()
    lit = tuple(lit)
    if segc is not None and len(lit) == 2:
        rgba(ctx, segc, a)
        ctx.set_line_width(max(2.5, r * 0.085))
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.move_to(*pts[lit[0]])
        ctx.line_to(*pts[lit[1]])
        ctx.stroke()
    if moves(lit):
        ang = resultant(lit)[0]
        arrow(ctx, 0, 0, ang, r * 0.64, ARROWC, max(2.5, r * 0.09), 1, a)
    else:
        nomove(ctx, 0, 0, r * 0.2, a)
    dr = r * 0.15
    for k in range(8):
        circle(ctx, pts[k][0], pts[k][1], dr)
        if k in lit:
            rgba(ctx, INK, a)
            ctx.fill()
        else:
            rgba(ctx, WHITE, a)
            ctx.fill_preserve()
            rgba(ctx, INK, 0.75 * a)
            ctx.set_line_width(max(1.2, r * 0.04))
            ctx.stroke()
    ctx.restore()


STRIP_R, STRIP_GAP, STRIP_Y = 19, 56, 288


def strip(ctx, x, y, lv=None, a=1.0, r=STRIP_R, gap=STRIP_GAP, nums=True, show=None, glow=AMBER):
    """'Fita' com as 8 patas lidas a partir da 1 (sentido horário)."""
    if a <= 0:
        return
    for i in range(8):
        sh = 1.0 if show is None else show[i]
        if sh <= 0:
            continue
        cx = x + i * gap
        ctx.save()
        ctx.translate(cx, y)
        ctx.scale(sh, sh)
        vdot(ctx, 0, 0, (lv[i] if lv else 0.0), glow, a, r)
        ctx.restore()
        if nums:
            text(ctx, str(i + 1), cx, y + r + 20, 18, MUTED, a * min(1, sh), 'semibold', 'center')


def header(ctx, s, color, a):
    if a <= 0:
        return
    rrect(ctx, PX, 62, 8, 32, 4)
    rgba(ctx, color, a)
    ctx.fill()
    text(ctx, s, PX + 24, 78, 24, color, a, 'bold', spacing=2.5)


# ----------------------------------------------------------------------------
# Cenas
# ----------------------------------------------------------------------------
SCENES = []


def add_scene(name, dur, fn, notes=''):
    SCENES.append(dict(name=name, dur=dur, fn=fn, notes=notes))


# --- Abertura ----------------------------------------------------------------
def s_title(ctx, t, d):
    fo = 1 - P(t, d - 0.6, 0.6)
    a0 = P(t, 0.1, 0.8) * fo
    web(ctx, 0.9 * a0, 960, 330, 175)
    spider(ctx, 960, 330, 175, a0, a0, a0, tip_r=10)
    text(ctx, 'A aranha e a teia', 960, 640, 92, INK, P(t, 0.5, 0.7) * fo, 'bold', 'center')
    text(ctx, 'FUVEST · QUESTÃO 59', 960, 740, 30, ARROWC, P(t, 0.9, 0.7) * fo, 'bold', 'center', spacing=4)
    text(ctx, 'Contando as combinações só com ideias do Fundamental II', 960, 810, 34, MUTED,
         P(t, 1.3, 0.7) * fo, 'regular', 'center')


add_scene('Abertura', 6.5, s_title)

# --- Regras --------------------------------------------------------------------
EX = [
    (1.6, (0, 1), '2 bolinhas', 'anda na direção média'),
    (6.6, (0, 4), '2 bolinhas opostas', 'NÃO se move'),
    (11.6, (6, 7, 0, 1), '4 bolinhas', 'anda na direção média'),
    (16.6, (0, 2, 4, 6), '2 pares de opostas', 'NÃO se move'),
]


def s_rules(ctx, t, d):
    fin = P(t, 0, 0.9)
    pan = 1 - P(t, d - 0.6, 0.6)
    web(ctx, fin)
    lit = {}
    for (t0, ks, _, _) in EX:
        lv = win(t, t0, t0 + 4.4, 0.45, 0.45)
        for k in ks:
            lit[k] = max(lit.get(k, 0.0), lv)
    spider(ctx, body_a=fin, legs_a=fin, tips_a=fin, lit=lit)
    for (t0, ks, _, _) in EX:
        lv = win(t, t0 + 0.6, t0 + 4.4, 0.5, 0.45)
        if lv <= 0:
            continue
        if moves(ks):
            ang = resultant(ks)[0]
            arrow(ctx, *at(ang, R * 0.33), ang, R * 0.5, ARROWC, 12, P(t, t0 + 0.6, 0.6), lv)
        else:
            nomove(ctx, CX, CY, 36, lv)
    header(ctx, 'AS REGRAS DA QUESTÃO', INK, P(t, 0.4) * pan)
    for i, (t0, ks, l1, l2) in enumerate(EX):
        y = 200 + i * 135
        a = P(t, t0 + 0.3, 0.5) * pan
        mini(ctx, PX + 56, y, 48, ks, a=a, s=pop(t, t0 + 0.3))
        text(ctx, l1, PX + 140, y - 20, 34, INK, a, 'bold')
        text(ctx, '→ ' + l2, PX + 140, y + 24, 30, MUTED if moves(ks) else RED, a,
             'regular' if moves(ks) else 'semibold')
    qa = P(t, 21.4, 0.6) * pan
    box(ctx, PX - 10, 760, 810, 200, ARROWC, qa, fill_a=0.07)
    text(ctx, 'PERGUNTA', PX + 22, 800, 22, ARROWC, qa, 'bold', spacing=3)
    text(ctx, 'Com 2 ou com 4 bolinhas pretas, quantas', PX + 22, 860, 33, INK, qa, 'semibold')
    text(ctx, 'combinações fazem a aranha se mover?', PX + 22, 910, 33, INK, qa, 'semibold')


add_scene('Relembrando as regras', 25, s_rules)


# --- Patas viram vértices -------------------------------------------------------
def s_morph(ctx, t, d):
    m = P(t, 0.2, 1.8)
    pan = 1 - P(t, d - 0.5, 0.5)
    web(ctx, 1 - m)
    spider(ctx, body_a=0, legs_a=1 - m, tips_a=0)
    octagon(ctx, P(t, 2.6, 3.4), 1)
    rb = R * 0.30 + (24 - R * 0.30) * m
    circle(ctx, CX, CY, rb)
    rgba(ctx, BODY, 1 - 0.4 * m)
    ctx.fill_preserve()
    rgba(ctx, INK, 1 - 0.45 * m)
    ctx.set_line_width(4 - m)
    ctx.stroke()
    for k in range(8):
        vdot(ctx, *vpos(k))
    numbers(ctx, P(t, 2.0, 0.8))
    header(ctx, 'A IDEIA', INK, P(t, 0.6) * pan)
    text(ctx, 'As pontas das 8 patas', PX, 170, 46, INK, P(t, 2.8) * pan, 'bold')
    text(ctx, 'formam um octógono regular.', PX, 232, 46, INK, P(t, 3.2) * pan, 'bold')
    runs(ctx, [('n = 8', BLUE, 'bold'), (' lados', INK, 'regular')], PX, 340, 40, P(t, 6.2) * pan)
    text(ctx, 'A aranha fica parada no centro.', PX, 420, 34, MUTED, P(t, 7.2) * pan)


add_scene('Patas viram vértices (octógono)', 10, s_morph)

# --- PARTE 1 -------------------------------------------------------------------
SIDES = [(i, (i + 1) % 8) for i in range(8)]
DIAGS = [(i, j) for i in range(8) for j in range(i + 1, 8) if (j - i) % 8 not in (1, 7)]
DIAMS = [(i, i + 4) for i in range(4)]


def p1_header(ctx, a):
    header(ctx, 'PARTE 1 · DUAS BOLINHAS PRETAS', BLUE, a)


def p1_intro(ctx, t, d):
    fo = 1 - P(t, d - 0.5, 0.5)
    base = P(t, 0, 0.5)
    ex1 = win(t, 2.0, 5.2, 0.45, 0.45)
    ex2 = win(t, 5.6, d - 0.5, 0.45, 0.45)
    segs = [(0, 1, BLUE, P(t, 2.4, 0.6), 7, ex1), (0, 3, GREEN, P(t, 6.0, 0.6), 7, ex2)]
    lit = {0: (max(ex1, ex2), BLUE if ex1 >= ex2 else GREEN), 1: (ex1, BLUE), 3: (ex2, GREEN)}
    oct_view(ctx, base_a=base, segs=segs, lit=lit)
    p1_header(ctx, P(t, 0.2))
    text(ctx, 'Acender 2 patas', PX, 160, 46, INK, P(t, 0.5) * fo, 'bold')
    text(ctx, '= escolher 2 vértices do octógono', PX, 222, 36, INK, P(t, 0.9) * fo)
    text(ctx, 'e ligar os dois com um segmento.', PX, 272, 36, INK, P(t, 1.2) * fo)
    a1 = P(t, 2.6) * fo
    w = chip(ctx, PX, 380, 'LADO', BLUE, a1)
    text(ctx, 'patas vizinhas', PX + w + 20, 380, 34, INK, a1)
    a2 = P(t, 6.2) * fo
    w = chip(ctx, PX, 455, 'DIAGONAL', GREEN, a2)
    text(ctx, 'patas não vizinhas', PX + w + 20, 455, 34, INK, a2)
    runs(ctx, [('Então vamos contar ', INK, 'regular'), ('LADOS', BLUE, 'bold'), (' + ', INK, 'regular'),
               ('DIAGONAIS', GREEN, 'bold')], PX, 580, 36, P(t, 8.6) * fo)


add_scene('Parte 1 – a ideia (lado ou diagonal)', 10.5, p1_intro)

S_T0, S_DT = 1.0, 0.8


def p1_sides(ctx, t, d):
    fo = 1 - P(t, d - 0.5, 0.5)
    dim = 1 - 0.65 * P(t, d - 0.8, 0.8)
    segs = []
    lit = {}
    count = 0
    for i, (a, b) in enumerate(SIDES):
        ts = S_T0 + i * S_DT
        segs.append((a, b, BLUE, P(t, ts, 0.55), 7, dim))
        if t >= ts + 0.5:
            count = i + 1
        g = win(t, ts, ts + S_DT + 0.1, 0.2, 0.35)
        for k in (a, b):
            lit[k] = (max(lit.get(k, (0, BLUE))[0], g), BLUE)
    oct_view(ctx, segs=segs, lit=lit)
    p1_header(ctx, 1)
    runs(ctx, [('Primeiro, os ', INK, 'bold'), ('LADOS', BLUE, 'bold')], PX, 160, 46, P(t, 0.2) * fo)
    text(ctx, 'cada lado liga 2 patas vizinhas', PX, 222, 34, MUTED, P(t, 0.5) * fo)
    ca = P(t, S_T0 + 0.4, 0.3) * fo
    cs = 1 + 0.12 * bump(t, S_T0 + (count - 1) * S_DT + 0.5, 0.3) if count else 1
    nw = text(ctx, str(count), PX, 400, 160, BLUE, ca, 'bold', scale=cs)
    text(ctx, 'lados', PX + nw + 24, 430, 44, BLUE, ca, 'semibold')
    text(ctx, '8 pares de patas vizinhas', PX, 560, 36, INK, P(t, S_T0 + 8 * S_DT + 0.2) * fo, 'semibold')


add_scene('Parte 1 – contando os lados', S_T0 + 8 * S_DT + 2.1, p1_sides)


def faded_sides(a=0.35):
    return [(i, j, BLUE, 1, 7, a) for i, j in SIDES]


D1_T0, D1_DT = 5.4, 0.7
D1_TARGETS = [2, 3, 4, 5, 6]


def p1_diag_one(ctx, t, d):
    fo = 1 - P(t, d - 0.5, 0.5)
    nb = win(t, 3.0, d - 0.5)
    segs = faded_sides() + [(0, 1, BLUE, 1, 7, nb * 0.65), (7, 0, BLUE, 1, 7, nb * 0.65)]
    count = 0
    lit = {0: (P(t, 0.8, 0.5) * (1 - P(t, d - 0.5, 0.5)), GREEN)}
    for n, j in enumerate(D1_TARGETS):
        ts = D1_T0 + n * D1_DT
        segs.append((0, j, GREEN, P(t, ts, 0.5), 6, 1))
        if t >= ts + 0.45:
            count = n + 1
        lit[j] = (win(t, ts + 0.35, ts + 0.9, 0.2, 0.4), GREEN)
    oct_view(ctx, segs=segs, lit=lit, num_hl={0})
    xa = win(t, 3.0, d - 0.5)
    for k in (1, 7):
        x, y = vpos(k, R - 52)
        xmark(ctx, x, y, 22, RED, xa, 6)
    p1_header(ctx, 1)
    runs(ctx, [('Agora, as ', INK, 'bold'), ('DIAGONAIS', GREEN, 'bold')], PX, 160, 46, P(t, 0.2) * fo)
    text(ctx, 'Do vértice 1, para onde posso ligar?', PX, 222, 34, INK, P(t, 0.7) * fo)
    a = P(t, 2.0) * fo
    xmark(ctx, PX + 14, 300, 20, RED, a, 5)
    text(ctx, 'nele mesmo, não', PX + 46, 300, 32, INK, a)
    a = P(t, 3.0) * fo
    xmark(ctx, PX + 14, 352, 20, RED, a, 5)
    text(ctx, 'nos 2 vizinhos (2 e 8): já são lados', PX + 46, 352, 32, INK, a)
    runs(ctx, [('Sobram ', INK, 'bold'), ('8 − 3 = 5', GREEN, 'bold'), (' diagonais', INK, 'bold')],
         PX, 450, 44, P(t, 4.4) * fo)
    ca = P(t, D1_T0 + 0.3, 0.3) * fo
    nw = text(ctx, str(count), PX, 600, 130, GREEN, ca, 'bold')
    text(ctx, 'diagonais saindo do vértice 1', PX + nw + 22, 625, 32, GREEN, ca, 'semibold')
    text(ctx, 'De cada vértice saem n − 3 diagonais.', PX, 760, 32, MUTED,
         P(t, D1_T0 + 5 * D1_DT + 0.6) * fo)


add_scene('Parte 1 – diagonais que saem de um vértice', D1_T0 + 5 * D1_DT + 3.6, p1_diag_one)

F_T0, F_DT = 0.8, 0.75


def diag_color_state(t, i, j):
    """(progresso, cor, largura) de uma diagonal na cena da fórmula."""
    first, second = F_T0 + i * F_DT, F_T0 + j * F_DT
    prog = P(t, first, 0.45)
    f2 = P(t, second, 0.3)
    col = mix(GREEN, GREEN_D, f2)
    width = 4.5 + 4 * bump(t, second, 0.45)
    return prog, col, width


def p1_diag_formula(ctx, t, d):
    fo = 1 - P(t, d - 0.5, 0.5)
    segs = faded_sides()
    for i, j in DIAGS:
        prog, col, width = diag_color_state(t, i, j)
        segs.append((i, j, col, prog, width, 1))
    lit = {}
    done = 0
    for v in range(8):
        tv = F_T0 + v * F_DT
        lit[v] = (win(t, tv, tv + F_DT, 0.15, 0.3), GREEN)
        if t >= tv + 0.45:
            done = v + 1
    oct_view(ctx, segs=segs, lit=lit)
    p1_header(ctx, 1)
    text(ctx, 'Fazendo isso em todos os vértices:', PX, 160, 40, INK, P(t, 0.2) * fo, 'bold')
    runs(ctx, [('8 vértices × 5 = ', INK, 'semibold'), (str(5 * done), GREEN, 'bold')], PX, 240, 48,
         P(t, 0.6) * fo)
    a = P(t, 7.3) * fo
    text(ctx, 'Mas cada diagonal tem 2 pontas:', PX, 330, 34, INK, a)
    text(ctx, 'foi contada 2 vezes!', PX, 380, 34, GREEN_D, P(t, 7.7) * fo, 'bold')
    runs(ctx, [('40 ÷ 2 = ', INK, 'bold'), ('20', GREEN, 'bold'), (' diagonais', INK, 'bold')], PX, 470, 50,
         P(t, 9.0) * fo)
    fa = P(t, 10.6, 0.6) * fo
    box(ctx, PX - 10, 560, 810, 170, GREEN, fa, fill_a=0.07)
    runs(ctx, [('d = ', INK, 'bold'), ('frac', 'n · (n − 3)', '2', INK, 'bold'), (' = ', INK, 'bold'),
               ('frac', '8 · 5', '2', INK, 'bold'), (' = ', INK, 'bold'), ('20', GREEN, 'bold')],
         PX + 395, 640, 54, fa, 'center')
    text(ctx, 'n = número de lados do polígono', PX, 780, 28, MUTED, P(t, 11.4) * fo)


add_scene('Parte 1 – fórmula das diagonais', 14, p1_diag_formula)


def p1_total(ctx, t, d):
    fo = 1 - P(t, d - 0.5, 0.5)
    sa = 0.35 + 0.65 * P(t, 0.3, 0.6)
    segs = [(i, j, BLUE, 1, 7, sa) for i, j in SIDES]
    back = P(t, 0.3, 0.6)
    for i, j in DIAGS:
        segs.append((i, j, mix(GREEN_D, GREEN, back), 1, 4.5, 1))
    oct_view(ctx, segs=segs)
    p1_header(ctx, 1)
    text(ctx, 'Juntando tudo:', PX, 160, 46, INK, P(t, 0.2) * fo, 'bold')
    runs(ctx, [('8', BLUE, 'bold'), (' lados', INK, 'regular')], PX, 260, 44, P(t, 0.8) * fo)
    runs(ctx, [('20', GREEN, 'bold'), (' diagonais', INK, 'regular')], PX, 330, 44, P(t, 1.4) * fo)
    runs(ctx, [('8', BLUE, 'bold'), (' + ', INK, 'bold'), ('20', GREEN, 'bold'), (' = 28', INK, 'bold')],
         PX, 460, 84, P(t, 2.4) * fo)
    text(ctx, 'jeitos de acender 2 patas', PX, 550, 36, MUTED, P(t, 3.0) * fo)


add_scene('Parte 1 – lados + diagonais = 28', 8, p1_total)

DM_T0, DM_DT = 1.6, 0.7


def p1_diam(ctx, t, d):
    fo = 1 - P(t, d - 0.6, 0.6)
    dim = 1 - 0.55 * P(t, 0.4, 0.6)
    rem = P(t, 7.2, 0.8)
    segs = [(i, j, BLUE, 1, 7, dim) for i, j in SIDES]
    for i, j in DIAGS:
        if (i, j) not in DIAMS:
            segs.append((i, j, GREEN, 1, 4.5, dim))
    lit = {}
    for n, (i, j) in enumerate(DIAMS):
        ts = DM_T0 + n * DM_DT
        f = P(t, ts, 0.35)
        col = mix(GREEN, RED, f)
        w = 4.5 + 3.5 * f
        segs.append((i, j, col, 1, w, 1 - 0.75 * rem, [16, 12] if rem > 0.5 else None))
        g = win(t, ts, ts + DM_DT + 0.2, 0.2, 0.3)
        for k in (i, j):
            lit[k] = (g, RED)
    oct_view(ctx, base_a=fo, segs=segs, lit=lit, nomove_a=win(t, 2.0, 7.4, 0.4, 0.6))
    p1_header(ctx, fo)
    runs(ctx, [('Cuidado com as patas ', INK, 'bold'), ('OPOSTAS', RED, 'bold'), ('!', INK, 'bold')],
         PX, 160, 44, P(t, 0.2) * fo)
    text(ctx, 'O segmento passa pelo centro (diâmetro)', PX, 225, 32, INK, P(t, 0.8) * fo)
    text(ctx, '→ a aranha NÃO se move.', PX, 275, 32, RED, P(t, 1.4) * fo, 'semibold')
    runs(ctx, [('São ', INK, 'regular'), ('4', RED, 'bold'), (' diâmetros: tiramos 4.', INK, 'regular')],
         PX, 365, 36, P(t, 4.6) * fo)
    ra = P(t, 7.4, 0.5) * fo
    box(ctx, PX - 10, 430, 810, 290, ARROWC, ra, fill_a=0.07)
    runs(ctx, [('28 − 4 = ', INK, 'bold'), ('24', ARROWC, 'bold')], PX + 395, 520, 92, ra, 'center',
         scale=pop(t, 7.4, 0.45) if t < 8.0 else 1)
    text(ctx, 'combinações com 2 bolinhas pretas', PX + 395, 625, 32, INK, P(t, 8.0) * fo, 'semibold', 'center')
    text(ctx, 'que fazem a aranha se mover', PX + 395, 670, 32, INK, P(t, 8.0) * fo, 'semibold', 'center')


add_scene('Parte 1 – tirando as patas opostas (28 − 4 = 24)', 12, p1_diam)

ROWS1 = [('vizinhas', '(lado)', 1, BLUE), ('pula 1', '(diagonal)', 2, GREEN), ('pula 2', '(diagonal)', 3, GREEN)]
G1X, G1DX = 640, 118


def p1_grid(ctx, t, d):
    fo = 1 - P(t, d - 0.6, 0.6)
    text(ctx, 'Conferindo: todas as combinações com 2 bolinhas pretas', 110, 90, 44, INK,
         P(t, 0.2) * fo, 'bold')
    for r, (l1, l2, dist, col) in enumerate(ROWS1):
        y = 235 + r * 145
        t0 = 0.8 + r * 1.7
        a = P(t, t0) * fo
        text(ctx, l1, 110, y - 18, 38, col, a, 'bold')
        text(ctx, l2, 110, y + 26, 28, MUTED, a)
        for c in range(8):
            tc = t0 + 0.1 + c * 0.08
            mini(ctx, G1X + c * G1DX, y, 46, (c, (c + dist) % 8), segc=col, a=P(t, tc, 0.25) * fo, s=pop(t, tc))
        text(ctx, '8', 1660, y, 64, col, P(t, t0 + 0.9) * fo, 'bold', 'center')
    y = 235 + 3 * 145 + 30
    t0 = 6.0
    a = P(t, t0) * fo
    text(ctx, 'opostas', 110, y - 18, 38, RED, a, 'bold')
    text(ctx, '(diâmetro)', 110, y + 26, 28, MUTED, a)
    for c in range(4):
        tc = t0 + 0.1 + c * 0.08
        mini(ctx, G1X + c * G1DX, y, 46, (c, c + 4), segc=RED, a=P(t, tc, 0.25) * fo, s=pop(t, tc))
    text(ctx, 'não se move: fica de fora', G1X + 4 * G1DX - 30, y, 32, RED, P(t, t0 + 0.5) * fo, 'semibold')
    text(ctx, '4', 1660, y, 64, RED, P(t, t0 + 0.9) * fo, 'bold', 'center')
    la = P(t, 7.8) * fo
    rgba(ctx, OCT, la)
    ctx.set_line_width(2)
    ctx.move_to(110, 850)
    ctx.line_to(1810, 850)
    ctx.stroke()
    runs(ctx, [('8 + 8 + 8 = ', INK, 'bold'), ('24', ARROWC, 'bold')], 110, 925, 64, P(t, 8.0) * fo)
    text(ctx, 'e as 20 diagonais = 8 (pula 1) + 8 (pula 2) + 4 (opostas)', 700, 930, 30, MUTED,
         P(t, 9.2) * fo)


add_scene('Parte 1 – conferindo as 24', 13, p1_grid)

# --- PARTE 2 -------------------------------------------------------------------
LABELS = ['4 juntas', '1 sozinha + 3 juntas', '2 juntas + 2 juntas', '2 juntas + 2 sozinhas',
          'não se move (pares opostos)']
TY0, TLH = 610, 58
TALLY_W = 800


def p2_header(ctx, a):
    header(ctx, 'PARTE 2 · QUATRO BOLINHAS PRETAS', PURPLE, a)


def tally(ctx, vals, total, a=1.0, hl=None, pop_line=None, pop_s=1.0, total_s=1.0):
    if a <= 0:
        return
    text(ctx, 'PLACAR', PX, TY0 - 56, 22, MUTED, a, 'bold', spacing=3)
    for i, lab in enumerate(LABELS):
        v = vals[i]
        if v is None:
            continue
        y = TY0 + i * TLH
        if hl == i:
            rrect(ctx, PX - 14, y - 25, TALLY_W + 14, 50, 12)
            rgba(ctx, AMBER, 0.16 * a)
            ctx.fill()
        col = RED if i == 4 else INK
        text(ctx, lab, PX, y, 30, col, a, 'semibold')
        if v:
            text(ctx, v, PX + TALLY_W - 14, y, 30, col, a, 'bold', 'right',
                 scale=pop_s if pop_line == i else 1.0)
    ys = TY0 + 5 * TLH - 14
    rgba(ctx, OCT, a)
    ctx.set_line_width(2)
    ctx.move_to(PX, ys)
    ctx.line_to(PX + TALLY_W, ys)
    ctx.stroke()
    text(ctx, 'Total que faz a aranha se mover', PX, ys + 46, 32, INK, a, 'bold')
    text(ctx, str(total), PX + TALLY_W - 14, ys + 46, 48, ARROWC, a, 'bold', 'right', scale=total_s)


def p2_intro(ctx, t, d):
    fo = 1 - P(t, d - 1.0, 0.6)
    base = P(t, 0, 0.6)
    lit = {}
    show = []
    for i in range(8):
        ti = 4.4 + i * 0.32
        lit[i] = (win(t, ti, ti + 0.55, 0.15, 0.4), AMBER)
        show.append(pop(t, ti, 0.3))
    oct_view(ctx, base_a=base, lit=lit)
    p2_header(ctx, P(t, 0.3))
    text(ctx, 'Agora são 4 patas acesas.', PX, 160, 46, INK, P(t, 0.6) * fo, 'bold')
    runs(ctx, [('Ideia: escolher um ', INK, 'regular'), ('FORMATO', PURPLE, 'bold')], PX, 240, 38,
         P(t, 1.6) * fo)
    text(ctx, 'e girar esse formato pelas 8 posições.', PX, 292, 38, INK, P(t, 2.2) * fo)
    text(ctx, 'Para enxergar o formato, lemos as patas', PX, 390, 30, MUTED, P(t, 3.3) * fo)
    text(ctx, 'a partir da 1, no sentido horário, numa fita:', PX, 432, 30, MUTED, P(t, 3.3) * fo)
    sy = 530 + (STRIP_Y - 530) * P(t, d - 1.0, 0.9)
    strip(ctx, PX + 22, sy, a=1, show=show)
    text(ctx, 'depois da 8 vem a 1 de novo: a fita fecha um círculo!', PX, 640, 28, MUTED,
         P(t, 7.6) * fo)
    tally(ctx, [None] * 5, 0, P(t, d - 0.8, 0.6))


add_scene('Parte 2 – a ideia (formato + giro)', 11, p2_intro)

FORMATOS = [
    dict(group=0, title='4 juntas', sub='4 patas vizinhas, uma depois da outra', pat=(0, 1, 2, 3),
         step=0.95, upd={0: '8'}),
    dict(group=1, title='1 sozinha + 3 juntas', sub='começa com 1, pula 1, vêm 3 juntas', pat=(0, 2, 3, 4),
         upd={1: '8'}),
    dict(group=1, title='1 sozinha + 3 juntas', sub='começa com 1, pula 2, vêm 3 juntas', pat=(0, 3, 4, 5),
         upd={1: '8 + 8'}),
    dict(group=1, title='1 sozinha + 3 juntas', sub='começa com 1, pula 3, vêm 3 juntas', pat=(0, 4, 5, 6),
         upd={1: '8 + 8 + 8 = 24'}),
    'FALTAM',
    dict(group=2, title='2 juntas + 2 juntas', sub='2 juntas, pula 1, 2 juntas', pat=(0, 1, 3, 4),
         note='(pular 3 dá no mesmo: é pular 1 pelo outro lado)', upd={2: '8'}),
    dict(group=2, title='2 juntas + 2 juntas', sub='2 juntas, pula 2, 2 juntas: 2 pares opostos!',
         pat=(0, 1, 4, 5), upd={4: '4'}),
    dict(group=3, title='2 juntas + 2 sozinhas', sub='2 juntas, pula 1, 1 pata, pula 1, 1 pata',
         pat=(0, 1, 3, 5), note='as 4 apagadas ficam 1 + 1 + 2: o "2" tem 3 lugares', upd={3: '8'}),
    dict(group=3, title='2 juntas + 2 sozinhas', sub='2 juntas, pula 1, 1 pata, pula 2, 1 pata',
         pat=(0, 1, 3, 6), note='as 4 apagadas ficam 1 + 1 + 2: o "2" tem 3 lugares', upd={3: '8 + 8'}),
    dict(group=3, title='2 juntas + 2 sozinhas', sub='2 juntas, pula 2, 1 pata, pula 1, 1 pata',
         pat=(0, 1, 4, 6), note='as 4 apagadas ficam 1 + 1 + 2: o "2" tem 3 lugares',
         upd={3: '8 + 8 + 8 = 24'}),
    dict(group=4, title='Todas separadas', sub='pula 1 entre cada uma: 2 pares opostos!', pat=(0, 2, 4, 6),
         upd={4: '4 + 2 = 6'}),
]

TH_X, TH_DX, TH_Y, TH_R = PX + 44, 99, 410, 40
T_ROT = 2.1


def make_formato(f, prev_group, next_group, vals_before, vals_after, total_before, total_after, last):
    pat = f['pat']
    moving = moves(pat)
    per = period(pat)
    step = f.get('step', 0.62 if moving else 0.75)
    nsteps = 7 if moving else per
    end_rot = T_ROT + nsteps * step
    t_upd = end_rot + (0.45 if moving else 1.5)
    dur = t_upd + 1.7
    changed = [i for i in range(5) if vals_after[i] != vals_before[i] and vals_after[i]]
    pop_line = changed[0] if changed else None
    hl = f['group'] if f['group'] < 4 else 4

    def fn(ctx, t, d):
        fo = 1 - P(t, d - 0.4, 0.4)
        base_a = (1 - P(t, d - 0.6, 0.6)) if last else 1.0
        title_a = (1.0 if prev_group == f['group'] else P(t, 0.0, 0.4)) * \
                  (1.0 if next_group == f['group'] else fo)
        rot = 0.0
        for i in range(nsteps):
            rot += P(t, T_ROT + i * step, 0.72 * step)
        lit_a = P(t, 0.7, 0.5) * fo
        movers = [(ang_of(k) + rot * math.pi / 4, lit_a, AMBER) for k in pat]
        arrow_spec = None
        nm = 0.0
        if moving:
            arrow_spec = (resultant(pat)[0] + rot * math.pi / 4, P(t, 1.2, 0.6), fo)
        else:
            nm = P(t, 1.2, 0.5) * fo
        oct_view(ctx, base_a=base_a, movers=movers, arrow_spec=arrow_spec, nomove_a=nm)
        if not moving:
            text(ctx, 'não se move', CX, CY + 72, 30, RED, nm * base_a, 'bold', 'center')
        # painel
        p2_header(ctx, base_a)
        text(ctx, f['title'], PX, 140, 44, INK, title_a, 'bold')
        sub_col = INK if moving else RED
        text(ctx, f['sub'], PX, 194, 30, sub_col, P(t, 0.15, 0.4) * fo, 'regular' if moving else 'semibold')
        if f.get('note'):
            same_note = lambda g: g is not None and g == f['group']
            na = (1.0 if same_note(prev_group) else P(t, 0.3, 0.4)) * (1.0 if same_note(next_group) else fo)
            text(ctx, f['note'], PX, 234, 24, MUTED, na)
        lv = [0.0] * 8
        for idx, k in enumerate(sorted(pat)):
            lv[k] = P(t, 0.3 + idx * 0.08, 0.3) * fo
        strip(ctx, PX + 22, STRIP_Y, lv, a=base_a)
        # miniaturas das posições
        nth = 8 if moving else per
        times = [1.8] + [T_ROT + i * step + 0.72 * step for i in range(nth - 1)]
        shown = 0
        for j in range(nth):
            tj = times[j]
            if t >= tj:
                shown = j + 1
            ring = None
            if not moving and j == 0:
                ring = (RED, bump(t, end_rot - 0.05, 0.9))
            mini(ctx, TH_X + j * TH_DX, TH_Y, TH_R, rotated(pat, j), a=P(t, tj, 0.25) * fo, s=pop(t, tj), ring=ring)
        ca = P(t, 1.8, 0.3) * fo
        runs(ctx, [('posições diferentes: ', INK, 'regular'), (str(shown), PURPLE if moving else RED, 'bold')],
             PX, 492, 30, ca)
        if not moving:
            text(ctx, f'girou e repetiu: só {per}!', PX + 380, 492, 30, RED, P(t, end_rot + 0.1) * fo, 'bold')
        # placar
        after = t >= t_upd
        vals = vals_after if after else vals_before
        total = total_after if after else total_before
        ps = 1 + 0.35 * bump(t, t_upd, 0.45)
        ts = 1 + 0.3 * bump(t, t_upd + 0.15, 0.45) if total_after != total_before else 1.0
        tally(ctx, vals, total, base_a, hl=hl if t < d - 0.4 else None, pop_line=pop_line, pop_s=ps, total_s=ts)

    return dur, fn


def p2_faltam_factory(vals, total):
    def fn(ctx, t, d):
        fo = 1 - P(t, d - 0.4, 0.4)
        oct_view(ctx)
        p2_header(ctx, 1)
        text(ctx, 'Até aqui: 8 + 24 = 32', PX, 150, 46, INK, P(t, 0.2) * fo, 'bold')
        text(ctx, 'Acabou? Ainda NÃO!', PX, 232, 46, RED, P(t, 1.2) * fo, 'bold',
             scale=pop(t, 1.2, 0.4) if t < 1.7 else 1)
        text(ctx, 'Faltam os formatos que não têm', PX, 330, 34, INK, P(t, 2.4) * fo)
        text(ctx, '3 patas juntas: com pares ou separadas.', PX, 378, 34, INK, P(t, 2.4) * fo)
        tally(ctx, vals, total, 1)
    return fn


def build_part2():
    vals = [None] * 5
    total = 0
    items = [x for x in FORMATOS]
    groups = [x['group'] if isinstance(x, dict) else None for x in items]
    for idx, f in enumerate(items):
        if f == 'FALTAM':
            add_scene('Parte 2 – ainda faltam formatos!', 6.0, p2_faltam_factory(list(vals), total))
            continue
        prev_group = groups[idx - 1] if idx > 0 else None
        next_group = groups[idx + 1] if idx + 1 < len(items) else None
        before = list(vals)
        if f['group'] < 4 and before[f['group']] is None:
            before[f['group']] = ''
        after = list(before)
        for k, v in f['upd'].items():
            after[k] = v
        t_before = total
        t_after = total + (8 if moves(f['pat']) else 0)
        last = idx == len(items) - 1
        dur, fn = make_formato(f, prev_group, next_group, before, after, t_before, t_after, last)
        name = f"Parte 2 – {f['title']}: {f['sub']}"
        add_scene(name, dur, fn)
        vals, total = after, t_after
    return vals, total


FINAL_VALS, FINAL_TOTAL = build_part2()
assert FINAL_TOTAL == 64, FINAL_TOTAL

MOVING_F = [f for f in FORMATOS if isinstance(f, dict) and moves(f['pat'])]
STOP_F = [f for f in FORMATOS if isinstance(f, dict) and not moves(f['pat'])]
GRID_LABELS = ['4 juntas', '1, pula 1, 3 juntas', '1, pula 2, 3 juntas', '1, pula 3, 3 juntas',
               '2, pula 1, 2 juntas', '2 juntas + 1 + 1 (a)', '2 juntas + 1 + 1 (b)', '2 juntas + 1 + 1 (c)']

# conferência: as 64 + 6 posições são todas diferentes e cobrem as 70 escolhas de 4 patas
_all = set()
for f in MOVING_F:
    for j in range(8):
        _all.add(rotated(f['pat'], j))
assert len(_all) == 64
for f in STOP_F:
    for j in range(period(f['pat'])):
        _all.add(rotated(f['pat'], j))
assert len(_all) == 70


def p2_grid(ctx, t, d):
    fo = 1 - P(t, d - 0.6, 0.6)
    text(ctx, 'Conferindo: todas as combinações com 4 bolinhas pretas', 110, 66, 44, INK, P(t, 0.2) * fo, 'bold')
    gx, gdx, gy, gdy, gr = 640, 106, 160, 113, 38
    for r, f in enumerate(MOVING_F):
        y = gy + r * gdy
        t0 = 0.7 + r * 0.55
        a = P(t, t0, 0.35) * fo
        lv = [1.0 if k in f['pat'] else 0.0 for k in range(8)]
        ctx.save()
        ctx.translate(110, y)
        strip(ctx, 0, 0, lv, a=a, r=9, gap=25, nums=False)
        ctx.restore()
        text(ctx, GRID_LABELS[r], 310, y, 22, MUTED, a, 'semibold')
        for c in range(8):
            tc = t0 + 0.05 + c * 0.04
            mini(ctx, gx + c * gdx, y, gr, rotated(f['pat'], c), a=P(t, tc, 0.2) * fo, s=pop(t, tc, 0.3))
    # coluna da direita: não se move + total
    cxr = 1660
    rgba(ctx, OCT, P(t, 0.5) * fo)
    ctx.set_line_width(2)
    ctx.move_to(1478, 140)
    ctx.line_to(1478, 960)
    ctx.stroke()
    t1 = 5.6
    a = P(t, t1) * fo
    text(ctx, 'Não se move:', cxr, 160, 30, RED, a, 'bold', 'center')
    stops = [rotated(STOP_F[0]['pat'], j) for j in range(4)] + [rotated(STOP_F[1]['pat'], j) for j in range(2)]
    for n, ks in enumerate(stops):
        cx = cxr - 62 + (n % 2) * 124
        cy = 238 + (n // 2) * 96
        tc = t1 + 0.2 + n * 0.1
        mini(ctx, cx, cy, 38, ks, a=P(t, tc, 0.2) * fo, s=pop(t, tc, 0.3))
    text(ctx, '4 + 2 = 6', cxr, 532, 34, RED, P(t, t1 + 1.0) * fo, 'bold', 'center')
    ta = P(t, 7.8) * fo
    text(ctx, 'Se move:', cxr, 645, 30, INK, ta, 'bold', 'center')
    text(ctx, '8 formatos', cxr, 697, 34, INK, ta, 'semibold', 'center')
    text(ctx, '× 8 posições', cxr, 743, 34, INK, ta, 'semibold', 'center')
    runs(ctx, [('= ', INK, 'bold'), ('64', ARROWC, 'bold')], cxr, 835, 96, ta, 'center',
         scale=pop(t, 7.8, 0.45) if t < 8.4 else 1)
    ca = P(t, 10.5) * fo
    text(ctx, 'conferência: 64 + 6 = 70', cxr, 925, 24, MUTED, ca, 'semibold', 'center')
    text(ctx, 'todas as escolhas de 4 patas', cxr, 958, 22, MUTED, ca, 'regular', 'center')


add_scene('Parte 2 – conferindo as 64', 15, p2_grid)


def s_final(ctx, t, d):
    a0 = P(t, 0.2)
    text(ctx, 'RESPOSTA', 960, 190, 28, MUTED, a0, 'bold', 'center', spacing=5)
    runs(ctx, [('2 bolinhas pretas:  ', INK, 'semibold'), ('24', BLUE, 'bold')], 960, 320, 58, P(t, 0.6), 'center')
    runs(ctx, [('4 bolinhas pretas:  ', INK, 'semibold'), ('64', PURPLE, 'bold')], 960, 420, 58, P(t, 1.4), 'center')
    la = P(t, 2.2)
    rgba(ctx, OCT, la)
    ctx.set_line_width(3)
    ctx.move_to(640, 500)
    ctx.line_to(1280, 500)
    ctx.stroke()
    runs(ctx, [('24', BLUE, 'bold'), (' + ', INK, 'bold'), ('64', PURPLE, 'bold'), (' = ', INK, 'bold'),
               ('88', ARROWC, 'bold')], 960, 620, 124, P(t, 2.6, 0.4), 'center',
         scale=pop(t, 2.6, 0.5) if t < 3.2 else 1)
    ba = P(t, 4.2)
    box(ctx, 960 - 230, 760, 460, 100, GREEN, ba, fill_a=0.10, lw=4, r=22)
    text(ctx, 'Alternativa A', 960, 810, 46, GREEN, ba, 'bold', 'center')


add_scene('Resposta: 24 + 64 = 88', 12, s_final)


# ----------------------------------------------------------------------------
# Motor de renderização
# ----------------------------------------------------------------------------
def timeline():
    t = 0.0
    out = []
    for s in SCENES:
        out.append((t, s))
        t += s['dur']
    return out, t


TL, TOTAL = timeline()
NFRAMES = int(round(TOTAL * FPS))


def draw_at(ctx, T):
    for start, s in TL:
        if start <= T < start + s['dur']:
            break
    else:
        start, s = TL[-1]
        T = start + s['dur'] - 1e-6
    rgba(ctx, BG, 1)
    ctx.paint()
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    s['fn'](ctx, T - start, s['dur'])


def new_surface():
    surf = cairo.ImageSurface(cairo.FORMAT_RGB24, W, H)
    ctx = cairo.Context(surf)
    fo = cairo.FontOptions()
    fo.set_antialias(cairo.ANTIALIAS_GRAY)
    fo.set_hint_style(cairo.HINT_STYLE_NONE)
    fo.set_hint_metrics(cairo.HINT_METRICS_OFF)
    ctx.set_font_options(fo)
    return surf, ctx


def fmt(t):
    return f'{int(t // 60)}:{t % 60:04.1f}'


def render_chunk(args):
    f0, f1, path = args
    surf, ctx = new_surface()
    cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'bgr0', '-s', f'{W}x{H}',
           '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-tune', 'animation',
           '-pix_fmt', 'yuv420p', '-threads', '2', path]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in range(f0, f1):
        draw_at(ctx, f / FPS)
        surf.flush()
        proc.stdin.write(surf.get_data())
    proc.stdin.close()
    proc.wait()
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--timeline', action='store_true')
    ap.add_argument('--sheet', nargs='+', type=float)
    ap.add_argument('--out', default=os.path.join(HERE, 'aranha_fuvest_q59.mp4'))
    ap.add_argument('--jobs', type=int, default=3)
    args = ap.parse_args()

    if args.timeline:
        for start, s in TL:
            print(f"{fmt(start):>7}  ({s['dur']:5.1f}s)  {s['name']}")
        print(f'Total: {fmt(TOTAL)}  ({NFRAMES} quadros)')
        return

    if args.sheet:
        big = cairo.ImageSurface(cairo.FORMAT_RGB24, W, H)
        bctx = cairo.Context(big)
        rgba(bctx, hexc('#333333'))
        bctx.paint()
        for n, T in enumerate(args.sheet[:4]):
            surf, ctx = new_surface()
            draw_at(ctx, T)
            bctx.save()
            bctx.translate((n % 2) * W / 2, (n // 2) * H / 2)
            bctx.scale(0.5, 0.5)
            bctx.translate(4 if n % 2 else 0, 4 if n // 2 else 0)
            bctx.set_source_surface(surf, 0, 0)
            bctx.paint()
            bctx.restore()
            rgba(bctx, hexc('#E8590C'))
            text(bctx, f'{T:.1f}s', (n % 2) * W / 2 + 14, (n // 2) * H / 2 + 22, 22, hexc('#E8590C'), 1, 'bold')
        big.write_to_png(args.out)
        print(args.out)
        return

    from multiprocessing import Pool
    jobs = max(1, args.jobs)
    tmpdir = tempfile.mkdtemp(prefix='aranha_')
    bounds = [round(NFRAMES * i / jobs) for i in range(jobs + 1)]
    chunks = [(bounds[i], bounds[i + 1], os.path.join(tmpdir, f'part{i}.mp4')) for i in range(jobs)]
    print(f'Renderizando {NFRAMES} quadros ({fmt(TOTAL)}) em {jobs} partes...', flush=True)
    with Pool(jobs) as pool:
        parts = pool.map(render_chunk, chunks)
    lst = os.path.join(tmpdir, 'list.txt')
    with open(lst, 'w') as fh:
        for p in parts:
            fh.write(f"file '{p}'\n")
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy',
                    '-movflags', '+faststart', args.out], check=True)
    for p in parts:
        os.remove(p)
    os.remove(lst)
    os.rmdir(tmpdir)
    print('OK ->', args.out)


if __name__ == '__main__':
    main()
