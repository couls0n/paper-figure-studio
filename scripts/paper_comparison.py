"""Source-informed paired case figures, with editable dialogue and local differences.

Two layouts preserve the same semantic columns: paired_dialogue (TAI3 Fig. 1)
and scenario_rows (BadAgent Fig. 1). Artwork and demonstration text are original.
"""
from __future__ import annotations

from copy import deepcopy
from schematics import SVG, Typography, esc, _required_list

INK = '#202020'
MUTED = '#636363'
USER = '#F0EEEB'
TOOL = '#E8F2F8'
GREEN = '#2E8B46'
RED = '#CE3439'
PURPLE = '#77609D'


class CaseTypography(Typography):
    """Use the same base-font metrics as the SVG→PDF exporter for rich spans."""
    def __init__(self, style):
        super().__init__(style)
        import pymupdf
        self._paper_fonts = [pymupdf.Font('helv'), pymupdf.Font('cour')]
        self.family = 'Helvetica, Arial, sans-serif'
        self.mono_family = 'Courier New, Courier, monospace'

    def width(self, text, size=None, mono=False):
        return self._paper_fonts[int(mono)].text_length(str(text), fontsize=size or self.size)


def _stroke(svg, d, color=INK, width=1.25, **attrs):
    extra=' '.join(f'{k.replace("_","-")}="{esc(v)}"' for k,v in attrs.items())
    svg.items.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}" {extra}/>')


def _icon(svg, x, y, kind, color=INK):
    """Tiny original vector role signs avoid platform-dependent emoji rendering."""
    svg.items.append(f'<g data-role="actor-icon" data-actor="{esc(kind)}">')
    if kind == 'user':
        svg.items.append(f'<circle cx="{x+12}" cy="{y+7}" r="5" fill="none" stroke="{color}" stroke-width="1.35"/>')
        _stroke(svg,f'M {x+2},{y+26} Q {x+2},{y+15} {x+12},{y+15} Q {x+22},{y+15} {x+22},{y+26} Z',color)
    elif kind == 'tool':
        svg.rect(x,y+4,25,20,'white',color,r=3,stroke_width=1.3)
        _stroke(svg,f'M {x+12.5},{y+4} V {y} M {x+5},{y+14} H {x+8} M {x+17},{y+14} H {x+20} M {x+8},{y+20} H {x+17}',color)
        _stroke(svg,f'M {x-3},{y+10} V {y+19} M {x+28},{y+10} V {y+19}',color)
    elif kind == 'web':
        svg.items.append(f'<circle cx="{x+12}" cy="{y+14}" r="11" fill="none" stroke="{color}" stroke-width="1.25"/>')
        _stroke(svg,f'M {x+1},{y+14} H {x+23} M {x+12},{y+3} C {x+4},{y+8} {x+4},{y+20} {x+12},{y+25} M {x+12},{y+3} C {x+20},{y+8} {x+20},{y+20} {x+12},{y+25}',color)
    else:
        svg.rect(x+1,y+2,22,25,'white',color,r=1,stroke_width=1.25)
        _stroke(svg,f'M {x+5},{y+9} H {x+19} M {x+5},{y+14} H {x+19} M {x+5},{y+19} H {x+15}',color)
    svg.items.append('</g>')


def _status(column):
    return GREEN if column.get('status') in {'safe','normal','success'} else RED if column.get('status') in {'unsafe','attack','blocked'} else MUTED


def _rich_lines(svg, text, width, size, mono, highlights):
    """Map full-text highlight ranges through wrapping, including split phrases."""
    lines=svg.typ.wrap(text,width,size,mono)
    expanded=str(text).expandtabs(4) if mono else str(text)
    ranges=[]
    for mark in highlights or []:
        value=mark.get('text','')
        if not value: continue
        start=0
        while True:
            pos=expanded.find(value,start)
            if pos < 0: break
            ranges.append((pos,pos+len(value),mark.get('color',RED)))
            start=pos+len(value)
    result=[];cursor=0
    for line in lines:
        pos=expanded.find(line,cursor) if line else cursor
        if pos<0: pos=cursor
        end=pos+len(line)
        bounds=sorted({pos,end,*[max(pos,min(end,p)) for a,b,_ in ranges for p in (a,b)]})
        spans=[(expanded[a:b],next((c for lo,hi,c in ranges if lo<=a and b<=hi),INK)) for a,b in zip(bounds,bounds[1:])]
        result.append((line,spans));cursor=end
    return result


def _event_kind(event):
    kind=event.get('kind')
    if kind is not None:
        if kind not in {'user','tool','text','outcome'}: raise ValueError('case event kind must be user, tool, text, or outcome')
        return kind
    role=str(event.get('role','')).lower()
    if any(x in role for x in ('user','request','用户','请求')): return 'user'
    if any(x in role for x in ('tool','action','调用','动作')): return 'tool'
    if any(x in role for x in ('outcome','result','结果')): return 'outcome'
    return 'text'


