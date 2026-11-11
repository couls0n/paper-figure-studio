"""Paper-informed execution evidence: temporal columns or an annotated run.

The screenshot is evidence; callouts and explanatory type stay editable. Source
papers inform the layout, never supply undisclosed example pixels or observations.
"""
from __future__ import annotations

import base64
import json
import math
import re
from pathlib import Path
import pymupdf

from schematics import SVG, esc, _image_data, _required_list

INK = '#171717'
MUTED = '#575757'
RULE = '#707070'
RED = '#BA2C29'
GREEN = '#217541'
BLUE = '#E6F5FA'
PURPLE = '#F0EAF4'
GRAY = '#F3F3F2'


class TraceCanvas(SVG):
    def __init__(self, spec):
        adapted = {**spec, 'style': {'font_size': 14, 'font_family': 'serif', 'mono_font_family': 'monospace', **spec.get('style', {})}}
        super().__init__(adapted)
        # Match the exporter's standard font metrics at fractional sizes. This
        # keeps highlighted spans flush instead of shifting or overlapping them.
        self.measure_fonts={k:pymupdf.Font(fontname=v) for k,v in [('serif','tiro'),('sans-serif','helv'),('mono','cour')]}
        self.typ.width=lambda text,size=None,mono=False:self.measure_fonts['mono' if mono else ('sans-serif' if self.typ.family=='sans-serif' else 'serif')].text_length(str(text),fontsize=size or self.typ.size)
        self.show_title = bool(spec.get('style', {}).get('show_title', False))
        self.content_top = 42 if self.title and self.show_title else 18
        self.title_lines = []

    def text(self, x, y, text, size=None, color=None, weight=None, mono=False, anchor='start', spans=None):
        return super().text(x, y, text, size, color or INK, weight, mono, anchor, spans)

    def finish(self, needed):
        needed = math.ceil(needed + (33 if self.illustrative else 18))
        if self.requested_height is not None and self.requested_height < needed:
            raise ValueError(f'height={self.requested_height} is too small; paper trace needs {needed} px')
        height = max(needed, self.requested_height or 0)
        header = ''
        if self.show_title and self.title:
            header = f'<text x="20" y="26" font-family="serif" font-size="18" font-weight="bold" fill="{INK}">{esc(self.title)}</text>'
        footer = f'<text x="20" y="{height-10}" font-family="sans-serif" font-size="10" fill="{MUTED}">ILLUSTRATIVE TRACE — schematic interfaces and example events, not recorded evidence</text>' if self.illustrative else ''
        return f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{self.width:g}" height="{height:g}" viewBox="0 0 {self.width:g} {height:g}"><title>{esc(self.title)}</title><rect width="100%" height="100%" fill="white"/>'+header+''.join(self.items)+footer+'</svg>'


def _spans(text, highlights):
    ranges=[]
    for h in highlights or []:
        if not isinstance(h, dict) or not isinstance(h.get('text'), str):
            raise ValueError('highlights contain {text, color?} objects')
        token=h['text']; start=text.find(token)
        if token and start >= 0:
            ranges.append((start,start+len(token),h.get('color',RED)))
    if not ranges:return None
    bounds=sorted({0,len(text),*[x for a,b,c in ranges for x in (a,b)]})
    return [(text[a:b], next((c for x,y,c in ranges if x<=a and b<=y),INK)) for a,b in zip(bounds,bounds[1:])]


def _lines(svg, text, width, size=13, mono=False):
    """Wrap at lexical boundaries without dropping indentation or source chars.

    This is display wrapping, not source reformatting: joining each original
    line's fragments recovers the same characters, including boundary spaces.
    CJK punctuation stays with the preceding glyph, and ordinary Latin words
    only fall back to character splitting when the token itself is too wide.
    """
    measure=lambda value:svg.typ.width(value,size,mono)
    if width<measure('MMMM'):
        raise ValueError('Text area is too narrow; increase canvas width')
    closing=set('.,;:!?，。！？；：、)]}〉》」』】%％”’\"\'')
    opening=set('([{〈《「『【“‘')
    def word(ch):return ch.isascii() and (ch.isalnum() or ch=='_')
    output=[]
    for original in str(text).split('\n'):
        remaining=original
        if not remaining:output.append('');continue
        while remaining:
            if measure(remaining)<=width:
                output.append(remaining);break
            lo,hi=1,len(remaining)
            while lo<hi:
                mid=(lo+hi+1)//2
                if measure(remaining[:mid])<=width:lo=mid
                else:hi=mid-1
            limit=lo
            candidates=[]
            for index in range(1,limit+1):
                before,after=remaining[index-1],remaining[index]
                if not remaining[:index].strip():continue
                # Never strand a closing mark, end on an opening mark, or cut
                # a word just because the rendering happens to be monospace.
                if after in closing or before in opening:continue
                if word(before) and word(after):continue
                candidates.append(index)
            if candidates:
                cut=candidates[-1]
            else:
                cut=limit  # A long unspaced identifier genuinely needs splitting.
                while cut>1 and remaining[cut] in closing:cut-=1
            output.append(remaining[:cut]);remaining=remaining[cut:]
    return output


