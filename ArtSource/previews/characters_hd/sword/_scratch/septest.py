import sys, os, json
sys.path.insert(0, r'C:\Users\imjun\SevenOaths\ArtSource\src\characters_hd')
sys.argv=['x']
import numpy as np
from PIL import Image
import sword_hd as S, hqA
D=S.D
frames=json.load(open(os.path.join(D,'kp_test.json')))
cache=S._rig_poses()
to=lambda f: np.array(__import__('px').to_rgba(f))
sc=Image.open(os.path.join(D,'_scratch','scene.png')).convert('RGBA')
wall=sc.crop((150,214,294,310))
ims=[]
for t,i in [('draw',0),('draw',1),('draw',2),('sheathe',3),('idle',0)]:
    f=[f for f in frames if f['tag']==t and f['i']==i][0]
    a=hqA.snap(hqA.load(os.path.join(D,'raw',f'{t}_{i}.png')))
    kpd={k['label']:(k['x']*144,k['y']*96) for k in f['kp']}
    a[S.deghost(a,kpd)]=0
    old=hqA.load(os.path.join(hqA.D,f'{t}_{i}.png'))
    dy=int(np.where(old[...,3]>0)[0].max())-int(np.where(a[...,3]>0)[0].max())
    a=np.roll(a,dy,0)
    poses,lay=cache[t]; q=poses[i]
    if t=='idle':
        import heroine as A; q=A.sheathed_hands(A.P(**A.IDLE_BASE))
    img=S.compose(a,q)
    fx=to(lay['fx'][i]); o=fx[...,3]>0; img[o]=fx[o]
    before=Image.open(os.path.join(D,f'{t}_{i}.png')).convert('RGBA')
    for im in [before, Image.fromarray(img)]:
        for bg in [(96,96,108,255),None]:
            c=Image.new('RGBA',(144,96),bg) if bg else wall.copy(); c.alpha_composite(im)
            ims.append(c.crop((14,34,104,96)).resize((90*4,62*4),Image.NEAREST))
cols=4
W=cols*(360+6); H=(len(ims)//cols)*(248+6)
sh=Image.new('RGB',(W,H),(0,0,0))
for k,im in enumerate(ims): sh.paste(im,((k%cols)*366,(k//cols)*254))
sh.save(os.path.join(D,'_scratch','sep_test.png'))