def _events(columns):
    ids=[]
    for col in columns:
        events=_required_list(col,'events')
        present=[]
        for i,event in enumerate(events):
            if not isinstance(event.get('text'),str): raise ValueError('Each comparison event needs text')
            key=event.get('id',str(i))
            if key in present: raise ValueError('event IDs must be unique within a condition')
            present.append(key)
            if key not in ids: ids.append(key)
    return ids,[{e.get('id',str(i)):e for i,e in enumerate(c['events'])} for c in columns]


def _bubble(svg, x, y, w, h, kind, lines, size, role, color, event_id, column_id):
    """A dialogue object, not an entire condition-colored card."""
    svg.items.append(f'<g data-role="case-event" data-event-id="{esc(event_id)}" data-column-id="{esc(column_id)}" data-kind="{kind}" data-x="{x}" data-y="{y}" data-width="{w}" data-height="{h}">')
    if kind=='outcome':
        svg.text(x+2,y+size+6,role,size=11,color=color,weight=700)
        xx=x+svg.typ.width(role,11)+13
        yy=y+6
        for line,spans in lines:
            svg.text(xx,yy+size,line,size,color,spans=[(t,color if c==INK else c) for t,c in spans]); yy+=size*1.28
    else:
        fill=USER if kind=='user' else TOOL if kind=='tool' else '#F5F5F5'
        left=kind!='tool';bx=x+34 if left else x;bw=w-34
        svg.rect(bx,y,bw,h,fill,'none',r=7)
        tail=f'{bx},{y+20} {bx-9},{y+28} {bx},{y+34}' if left else f'{bx+bw},{y+20} {bx+bw+9},{y+28} {bx+bw},{y+34}'
        svg.items.append(f'<polygon points="{tail}" fill="{fill}"/>')
        _icon(svg,x+1 if left else x+w-24,y+10,'user' if kind=='user' else 'tool' if kind=='tool' else 'document',MUTED)
        svg.text(bx+11,y+15,role,10.5,MUTED,700)
        yy=y+22
        for line,spans in lines:
            svg.text(bx+11,yy+size,line,size,mono=kind=='tool',spans=spans);yy+=size*1.3
    svg.items.append('</g>')


def _top(svg,data):
    y=22
    if data.get('shared_input'):
        lines=svg.typ.wrap(data['shared_input'],svg.width-66,14)
        svg.text(24,y+12,data.get('shared_label','Shared intent'),11,MUTED,700)
        y+=22
        for line in lines:
            svg.text(24,y+14,line,14,INK);y+=18
        y+=9
    return y


def _paired(svg,data,columns):
    n=len(columns);gap=44;left=24;w=(svg.width-2*left-gap*(n-1))/n
    if w<240: raise ValueError('paired dialogue needs at least 240 px per condition; widen the figure')
    y=_top(svg,data)
    if data.get('intervention'):
        label=str(data['intervention']);lw=svg.typ.width(label,12)+24
        if lw>svg.width-80: raise ValueError('Intervention label is too long; use a short phrase')
        svg.rect((svg.width-lw)/2,y,lw,24,'#F2EFF7','none',r=3)
        svg.text(svg.width/2,y+16,label,12,PURPLE,anchor='middle')
        # Broad shallow connector conveys the transformation between cases.
        x1=left+w*.60;x2=left+w+gap+w*.40
        _stroke(svg,f'M {x1},{y+35} Q {(x1+x2)/2},{y+2} {x2},{y+35}','#A8A8A8',1.7)
        svg.arrowhead(x2-16,y+28,x2,y+35,'#A8A8A8')
        y+=49
    title_lines=[svg.typ.wrap(c.get('title',c['id']),w-12,16) for c in columns]
    th=max(len(x) for x in title_lines)*21+10
    for j,lines in enumerate(title_lines):
        x=left+j*(w+gap)
        for k,line in enumerate(lines): svg.text(x+w/2,y+16+k*21,line,16,INK,700,anchor='middle')
    y+=th
    ids,maps=_events(columns);plans=[]
    for key in ids:
        cells=[]
        for ci,event_map in enumerate(maps):
            event=event_map.get(key)
            if event is None: cells.append(None);continue
            kind=_event_kind(event);size=14 if kind=='tool' else 15
            inner=w-56 if kind!='outcome' else w-svg.typ.width(event.get('role',kind.title()),11)-15
            lines=_rich_lines(svg,event['text'],inner,size,kind=='tool',event.get('highlights'))
            height=31+len(lines)*size*1.3 if kind!='outcome' else 12+len(lines)*size*1.28
            cells.append((event,kind,size,lines,height))
        plans.append((key,cells,max(c[-1] for c in cells if c)))
    panel_top=y-4
    for key,cells,h in plans:
        for j,cell in enumerate(cells):
            x=left+j*(w+gap)
            if cell is None:
                svg.text(x+w/2,y+20,'—',14,MUTED,anchor='middle');continue
            event,kind,size,lines,_=cell
            _bubble(svg,x,y,w,h,kind,lines,size,event.get('role',kind.title()),_status(columns[j]),key,columns[j]['id'])
        y+=h+12
    for j in range(n-1):
        xx=left+w+j*(w+gap)+gap/2
        svg.line(xx,panel_top,xx,y-14,'#B5B5B5',1,'2 4')
    return y-10


