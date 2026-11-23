import sys, os, math, subprocess, wave, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import json
CFG = json.load(open(sys.argv[1], encoding='utf-8'))
PUZZLES = CFG['items']
VOL = 0
OUTFILE = sys.argv[2]

W, H, FPS = 1920, 1080, 30
OUT = os.path.abspath(os.environ.get('WORKDIR', '/tmp/longwork')); os.makedirs(OUT, exist_ok=True)
FB = '/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc'
FBo = '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'
EMO = ImageFont.truetype('/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf', 109)
_fc = {}
def F(size, black=True):
    k = (size, black)
    if k not in _fc: _fc[k] = ImageFont.truetype(FB if black else FBo, size, index=0)
    return _fc[k]

GOLD = (245, 196, 66); WHITE = (245, 245, 250); RED = (230, 60, 60); YEL = (255, 226, 60); GRAYT = (170, 175, 195)
THINK = float(CFG.get('think', 20))

# ---------- background ----------
def make_bg():
    y, x = np.mgrid[0:H, 0:W]
    r = np.sqrt(((x - W/2)/W)**2 + ((y - H/2)/H)**2)
    base = np.array([18, 22, 44]); edge = np.array([6, 7, 16])
    k = np.clip(r/0.75, 0, 1)[..., None]
    img = base*(1-k) + edge*k
    im = Image.fromarray(img.astype(np.uint8))
    d = ImageDraw.Draw(im)
    for i in range(0, W, 80):  # faint grid
        d.line([(i, 0), (i, H)], fill=(255, 255, 255), width=1)
    for j in range(0, H, 80):
        d.line([(0, j), (W, j)], fill=(255, 255, 255), width=1)
    im = Image.blend(Image.fromarray(img.astype(np.uint8)), im, 0.035)
    return im.convert('RGBA')
BG = make_bg()