def _draw_lines(svg, lines, x, y, size=13, mono=False, highlights=None, line_height=None, color=None):
    lead=line_height or size*1.32
    joined=''.join(lines);ranges=[]
    for h in highlights or []:
        token=h.get('text','')
        if not token:continue
        start=0
        while (start:=joined.find(token,start))>=0:
            ranges.append((start,start+len(token),h.get('color',RED)));start+=len(token)
    offset=0
    for index,line in enumerate(lines):
        local=[(max(0,a-offset),min(len(line),b-offset),c) for a,b,c in ranges if a<offset+len(line) and b>offset]
        spans=None
        if local:
            bounds=sorted({0,len(line),*[v for a,b,c in local for v in (a,b)]})
            spans=[(line[a:b],next((c for s,e,c in local if s<=a and b<=e),color or INK)) for a,b in zip(bounds,bounds[1:])]
        svg.text(x,y+size+index*lead,line,size,color,mono=mono,spans=spans)
        offset+=len(line)
    return len(lines)*lead


def _info(spec,step):
    if not isinstance(step.get('action'),str) or not step['action'].strip():
        raise ValueError('Every trajectory step needs a non-empty action')
    if bool(step.get('image')) == bool(step.get('illustration')):
        raise ValueError('Each trajectory step needs exactly one real image or explicitly labeled illustration')
    if step.get('image'):
        return _image_data(Path(spec.get('_base_dir','.'))/step['image'])
    if not isinstance(step['illustration'],dict):
        raise ValueError('illustration must be an object')
    aspect=step['illustration'].get('aspect_ratio',1.55)
    if isinstance(aspect,bool) or not isinstance(aspect,(int,float)) or not math.isfinite(aspect) or aspect <= 0:
        raise ValueError('illustration.aspect_ratio must be finite and positive')
    return None


def _image_height(step,info,width):
    return width * (info[3]/info[2] if info else 1/step['illustration'].get('aspect_ratio',1.55))


