"""ロング動画のサムネ（1280x720）を作る
使い方：python3 gen/thumb.py thumb.json out.png
thumb.json：{"tag":"第2弾 全問わかる？","line1":"推理クイズ","line2":"20問",
             "band1":"全問正解で","band2":"名探偵","emoji":"🕵️","glow":[255,210,60],"bg":[70,52,10]}
"""
import sys, json
CFG=json.load(open(sys.argv[1], encoding='utf-8'))
import numpy as np, math
from PIL import Image, ImageDraw, ImageFont, ImageFilter
W,H=1280,720
FB='/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc'
EMO=ImageFont.truetype('/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf',109)
def F(s): return ImageFont.truetype(FB,s,index=0)
def emoji(ch,size):
    im=Image.new('RGBA',(140,140),(0,0,0,0)); ImageDraw.Draw(im).text((6,6),ch,font=EMO,embedded_color=True)
    im=im.crop(im.getbbox()); s=size/max(im.size)
    return im.resize((int(im.width*s),int(im.height*s)),Image.LANCZOS)
# background: dark with yellow spotlight on right
y,x=np.mgrid[0:H,0:W]
r=np.sqrt(((x-960)/700)**2+((y-380)/520)**2)
k=np.clip(r,0,1)[...,None]
img=np.array(CFG.get('bg',[70,52,10]))*(1-k)+np.array([10,12,28])*k
bg=Image.fromarray(img.astype(np.uint8)).convert('RGBA')
d=ImageDraw.Draw(bg)
# scattered question marks
rng=np.random.default_rng(3)
for _ in range(14):
    qx,qy=rng.integers(0,W),rng.integers(0,H); s=int(rng.integers(50,120))
    q=Image.new('RGBA',(s*2,s*2),(0,0,0,0)); ImageDraw.Draw(q).text((s//2,0),'?',font=F(s),fill=(255,255,255,28))
    q=q.rotate(int(rng.integers(-30,30)),expand=True); bg.alpha_composite(q,(int(qx)-s,int(qy)-s))
# detective
det=emoji(CFG.get('emoji','🕵️'),400)
glow=Image.new('RGBA',(W,H),(0,0,0,0)); ImageDraw.Draw(glow).ellipse([700,110,1240,650],fill=tuple(CFG.get('glow',[255,210,60]))+(90,))
bg.alpha_composite(glow.filter(ImageFilter.GaussianBlur(60)))
bg.alpha_composite(det,(1250-det.width,H-det.height-20))
def txt(xy,s,size,fill,stroke=14,sf=(0,0,0),rot=0):
    f=F(size); bb=f.getbbox(s,stroke_width=stroke)
    t=Image.new('RGBA',(bb[2]+40,bb[3]+40),(0,0,0,0))
    ImageDraw.Draw(t).text((20,20),s,font=f,fill=fill,stroke_width=stroke,stroke_fill=sf)
    if rot: t=t.rotate(rot,expand=True,resample=Image.BICUBIC)
    sh=Image.new('RGBA',t.size,(0,0,0,0)); sh.putalpha(t.split()[3].point(lambda v:int(v*0.6)))
    bg.alpha_composite(sh.filter(ImageFilter.GaussianBlur(8)),(xy[0]+8,xy[1]+10)); bg.alpha_composite(t,xy)
# top tag
d=ImageDraw.Draw(bg)
tag=CFG.get('tag','全問わかる？'); tw=int(F(56).getlength(tag))
d.polygon([(40,40),(tw+110,40),(tw+85,120),(40,120)],fill=(230,40,50))
txt((50,28),tag,56,(255,255,255),stroke=0)
txt((28,120),CFG.get('line1','推理クイズ'),150 if len(CFG.get('line1','推理クイズ'))<=5 else int(150*5/len(CFG.get('line1'))) ,(255,226,40),stroke=16,rot=2)
txt((40,285),CFG.get('line2','20問'),180,(255,255,255),stroke=18,sf=(0,0,0),rot=2)
# bottom band
band=Image.new('RGBA',(740,130),(0,0,0,0)); bd=ImageDraw.Draw(band)
bd.rounded_rectangle([0,0,739,129],24,fill=(255,255,255))
bg.alpha_composite(band.rotate(2,expand=True,resample=Image.BICUBIC),(30,545))
txt((50,545),CFG.get('band1','全問正解で'),72,(20,20,30),stroke=0,rot=2)
txt((60+int(F(72).getlength(CFG.get('band1','全問正解で'))),535),CFG.get('band2','名探偵'),90,(230,40,50),stroke=0,rot=2)
bg.convert('RGB').save(sys.argv[2])
