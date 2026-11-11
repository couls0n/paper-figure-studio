"""Editable SVG renderers for five semantic figure families.

Every visible word is an SVG text object. Source paths are resolved relative to
spec['_base_dir']; arbitrary diagram/code content is displayed, never executed.
"""
from __future__ import annotations

import base64
from collections import defaultdict, deque
import html
import heapq
import math
from pathlib import Path
import re
from typing import Any

from PIL import Image, ImageFont

TYPES = {"architecture", "comparison", "trajectory", "text_card", "taxonomy"}
PALETTE = {"ink":"#183248", "muted":"#587087", "border":"#B9C9D5", "blue":"#E9F2FA", "green":"#E8F4EE", "red":"#FBECEB", "purple":"#F0ECF8", "yellow":"#FFF4DA", "white":"#FFFFFF", "accent":"#286A99"}
STATUS = {"normal":"#2D8060", "safe":"#2D8060", "success":"#2D8060", "unsafe":"#B33D42", "attack":"#B33D42", "blocked":"#B33D42", "neutral":"#286A99"}


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _positive(value, name):
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a finite positive number")
    return float(value)


def _required_list(data, key):
    value=data.get(key)
    if not isinstance(value,list) or not value:
        raise ValueError(f"data.{key} must be a non-empty list")
    return value


