import json, os, re, subprocess, urllib.request
from pathlib import Path
from PIL import Image
from ocrmac import ocrmac
BASE=Path('data/improve_details'); OUT=Path('data/improve_ocr'); OUT.mkdir(exist_ok=True)
for p in sorted(BASE.glob('*.json')):
    d=json.loads(p.read_text()); n=d['data']['note']; pid=p.stem
    imgs=(n.get('imageList') or [])
    texts=[]
    for i,im in enumerate(imgs):
        url=im.get('urlDefault') or im.get('urlPre') or ''
        if not url: continue
        raw=OUT/f'{pid}_{i}.raw'; jpg=OUT/f'{pid}_{i}.jpg'
        try:
            req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
            with urllib.request.urlopen(req,timeout=40) as r: data=r.read()
            raw.write_bytes(data)
        except Exception as e:
            print('dl err',pid,i,e); continue
        subprocess.run(['sips','-s','format','jpeg',str(raw),'--out',str(jpg)],capture_output=True)
        raw.unlink(missing_ok=True)
        if not jpg.exists(): continue
        im=Image.open(jpg).convert('RGB')
        variants={'orig':im,'rot180':im.rotate(180),'flip_h':im.transpose(Image.FLIP_LEFT_RIGHT),'flip_v':im.transpose(Image.FLIP_TOP_BOTTOM)}
        for name,v in variants.items():
            vp=OUT/f'{pid}_{i}_{name}.jpg'; v.save(vp,quality=90)
            try:
                anns=ocrmac.OCR(str(vp),language_preference=['zh-Hans','en-US']).recognize()
                txt='\n'.join(a[0] for a in anns)
            except Exception: txt=''
            texts.append(f'--- img{i} {name} ---\n{txt}')
    alltxt='\n'.join(texts)
    (OUT/f'{pid}.txt').write_text(alltxt)
    emails=sorted(set(re.findall(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}',alltxt)))
    print(pid,n['title'][:35],'imgs',len(imgs),'emails',emails)
