"""Object-centred paper workflows, grounded in the surveyed stage/guard figures."""
from __future__ import annotations

from copy import deepcopy
import math

from schematics import (SVG, esc, _required_list, _validate_graph, _positions,
                        _rects_overlap, _edge_route, _edge_label_box,
                        _port, _orthogonal_route, _clean_route)

INK = '#252525'
MUTED = '#505050'
COLORS = {'flow': INK, 'allow': '#39814A', 'reject': '#BC3335', 'retrieve': '#567692'}
FILLS = {'document':'#E9EEF6', 'memory':'#EEF1C7', 'model':'#EEE8F5',
         'process':'#EAF2E6', 'tool':'#E4EFF5', 'environment':'#F2F2F2',
         'decision':'#F7E2CF', 'user':'#E8EEF8', 'table':'#EAF0F7'}
KINDS = set(FILLS)


class PaperSVG(SVG):
    """Small typography and limited border/colour vocabulary, without a UI header."""
    def __init__(self, spec):
        adapted=deepcopy(spec)
        adapted['style']={'font_size':15, **spec.get('style',{})}
        adapted['title']=''
        super().__init__(adapted)
        self.title=str(spec.get('title',''))
        self.show_title=bool(spec.get('style',{}).get('show_title',False))
        title_lines=self.typ.wrap(self.title,self.width-56,18) if self.show_title else []
        self.content_top=26+len(title_lines)*24 if title_lines else 22
        for i,line in enumerate(title_lines):self.text(28,29+i*24,line,18,weight=700)

    def text(self,x,y,text,size=None,color=None,weight=None,mono=False,anchor='start',spans=None):
        return super().text(x,y,text,size,color or INK,weight,mono,anchor,spans)

    def rect(self,x,y,w,h,fill='white',stroke=None,r=3,**attrs):
        return super().rect(x,y,w,h,fill,stroke or '#777777',r,**attrs)

    def finish(self, needed):
        needed=math.ceil(needed+34+(18 if self.illustrative else 0))
        if self.requested_height is not None and self.requested_height<needed:
            raise ValueError(f'height={self.requested_height} is too small; content needs at least {needed} px')
        h=max(needed,self.requested_height or 0)
        if self.illustrative:self.text(28,h-15,'ILLUSTRATIVE EXAMPLE · original demonstration, not reported results',10,'#6D6D6D')
        return f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width:g}" height="{h:g}" viewBox="0 0 {self.width:g} {h:g}"><title>{esc(self.title)}</title><rect width="100%" height="100%" fill="white"/>'+''.join(self.items)+'</svg>'


