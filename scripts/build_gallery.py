#!/usr/bin/env python3
"""Render the twelve demonstration templates and two composition examples."""
import argparse
import json
from pathlib import Path
from render import load_spec, export

ORDER=['architecture','comparison','trajectory','text_card','taxonomy','proportion','bar','line','matrix','scatter','distribution','radar','multipanel','multipanel_28']
ROOT=Path(__file__).resolve().parents[1]

def make_atlas(target):
    """Contact sheet for reviewing coverage; use individual files to inspect details."""
    from PIL import Image, ImageDraw, ImageFont
    sheet = Image.new('RGB', (1800, 1640), '#eef2f6')
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default(size=22)
    for i, name in enumerate(ORDER[:12]):
        x, y = (i % 3) * 600, (i // 3) * 410
        draw.rounded_rectangle((x+10, y+10, x+590, y+400), radius=10, fill='white')
        draw.text((x+24, y+20), f'{i+1:02d}  {name}', fill='#172d45', font=font)
        with Image.open(target/f'{name}.png') as source:
            thumb = source.convert('RGB')
            thumb.thumbnail((550, 335), Image.Resampling.LANCZOS)
            sheet.paste(thumb, (x+(600-thumb.width)//2, y+58+(335-thumb.height)//2))
    sheet.save(target/'atlas.png')

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',default=str(ROOT/'output/gallery'))
    ap.add_argument('--formats',default='svg,png,pdf')
    args=ap.parse_args()
    target=Path(args.out)
    target.mkdir(parents=True,exist_ok=True)
    report=[]
    for name in ORDER:
        path=ROOT/'assets/templates'/f'{name}.json'
        meta=export(load_spec(path),target/name,tuple(args.formats.split(',')),scale=1.5)
        report.append({'template':name,'type':meta['type'],'files':meta['outputs']})
        print(f'{name}: rendered',flush=True)
    (target/'manifest.json').write_text(json.dumps(report,indent=2))
    lines=['# Template gallery','','All values, cases and interface sketches below are illustrative. Every figure is generated from an editable JSON specification.','']
    for name in ORDER:
        lines.extend([f'## {name}',f'![{name}]({name}.png)',f'[Editable SVG]({name}.svg) · [PDF]({name}.pdf)',''])
    (target/'GALLERY.md').write_text('\n'.join(lines))
    if 'png' in args.formats.split(','):
        make_atlas(target)

if __name__=='__main__':main()