def _screenshot(svg,step,info,x,y,width,height):
    svg.items.append(f'<g data-role="screenshot" data-step="{esc(step["id"])}" data-source-width="{info[2] if info else width}" data-source-height="{info[3] if info else height}">')
    if info:
        mime,blob,_,_=info;href='data:'+mime+';base64,'+base64.b64encode(blob).decode()
        svg.items.append(f'<image x="{x}" y="{y}" width="{width}" height="{height}" preserveAspectRatio="xMidYMid meet" href="{href}" xlink:href="{href}"/>')
    else:
        # Deliberately schematic UI with a persistent visible disclosure.
        old_family=svg.typ.family
        svg.typ.family='sans-serif'
        ill=step['illustration'];unit=width/360
        svg.rect(x,y,width,height,'white','#B7B7B7',r=0)
        svg.rect(x,y,width,24*unit,'#E4E8ED','#B7B7B7',r=0)
        svg.text(x+9*unit,y+16*unit,'ILLUSTRATIVE UI  /  '+ill.get('app','Project workspace'),10*unit,'#515761',mono=False)
        svg.rect(x,y+24*unit,42*unit,height-24*unit,'#EFF1F4','none',r=0)
        for k in range(5):
            svg.rect(x+10*unit,y+(41+24*k)*unit,21*unit,5*unit,'#BBC5D1','none',r=1)
        left=x+53*unit;bodyw=width-66*unit
        title=ill.get('label','Review change request')
        title_lines=_lines(svg,title,bodyw,13*unit)
        ty=y+38*unit
        ty+=_draw_lines(svg,title_lines,left,ty,13*unit)
        svg.line(left,ty+9*unit,x+width-12*unit,ty+9*unit,'#CCD1D8',1)
        svg.text(left,ty+27*unit,ill.get('subtitle','Overview    Activity    Changes'),9*unit,'#58616E')
        cy=ty+41*unit
        body=ill.get('lines',['Ready for review','No message submitted'])
        max_bottom=y+height-33*unit
        for line in body:
            wrapped=_lines(svg,line,bodyw-14*unit,10*unit)
            row_h=max(23*unit,len(wrapped)*13.2*unit+9*unit)
            if cy+row_h>max_bottom:
                raise ValueError('Illustrative screenshot content exceeds its aspect ratio; use a taller aspect_ratio or shorter UI text')
            svg.rect(left,cy,bodyw,row_h,'#FAFBFC','#D7DCE2',r=1)
            _draw_lines(svg,wrapped,left+7*unit,cy+3*unit,10*unit,highlights=ill.get('highlights'))
            cy+=row_h+7*unit
        button=ill.get('button','Save draft')
        svg.rect(left,y+height-24*unit,78*unit,16*unit,'#3478B8','none',r=1)
        svg.text(left+39*unit,y+height-12*unit,button,8*unit,'white',anchor='middle')
        svg.typ.family=old_family
    for idx,c in enumerate(step.get('callouts',[]),1):
        vals=[c.get(k) for k in ('x','y','width','height')]
        if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in vals):
            raise ValueError('callouts use finite normalized x/y/width/height in [0,1]')
        cx,cy,cw,ch=vals
        if cx<0 or cy<0 or cw<=0 or ch<=0 or cx+cw>1 or cy+ch>1:
            raise ValueError('callout bbox lies outside the image')
        bx,by,bw,bh=x+cx*width,y+cy*height,cw*width,ch*height
        svg.rect(bx,by,bw,bh,'none',c.get('color',RED),r=0,stroke_width=1.5,data_role='callout',data_step=step['id'])
        number=str(c.get('id',idx))
        label_w=max(14,svg.typ.width(number,10)+6)
        lx=min(bx,x+width-label_w);ly=max(y,by-14)
        svg.rect(lx,ly,label_w,14,'white',c.get('color',RED),r=0)
        svg.text(lx+label_w/2,ly+10,number,10,c.get('color',RED),weight=700,anchor='middle')
    svg.items.append('</g>')


def _step_text(step):
    parts=[]
    if step.get('observation'):parts.append(('Observation',step['observation']))
    if step.get('thought'):parts.append(('Thought',step['thought']))
    parts.append(('Action',step['action']))
    return '\n'.join(f'{name}: {value}' for name,value in parts)


def _notes(step):
    parts=[]
    if step.get('note'):parts.append(str(step['note']))
    elif step.get('decision'):parts.append(str(step['decision']))
    for i,c in enumerate(step.get('callouts',[]),1):
        if c.get('label'):parts.append(f'[{c.get("id",i)}] {c["label"]}')
    return ' '.join(parts)


def _top_context(svg,data,x,y,w):
    task=str(data.get('task',data.get('shared_input','')))
    context=str(data.get('context',''))
    if not task and not context:return y
    left_w=w*.32 if context else w
    llines=_lines(svg,task,left_w-24,14)
    rlines=_lines(svg,context,w-left_w-24,13) if context else []
    height=max(len(llines)*18.48+37,len(rlines)*17.16+37)
    svg.text(x+10,y+18,'user_instruction:',12,mono=True)
    _draw_lines(svg,llines,x+10,y+25,14)
    if context:
        svg.line(x+left_w,y+8,x+left_w,y+height-6,RULE,1)
        svg.text(x+left_w+11,y+18,'user_data:',12,mono=True)
        _draw_lines(svg,rlines,x+left_w+11,y+25,13,highlights=data.get('context_highlights'))
    return y+height+8