def _path(svg, d, fill='none', stroke=INK, width=1.3, dash=None):
    svg.items.append(f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{width}"'+(f' stroke-dasharray="{dash}"' if dash else '')+'/>')


def _ellipse(svg,cx,cy,rx,ry,fill,stroke=INK):
    svg.items.append(f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{fill}" stroke="{stroke}" stroke-width="1.3"/>')


def _icon(svg,kind,x,y,color):
    """Original editable vector glyphs; semantic objects, not product logos."""
    if kind=='document':
        svg.rect(x+8,y+5,42,49,'#FFFFFF',INK,r=1)
        svg.rect(x+4,y+2,42,49,'#F6F7FA',INK,r=1)
        _path(svg,f'M {x} {y} H {x+31} L {x+43} {y+12} V {y+51} H {x} Z',color)
        _path(svg,f'M {x+31} {y} V {y+12} H {x+43}')
        for k in range(4):svg.line(x+8,y+20+k*7,x+34,y+20+k*7,INK,1)
    elif kind=='memory':
        _path(svg,f'M {x} {y+9} V {y+43} C {x} {y+57},{x+52} {y+57},{x+52} {y+43} V {y+9}',color)
        _ellipse(svg,x+26,y+9,26,9,color)
        for yy in (y+23,y+36):_path(svg,f'M {x} {yy} C {x} {yy+12},{x+52} {yy+12},{x+52} {yy}')
    elif kind=='model':
        svg.rect(x+2,y+10,50,34,color,INK,r=7)
        svg.line(x+27,y+10,x+27,y+2,INK,1.3)
        _ellipse(svg,x+27,y+1,3,3,'#D1B9E8')
        _ellipse(svg,x+16,y+24,4,4,'white');_ellipse(svg,x+38,y+24,4,4,'white')
        svg.line(x+20,y+35,x+34,y+35,INK,1.4)
        svg.rect(x-4,y+20,6,15,color,INK,r=2);svg.rect(x+52,y+20,6,15,color,INK,r=2)
        svg.text(x+27,y+58,'LLM',11,INK,700,anchor='middle')
    elif kind in {'tool','environment'}:
        svg.rect(x-5,y+3,64,44,color,INK,r=2)
        svg.line(x-5,y+13,x+59,y+13,INK,1)
        for xx in (x+1,x+7,x+13):_ellipse(svg,xx,y+8,1.4,1.4,'#777777','#777777')
        if kind=='environment':
            svg.rect(x+1,y+19,17,21,'#D9E2E8','none',r=0)
            for k in range(3):svg.line(x+24,y+22+k*7,x+51,y+22+k*7,'#767676',1)
        else:
            svg.text(x+27,y+35,'>_ ',20,INK,700,mono=True,anchor='middle')
        svg.line(x+27,y+47,x+27,y+55,INK,1.3);svg.line(x+12,y+55,x+42,y+55,INK,1.3)
    elif kind=='user':
        _ellipse(svg,x+26,y+12,11,11,color)
        _path(svg,f'M {x+7} {y+48} V {y+35} Q {x+26} {y+18},{x+45} {y+35} V {y+48} Z',color)


def _table_plan(svg,node,width):
    columns=node.get('columns');rows=node.get('rows')
    if not isinstance(columns,list) or not columns or any(not isinstance(c,str) or not c.strip() for c in columns) or len(set(columns))!=len(columns):
        raise ValueError('Table node columns must be non-empty unique strings')
    if not isinstance(rows,list) or not rows or any(not isinstance(r,list) or len(r)!=len(columns) for r in rows):
        raise ValueError('Table node rows must be non-empty and match the column count')
    for row in rows:
        for value in row:
            if not isinstance(value,(str,int,float,bool)) or isinstance(value,float) and not math.isfinite(value):
                raise ValueError('Table node cells must be strings or finite scalar values')
    if width<len(columns)*52:raise ValueError('Table node needs at least 52 px per column; increase width or reduce columns')
    natural=[max(svg.typ.width(str(row[i]),11) for row in [columns]+rows)+12 for i in range(len(columns))]
    room=width-52*len(columns)
    widths=[52+room*v/sum(natural) for v in natural]
    wrapped=[[svg.typ.wrap(str(cell),widths[i]-12,11) for i,cell in enumerate(row)] for row in [columns]+rows]
    heights=[max(len(cell) for cell in row)*15+8 for row in wrapped]
    return widths,wrapped,heights


def _draw_node(svg, node, box):
    x,y,w,h=box;kind=node.get('kind','process');fill=node.get('color',FILLS[kind])
    svg.items.append(f'<g data-role="component" data-node-id="{esc(node["id"])}" data-kind="{kind}">')
    # Invisible semantic rectangle supports exact geometric regression tests.
    svg.rect(x,y,w,h,'none','none',r=0,data_role='node',data_node_id=node['id'])
    label=str(node.get('label',node['id']));detail=str(node.get('detail',''))
    if kind=='table':
        widths,wrapped,heights=_table_plan(svg,node,w)
        yy=y
        for ri,(row,rh) in enumerate(zip(wrapped,heights)):
            xx=x
            for ci,(cell,cw) in enumerate(zip(row,widths)):
                svg.rect(xx,yy,cw,rh,'#6D99B8' if ri==0 else fill if ri%2 else '#FFFFFF','#BCC9D3',r=0,stroke_width=.65,
                         data_role='table-cell',data_row=ri-1,data_column=ci)
                for li,line in enumerate(cell):svg.text(xx+6,yy+15+li*15,line,11,'white' if ri==0 else INK,700 if ri==0 else None)
                xx+=cw
            yy+=rh
        ty=yy+20
        for line in svg.typ.wrap(label,w-8,15):svg.text(x+w/2,ty,line,15,weight=700,anchor='middle');ty+=20
        for line in svg.typ.wrap(detail,w-8,12) if detail else []:svg.text(x+w/2,ty,line,12,MUTED,anchor='middle');ty+=16
    elif kind in {'process','decision'}:
        if kind=='decision':
            _path(svg,f'M {x+w/2} {y} L {x+w} {y+h/2} L {x+w/2} {y+h} L {x} {y+h/2} Z',fill)
            pad=w*.2;size=14
        else:
            svg.rect(x,y,w,h,fill,'#777777',r=3,stroke_width=1.1)
            pad=12;size=15
        ll=svg.typ.wrap(label,w-2*pad,size);dl=svg.typ.wrap(detail,w-2*pad,12) if detail else []
        total=len(ll)*20+(len(dl)*16+7 if dl else 0)
        ty=y+(h-total)/2+size
        for line in ll:svg.text(x+w/2,ty,line,size,weight=700,anchor='middle');ty+=20
        if dl:ty+=5
        for line in dl:svg.text(x+w/2,ty,line,12,MUTED,anchor='middle');ty+=16
    else:
        _icon(svg,kind,x+w/2-26,y+3,fill)
        ty=y+79
        for line in svg.typ.wrap(label,w-8,15):svg.text(x+w/2,ty,line,15,weight=700,anchor='middle');ty+=20
        for line in svg.typ.wrap(detail,w-8,12) if detail else []:svg.text(x+w/2,ty,line,12,MUTED,anchor='middle');ty+=16
    svg.items.append('</g>')


def _route(edge, a, b, obstacles):
    """Use neighbouring corridors before an exterior return, with optional ports."""
    sides={'left','right','top','bottom'}
    sa=edge.get('from_port');sb=edge.get('to_port')
    if sa is not None or sb is not None:
        if sa not in sides or sb not in sides:raise ValueError('Set both from_port and to_port to left/right/top/bottom')
    elif edge.get('kind')=='feedback' and abs(a[0]-b[0])>1 and abs(a[1]-b[1])>1:
        sa='bottom' if b[1]>a[1] else 'top'
        sb='right' if a[0]>b[0] else 'left'
    else:
        return _edge_route(a,b,edge.get('kind','flow'),obstacles,24)
    route=_orthogonal_route(_port(a,sa,12),_port(b,sb,12),obstacles)
    return _clean_route([_port(a,sa)]+route+[_port(b,sb,4)])


def render(spec):
    data=spec['data'];nodes=_required_list(data,'nodes');edges=data.get('edges',[])
    _validate_graph(nodes,edges);pos=_positions(nodes,edges)
    variant=data.get('variant','runtime')
    if variant not in {'runtime','staged'}:raise ValueError('paper_flow variant must be runtime or staged')
    for n in nodes:
        if n.get('kind','process') not in KINDS:raise ValueError('Unsupported workflow node kind: '+str(n.get('kind')))
    svg=PaperSVG(spec);cols=max(c for r,c in pos.values())+1;rows=max(r for r,c in pos.values())+1
    margin=55;gx=70;gy=68
    for e in edges:
        if e.get('label'):
            tw=svg.typ.width(e['label'],12)
            if tw>150:raise ValueError('Keep edge labels short; put explanations in node detail')
            if pos[e['from']][0]==pos[e['to']][0]:gx=max(gx,tw+22)
    w=(svg.width-2*margin-gx*(cols-1))/cols
    if w<115:raise ValueError(f'paper_flow needs a wider canvas for {cols} columns')
    heights={}
    for n in nodes:
        kind=n.get('kind','process');pad=w*.2 if kind=='decision' else 12 if kind=='process' else 4
        lh=len(svg.typ.wrap(n.get('label',n['id']),w-2*pad,14 if kind=='decision' else 15))*20
        dh=len(svg.typ.wrap(n.get('detail',''),w-2*pad,12))*16 if n.get('detail') else 0
        if kind=='table':heights[n['id']]=sum(_table_plan(svg,n,w)[2])+14+lh+dh
        else:heights[n['id']]=max(78,lh+dh+35) if kind in {'process','decision'} else 83+lh+dh
    rowh=[max([heights[n['id']] for n in nodes if pos[n['id']][0]==r] or [100]) for r in range(rows)]
    groups=data.get('groups',[]);gids=[g.get('id') for g in groups]
    if len(set(gids))!=len(gids):raise ValueError('Group ids must be unique')
    for n in nodes:
        if n.get('group') and n['group'] not in gids:raise ValueError('Unknown group '+str(n['group']))
    ys=[svg.content_top+(31 if groups else 5)]
    for r in range(1,rows):ys.append(ys[-1]+rowh[r-1]+gy)
    boxes={n['id']:(margin+pos[n['id']][1]*(w+gx),ys[pos[n['id']][0]]+(rowh[pos[n['id']][0]]-heights[n['id']])/2,w,heights[n['id']]) for n in nodes}
    headers=[];group_boxes=[]
    for i,g in enumerate(groups):
        members=[boxes[n['id']] for n in nodes if n.get('group')==g['id']]
        if not members:raise ValueError('Every group needs member nodes')
        x=min(b[0] for b in members)-15;y=min(b[1] for b in members)-28
        right=max(b[0]+b[2] for b in members)+15;bottom=max(b[1]+b[3] for b in members)+15
        box=(x,y,right-x,bottom-y)
        if any(_rects_overlap(box,b) for b in group_boxes):raise ValueError('Group containers overlap; separate groups across rows/columns')
        group_boxes.append(box)
        # Only the title's actual footprint is an obstacle; a phase band is
        # not an impermeable wall for cross-stage evidence/retrieval arrows.
        headers.append((x,y,min(right-x,svg.typ.width(g.get('label',g['id']),14)+22),24))
        fill=g.get('color',('#EEF4F8','#FCF0EE','#EFF5EF')[i%3] if variant=='staged' else '#F7F7F7')
        svg.rect(*box,fill,g.get('border_color','#909090') if variant=='runtime' else 'none',r=2,
                 stroke_dasharray='3 3' if variant=='runtime' else 'none',data_role='stage',data_stage_id=g['id'])
        if g.get('header_color'):
            svg.rect(x,y,right-x,23,g['header_color'],'none',r=0)
        svg.text(x+10,y+17,g.get('label',g['id']),14,'white' if g.get('header_color') else INK,700)
    obstacles=[(x-12,y-12,nw+24,nh+24) for x,y,nw,nh in boxes.values()]+headers
    routes=[]
    for e in edges:
        kind=e.get('kind','flow');semantic=e.get('semantic','reject' if kind=='attack' else 'flow')
        if kind not in {'flow','feedback','attack','mapping'}:raise ValueError('Unknown edge kind '+str(kind))
        if semantic not in COLORS:raise ValueError('Unknown edge semantic '+str(semantic))
        route=_route(e,boxes[e['from']],boxes[e['to']],obstacles)
        routes.append(route);color=COLORS[semantic]
        svg.items.append(f'<g data-role="edge" data-from="{esc(e["from"])}" data-to="{esc(e["to"])}" data-kind="{kind}" data-semantic="{semantic}">')
        d='M '+' L '.join(f'{x:.2f},{y:.2f}' for x,y in route)
        _path(svg,d,stroke=color,width=1.6,dash='4 3' if e.get('dashed') else None)
        svg.arrowhead(*route[-2],*route[-1],color);svg.items.append('</g>')
    for n in nodes:_draw_node(svg,n,boxes[n['id']])
    occupied=[(x-3,y-3,nw+6,nh+6) for x,y,nw,nh in boxes.values()]+headers+[(0,0,svg.width,svg.content_top)]
    label_boxes=[]
    for e,route in zip(edges,routes):
        if not e.get('label'):continue
        label=str(e['label']);tw=svg.typ.width(label,12)
        x,y,lw,lh=_edge_label_box(route,tw+8,occupied,svg.width)
        color=COLORS[e.get('semantic','reject' if e.get('kind')=='attack' else 'flow')]
        svg.rect(x,y,lw,lh,'white','none',r=1,data_role='edge-label',data_from=e['from'],data_to=e['to'])
        svg.text(x+lw/2,y+14,label,12,color,anchor='middle');occupied.append((x-2,y-2,lw+4,lh+4));label_boxes.append((x,y,lw,lh))
    extent=max([y+h for x,y,w,h in boxes.values()]+[y+h for x,y,w,h in label_boxes]+[y for route in routes for x,y in route]+[y+h for x,y,w,h in group_boxes])
    legend=data.get('legend',[])
    if legend:
        xx=margin;yy=extent+25
        for item in legend:
            semantic=item.get('semantic','flow')
            if semantic not in COLORS:raise ValueError('Unknown legend semantic '+str(semantic))
            text=str(item['label']);lw=svg.typ.width(text,11)+55
            if xx+lw>svg.width-margin:xx=margin;yy+=22
            svg.line(xx,yy-4,xx+25,yy-4,COLORS[semantic],1.5,arrow=True)
            svg.text(xx+33,yy,text,11,MUTED);xx+=lw
        extent=yy
    return svg.finish(extent)