def _font_path(mono=False):
    paths = (["/System/Library/Fonts/Menlo.ttc", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"] if mono else ["/System/Library/Fonts/Supplemental/Arial Unicode.ttf", "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"])
    for path in paths:
        if Path(path).is_file(): return path
    try:
        import matplotlib
        path = Path(matplotlib.get_data_path()) / "fonts/ttf" / ("DejaVuSansMono.ttf" if mono else "DejaVuSans.ttf")
        if path.is_file(): return str(path)
    except ImportError:
        pass
    return None


class Typography:
    def __init__(self, style):
        self.size = _positive(style.get('font_size',17),'style.font_size')
        self.family = style.get('font_family','Arial Unicode MS, Noto Sans CJK SC, DejaVu Sans, Arial, sans-serif')
        self.mono_family = style.get('mono_font_family','Menlo, DejaVu Sans Mono, monospace')
        self.font_path = style.get('font_path') or _font_path()
        self.mono_path = style.get('mono_font_path') or _font_path(True)
        if style.get('font_path') and not Path(style['font_path']).is_file():
            raise ValueError('style.font_path does not exist')
        self.cache={}
    def font(self,size,mono=False):
        key=(round(size),mono)
        if key not in self.cache:
            path=self.mono_path if mono else self.font_path
            self.cache[key]=ImageFont.truetype(path,round(size)) if path else ImageFont.load_default(size=round(size))
        return self.cache[key]
    def width(self,text,size=None,mono=False):
        return self.font(size or self.size,mono).getlength(str(text))
    def wrap(self,text,width,size=None,mono=False):
        """Wrap without discarding code indentation or any non-whitespace text."""
        size=size or self.size
        if width<self.width('MMMM',size,mono): raise ValueError('Text area is too narrow; increase canvas width or reduce columns')
        output=[]
        for raw in str(text).split('\n'):
            if not raw: output.append('');continue
            if mono:
                pending=raw.expandtabs(4)
                while pending:
                    count=1
                    while count<=len(pending) and self.width(pending[:count],size,True)<=width:count+=1
                    count=max(1,count-1)
                    output.append(pending[:count]);pending=pending[count:]
            else:
                current=''
                for char in raw:
                    if current and self.width(current+char,size)>width:
                        # Prefer the last word boundary for Latin text, keeping CJK viable.
                        cut=current.rfind(' ')
                        if cut>len(current)//2:
                            output.append(current[:cut]);current=current[cut+1:]+char
                        else:output.append(current);current=char
                    else:current+=char
                output.append(current)
        return output


class SVG:
    def __init__(self,spec):
        self.width=_positive(spec.get('width',1000),'width')
        if self.width<360:raise ValueError('Schematic width must be at least 360 px')
        self.requested_height=spec.get('height')
        if self.requested_height is not None:_positive(self.requested_height,'height')
        self.typ=Typography(spec.get('style',{}))
        self.items=[]
        self.title=str(spec.get('title',''))
        self.title_lines=self.typ.wrap(self.title,self.width-64,25) if self.title else []
        self.content_top=32+len(self.title_lines)*34+(18 if self.title else 0)
        self.illustrative=spec.get('data_status')=='illustrative'
    def rect(self,x,y,w,h,fill='white',stroke=None,r=10,**attrs):
        if w<=0 or h<=0:raise ValueError('Rectangle has non-positive area')
        other=' '.join(f'{k.replace("_","-")}="{esc(v)}"' for k,v in attrs.items())
        self.items.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" rx="{r}" fill="{esc(fill)}" stroke="{esc(stroke or PALETTE["border"])}" {other}/>')
    def line(self,x1,y1,x2,y2,color=None,width=1.5,dash=None,arrow=False):
        extra=(f' stroke-dasharray="{dash}"' if dash else '')+''
        self.items.append(f'<path d="M {x1:.2f},{y1:.2f} L {x2:.2f},{y2:.2f}" fill="none" stroke="{esc(color or PALETTE["ink"])}" stroke-width="{width}"{extra}/>')
        if arrow:self.arrowhead(x1,y1,x2,y2,color or PALETTE['ink'])
    def path(self,d,color=None,dash=None,arrow=False):
        extra=(f' stroke-dasharray="{dash}"' if dash else '')+''
        self.items.append(f'<path d="{d}" fill="none" stroke="{esc(color or PALETTE["ink"])}" stroke-width="1.8"{extra}/>')
        if arrow:
            coords=[float(x) for x in re.findall(r'-?\d+(?:\.\d+)?',d)]
            self.arrowhead(*coords[-4:],color or PALETTE['ink'])
    def arrowhead(self,x1,y1,x2,y2,color):
        angle=math.atan2(y2-y1,x2-x1);length=9;half=4.2
        bx=x2-length*math.cos(angle);by=y2-length*math.sin(angle)
        points=f'{x2},{y2} {bx-half*math.sin(angle)},{by+half*math.cos(angle)} {bx+half*math.sin(angle)},{by-half*math.cos(angle)}'
        self.items.append(f'<polygon points="{points}" fill="{esc(color)}"/>')
    def text(self,x,y,text,size=None,color=None,weight=None,mono=False,anchor='start',spans=None):
        size=size or self.typ.size
        family=self.typ.mono_family if mono else self.typ.family
        body=esc(text)
        if spans is not None:
            parts=[];offset=0
            for t,c in spans:
                leading=len(t)-len(t.lstrip(' '))
                if t.strip():
                    tx=x+offset+self.typ.width(t[:leading],size,mono)
                    parts.append(f'<tspan x="{tx:.2f}" xml:space="preserve" fill="{esc(c)}">{esc(t[leading:])}</tspan>')
                offset+=self.typ.width(t,size,mono)
            body=''.join(parts)
        self.items.append(f'<text x="{x:.2f}" y="{y:.2f}" font-family="{esc(family)}" font-size="{size:.2f}" fill="{esc(color or PALETTE["ink"])}" text-anchor="{anchor}" xml:space="preserve"'+(f' font-weight="{weight}"' if weight else '')+f'>{body}</text>')
    def para(self,x,y,text,width,size=None,mono=False,color=None,weight=None):
        size=size or self.typ.size
        lines=self.typ.wrap(text,width,size,mono)
        for i,line in enumerate(lines):self.text(x,y+size+i*size*1.4,line,size,color,weight,mono)
        return len(lines)*size*1.4
    def finish(self,needed):
        footer_lines=self.typ.wrap('ILLUSTRATIVE EXAMPLE — replace content with your own evidence',self.width-64,12) if self.illustrative else []
        needed=math.ceil(needed+30+len(footer_lines)*16)
        if self.requested_height is not None and self.requested_height<needed:
            raise ValueError(f'height={self.requested_height} is too small; this content needs at least {needed} px. Omit height to size automatically.')
        height=max(needed,self.requested_height or 0)
        title_items=[]
        for i,line in enumerate(self.title_lines):
            title_items.append(f'<text x="32" y="{35+i*34}" font-family="{esc(self.typ.family)}" font-size="25" font-weight="700" fill="{PALETTE["ink"]}">{esc(line)}</text>')
        footer=''.join(f'<text x="32" y="{height-18-(len(footer_lines)-1-i)*16}" font-family="{esc(self.typ.family)}" font-size="12" fill="{PALETTE["muted"]}">{esc(line)}</text>' for i,line in enumerate(footer_lines))
        return f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{self.width:g}" height="{height:g}" viewBox="0 0 {self.width:g} {height:g}"><title>{esc(self.title)}</title><defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L8,4 L0,8 Z" fill="context-stroke"/></marker></defs><rect width="100%" height="100%" fill="white"/>'+''.join(title_items)+''.join(self.items)+footer+'</svg>'


def _validate_graph(nodes,edges):
    ids=[n.get('id') for n in nodes]
    if any(not isinstance(i,str) or not i for i in ids) or len(set(ids))!=len(ids):raise ValueError('Every node needs a non-empty unique string id')
    for e in edges:
        if e.get('from') not in ids or e.get('to') not in ids:raise ValueError(f'Edge references unknown node: {e}')
        if e['from']==e['to']:raise ValueError('Self-loop edges require a separate feedback node or explicit manual diagram')


def _positions(nodes,edges):
    explicit=[('row' in n or 'col' in n) for n in nodes]
    if any(explicit):
        if not all('row' in n and 'col' in n for n in nodes):raise ValueError('Provide row and col on all nodes, or omit them on all nodes')
        for n in nodes:
            if any(not isinstance(n[k],int) or isinstance(n[k],bool) or n[k]<0 for k in ['row','col']):raise ValueError('row and col must be non-negative integers')
        pos={n['id']:(n['row'],n['col']) for n in nodes}
        if len(set(pos.values()))!=len(pos):raise ValueError('Two nodes occupy the same row/col')
        return pos
    indegree={n['id']:0 for n in nodes};following=defaultdict(list);depth=defaultdict(int)
    for e in edges:
        if e.get('kind')=='feedback':continue
        indegree[e['to']]+=1;following[e['from']].append(e['to'])
    queue=deque(i for i,d in indegree.items() if d==0);visited=[]
    while queue:
        i=queue.popleft();visited.append(i)
        for j in following[i]:
            depth[j]=max(depth[j],depth[i]+1);indegree[j]-=1
            if indegree[j]==0:queue.append(j)
    if len(visited)!=len(nodes):raise ValueError('Graph contains a cycle. Mark feedback edges kind=feedback or provide explicit row/col positions')
    counter=defaultdict(int);pos={}
    for n in nodes:
        col=depth[n['id']];pos[n['id']]=(counter[col],col);counter[col]+=1
    return pos


def _rects_overlap(a,b):
    return max(a[0],b[0])<min(a[0]+a[2],b[0]+b[2])-0.01 and max(a[1],b[1])<min(a[1]+a[3],b[1]+b[3])-0.01


def _segment_hits_rect(a,b,rect):
    """Interior intersections only: a connector may touch its node's port."""
    x,y,w,h=rect
    if abs(a[0]-b[0])<0.01:
        return x+0.01<a[0]<x+w-0.01 and max(min(a[1],b[1]),y)<min(max(a[1],b[1]),y+h)-0.01
    if abs(a[1]-b[1])<0.01:
        return y+0.01<a[1]<y+h-0.01 and max(min(a[0],b[0]),x)<min(max(a[0],b[0]),x+w)-0.01
    raise ValueError('Diagram connectors must be orthogonal')


def _clean_route(points):
    clean=[]
    for point in points:
        if clean and point==clean[-1]:continue
        if len(clean)>1 and ((clean[-2][0]==clean[-1][0]==point[0]) or (clean[-2][1]==clean[-1][1]==point[1])):
            clean[-1]=point
        else:clean.append(point)
    return clean


def _orthogonal_route(start,end,obstacles):
    """Shortest visible grid route, with a bend penalty to avoid busy zigzags."""
    if start==end:return [start]
    candidates=[[start,(end[0],start[1]),end],[start,(start[0],end[1]),end]]
    for candidate in candidates:
        route=_clean_route(candidate)
        if all(not _segment_hits_rect(a,b,r) for a,b in zip(route,route[1:]) for r in obstacles):return route
    xs=sorted({start[0],end[0],*[v for x,y,w,h in obstacles for v in (x,x+w)]})
    ys=sorted({start[1],end[1],*[v for x,y,w,h in obstacles for v in (y,y+h)]})
    first=(xs.index(start[0]),ys.index(start[1]),0)
    target=(xs.index(end[0]),ys.index(end[1]))
    queue=[(0,first)];dist={first:0};previous={}
    while queue:
        cost,state=heapq.heappop(queue)
        if cost!=dist[state]:continue
        ix,iy,direction=state
        if (ix,iy)==target:
            route=[]
            while True:
                route.append((xs[state[0]],ys[state[1]]))
                if state==first:break
                state=previous[state]
            return _clean_route(route[::-1])
        a=(xs[ix],ys[iy])
        for nx,ny,nd in [(ix-1,iy,1),(ix+1,iy,1),(ix,iy-1,2),(ix,iy+1,2)]:
            if not (0<=nx<len(xs) and 0<=ny<len(ys)):continue
            b=(xs[nx],ys[ny])
            if any(_segment_hits_rect(a,b,r) for r in obstacles):continue
            value=cost+abs(a[0]-b[0])+abs(a[1]-b[1])+(24 if direction and direction!=nd else 0)
            nxt=(nx,ny,nd)
            if value<dist.get(nxt,float('inf')):
                dist[nxt]=value;previous[nxt]=state;heapq.heappush(queue,(value,nxt))
    raise ValueError('Cannot route an edge without crossing nodes; increase spacing or change row/col')


def _port(box,side,offset=0):
    x,y,w,h=box
    return {'left':(x-offset,y+h/2),'right':(x+w+offset,y+h/2),
            'top':(x+w/2,y-offset),'bottom':(x+w/2,y+h+offset)}[side]


def _edge_route(a,b,kind,obstacles,rail):
    if kind=='feedback':
        # Same-column feedback stays in its inter-column corridor if clear.
        # Cross-column feedback uses an exterior rail: never rise blindly
        # through an unrelated component above the source node.
        side_a=side_b='left'
        local=a[0]-25
        route_x=local if abs(a[0]-b[0])<1 else rail
        start=_port(a,side_a,12);end=_port(b,side_b,12)
        p=(route_x,start[1]);q=(route_x,end[1])
        if any(_segment_hits_rect(p,q,r) for r in obstacles):p=(rail,start[1]);q=(rail,end[1])
        route=_orthogonal_route(start,p,obstacles)+_orthogonal_route(p,q,obstacles)[1:]+_orthogonal_route(q,end,obstacles)[1:]
    else:
        if abs(a[1]-b[1])<1:side_a,side_b=('right','left') if b[0]>a[0] else ('left','right')
        elif abs(a[0]-b[0])<1:side_a,side_b=('bottom','top') if b[1]>a[1] else ('top','bottom')
        else:side_a,side_b=('right','left') if b[0]>a[0] else ('left','right')
        start=_port(a,side_a,12);end=_port(b,side_b,12)
        route=_orthogonal_route(start,end,obstacles)
    return _clean_route([_port(a,side_a)]+route+[_port(b,side_b,4)])


def _edge_label_box(route,width,occupied,canvas_width):
    candidates=[]
    segments=list(zip(route,route[1:]))
    # Prefer horizontal space that can contain the complete centered label.
    horizontal=[(a,b) for a,b in segments if a[1]==b[1] and abs(a[0]-b[0])>=width+8]
    vertical=[(a,b) for a,b in segments if a[0]==b[0]]
    remaining=[(a,b) for a,b in segments if a[1]==b[1] and (a,b) not in horizontal]
    for a,b in horizontal+vertical+remaining:
        for fraction in [.5,.25,.75]:
            x=a[0]+fraction*(b[0]-a[0]);y=a[1]+fraction*(b[1]-a[1])
            if a[1]==b[1]:candidates.extend([(x-width/2,y-25,width,20),(x-width/2,y+6,width,20)])
            else:candidates.extend([(x+10,y-10,width,20),(x-width-10,y-10,width,20)])
    for box in candidates:
        if box[0]<8 or box[0]+box[2]>canvas_width-8:continue
        if not any(_rects_overlap(box,r) for r in occupied):return box
    raise ValueError('No clear space for an edge label; increase canvas width, shorten labels, or spread nodes across rows')


def architecture(spec):
    data=spec['data'];nodes=_required_list(data,'nodes');edges=data.get('edges',[])
    _validate_graph(nodes,edges);pos=_positions(nodes,edges);svg=SVG(spec)
    cols=max(c for r,c in pos.values())+1;rows=max(r for r,c in pos.values())+1
    margin=52;gx=64;gy=80
    for e in edges:
        if e.get('label'):
            label_width=svg.typ.width(str(e['label']),12)
            if label_width>150:raise ValueError('Edge labels must be short (about 20 characters); move long explanations into node detail')
            if pos[e['from']][0]==pos[e['to']][0]:gx=max(gx,label_width+28)
    w=(svg.width-2*margin-gx*(cols-1))/cols
    if w<145:raise ValueError(f'{cols} columns need a wider canvas (at least {math.ceil(2*margin+cols*145+gx*(cols-1))} px) or fewer stages per row')
    groups=data.get('groups',[]);group_ids=[g.get('id') for g in groups]
    if len(set(group_ids))!=len(group_ids):raise ValueError('Group ids must be unique')
    for n in nodes:
        if n.get('group') and n['group'] not in group_ids:raise ValueError(f'Unknown group {n["group"]}')
    heights={}
    for n in nodes:
        label=svg.typ.wrap(n.get('label',n['id']),w-32,18)
        detail=svg.typ.wrap(n.get('detail',''),w-32,15) if n.get('detail') else []
        heights[n['id']]=max(88,32+len(label)*25+len(detail)*21+(8 if detail else 0))
    rowh=[max([heights[n['id']] for n in nodes if pos[n['id']][0]==r] or [88]) for r in range(rows)]
    ys=[svg.content_top+45]
    for r in range(1,rows):ys.append(ys[-1]+rowh[r-1]+gy)
    boxes={n['id']:(margin+pos[n['id']][1]*(w+gx),ys[pos[n['id']][0]],w,rowh[pos[n['id']][0]]) for n in nodes}
    group_rects=[];headers=[]
    for g in groups:
        members=[boxes[n['id']] for n in nodes if n.get('group')==g['id']]
        if not members:raise ValueError(f'Group {g["id"]} has no member nodes')
        x=min(b[0] for b in members)-17;y=min(b[1] for b in members)-34
        right=max(b[0]+b[2] for b in members)+17;bottom=max(b[1]+b[3] for b in members)+17
        bounds=(x,y,right-x,bottom-y)
        if any(_rects_overlap(bounds,old) for old in group_rects):raise ValueError('Group containers overlap; arrange each group in separate rows or columns')
        group_rects.append(bounds);headers.append((x,y,right-x,30))
        svg.rect(x,y,right-x,bottom-y,g.get('color',PALETTE['blue']),r=12,stroke_dasharray='5 4')
        svg.text(x+12,y+23,g.get('label',g['id']),15,weight=700)
    obstacles=[(x-12,y-12,nw+24,nh+24) for x,y,nw,nh in boxes.values()]+headers
    routes=[]
    for e in edges:
        kind=e.get('kind','flow')
        if kind not in ['flow','feedback','attack','mapping']:raise ValueError(f'Unknown edge kind {kind}')
        route=_edge_route(boxes[e['from']],boxes[e['to']],kind,obstacles,24)
        routes.append(route)
        color=STATUS['attack'] if kind=='attack' else PALETTE['muted'] if kind=='feedback' else PALETTE['ink']
        d='M '+' L '.join(f'{x:.2f},{y:.2f}' for x,y in route)
        svg.items.append(f'<g data-role="edge" data-from="{esc(e["from"])}" data-to="{esc(e["to"])}" data-kind="{kind}">')
        svg.path(d,color,'5 4' if kind=='feedback' else None,True);svg.items.append('</g>')
    for n in nodes:
        x,y,nw,nh=boxes[n['id']];svg.rect(x,y,nw,nh,n.get('color','white'),r=10,data_role='node',data_node_id=n['id'])
        cy=y+16;cy+=svg.para(x+16,cy,n.get('label',n['id']),nw-32,18,weight=700)
        if n.get('detail'):svg.para(x+16,cy+8,n['detail'],nw-32,15,color=PALETTE['muted'])
    occupied=[(x-4,y-4,nw+8,nh+8) for x,y,nw,nh in boxes.values()]+headers+[(0,0,svg.width,svg.content_top)]
    label_boxes=[]
    for e,route in zip(edges,routes):
        if not e.get('label'):continue
        label=str(e['label']);tw=svg.typ.width(label,12)
        x,y,lw,lh=_edge_label_box(route,tw+10,occupied,svg.width)
        svg.rect(x,y,lw,lh,'white','white',r=2,data_role='edge-label',data_from=e['from'],data_to=e['to'])
        svg.text(x+lw/2,y+14,label,12,color=PALETTE['muted'],anchor='middle')
        occupied.append((x-3,y-3,lw+6,lh+6));label_boxes.append((x,y,lw,lh))
    extent=max([y+h for x,y,w,h in boxes.values()]+[y+h for x,y,w,h in label_boxes]+[y for route in routes for x,y in route])
    return svg.finish(extent+25)


def _highlight_spans(text,highlights):
    ranges=[]
    for h in highlights or []:
        value=h.get('text','')
        if not value:continue
        start=text.find(value)
        if start>=0:ranges.append((start,start+len(value),h.get('color','#B33D42')))
    if not ranges:return None
    bounds=sorted({0,len(text),*[x for a,b,c in ranges for x in [a,b]]})
    return [(text[a:b],next((c for s,e,c in ranges if s<=a and b<=e),PALETTE['ink'])) for a,b in zip(bounds,bounds[1:])]


def comparison(spec):
    data=spec['data'];columns=_required_list(data,'columns');svg=SVG(spec)
    if len(columns)<2:raise ValueError('comparison needs at least two columns')
    gap=24;w=(svg.width-64-gap*(len(columns)-1))/len(columns)
    if w<220:raise ValueError('comparison columns need at least 220 px each; increase width or split the figure')
    top=svg.content_top
    if data.get('shared_input'):
        hh=len(svg.typ.wrap(data['shared_input'],svg.width-100,16))*22.4+58
        svg.rect(32,top,svg.width-64,hh,PALETTE['blue']);svg.text(50,top+26,'SHARED INPUT',12,weight=700,color=PALETTE['accent'])
        svg.para(50,top+37,data['shared_input'],svg.width-100,16);top+=hh+26
    plans=[]
    for column in columns:
        events=_required_list(column,'events');header_lines=svg.typ.wrap(column.get('title',column.get('id','')),w-32,19)
        sizes=[]
        for event in events:
            if 'text' not in event:raise ValueError('Each comparison event needs text')
            lines=svg.typ.wrap(event['text'],w-32,16);sizes.append((lines,50+len(lines)*22.4))
        plans.append((column,header_lines,sizes))
    header=max(55,len(max([p[1] for p in plans],key=len))*26+24)
    max_events=max(len(p[2]) for p in plans)
    rowheights=[max([p[2][i][1] for p in plans if i<len(p[2])]) for i in range(max_events)]
    total=header+sum(rowheights)+16*max_events+18
    for j,(column,titles,sizes) in enumerate(plans):
        x=32+j*(w+gap);status=column.get('status','neutral');color=STATUS.get(status,STATUS['neutral'])
        svg.rect(x,top,w,total,'white');svg.rect(x,top,w,header,color,color,r=10)
        for k,line in enumerate(titles):svg.text(x+16,top+28+k*26,line,19,'white',700)
        y=top+header+16
        for i,(lines,h) in enumerate(sizes):
            event=column['events'][i];svg.rect(x+10,y,w-20,rowheights[i],PALETTE['green'] if status in ['safe','normal','success'] else PALETTE['red'] if status in ['attack','unsafe','blocked'] else PALETTE['blue'],stroke='none',r=7)
            svg.text(x+18,y+24,event.get('role',f'Step {i+1}'),12,color,700)
            for k,line in enumerate(lines):svg.text(x+18,y+47+k*22.4,line,16,spans=_highlight_spans(line,event.get('highlights')))
            y+=rowheights[i]+16
    return svg.finish(top+total)


def _image_data(path):
    if not path.is_file():raise ValueError(f'Trajectory image does not exist: {path}')
    if path.suffix.lower()=='.svg':
        import xml.etree.ElementTree as ET
        try:
            root=ET.parse(path).getroot();vb=[float(x) for x in re.split(r'[ ,]+',root.get('viewBox','').strip()) if x]
            if len(vb)==4:iw,ih=vb[2:]
            else:iw=float(root.get('width','').replace('px',''));ih=float(root.get('height','').replace('px',''))
        except (ValueError,ET.ParseError) as exc:raise ValueError(f'Cannot read SVG dimensions: {path}') from exc
        return 'image/svg+xml',path.read_bytes(),iw,ih
    try:
        with Image.open(path) as im:iw,ih=im.size;format=im.format.lower()
    except Exception as exc:raise ValueError(f'Cannot read trajectory image: {path}') from exc
    if format not in ['png','jpeg','gif','webp']:raise ValueError('Use PNG, JPEG, WebP or SVG screenshots')
    return 'image/'+format,path.read_bytes(),iw,ih


def trajectory(spec):
    data=spec['data'];steps=_required_list(data,'steps');svg=SVG(spec);ncols=int(data.get('columns',min(3,len(steps))))
    if ncols<1 or ncols>len(steps):raise ValueError('trajectory columns must be between 1 and number of steps')
    gap=24;w=(svg.width-64-gap*(ncols-1))/ncols
    if w<235:raise ValueError('trajectory needs at least 235 px per column')
    base=Path(spec.get('_base_dir','.'));planned=[]
    for i,s in enumerate(steps):
        if not s.get('action'):raise ValueError('Every trajectory step needs an action')
        if bool(s.get('image'))==bool(s.get('illustration')):raise ValueError('Each trajectory step needs exactly one real image or explicitly labeled illustration')
        imageinfo=None
        if s.get('image'):imageinfo=_image_data(base/s['image'])
        titles=svg.typ.wrap(s.get('title',str(s.get('id',i+1))),w-28,17)
        action=svg.typ.wrap(s['action'],w-28,15);obs=svg.typ.wrap(s.get('observation',''),w-28,14) if s.get('observation') else []
        # Images preserve aspect ratios; tall images grow their row instead of being silently cropped.
        ih=(w-28)*(imageinfo[3]/imageinfo[2]) if imageinfo else max(150,70+sum(len(svg.typ.wrap(line,w-52,12))*17+6 for line in s['illustration'].get('lines',[])))
        ih=max(80,ih)
        top_h=26+len(titles)*24;body_h=len(action)*21+len(obs)*19.6+44+(18 if obs else 0)
        planned.append((s,titles,action,obs,imageinfo,ih,top_h,body_h))
    y=svg.content_top
    for start in range(0,len(steps),ncols):
        batch=planned[start:start+ncols];max_title=max(p[6] for p in batch);max_image=max(p[5] for p in batch);max_body=max(p[7] for p in batch);total=max_title+max_image+max_body+24
        for j,(s,titles,action,obs,info,ih,top_h,body_h) in enumerate(batch):
            x=32+j*(w+gap);svg.rect(x,y,w,total,'white');svg.rect(x,y,w,max_title,PALETTE['blue'],r=10)
            for k,line in enumerate(titles):svg.text(x+14,y+27+k*24,line,17,weight=700)
            ix=x+14;iy=y+max_title+12;iw=w-28
            if info:
                mime,blob,srcw,srch=info;href='data:'+mime+';base64,'+base64.b64encode(blob).decode()
                svg.items.append(f'<image x="{ix}" y="{iy}" width="{iw}" height="{ih}" href="{href}" xlink:href="{href}"/>')
            else:
                illustration=s['illustration'];svg.rect(ix,iy,iw,ih,'#F4F7F9',r=4)
                svg.text(ix+12,iy+22,'ILLUSTRATION',10,PALETTE['muted'],700)
                svg.para(ix+12,iy+30,illustration.get('label','Example interface'),iw-24,14,weight=700)
                ly=iy+70
                for line in illustration.get('lines',[]):ly+=svg.para(ix+12,ly,line,iw-24,12)+6
            for c in s.get('callouts',[]):
                vals=[c.get(k) for k in ['x','y','width','height']]
                if any(not isinstance(v,(int,float)) or not math.isfinite(v) for v in vals):raise ValueError('callouts use finite normalized x/y/width/height in [0,1]')
                cx,cy,cw,ch=vals
                if cx<0 or cy<0 or cw<=0 or ch<=0 or cx+cw>1 or cy+ch>1:raise ValueError('callout bbox lies outside the image')
                svg.rect(ix+cx*iw,iy+cy*ih,cw*iw,ch*ih,'none','#B33D42',r=2,stroke_width=2)
                if c.get('label'):
                    label=str(c['label']);lw=svg.typ.width(label,11)+8
                    if lw>iw:raise ValueError('Callout label is too long; use a short ID and describe it below')
                    lx=min(ix+cx*iw,ix+iw-lw);ly=max(iy+13,iy+cy*ih-4)
                    svg.rect(lx,ly-12,lw,16,'white','white',r=2);svg.text(lx+4,ly,label,11,'#B33D42',700)
            ty=y+max_title+max_image+31;svg.text(x+14,ty,'ACTION',11,PALETTE['accent'],700)
            for k,line in enumerate(action):svg.text(x+14,ty+21+k*21,line,15)
            ty+=len(action)*21+25
            if obs:
                svg.text(x+14,ty,'OBSERVATION',11,PALETTE['muted'],700)
                for k,line in enumerate(obs):svg.text(x+14,ty+20+k*19.6,line,14)
        y+=total+28
    return svg.finish(y-28)


TOKEN=re.compile(r'''("(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|\b(?:class|def|return|if|else|elif|for|in|while|import|from|and|or|not|True|False|None|null|true|false|when|then|enforce|stop|rule|event|predicate)\b|#[^\n]*|\b\d+(?:\.\d+)?\b)''')
def _code_spans(line,highlights):
    matches=list(TOKEN.finditer(line));spans=[];cursor=0
    for m in matches:
        if m.start()>cursor:spans.append((line[cursor:m.start()],PALETTE['ink']))
        token=m.group();color='#377B58' if token.startswith(('"',"'")) else '#72818C' if token.startswith('#') else '#735498' if token[0].isdigit() else '#1D5F9B'
        spans.append((token,color));cursor=m.end()
    if cursor<len(line):spans.append((line[cursor:],PALETTE['ink']))
    # Explicit scientific highlights take precedence over lexical coloring.
    explicit=_highlight_spans(line,highlights)
    return explicit or spans or [(line,PALETTE['ink'])]


def text_card(spec):
    data=spec['data'];cards=_required_list(data,'cards');svg=SVG(spec);columns=int(data.get('columns',1));gap=24
    if columns<1 or columns>len(cards):raise ValueError('text_card columns must be between 1 and number of cards')
    w=(svg.width-64-gap*(columns-1))/columns
    if w<240:raise ValueError('text_card needs at least 240 px per column')
    plans=[]
    for c in cards:
        if not isinstance(c.get('content'),str):raise ValueError('Each card content must be a string')
        lang=c.get('language','text');mono=lang!='text';size=15 if mono else 16
        numbers=bool(c.get('line_numbers',mono));number_width=38 if numbers else 0
        titles=svg.typ.wrap(c.get('title',''),w-32,18)
        lines=[]
        for num,line in enumerate(c['content'].split('\n'),1):
            hs=[h for h in c.get('highlights',[]) if h.get('line',num)==num]
            wrapped=svg.typ.wrap(line,w-32-number_width,size,mono)
            lines.extend((part,num if idx==0 else None,hs) for idx,part in enumerate(wrapped))
        header=max(45,20+len(titles)*25);h=header+24+len(lines)*size*1.45+12
        plans.append((c,titles,lines,mono,size,numbers,number_width,header,h))
    y=svg.content_top
    for start in range(0,len(plans),columns):
        batch=plans[start:start+columns];rowheight=max(p[-1] for p in batch)
        for j,(c,titles,lines,mono,size,numbers,nw,header,h) in enumerate(batch):
            x=32+j*(w+gap);svg.rect(x,y,w,rowheight,'#F7F9FB');svg.rect(x,y,w,header,PALETTE['ink'],PALETTE['ink'],r=10)
            for k,title in enumerate(titles):svg.text(x+16,y+29+k*25,title,18,'white',700)
            for k,(line,num,hs) in enumerate(lines):
                ty=y+header+size+14+k*size*1.45
                if numbers and num is not None:svg.text(x+14,ty,str(num),12,PALETTE['muted'],mono=True)
                svg.text(x+16+nw,ty,line,size,mono=mono,spans=_code_spans(line,hs) if mono else _highlight_spans(line,hs))
        y+=rowheight+24
    return svg.finish(y-24)


def taxonomy(spec):
    data=spec['data'];variant=data.get('variant','tree')
    if variant=='mapping':
        svg=SVG(spec);mappings=_required_list(data,'mappings');left=float(data.get('left_fraction',0.3))
        if not .18<=left<=.6:raise ValueError('left_fraction must be between .18 and .6')
        lw=(svg.width-116)*left;rw=svg.width-116-lw;top=svg.content_top
        svg.text(48,top+18,data.get('left_title','FIELD'),12,PALETTE['accent'],700);svg.text(100+lw,top+18,data.get('right_title','MEANING'),12,PALETTE['accent'],700)
        y=top+35
        for m in mappings:
            if not m.get('field') or not m.get('description'):raise ValueError('Each mapping needs field and description')
            lh=len(svg.typ.wrap(m['field'],lw-30,16))*22.4;rh=len(svg.typ.wrap(m['description'],rw-30,16))*22.4;h=max(lh,rh)+28
            svg.rect(32,y,lw,h,PALETTE['purple']);svg.rect(84+lw,y,rw,h,PALETTE['green']);svg.para(47,y+11,m['field'],lw-30,16,weight=700);svg.para(99+lw,y+11,m['description'],rw-30,16)
            svg.line(37+lw,y+h/2,76+lw,y+h/2,arrow=True);y+=h+18
        return svg.finish(y-18)
    if variant!='tree':raise ValueError('taxonomy variant must be tree or mapping')
    nodes=_required_list(data,'nodes');edges=data.get('edges',[]);_validate_graph(nodes,edges)
    # A taxonomy tree is containment, not an arbitrary process graph.
    indegree=defaultdict(int)
    for e in edges:indegree[e['to']]+=1
    if any(v>1 for v in indegree.values()):raise ValueError('Tree taxonomy nodes may have at most one parent; use separate independent trees for marginal categories')
    if any(e.get('kind')=='feedback' for e in edges):raise ValueError('Taxonomy cannot contain feedback edges')
    if any('row' in n or 'col' in n for n in nodes):
        adapted={**spec,'data':{**data,'edges':[{**e,'kind':'mapping'} for e in edges]}}
        return architecture(adapted)
    # Center every parent over the complete extent of its own descendants.
    levels=_positions(nodes,edges);svg=SVG(spec);children=defaultdict(list)
    for e in edges:children[e['from']].append(e['to'])
    roots=[n['id'] for n in nodes if indegree[n['id']]==0]
    cols=max(col for row,col in levels.values())+1;gap=64;w=(svg.width-104-gap*(cols-1))/cols
    if w<145:raise ValueError('Taxonomy is too deep for this width; increase width or split into panels')
    maxh=max(80,*(30+len(svg.typ.wrap(n.get('label',n['id']),w-32,18))*25+(len(svg.typ.wrap(n['detail'],w-32,15))*21+8 if n.get('detail') else 0) for n in nodes))
    centers={};leaf_index=0
    def place(node):
        nonlocal leaf_index
        if not children[node]:
            centers[node]=svg.content_top+maxh/2+leaf_index*(maxh+32);leaf_index+=1
        else:
            for child in children[node]:place(child)
            centers[node]=(centers[children[node][0]]+centers[children[node][-1]])/2
    for root in roots:place(root)
    boxes={n['id']:(52+levels[n['id']][1]*(w+gap),centers[n['id']]-maxh/2,w,maxh) for n in nodes}
    for e in edges:
        a=boxes[e['from']];b=boxes[e['to']];x1=a[0]+a[2];x2=b[0]-4;y1=a[1]+maxh/2;y2=b[1]+maxh/2;mid=(x1+x2)/2
        svg.path(f'M {x1},{y1} L {mid},{y1} L {mid},{y2} L {x2},{y2}',arrow=True)
    for n in nodes:
        x,y,nw,nh=boxes[n['id']];svg.rect(x,y,nw,nh,n.get('color','white'))
        cy=y+16;cy+=svg.para(x+16,cy,n.get('label',n['id']),nw-32,18,weight=700)
        if n.get('detail'):svg.para(x+16,cy+8,n['detail'],nw-32,15,color=PALETTE['muted'])
    return svg.finish(max(y+h for x,y,w,h in boxes.values()))


def render_schematic(spec:dict)->str:
    if not isinstance(spec,dict) or spec.get('type') not in TYPES:raise ValueError(f'Schematic type must be one of {sorted(TYPES)}')
    if not isinstance(spec.get('data'),dict):raise ValueError('spec.data must be an object')
    return globals()[spec['type']](spec)