def _evidence_columns(spec,svg,steps,infos):
    data=spec['data'];cols=data.get('columns',min(3,len(steps)))
    if isinstance(cols,bool) or not isinstance(cols,int) or not 1<=cols<=len(steps):
        raise ValueError('trajectory columns must be an integer between 1 and the number of steps')
    outer_x=20;outer_y=svg.content_top;outer_w=svg.width-40
    x=outer_x+8;w=outer_w-16;colw=w/cols
    if colw<250:raise ValueError('paper evidence columns need at least 250 px each')
    # Content is drawn after the background geometry has been calculated.
    content_start=len(svg.items)
    y=_top_context(svg,data,x,outer_y+4,w)
    svg.line(x,y,x+w,y,INK,1)
    trace_label=data.get('trace_label','EXECUTION TRACE: OBSERVATIONS, ACTIONS, AND ENVIRONMENT STATES')
    label_lines=_lines(svg,trace_label,w-20,13)
    y+=5;label_h=_draw_lines(svg,label_lines,x+10,y,13)
    y+=label_h+8
    for start in range(0,len(steps),cols):
        batch=steps[start:start+cols]
        prepared=[]
        for j,step in enumerate(batch):
            iw=colw-20;ih=_image_height(step,infos[start+j],iw)
            trace=_lines(svg,_step_text(step),colw-20,11.4,True)
            notes=_lines(svg,_notes(step),colw-20,13) if _notes(step) else []
            prepared.append((trace,notes,iw,ih))
        trace_h=max(len(p[0])*15.05 for p in prepared)+14
        image_h=max(p[3] for p in prepared)
        note_h=max((len(p[1])*17.16 for p in prepared),default=0)+18
        svg.line(x,y,x+w,y,INK,1)
        for j,step in enumerate(batch):
            cx=x+j*colw
            svg.text(cx+colw/2,y+19,step.get('time',step.get('title',step['id'])),14,anchor='middle')
        svg.line(x,y+27,x+w,y+27,INK,1)
        body_y=y+34;iy=body_y+trace_h
        note_y=iy+image_h+12
        bottom=note_y+note_h
        for j,step in enumerate(batch):
            cx=x+j*colw;trace,notes,iw,ih=prepared[j]
            svg.items.append(f'<g data-role="trace-step" data-step="{esc(step["id"])}">')
            _draw_lines(svg,trace,cx+10,body_y,11.4,True,step.get('highlights'),15.05)
            _screenshot(svg,step,infos[start+j],cx+10,iy,iw,ih)
            _draw_lines(svg,notes,cx+10,note_y+3,13,highlights=step.get('note_highlights'))
            if j>0:svg.line(cx,y+4,cx,bottom-2,INK,.8)
            svg.items.append('</g>')
        svg.line(x,note_y-2,x+w,note_y-2,INK,.8)
        y=bottom+12
    content=svg.items[content_start:];del svg.items[content_start:]
    svg.rect(outer_x,outer_y,outer_w,y-outer_y,GRAY,'#4B4B4B',r=7,stroke_width=1.8)
    svg.items.extend(content)
    return svg.finish(y)


def _json_panel(svg,x,y,w,label,value,color,step_id=None):
    text=json.dumps(value,ensure_ascii=False,indent=2) if not isinstance(value,str) else value
    lines=_lines(svg,text,w-24,11.2,True)
    h=40+len(lines)*14.8
    attrs=f'data-role="trace-annotation" data-step="{esc(step_id)}"' if step_id is not None else 'data-role="task-configuration"'
    svg.items.append(f'<g {attrs} data-top="{y}" data-bottom="{y+h}">')
    svg.rect(x,y,w,h,color,'none',r=3)
    svg.text(x+10,y+19,label,12,weight=700)
    highlights=[]
    for match in re.finditer(r'"[^"\n]*"(?=\s*:)|"[^"\n]*"|\b(?:true|false|null)\b',text):
        tail=text[match.end():].lstrip()
        highlights.append({'text':match.group(),'color':RED if tail.startswith(':') else GREEN})
    _draw_lines(svg,lines,x+12,y+28,11.2,True,highlights,14.8)
    svg.items.append('</g>')
    return y+h+12


def _role(svg,x,y,label,color):
    # Simple original silhouette, no emoji or borrowed brand artwork.
    if label=='Env':
        svg.rect(x,y,23,17,'white',color,r=1,stroke_width=1.2)
        svg.line(x+7,y+20,x+16,y+20,color,1.2)
        svg.line(x+11.5,y+17,x+11.5,y+20,color,1.2)
    else:
        svg.rect(x+2,y+2,20,16,'white',color,r=3,stroke_width=1.2)
        svg.rect(x+6,y+7,3,3,color,'none',r=0)
        svg.rect(x+16,y+7,3,3,color,'none',r=0)
        svg.line(x+11.5,y-2,x+11.5,y+2,color,1.2)
    svg.text(x+12,y+32,label,10,color,anchor='middle')


