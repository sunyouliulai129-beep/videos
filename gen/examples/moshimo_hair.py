"""もしも系ショートの見本：もしも、髪の毛を一生切らなかったら？
実行：python3 gen/examples/moshimo_hair.py /tmp/out/moshimo_hair.mp4
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from moshimo_kit import *

Q = 'もしも、髪の毛を一生切らなかったら？'
GROUND = 1400
PERSON_H = 600            # 170cm を 600px で描く
PX_PER_CM = PERSON_H/170
X = W//2

BG_TITLE = bg_flat((28, 24, 44))
BG_ROOM = bg_sky(top=(70, 80, 120), bottom=(120, 130, 170), ground=(60, 50, 70), ground_y=GROUND)

def draw_person_with_hair(b, hair_cm, color=(25, 25, 35)):
    d = ImageDraw.Draw(b)
    head_top = GROUND - PERSON_H
    L = hair_cm*PX_PER_CM
    hw = PERSON_H*0.21
    if L > 0:
        d.rounded_rectangle([X - hw, head_top + 8, X + hw, head_top + 8 + max(L, 30)], 40, fill=(150, 90, 40))
    person(d, X, GROUND, PERSON_H, color)
    # 身長の目盛り
    d.line([(X + 220, GROUND), (X + 220, head_top)], fill=(200, 200, 220), width=3)
    put(b, (X + 236, head_top), '170cm', 28, fill=GRAY, anchor='lm', black=False)

SCENES = [  # (開始, 終了, バッジ, 見出し, ラベル, 値, 髪cm, 字幕1, 字幕2)
    (3.2, 11.0, 'その1', '1年後', '伸びた長さ', '約12cm', 12, '髪は1か月に約1cm伸びる', '1年でおよそ12cm'),
    (11.0, 19.0, 'その2', '3年後', '伸びた長さ', '約36cm', 36, '肩をこえて', '背中まで届く'),
    (19.0, 27.0, 'その3', '10年後', '計算上の長さ', '約1.2m', 120, 'このままいけば', '足元まで届く…？'),
]

def frame(t):
    if t < 3.2:
        b = BG_TITLE.copy()
        title(b, t, 'もしも、髪の毛を', '一生切らなかったら？')
        ic = emoji('💇', 460); b.alpha_composite(ic, (X - ic.width//2, 1000))
        return b
    for s0, s1, badge, head, label, value, cm, c1, c2 in SCENES:
        if s0 <= t < s1:
            b = BG_ROOM.copy()
            grow = ease_out((t - s0)/2.0)
            prev = {12: 3, 36: 12, 120: 36}[cm]
            draw_person_with_hair(b, lerp(prev, cm, grow))
            info_card(b, Q, badge, head, label, value, alpha=fade(t, s0, 0.2))
            caption(b, t, s0 + 0.6, c1, c2)
            return b
    if t < 37.0:
        b = BG_ROOM.copy(); s0 = 27.0
        draw_person_with_hair(b, 120*(1 - ease_out((t - s0 - 1.5)/2.5)*0.25))
        flash(b, t, s0)
        info_card(b, Q, 'その4', '実は途中で止まる', '1本の髪が伸び続ける期間', '約2〜6年', alpha=fade(t, s0, 0.2))
        caption(b, t, s0 + 0.8, '髪には寿命があって', '抜けて生え変わる')
        return b
    if t < 46.0:
        b = BG_TITLE.copy(); s0 = 37.0
        ending(b, t, s0, head='だから、ふつうは', sub='髪の長さの限界は', big='1m前後',
               note='※伸びる期間には個人差があり、もっと長く伸びる人もいる')
        ic = emoji('💇', 380); b.alpha_composite(ic, (X - ic.width//2, 1050))
        return b
    b = BG_TITLE.copy(); s0 = 46.0
    put(b, (W//2, 820), 'あなたの髪は', 76, stroke=6, scale=pop(t, s0))
    put(b, (W//2, 940), '今何cm？', 96, fill=YEL, stroke=7, scale=pop(t, s0 + 0.3))
    put(b, (W//2, 1090), 'コメントで教えてね', 54, alpha=fade(t, s0 + 0.8))
    return b

EVENTS = [(0.0, pop_sfx()), (0.25, pop_sfx())] + [(s[0], whoosh()) for s in SCENES] + [(s[0] + 0.6, tone(1200, 0.08, 0.15, 40)) for s in SCENES] + \
         [(27.0, boom()), (37.0, whoosh()), (37.9, ding()), (46.0, pop_sfx())]

if __name__ == '__main__':
    render(sys.argv[1], 49.5, frame, EVENTS)
