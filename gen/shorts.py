import sys, os, math, subprocess, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
FB = '/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc'
FBo = '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'
EMO = ImageFont.truetype('/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf', 109)
_fc = {}
def F(size, black=True):
    k = (size, black)
    if k not in _fc: _fc[k] = ImageFont.truetype(FB if black else FBo, size, index=0)
    return _fc[k]
GOLD = (245, 196, 66); WHITE = (245, 245, 250); RED = (230, 60, 60); YEL = (255, 226, 60); GRAYT = (170, 175, 195); BLUE = (190, 225, 255)

def make_bg(c1, c2):
    y, x = np.mgrid[0:H, 0:W]
    r = np.sqrt(((x - W/2)/W)**2 + ((y - H*0.45)/H)**2)
    k = np.clip(r/0.8, 0, 1)[..., None]
    return Image.fromarray((np.array(c1)*(1-k) + np.array(c2)*k).astype(np.uint8)).convert('RGBA')

def emoji(ch, size):
    im = Image.new('RGBA', (140, 140), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((6, 6), ch, font=EMO, embedded_color=True)
    im = im.crop(im.getbbox()); s = size/max(im.size)
    return im.resize((int(im.width*s), int(im.height*s)), Image.LANCZOS)

def ease_back(t):
    t = min(max(t, 0), 1); c = 1.7
    return 1 + (c+1)*(t-1)**3 + c*(t-1)**2

def put(base, xy, text, size, fill=WHITE, anchor='mm', stroke=0, sf=(0, 0, 0), black=True, alpha=1.0, scale=1.0, maxw=980):
    while size > 20 and F(size, black).getlength(text) > maxw: size -= 2
    f = F(size, black)
    bb = f.getbbox(text, stroke_width=stroke)
    w, h = bb[2]+stroke*2+10, bb[3]+stroke*2+10
    tmp = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(tmp).text((stroke+5, stroke+5), text, font=f, fill=fill, stroke_width=stroke, stroke_fill=sf)
    if abs(scale-1) > 1e-3:
        tmp = tmp.resize((max(1, int(w*scale)), max(1, int(h*scale))), Image.LANCZOS)
    if alpha < 0.999:
        tmp.putalpha(tmp.split()[3].point(lambda v: int(v*alpha)))
    x, y = xy
    if anchor[0] == 'm': x -= tmp.width//2
    if anchor[1] == 'm': y -= tmp.height//2
    base.alpha_composite(tmp, (int(x), int(y)))

def pop(t, t0, d=0.22): return max(ease_back((t-t0)/d), 0.01)
def fade(t, t0, d=0.3): return min(max((t-t0)/d, 0), 1)

SR = 44100
def tone(f, dur, vol, decay, harm=0.3):
    t = np.arange(int(dur*SR))/SR
    return vol*(np.sin(2*np.pi*f*t) + harm*np.sin(4*np.pi*f*t))*np.exp(-t*decay)
def noise(dur, vol, smooth=20, seed=0):
    n = np.convolve(np.random.default_rng(seed).standard_normal(int(dur*SR)), np.ones(smooth)/smooth, 'same')
    return vol*n

def bgm(total, bpm=100):
    beat = 60/bpm
    chords = [(220.0, 261.63, 329.63), (174.61, 220.0, 261.63), (196.0, 246.94, 293.66), (164.81, 207.65, 246.94)]
    bar = beat*4; loop = np.zeros(int(bar*4*SR) + SR)
    for ci, ch in enumerate(chords):
        base = ci*bar
        b = tone(ch[0]/2, bar, 0.35, 1.2, 0.1); s = int(base*SR); loop[s:s+len(b)] += b
        for k, ix in enumerate([0, 1, 2, 1, 0, 2, 1, 2]):
            n = tone(ch[ix]*2, beat*1.5, 0.18, 4.0, 0.2); s = int((base + k*beat/2)*SR); loop[s:s+len(n)] += n
    L = int(bar*4*SR); out = np.zeros(int(total*SR))
    for s in range(0, len(out), L):
        seg = loop[:min(len(loop), len(out)-s)]; out[s:s+len(seg)] += seg
    return out*0.3

def write_video(name, dur, fn, events):
    tmp = f'{name}.tmp.mp4'
    p = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
        '-c:v', 'libx264', '-crf', '20', '-preset', 'veryfast', '-pix_fmt', 'yuv420p', tmp], stdin=subprocess.PIPE)
    for i in range(int(round(dur*FPS))):
        p.stdin.write(fn(i/FPS).convert('RGB').tobytes())
    p.stdin.close(); assert p.wait() == 0
    a = bgm(dur)
    for t, sig in events:
        s = int(t*SR); e = min(len(a), s+len(sig)); a[s:e] += sig[:e-s]
    fl = int(1.0*SR); a[-fl:] *= np.linspace(1, 0, fl)
    with wave.open(f'{name}.tmp.wav', 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(a, -1, 1)*30000).astype(np.int16).tobytes())
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', tmp, '-i', f'{name}.tmp.wav', '-map', '0:v', '-map', '1:a', '-c:v', 'copy',
                    '-c:a', 'aac', '-b:a', '160k', '-shortest', '-movflags', '+faststart', f'{name}.mp4'], check=True)

