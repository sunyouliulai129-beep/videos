"""もしも系ショート用の部品集（チャンネル YNSSNSK の既存動画のスタイルに合わせたもの）

使い方：content/DAY/moshimo.py を書き、このファイルを import して
  render(out_path, total_seconds, frame_fn, events)
を呼ぶ。frame_fn(t) は PIL.Image(RGBA, 1080x1920) を返す関数。

スタイルのきまり（既存の6本から）
- 1080x1920 / 30fps / 50〜60秒
- 冒頭3秒：大きなタイトル「もしも、〜が／〜たら？」（1行目は白、2行目は黄色）と、中央に主役のイラスト
- 本編：上に「情報カード」（小さな問い ＋ 黄色い「その1」バッジ＋見出し ＋ ラベル ＋ 黄色の大きな数字）
        下に「字幕」（白文字に黒フチ、2行目は黄色で強調）、真ん中はシーンのイラスト
- 数字で段階的にスケールが大きくなる見せ方（回数・日数・倍率）が強い
- 最後：「でも、安心して。」＋現実の補足（小さく注釈） または コメントを促す一言
"""
import math, subprocess, wave, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
FB = '/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc'
FBo = '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'
EMO = '/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf'
WHITE = (250, 250, 250); YEL = (255, 205, 50); GRAY = (190, 195, 210); RED = (235, 70, 55); NAVY = (14, 18, 38)
_fc = {}
def F(size, black=True):
    k = (size, black)
    if k not in _fc: _fc[k] = ImageFont.truetype(FB if black else FBo, size, index=0)
    return _fc[k]

# ---------- easing ----------
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def ease_out(t): t = clamp(t); return 1 - (1 - t)**3
def ease_back(t):
    t = clamp(t); c = 1.7
    return 1 + (c+1)*(t-1)**3 + c*(t-1)**2
def pop(t, t0, d=0.25): return max(ease_back((t - t0)/d), 0.01)
def fade(t, t0, d=0.3): return clamp((t - t0)/d)
def lerp(a, b, k): return a + (b - a)*k

# ---------- text ----------
def put(base, xy, text, size, fill=WHITE, anchor='mm', stroke=0, sf=(0, 0, 0), black=True, alpha=1.0, scale=1.0, maxw=1000):
    while size > 16 and F(size, black).getlength(text) > maxw: size -= 2
    f = F(size, black)
    bb = f.getbbox(text, stroke_width=stroke)
    w, h = bb[2] + stroke*2 + 12, bb[3] + stroke*2 + 12
    tmp = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(tmp).text((stroke + 6, stroke + 6), text, font=f, fill=fill, stroke_width=stroke, stroke_fill=sf)
    if abs(scale - 1) > 1e-3:
        tmp = tmp.resize((max(1, int(w*scale)), max(1, int(h*scale))), Image.LANCZOS)
    if alpha < 0.999:
        tmp.putalpha(tmp.split()[3].point(lambda v: int(v*alpha)))
    x, y = xy
    if anchor[0] == 'm': x -= tmp.width//2
    elif anchor[0] == 'r': x -= tmp.width
    if anchor[1] == 'm': y -= tmp.height//2
    base.alpha_composite(tmp, (int(x), int(y)))