def emoji(ch, size):
    im = Image.new('RGBA', (140, 140), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((6, 6), ch, font=EMO, embedded_color=True)
    im = im.crop(im.getbbox())
    s = size / max(im.size)
    return im.resize((int(im.width*s), int(im.height*s)), Image.LANCZOS)

def clock_icon(size, hour_deg=90, mirror_label=True):
    S = size*2
    im = Image.new('RGBA', (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    c = S//2; R = S//2 - 20
    # mirror frame
    d.rounded_rectangle([0, 0, S-1, S-1], 60, fill=(120, 170, 210, 255))
    d.rounded_rectangle([18, 18, S-19, S-19], 48, fill=(200, 230, 250, 255))
    R = int(R*0.78)
    d.ellipse([c-R, c-R, c+R, c+R], fill=(255, 255, 255, 255), outline=(40, 40, 60, 255), width=14)
    for i in range(12):
        a = math.radians(i*30)
        r1, r2 = R*0.80, R*0.92
        d.line([(c+r1*math.sin(a), c-r1*math.cos(a)), (c+r2*math.sin(a), c-r2*math.cos(a))], fill=(40, 40, 60, 255), width=10 if i % 3 == 0 else 5)
    a = math.radians(hour_deg)
    d.line([(c, c), (c+R*0.5*math.sin(a), c-R*0.5*math.cos(a))], fill=(30, 30, 40, 255), width=26)
    d.line([(c, c), (c, c-R*0.78)], fill=(30, 30, 40, 255), width=14)
    d.ellipse([c-22, c-22, c+22, c+22], fill=(220, 50, 50, 255))
    return im.resize((size, size), Image.LANCZOS)

def icon_for(p, size=380):
    if p['icon'] == 'CLOCK': return clock_icon(size)
    return emoji(p['icon'], size)

def ease_back(t):
    t = min(max(t, 0), 1); c = 1.7
    return 1 + (c+1)*(t-1)**3 + c*(t-1)**2

def put_text(base, xy, text, size, maxw=None, fill=WHITE, anchor='la', stroke=0, sf=(0, 0, 0), black=True, alpha=1.0, scale=1.0):
    if maxw:
        while size > 20 and F(size, black).getlength(text) > maxw: size -= 2
    if alpha >= 0.999 and abs(scale-1) < 1e-3:
        ImageDraw.Draw(base).text(xy, text, font=F(size, black), fill=fill, anchor=anchor, stroke_width=stroke, stroke_fill=sf)
        return
    f = F(size, black)
    bb = f.getbbox(text, anchor='la', stroke_width=stroke)
    w, h = bb[2]+stroke*2+8, bb[3]+stroke*2+8
    tmp = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(tmp).text((stroke+4, stroke+4), text, font=f, fill=fill, stroke_width=stroke, stroke_fill=sf)
    if abs(scale-1) > 1e-3:
        tmp = tmp.resize((max(1, int(w*scale)), max(1, int(h*scale))), Image.LANCZOS)
    if alpha < 0.999:
        tmp.putalpha(tmp.split()[3].point(lambda v: int(v*alpha)))
    x, y = xy
    if anchor[0] == 'm': x -= tmp.width//2
    if anchor[1] == 'm': y -= tmp.height//2
    base.alpha_composite(tmp, (int(x), int(y)))

def header(b, n, p, a=1.0):
    d = ImageDraw.Draw(b)
    d.rectangle([0, 0, W, 130], fill=(10, 12, 26, 255))
    d.line([(0, 130), (W, 130)], fill=GOLD, width=4)
    d.rounded_rectangle([60, 28, 290, 104], 14, fill=GOLD)
    put_text(b, (175, 66), f'第{n}問', 50, fill=(20, 20, 30), anchor='mm')
    put_text(b, (320, 66), p['title'], 54, maxw=1150, anchor='lm')
    stars = '★'*p['stars'] + '☆'*(4-p['stars'])
    put_text(b, (1580, 66), '難易度', 34, fill=GRAYT, anchor='rm', black=False)
    put_text(b, (1600, 66), stars, 52, fill=GOLD, anchor='lm')

# ---------- timeline per puzzle ----------
TITLE = 3.0
def line_dur(s): return 0.9 + len(s)*0.13
def plan(p):
    t = TITLE; q_times = []
    for s in p['q']:
        q_times.append(t); t += line_dur(s)
    ask_t = t; t += 2.0
    think_t = t; t += THINK
    drum_t = t; t += 1.6
    ans_t = t; t += 1.8
    exp_times = []
    for s in p['exp']:
        exp_times.append(t); t += line_dur(s) + 0.4
    t += 2.5
    return dict(q=q_times, ask=ask_t, think=think_t, drum=drum_t, ans=ans_t, exp=exp_times, end=t)

def pop(t, t0, d=0.22): return ease_back((t - t0)/d)

def draw_puzzle(n, p, pl, t, icon):
    b = BG.copy()
    if t < TITLE:  # title card
        d = ImageDraw.Draw(b)
        k = pop(t, 0.05, 0.3)
        put_text(b, (W//2, 380), f'第{n}問', 150, fill=GOLD, anchor='mm', scale=max(k, 0.01), stroke=6, sf=(0, 0, 0))
        if t > 0.5:
            put_text(b, (W//2, 560), p['title'], 96, anchor='mm', scale=max(pop(t, 0.5, 0.3), 0.01))
        if t > 1.0:
            stars = '★'*p['stars'] + '☆'*(4-p['stars'])
            put_text(b, (W//2, 700), '難易度  ' + stars, 60, fill=GOLD, anchor='mm', alpha=min((t-1.0)/0.4, 1))
        return b
    header(b, n, p)
    if t < pl['drum']:
        # question screen
        b.alpha_composite(icon, (110 + (400-icon.width)//2, 250 + (400-icon.height)//2))
        y = 210
        for i, s in enumerate(p['q']):
            if t >= pl['q'][i]:
                a = min((t - pl['q'][i])/0.25, 1)
                col = (190, 225, 255) if ('「' in s[:3] or s.startswith('　')) else WHITE
                put_text(b, (600, y + int((1-a)*20)), s, 54, maxw=1240, fill=col, alpha=a)
            y += 92
        if t >= pl['ask']:
            k = pop(t, pl['ask'])
            d = ImageDraw.Draw(b)
            put_text(b, (W//2+200, 800), 'Q. ' + p['ask'], 72, maxw=1240, fill=YEL, anchor='mm', scale=max(k, 0.01), stroke=4)
        if t >= pl['think']:
            left = THINK - (t - pl['think'])
            # hint after half
            if left <= THINK/2:
                a = min((THINK/2 - left)/0.3, 1)
                d = ImageDraw.Draw(b)
                put_text(b, (W//2+200, 905), 'ヒント：' + p['hint'], 46, maxw=1240, fill=(150, 240, 170), anchor='mm', alpha=a)
            d = ImageDraw.Draw(b)
            frac = max(left, 0)/THINK
            d.rounded_rectangle([110, 1000, W-110, 1030], 15, fill=(45, 50, 75, 255))
            col = GOLD if left > 3 else RED
            d.rounded_rectangle([110, 1000, 110 + max(int((W-220)*frac), 30), 1030], 15, fill=col)
            sec = int(math.ceil(left)) if left > 0 else 0
            # circular timer near icon
            cx, cy, R = 310, 790, 110
            d.ellipse([cx-R, cy-R, cx+R, cy+R], fill=(30, 34, 60, 255))
            d.pieslice([cx-R, cy-R, cx+R, cy+R], -90, -90 + 360*frac, fill=col)
            d.ellipse([cx-R+18, cy-R+18, cx+R-18, cy+R-18], fill=(18, 22, 44, 255))
            fs = 100 if left - math.floor(left) < 0.85 or sec <= 0 else 112
            put_text(b, (cx, cy), str(sec), fs, fill=WHITE if left > 3 else RED, anchor='mm')
            put_text(b, (cx, cy + R + 40), '考えてみよう', 34, fill=GRAYT, anchor='mm', black=False)
        return b
    # answer
    if t < pl['ans']:
        k = (t - pl['drum'])/1.6
        dots = '．' * (1 + int(k*3) % 3 + (1 if k > 0.66 else 0))
        put_text(b, (W//2, 540), '正解は' + dots[:3], 110, anchor='mm')
        return b
    d = ImageDraw.Draw(b)
    k = pop(t, pl['ans'], 0.28)
    d.rounded_rectangle([110, 190, 330, 300], 18, fill=RED)
    put_text(b, (220, 245), '答え', 64, anchor='mm')
    put_text(b, (W//2 + 110, 360), p['ans'], 104, maxw=1600, fill=YEL, anchor='mm', scale=max(k, 0.01), stroke=6)
    d.line([(160, 470), (W-160, 470)], fill=(80, 86, 120), width=3)
    put_text(b, (160, 510), '解説', 40, fill=GOLD)
    y = 580
    for i, s in enumerate(p['exp']):
        if t >= pl['exp'][i]:
            a = min((t - pl['exp'][i])/0.3, 1)
            put_text(b, (200, y), s, 54, maxw=1600, alpha=a)
        y += 96
    return b

# ---------- intro / outro ----------
INTRO = 9.0
def draw_intro(t):
    b = BG.copy()
    icon = emoji(CFG.get('intro_icon', '🕵️'), 300)
    b.alpha_composite(icon, (W//2 - icon.width//2, 120 + int(10*math.sin(t*2))))
    if t > 0.2: put_text(b, (W//2, 540), CFG['series'], 150, maxw=1700, fill=GOLD, anchor='mm', scale=max(pop(t, 0.2, 0.3), .01), stroke=8)
    if t > 0.9: put_text(b, (W//2, 690), CFG.get('subtitle', '全%d問' % len(PUZZLES)), 96, maxw=1700, anchor='mm', scale=max(pop(t, 0.9, 0.3), .01), stroke=5)
    if t > 2.0: put_text(b, (W//2, 830), CFG.get('tagline', '全問正解できたら天才！'), 60, maxw=1700, fill=YEL, anchor='mm', alpha=min((t-2.0)/0.4, 1))
    if t > 4.5: put_text(b, (W//2, 940), '考える時間は各%d秒。むずかしい時は一時停止してOK！' % int(THINK), 42, fill=GRAYT, anchor='mm', black=False, alpha=min((t-4.5)/0.4, 1))
    return b

OUTRO = 10.0
def draw_outro(t):
    b = BG.copy()
    put_text(b, (W//2, 330), 'おつかれさま！', 120, fill=GOLD, anchor='mm', scale=max(pop(t, 0.1, 0.3), .01), stroke=6)
    if t > 1.0: put_text(b, (W//2, 520), '%d問中、何問わかった？' % len(PUZZLES), 80, anchor='mm', alpha=min((t-1)/0.4, 1))
    if t > 2.2: put_text(b, (W//2, 650), 'コメントで教えてね！', 80, fill=YEL, anchor='mm', scale=max(pop(t, 2.2, 0.3), .01))
    if t > 3.6:
        a = min((t-3.6)/0.4, 1)
        put_text(b, (W//2, 820), '面白かったら 高評価 と チャンネル登録 をよろしく！', 50, fill=GRAYT, anchor='mm', black=False, alpha=a)
    return b

# ---------- render ----------
def encode(name, dur, fn):
    tmp = os.path.join(OUT, f'_{name}.tmp.mp4'); fin = os.path.join(OUT, f'{name}.mp4')
    p = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
        '-c:v', 'libx264', '-crf', '20', '-preset', 'veryfast', '-pix_fmt', 'yuv420p', '-r', str(FPS), tmp], stdin=subprocess.PIPE)
    n = int(round(dur*FPS))
    last_key, last = None, None
    for i in range(n):
        t = i/FPS
        im = fn(t)
        p.stdin.write(im.convert('RGB').tobytes())
    p.stdin.close()
    if p.wait() == 0: os.rename(tmp, fin)
    else: sys.exit('ffmpeg failed ' + name)

def plans():
    return [plan(p) for p in PUZZLES]

# ---------- audio ----------
SR = 44100
def _tone(f, dur, vol, decay, harm=0.3):
    t = np.arange(int(dur*SR))/SR
    return vol*(np.sin(2*np.pi*f*t) + harm*np.sin(4*np.pi*f*t))*np.exp(-t*decay)
def _noise(dur, vol, smooth=20, seed=0):
    t = np.arange(int(dur*SR))/SR
    n = np.convolve(np.random.default_rng(seed).standard_normal(len(t)), np.ones(smooth)/smooth, 'same')
    return vol*n
def bgm(total):
    bpm = 84; beat = 60/bpm
    chords = [(220.0, 261.63, 329.63), (174.61, 220.0, 261.63), (130.81, 164.81, 196.0), (164.81, 207.65, 246.94)]  # Am F C E
    bar = beat*4; loop = np.zeros(int(bar*4*SR) + SR)
    for ci, ch in enumerate(chords):
        base = ci*bar
        b = _tone(ch[0]/2, bar, 0.35, 1.2, 0.1); s = int(base*SR); loop[s:s+len(b)] += b
        pat = [0, 1, 2, 1, 0, 2, 1, 2]
        for k, ix in enumerate(pat):
            n = _tone(ch[ix]*2, beat*1.5, 0.18, 4.0, 0.2); s = int((base + k*beat/2)*SR); loop[s:s+len(n)] += n
    L = int(bar*4*SR)
    out = np.zeros(int(total*SR))
    for s in range(0, len(out), L):
        seg = loop[:min(len(loop), len(out)-s)]; out[s:s+len(seg)] += seg
    return out*0.35
def build_audio():
    pls = [plan(p) for p in PUZZLES]
    total = INTRO + sum(pl['end'] for pl in pls) + OUTRO
    a = bgm(total)
    def add(t, sig):
        s = int(t*SR); e = min(len(a), s+len(sig)); a[s:e] += sig[:e-s]
    add(0.2, _tone(523, 0.4, 0.35, 8)); add(0.9, _tone(784, 0.5, 0.35, 6)); add(2.0, _tone(1046, 0.8, 0.3, 4))
    t0 = INTRO
    for pl in pls:
        add(t0 + 0.0, _noise(0.35, 0.6, seed=1)*np.sin(np.linspace(0, np.pi, int(0.35*SR)))**2)
        add(t0 + 0.05, _tone(659, 0.5, 0.35, 6)); add(t0 + 0.5, _tone(988, 0.6, 0.3, 6))
        for qt in pl['q']: add(t0 + qt, _tone(1400, 0.05, 0.12, 80))
        add(t0 + pl['ask'], _tone(880, 0.3, 0.3, 9)); add(t0 + pl['ask'] + 0.12, _tone(1175, 0.4, 0.3, 8))
        for s in range(1, int(THINK)):
            left = THINK - s
            add(t0 + pl['think'] + s, _tone(1500 if left <= 3 else 1000, 0.06, 0.22 if left <= 3 else 0.14, 60))
        dur = pl['ans'] - pl['drum']
        roll = _noise(dur, 0.9, smooth=6, seed=2)*(0.3 + 0.7*np.linspace(0, 1, int(dur*SR)))*(0.6 + 0.4*np.sign(np.sin(2*np.pi*22*np.arange(int(dur*SR))/SR)))
        add(t0 + pl['drum'], roll*0.5)
        for f in (523.25, 659.25, 783.99, 1046.5): add(t0 + pl['ans'], _tone(f, 1.4, 0.22, 2.5))
        t0 += pl['end']
    add(t0 + 0.1, _tone(784, 0.4, 0.3, 6)); add(t0 + 0.4, _tone(1046, 0.8, 0.3, 4))
    # fade out end
    fl = int(2.5*SR); a[-fl:] *= np.linspace(1, 0, fl)
    a = np.clip(a, -1, 1)
    with wave.open(os.path.join(OUT, 'audio.wav'), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((a*30000).astype(np.int16).tobytes())

def assemble():
    names = ['p00.mp4'] + [f'p{n:02d}.mp4' for n in range(1, len(PUZZLES)+1)] + ['p99.mp4']
    lst = os.path.join(OUT, 'list.txt')
    with open(lst, 'w') as f:
        for n in names: f.write(f"file '{os.path.join(OUT, n)}'\n")
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy', os.path.join(OUT, 'video.mp4')], check=True)
    build_audio()
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', os.path.join(OUT, 'video.mp4'), '-i', os.path.join(OUT, 'audio.wav'), '-map', '0:v', '-map', '1:a',
                    '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k', '-shortest', '-movflags', '+faststart', OUTFILE], check=True)

if __name__ == '__main__':
    encode('p00', INTRO, draw_intro)
    for n, p in enumerate(PUZZLES, 1):
        pl = plan(p); ic = icon_for(p)
        encode(f'p{n:02d}', pl['end'], lambda t: draw_puzzle(n, p, pl, t, ic))
    encode('p99', OUTRO, draw_outro)
    assemble()
    print('done', OUTFILE)