def _annotated_run(spec,svg,steps,infos):
    data=spec['data'];x=20;y=svg.content_top;totalw=svg.width-40
    sidebar=data.get('annotation_fraction',.29)
    if not isinstance(sidebar,(int,float)) or not .22<=sidebar<=.42:
        raise ValueError('annotation_fraction must be between .22 and .42')
    sidew=totalw*sidebar;leftw=totalw-sidew-16;sidex=x+leftw+16
    if leftw<500 or sidew<225:raise ValueError('annotated_run needs a wider canvas (at least 1050 px recommended)')
    start=len(svg.items)
    task=str(data.get('task',data.get('shared_input','Run the supplied task.')))
    tasklines=_lines(svg,'Instruction: '+task,leftw-34,14)
    taskh=20+len(tasklines)*18.48
    svg.rect(x+9,y+9,leftw-18,taskh,BLUE,'none',r=0)
    _draw_lines(svg,tasklines,x+17,y+16,14)
    sidey=y+9
    if data.get('task_config') is not None:
        sidey=_json_panel(svg,sidex+8,sidey,sidew-16,'task_config',data['task_config'],BLUE)
    annotations_present=any(s.get('annotation') is not None for s in steps) or data.get('annotation') is not None
    if not annotations_present and data.get('task_config') is None:
        raise ValueError('annotated_run requires task_config, annotation, or a per-step annotation')
    # A shared step origin makes each verdict unambiguously refer to its own
    # environment/agent turn. The taller of the two sides controls the next row.
    cy=max(y+taskh+30,sidey)
    for i,step in enumerate(steps):
        step_start=len(svg.items)
        svg.items.append('')
        _role(svg,x+10,cy+6,'Env','#AA5C55')
        ix=x+49; iw=(leftw-70)*.50; ih=_image_height(step,infos[i],iw)
        svg.text(ix,cy+14,step.get('time',step.get('title',step['id'])),13,weight=700)
        _screenshot(svg,step,infos[i],ix,cy+22,iw,ih)
        obsx=ix+iw+15;obsw=x+leftw-15-obsx
        obs=_lines(svg,'Observation: '+str(step.get('observation','See the environment state.')),obsw,12)
        _draw_lines(svg,obs,obsx,cy+24,12,highlights=step.get('highlights'))
        if step.get('note'):
            ny=cy+33+len(obs)*15.84
            _draw_lines(svg,_lines(svg,step['note'],obsw,12),obsx,ny,12,highlights=step.get('note_highlights'))
        obs_bottom=cy+50+(len(obs)+len(_lines(svg,step.get('note',''),obsw,12)))*15.84
        by=max(cy+ih+35,obs_bottom)
        agenttext=('Thought: '+step['thought']+'\n' if step.get('thought') else '')+'Action: '+step['action']
        agentlines=_lines(svg,agenttext,leftw-98,12.2,True)
        bh=20+len(agentlines)*16.1
        svg.rect(x+49,by,leftw-94,bh,'#E2F0DF','none',r=1)
        _draw_lines(svg,agentlines,x+59,by+8,12.2,True,step.get('highlights'),16.1)
        _role(svg,x+leftw-33,by+8,'Agent',GREEN)
        svg.items.append('</g>')
        if step.get('annotation') is not None:
            sidey=_json_panel(svg,sidex+8,cy,sidew-16,'annotation · '+step['id'],step['annotation'],PURPLE,step['id'])
        row_bottom=max(by+bh,sidey-12 if step.get('annotation') is not None else by+bh)
        svg.items[step_start]=f'<g data-role="trace-step" data-step="{esc(step["id"])}" data-top="{cy}" data-bottom="{row_bottom}">'
        cy=row_bottom+22
    if data.get('annotation') is not None:
        sidey=_json_panel(svg,sidex+8,cy,sidew-16,'annotation · run',data['annotation'],PURPLE,'run')
    bottom=max(cy,sidey)
    content=svg.items[start:];del svg.items[start:]
    svg.rect(x,y,leftw,bottom-y,GRAY,'none',r=7)
    svg.rect(sidex,y,sidew,bottom-y,GRAY,'none',r=7)
    svg.items.extend(content)
    return svg.finish(bottom)


def render(spec):
    if spec.get('type')!='trajectory':raise ValueError('paper_trace only renders trajectory specifications')
    data=spec.get('data',{});steps=_required_list(data,'steps')
    ids=[str(s.get('id',f't{i+1}')) for i,s in enumerate(steps)]
    if len(set(ids))!=len(ids):raise ValueError('trajectory step IDs must be unique')
    steps=[{**s,'id':sid} for s,sid in zip(steps,ids)]
    infos=[_info(spec,s) for s in steps]
    svg=TraceCanvas(spec)
    variant=data.get('variant','evidence_columns')
    if variant=='evidence_columns':return _evidence_columns(spec,svg,steps,infos)
    if variant=='annotated_run':return _annotated_run(spec,svg,steps,infos)
    raise ValueError('paper_trace variant must be evidence_columns or annotated_run')