_emo = {}
def emoji(ch, size):
    k = (ch, size)
    if k not in _emo:
        im = Image.new('RGBA', (140, 140), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((6, 6), ch, font=ImageFont.truetype(EMO, 109), embedded_color=True)
        im = im.crop(im.getbbox()); s = size/max(im.size)
        _emo[k] = im.resize((int(im.width*s), int(im.height*s)), Image.LANCZOS)
    return _emo[k]

# ---------- backgrounds ----------
def bg_space(seed=1, top=(10, 12, 30), bottom=(18, 22, 48)):
    y = np.linspace(0, 1, H)[:, None, None]
    img = np.array(top)*(1-y) + np.array(bottom)*y
    img = np.broadcast_to(img, (H, W, 3)).copy()
    rng = np.random.default_rng(seed)
    for _ in range(260):
        x, yy = rng.integers(0, W), rng.integers(0, H); v = rng.integers(90, 230)
        img[yy, x] = (v, v, v)
        if rng.random() < 0.12 and 0 < x < W-1 and 0 < yy < H-1: img[yy-1:yy+2, x-1:x+2] = (v, v, v)
    return Image.fromarray(img.astype(np.uint8)).convert('RGBA')

def bg_sky(top=(110, 170, 235), bottom=(190, 225, 250), ground=(70, 110, 70), ground_y=1380):
    y = np.linspace(0, 1, H)[:, None, None]
    img = np.array(top)*(1-y) + np.array(bottom)*y
    img = np.broadcast_to(img, (H, W, 3)).copy().astype(np.uint8)
    im = Image.fromarray(img).convert('RGBA')
    ImageDraw.Draw(im).rectangle([0, ground_y, W, H], fill=ground)
    return im

def bg_flat(color=NAVY): return Image.new('RGBA', (W, H), color + (255,))

# ---------- common drawings ----------
def person(d, x, foot_y, height, color=(25, 25, 35)):
    """シルエットの人（既存動画と同じ黒い人型）。x=中心、foot_y=足元、height=身長(px)"""
    h = height; head = h*0.13
    d.ellipse([x - head, foot_y - h, x + head, foot_y - h + head*2], fill=color)
    bw = h*0.16
    d.rectangle([x - bw, foot_y - h + head*2.1, x + bw, foot_y - h*0.45], fill=color)
    d.rectangle([x - bw*1.45, foot_y - h + head*2.2, x - bw*1.05, foot_y - h*0.5], fill=color)
    d.rectangle([x + bw*1.05, foot_y - h + head*2.2, x + bw*1.45, foot_y - h*0.5], fill=color)
    d.rectangle([x - bw, foot_y - h*0.45, x - bw*0.12, foot_y], fill=color)
    d.rectangle([x + bw*0.12, foot_y - h*0.45, x + bw, foot_y], fill=color)

def earth(size, rot=0.0):
    """地球のイラスト（青い海＋緑の大陸）。rot で回転感を出す"""
    S = size
    im = Image.new('RGBA', (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse([0, 0, S-1, S-1], fill=(40, 110, 200))
    rng = np.random.default_rng(7)
    for _ in range(7):
        cx = (rng.random()*1.6 - 0.3 + rot) % 1.6 - 0.3; cy = rng.random()
        r = S*(0.10 + rng.random()*0.13)
        d.ellipse([cx*S - r, cy*S - r*0.8, cx*S + r, cy*S + r*0.8], fill=(70, 160, 80))
    mask = Image.new('L', (S, S), 0); ImageDraw.Draw(mask).ellipse([0, 0, S-1, S-1], fill=255)
    out = Image.new('RGBA', (S, S), (0, 0, 0, 0)); out.paste(im, (0, 0), mask)
    shade = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(shade).ellipse([int(S*0.25), int(S*0.15), int(S*1.25), int(S*1.15)], fill=(0, 0, 30, 110))
    shade = shade.filter(ImageFilter.GaussianBlur(S//12)); m2 = Image.new('RGBA', (S, S), (0, 0, 0, 0)); m2.paste(shade, (0, 0), mask)
    out.alpha_composite(m2)
    return out

def city(d, ground_y, color=(55, 62, 80), win=(255, 220, 120), seed=3):
    rng = np.random.default_rng(seed); x = 0
    while x < W:
        bw = int(rng.integers(90, 170)); bh = int(rng.integers(140, 380))
        d.rectangle([x, ground_y - bh, x + bw - 8, ground_y], fill=color)
        for wy in range(ground_y - bh + 20, ground_y - 20, 38):
            for wx in range(x + 14, x + bw - 26, 30):
                if rng.random() < 0.7: d.rectangle([wx, wy, wx + 14, wy + 20], fill=win)
        x += bw

def scale_bar(b, x, y, length_px, label):
    d = ImageDraw.Draw(b)
    d.line([(x, y), (x + length_px, y)], fill=WHITE, width=3)
    d.line([(x, y - 10), (x, y + 10)], fill=WHITE, width=3); d.line([(x + length_px, y - 10), (x + length_px, y + 10)], fill=WHITE, width=3)
    put(b, (x + length_px + 12, y), label, 26, fill=GRAY, anchor='lm', black=False)

# ---------- layout pieces ----------
def title(b, t, line1, line2, sub=None, y=330):
    """冒頭タイトル。line1=白、line2=黄色"""
    put(b, (W//2, y), line1, 78, stroke=8, scale=pop(t, 0.0))
    put(b, (W//2, y + 105), line2, 84, fill=YEL, stroke=8, scale=pop(t, 0.25))
    if sub: put(b, (W//2, y + 220), sub, 64, stroke=6, alpha=fade(t, 0.7))

def info_card(b, question, badge=None, headline=None, label=None, value=None, value2=None, alpha=1.0, big_number=None, big_unit=None):
    """上の情報カード。
    question : 小さな問い（例「もしも、紙を何回でも折れたら？」）
    badge    : 「その1」など（黄色のピル）。big_number を使う時は None
    headline : 見出し（白・太字）
    label    : 小さいラベル（灰）
    value    : 大きな黄色の値
    big_number/big_unit : 「28 回目」のような大きな数字（カウンター型）
    """
    card = Image.new('RGBA', (W, 420), (0, 0, 0, 0)); d = ImageDraw.Draw(card)
    h = 190
    if label or value: h = 300
    d.rounded_rectangle([30, 30, W - 30, 30 + h], 28, fill=(20, 26, 50, 215))
    put(card, (70, 70), question, 34, anchor='lm', maxw=940)
    y = 135
    if big_number is not None:
        put(card, (70, y + 10), str(big_number), 96, anchor='lm')
        nw = F(96).getlength(str(big_number))
        if big_unit: put(card, (70 + nw + 14, y + 26), big_unit, 40, anchor='lm')
        y += 85
    else:
        x = 70
        if badge:
            bw = int(F(34).getlength(badge)) + 34
            d.rounded_rectangle([x, y - 26, x + bw, y + 26], 26, fill=YEL)
            put(card, (x + bw//2, y), badge, 34, fill=(25, 25, 25))
            x += bw + 18
        if headline: put(card, (x, y), headline, 46, anchor='lm', maxw=W - x - 80)
        y += 70
    if label: put(card, (70, y + 5), label, 32, fill=GRAY, anchor='lm', black=False); y += 60
    if value: put(card, (70, y + 10), value, 60, fill=YEL, anchor='lm', maxw=930)
    if value2: put(card, (W - 70, y + 10), value2, 34, fill=YEL, anchor='rm')
    if alpha < 0.999: card.putalpha(card.split()[3].point(lambda v: int(v*alpha)))
    b.alpha_composite(card, (0, 0))

def caption(b, t, t0, line1, line2=None, y=1560):
    """下の字幕。1行目=白、2行目=黄色（強調）"""
    a = fade(t, t0, 0.25)
    put(b, (W//2, y), line1, 58, stroke=7, alpha=a, maxw=1000)
    if line2: put(b, (W//2, y + 80), line2, 58, fill=YEL, stroke=7, alpha=fade(t, t0 + 0.15, 0.25), maxw=1000)

def ending(b, t, t0, head='でも、安心して。', sub=None, big=None, note=None):
    put(b, (W//2, 330), head, 80, stroke=7, scale=pop(t, t0))
    if sub: put(b, (W//2, 460), sub, 52, alpha=fade(t, t0 + 0.5), maxw=1000)
    if big: put(b, (W//2, 560), big, 90, fill=YEL, stroke=7, scale=pop(t, t0 + 0.9))
    if note: put(b, (W//2, 1720), note, 30, fill=GRAY, black=False, alpha=fade(t, t0 + 1.4), maxw=1000)

def flash(b, t, t0, d=0.12):
    k = (t - t0)/d
    if 0 <= k < 1: b.alpha_composite(Image.new('RGBA', (W, H), (255, 255, 255, int(170*(1 - k)))))

# ---------- sound ----------
SR = 44100
def tone(f, dur, vol, decay, harm=0.3):
    tt = np.arange(int(dur*SR))/SR
    return vol*(np.sin(2*np.pi*f*tt) + harm*np.sin(4*np.pi*f*tt))*np.exp(-tt*decay)
def whoosh(dur=0.3, vol=0.5, seed=1):
    n = np.convolve(np.random.default_rng(seed).standard_normal(int(dur*SR)), np.ones(20)/20, 'same')
    return vol*n*np.sin(np.linspace(0, np.pi, len(n)))**2
def pop_sfx(): return tone(880, 0.25, 0.3, 12) + np.pad(tone(1320, 0.15, 0.2, 15), (0, int(0.1*SR)))
def ding(): return tone(1046, 0.8, 0.3, 4) + tone(1568, 0.8, 0.18, 4)
def boom(): return tone(70, 0.7, 0.8, 5, 0.1) + whoosh(0.7, 0.6, 3)

def bgm(total, bpm=96, mood='mystery'):
    beat = 60/bpm
    if mood == 'bright': chords = [(261.63, 329.63, 392.0), (220.0, 261.63, 329.63), (174.61, 220.0, 261.63), (196.0, 246.94, 293.66)]
    else: chords = [(220.0, 261.63, 329.63), (174.61, 220.0, 261.63), (196.0, 246.94, 293.66), (164.81, 207.65, 246.94)]
    bar = beat*4; loop = np.zeros(int(bar*4*SR) + SR)
    for ci, ch in enumerate(chords):
        base = ci*bar
        bb = tone(ch[0]/2, bar, 0.35, 1.2, 0.1); s = int(base*SR); loop[s:s+len(bb)] += bb
        for k, ix in enumerate([0, 1, 2, 1, 0, 2, 1, 2]):
            n = tone(ch[ix]*2, beat*1.5, 0.16, 4.0, 0.2); s = int((base + k*beat/2)*SR); loop[s:s+len(n)] += n
    L = int(bar*4*SR); out = np.zeros(int(total*SR))
    for s in range(0, len(out), L):
        seg = loop[:min(len(loop), len(out) - s)]; out[s:s+len(seg)] += seg
    return out*0.28

def render(out, total, frame_fn, events=(), mood='mystery'):
    """frame_fn(t)->RGBA画像。events=[(秒, 波形), ...]"""
    tmp = out + '.tmp.mp4'; wav = out + '.tmp.wav'
    p = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                          '-c:v', 'libx264', '-crf', '20', '-preset', 'veryfast', '-pix_fmt', 'yuv420p', tmp], stdin=subprocess.PIPE)
    for i in range(int(round(total*FPS))):
        p.stdin.write(frame_fn(i/FPS).convert('RGB').tobytes())
    p.stdin.close(); assert p.wait() == 0
    a = bgm(total, mood=mood)
    for t, sig in events:
        s = int(t*SR); e = min(len(a), s + len(sig)); a[s:e] += sig[:e - s]
    fl = int(1.2*SR); a[-fl:] *= np.linspace(1, 0, fl)
    with wave.open(wav, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(a, -1, 1)*30000).astype(np.int16).tobytes())
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', tmp, '-i', wav, '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k',
                    '-shortest', '-movflags', '+faststart', out], check=True)
    os.remove(tmp); os.remove(wav)
    print('done', out)