# ================= 推理ショート =================
SUIRI = [
 dict(name='推理ショート1_消えたへそくり', hook=['このウソ、', '見抜ける？'], icon='📕',
      q=['おばあちゃんの1万円札が消えた。', '孫のユウタはこう言った。',
         '「本の87ページと', '　88ページの間に', '　はさんでおいたのに', '　なくなってたんだ」'],
      ask='ユウタのウソはどこ？', ans=['87と88ページの間には', 'はさめない！'],
      exp=['87ページと88ページは', '同じ1枚の紙の「表」と「裏」。', '間にお札は はさめない。']),
 dict(name='推理ショート2_ウソつきは1人', hook=['この中に', 'ウソつきが1人'], icon='🕵️',
      q=['犯人だけがウソをつく。', 'ほかの2人は本当のことを言う。',
         'A「犯人はBだ」', 'B「ぼくは犯人じゃない」', 'C「Aはウソをついている」'],
      ask='犯人はだれ？', ans=['犯人は A！'],
      exp=['Bが犯人だと、CもウソつきになってNG。', 'Cが犯人だと、AもウソつきになってNG。', 'Aが犯人のときだけ全部合う！']),
]
THINK_S = 7.0
def suiri(d):
    bg = make_bg((28, 30, 70), (6, 7, 20)); ic = emoji(d.get('icon', '❓'), 300)
    T_HOOK = 2.6
    qt = []; t = T_HOOK + 0.4
    for s in d['q']: qt.append(t); t += 0.6 + len(s)*0.10
    ask_t = t + 0.3; think_t = ask_t + 1.5; ans_t = think_t + THINK_S + 0.3
    exp_t = [ans_t + 1.6 + i*2.2 for i in range(len(d['exp']))]
    end_t = exp_t[-1] + 2.8; total = end_t + 3.2
    def fr(t):
        b = bg.copy(); dd = ImageDraw.Draw(b)
        if t < T_HOOK:
            put(b, (W//2, 300), d.get('label', 'クイズ'), 70, fill=GOLD, alpha=fade(t, 0, 0.2))
            for i, s in enumerate(d['hook']):
                if t > 0.15 + i*0.35: put(b, (W//2, 700 + i*190), s, 150, fill=YEL if i else WHITE, stroke=10, scale=pop(t, 0.15 + i*0.35))
            b.alpha_composite(ic, (W//2 - ic.width//2, 1150))
            return b
        if t >= end_t:
            put(b, (W//2, 700), d.get('end1', 'もっと解きたい人は'), 70, alpha=fade(t, end_t))
            put(b, (W//2, 840), d.get('end2', 'チャンネルのロング動画で！'), 76, fill=YEL, scale=pop(t, end_t + 0.3))
            put(b, (W//2, 1050), 'フォローしてね', 60, fill=GRAYT, alpha=fade(t, end_t + 0.8))
            return b
        dd.rectangle([0, 0, W, 170], fill=(10, 12, 26, 255)); dd.line([(0, 170), (W, 170)], fill=GOLD, width=5)
        put(b, (W//2, 88), d['hook'][0] + d['hook'][1], 64, fill=YEL)
        if t < ans_t:
            sm = ic.resize((180, int(180*ic.height/ic.width)))
            b.alpha_composite(sm, (W//2 - sm.width//2, 220))
            y = 500
            for i, s in enumerate(d['q']):
                if t >= qt[i]: put(b, (W//2, y), s, 62, fill=BLUE if s.startswith(('「', '　')) or '「' in s[:2] else WHITE, alpha=fade(t, qt[i], 0.2))
                y += 100
            if t >= ask_t: put(b, (W//2, y + 60), 'Q. ' + d['ask'], 76, fill=YEL, stroke=5, scale=pop(t, ask_t))
            if t >= think_t:
                left = max(THINK_S - (t - think_t), 0); frac = left/THINK_S
                cx, cy, R = W//2, 1620, 130
                col = GOLD if left > 3 else RED
                dd.ellipse([cx-R, cy-R, cx+R, cy+R], fill=(30, 34, 60, 255))
                dd.pieslice([cx-R, cy-R, cx+R, cy+R], -90, -90 + 360*frac, fill=col)
                dd.ellipse([cx-R+20, cy-R+20, cx+R-20, cy+R-20], fill=(18, 22, 44, 255))
                put(b, (cx, cy), str(math.ceil(left)) if left > 0 else '0', 120, fill=WHITE if left > 3 else RED)
            return b
        dd.rounded_rectangle([W//2-130, 260, W//2+130, 370], 20, fill=RED)
        put(b, (W//2, 315), '答え', 70)
        for i, s in enumerate(d['ans']):
            put(b, (W//2, 520 + i*140), s, 110, fill=YEL, stroke=7, scale=pop(t, ans_t + i*0.15, 0.28))
        y = 520 + len(d['ans'])*140 + 120
        dd.line([(90, y-60), (W-90, y-60)], fill=(80, 86, 120), width=3)
        for i, s in enumerate(d['exp']):
            if t >= exp_t[i]: put(b, (W//2, y), s, 58, alpha=fade(t, exp_t[i]))
            y += 110
        return b
    ev = [(0.15, tone(880, 0.3, 0.35, 9)), (0.5, tone(1175, 0.4, 0.35, 8)), (ask_t, tone(988, 0.4, 0.3, 8))]
    ev += [(x, tone(1400, 0.05, 0.12, 80)) for x in qt]
    ev += [(think_t + s, tone(1500 if THINK_S - s <= 3 else 1000, 0.06, 0.2, 60)) for s in range(1, int(THINK_S))]
    ev += [(ans_t, tone(f, 1.3, 0.22, 2.5)) for f in (523.25, 659.25, 783.99, 1046.5)]
    ev += [(end_t, tone(784, 0.4, 0.3, 6))]
    write_video(d['name'], total, fr, ev)

# ================= 雑学ショート =================
ZATSU = [
 dict(name='雑学ショート1_動物のびっくり雑学5選', hook=['動物の', 'びっくり雑学'], sub='知ってたらすごい！5選', color=((20, 70, 60), (5, 20, 18)),
      facts=[('🐙', 'タコの心臓は', '3つある', '体に血を送る心臓が1つ、エラ用が2つ。'),
             ('🦒', 'キリンの首の骨は', '人間と同じ7個', 'あんなに長いのに、骨の数は同じ。'),
             ('🐋', 'シャチは', 'イルカの仲間', '分類では、マイルカ科のいちばん大きな種類。'),
             ('🦦', 'ラッコは寝るとき', '手をつなぐことがある', '流されて離ればなれにならないように。'),
             ('🐌', 'カタツムリには', '1万本以上の歯がある種類も', '「歯舌」というヤスリのような歯で食べる。')]),
 dict(name='雑学ショート2_宇宙と人体のびっくり雑学5選', hook=['宇宙と人体の', 'びっくり雑学'], sub='知ってたらすごい！5選', color=((50, 25, 80), (10, 5, 22)),
      facts=[('🪐', '金星は1日が', '1年より長い', '自転に約243日、公転は約225日。'),
             ('⚡', '雷は', '太陽の表面より熱い', '雷は約3万度、太陽の表面は約6000度。'),
             ('👶', '赤ちゃんの骨は', '大人より多い', '約300個→成長でくっついて約206個に。'),
             ('🏔️', 'エベレストは今も', '少しずつ高くなっている', '大陸をのせたプレートが押し合っているから。'),
             ('🚀', '宇宙に行くと', '身長が少し伸びる', '重力がなく、背骨の間がのびるため。')]),
]
FACT = 6.6
def zatsu(d):
    bg = make_bg(d['color'][0], d['color'][1])
    icons = [emoji(f[0], 340) for f in d['facts']]
    T_HOOK = 2.6; t0s = [T_HOOK + i*FACT for i in range(5)]
    end_t = T_HOOK + 5*FACT; total = end_t + 3.5
    def fr(t):
        b = bg.copy(); dd = ImageDraw.Draw(b)
        if t < T_HOOK:
            for i, s in enumerate(d['hook']):
                if t > 0.1 + i*0.35: put(b, (W//2, 650 + i*190), s, 140, fill=YEL if i else WHITE, stroke=10, scale=pop(t, 0.1 + i*0.35))
            if t > 0.9: put(b, (W//2, 1080), d['sub'], 76, fill=GOLD, alpha=fade(t, 0.9))
            return b
        if t >= end_t:
            put(b, (W//2, 760), 'いくつ知ってた？', 100, fill=YEL, stroke=6, scale=pop(t, end_t))
            put(b, (W//2, 920), 'コメントで教えてね！', 72, alpha=fade(t, end_t + 0.5))
            put(b, (W//2, 1080), 'フォローで毎日雑学', 56, fill=GRAYT, alpha=fade(t, end_t + 1.0))
            return b
        i = min(int((t - T_HOOK)//FACT), 4); tt = t - t0s[i]; f = d['facts'][i]
        dd.rectangle([0, 0, W, 170], fill=(0, 0, 0, 120));
        put(b, (W//2, 88), d['hook'][0] + d['hook'][1], 60, fill=WHITE)
        # progress dots
        for k in range(5):
            x = W//2 - 160 + k*80
            dd.ellipse([x-16, 220-16, x+16, 220+16], fill=YEL if k <= i else (90, 90, 110))
        put(b, (W//2, 380), f'その{i+1}', 90, fill=GOLD, scale=pop(tt, 0.0))
        ic = icons[i]; s = pop(tt, 0.1, 0.3)
        sc = ic.resize((max(1, int(ic.width*s)), max(1, int(ic.height*s))))
        b.alpha_composite(sc, (W//2 - sc.width//2, 700 - sc.height//2))
        put(b, (W//2, 1010), f[1], 76, alpha=fade(tt, 0.4))
        if tt > 1.2: put(b, (W//2, 1150), f[2], 104, fill=YEL, stroke=7, scale=pop(tt, 1.2, 0.28))
        if tt > 2.6: put(b, (W//2, 1340), f[3], 50, fill=WHITE, black=False, alpha=fade(tt, 2.6), maxw=960)
        return b
    ev = [(0.1, tone(880, 0.3, 0.35, 9)), (0.45, tone(1175, 0.4, 0.35, 8))]
    for x in t0s:
        ev += [(x, noise(0.25, 0.5, seed=1)*np.sin(np.linspace(0, np.pi, int(0.25*SR)))**2), (x + 1.2, tone(1046, 0.5, 0.3, 6)), (x + 1.32, tone(1318, 0.6, 0.25, 6))]
    ev += [(end_t, tone(784, 0.4, 0.3, 6)), (end_t + 0.3, tone(1046, 0.8, 0.3, 4))]
    write_video(d['name'], total, fr, ev)

if __name__ == '__main__':
    import json
    d = json.load(open(sys.argv[1], encoding='utf-8'))
    out = sys.argv[2]
    d['name'] = out[:-4] if out.endswith('.mp4') else out
    if d['type'] == 'quiz': suiri(d)
    elif d['type'] == 'facts':
        d.setdefault('color', [[20, 70, 60], [5, 20, 18]])
        zatsu(d)
    for ext in ('.tmp.mp4', '.tmp.wav'):
        try: os.remove(d['name'] + ext)
        except OSError: pass
    print('done', out)