def _scenario_rows(svg,data,columns):
    """Compact rows hold user/agent evidence for the same scenario in each condition."""
    n=len(columns);left=24;gutter=26;scenario_w=96
    w=(svg.width-2*left-scenario_w-gutter*n)/n
    if w<240: raise ValueError('scenario rows need at least 240 px per condition; widen the figure')
    y=_top(svg,data);heads=[]
    for col in columns:heads.append(svg.typ.wrap(col.get('title',col['id']),w-8,16))
    hh=max(len(v) for v in heads)*21+12
    for j,lines in enumerate(heads):
        x=left+scenario_w+gutter+j*(w+gutter)
        for k,line in enumerate(lines):svg.text(x+w/2,y+17+k*21,line,16,INK,700,anchor='middle')
    y+=hh
    ids,maps=_events(columns)
    for row,key in enumerate(ids):
        cells=[]
        scenario=next(m[key].get('scenario',m[key].get('role',str(key))) for m in maps if key in m)
        for ci,m in enumerate(maps):
            e=m.get(key)
            if not e: cells.append(None);continue
            prompt=_rich_lines(svg,e.get('prompt',''),w-53,14,False,e.get('prompt_highlights')) if e.get('prompt') else []
            response=_rich_lines(svg,e['text'],w-53,14,bool(e.get('code')),e.get('highlights'))
            ph=18+len(prompt)*18.2 if prompt else 0
            rh=18+len(response)*18.2
            cells.append((e,prompt,response,ph,rh))
        h=max((c[3]+c[4]+22 if c[1] else c[4]+12) for c in cells if c)
        sx=left+34
        _icon(svg,sx,y+12,'web' if row%2 else 'document',MUTED)
        for k,line in enumerate(svg.typ.wrap(scenario,scenario_w-5,12)):
            svg.text(left+scenario_w/2,y+57+k*16,line,12,INK,anchor='middle')
        for j,c in enumerate(cells):
            x=left+scenario_w+gutter+j*(w+gutter)
            svg.items.append(f'<g data-role="case-event" data-event-id="{esc(key)}" data-column-id="{esc(columns[j]["id"])}" data-y="{y}" data-height="{h}">')
            if not c:
                svg.text(x+w/2,y+25,'—',14,MUTED,anchor='middle');svg.items.append('</g>');continue
            e,prompt,response,ph,rh=c
            fill=('#F8EBDD','#EBF0F4','#E8F2F8')[row%3]
            svg.rect(x,y,w,h,fill,'none',r=0)
            cy=y+7
            for role,lines,bh,kind in [('User',prompt,ph,'user'),('Agent',response,rh,'tool')]:
                if not lines: continue
                _icon(svg,x+8,cy+3,kind,MUTED)
                svg.rect(x+39,cy,w-46,bh,'none','#777777',r=4,stroke_width=.9)
                for k,(line,spans) in enumerate(lines):
                    svg.text(x+46,cy+15+k*18.2,line,14,mono=bool(e.get('code')) and role=='Agent',spans=spans)
                cy+=bh+7
            svg.items.append('</g>')
        y+=h+17
    if data.get('intervention'):
        svg.text(svg.width/2,y+10,str(data['intervention']),12,PURPLE,anchor='middle');y+=24
    return y


def render(spec):
    if spec.get('type')!='comparison':raise ValueError('paper comparison requires type=comparison')
    data=spec.get('data',{});columns=_required_list(data,'columns')
    if len(columns)<2:raise ValueError('comparison needs at least two columns')
    names=[c.get('id') for c in columns]
    if any(not isinstance(v,str) or not v for v in names) or len(set(names))!=len(names):raise ValueError('comparison conditions need unique non-empty IDs')
    # The paper figure's prose title belongs in its caption; SVG title remains
    # accessible metadata. An explicit show_title option adds a compact heading.
    clean=deepcopy(spec);clean['title']='';svg=SVG(clean);svg.title=str(spec.get('title',''))
    svg.typ=CaseTypography(spec.get('style',{}))
    variant=data.get('variant','paired_dialogue')
    if variant not in {'paired_dialogue','scenario_rows'}:raise ValueError('comparison variant must be paired_dialogue or scenario_rows')
    extent=_paired(svg,data,columns) if variant=='paired_dialogue' else _scenario_rows(svg,data,columns)
    return svg.finish(extent+6)
