import copy
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from schematics import render_schematic


def template(kind):
    return json.loads((ROOT/'assets/templates'/f'{kind}.json').read_text())


def text_of(svg):
    return ''.join(ET.fromstring(svg).itertext())


class SchematicTests(unittest.TestCase):
    def test_all_templates_are_editable_svg(self):
        for kind in ['architecture','comparison','trajectory','text_card','taxonomy']:
            with self.subTest(kind=kind):
                svg=render_schematic(template(kind));root=ET.fromstring(svg)
                self.assertEqual(root.tag,'{http://www.w3.org/2000/svg}svg')
                self.assertGreater(float(root.get('height')),100)
                self.assertIn('ILLUSTRATIVE EXAMPLE',text_of(svg))
                self.assertGreater(len(root.findall('.//{http://www.w3.org/2000/svg}text')),3)
    def test_graph_validation_and_variable_nodes(self):
        spec=template('architecture');spec['data']['edges'][0]['to']='missing'
        with self.assertRaisesRegex(ValueError,'unknown node'):render_schematic(spec)
        spec={'type':'architecture','title':'Four stages','data':{'nodes':[{'id':str(i),'label':'Stage '+str(i)} for i in range(4)],'edges':[{'from':str(i),'to':str(i+1)} for i in range(3)]},'width':1200}
        svg=render_schematic(spec)
        for i in range(4):self.assertIn('Stage '+str(i),text_of(svg))
        spec['data']['edges'].append({'from':'3','to':'0'})
        with self.assertRaisesRegex(ValueError,'cycle'):render_schematic(spec)
    def assert_architecture_geometry(self,spec):
        root=ET.fromstring(render_schematic(spec))
        def box(element):return tuple(float(element.get(k)) for k in ['x','y','width','height'])
        nodes={e.get('data-node-id'):box(e) for e in root.iter() if e.get('data-role')=='node'}
        edges=[e for e in root.iter() if e.get('data-role')=='edge']
        self.assertEqual(len(edges),len(spec['data']['edges']))
        for edge in edges:
            d=edge.find('{http://www.w3.org/2000/svg}path').get('d')
            coords=[float(v) for v in re.findall(r'-?\d+(?:\.\d+)?',d)]
            points=list(zip(coords[::2],coords[1::2]))
            for a,b in zip(points,points[1:]):
                self.assertTrue(abs(a[0]-b[0])<.02 or abs(a[1]-b[1])<.02)
                for node,(x,y,w,h) in nodes.items():
                    if abs(a[0]-b[0])<.02:
                        crossing=x+.02<a[0]<x+w-.02 and max(min(a[1],b[1]),y)<min(max(a[1],b[1]),y+h)-.02
                    else:
                        crossing=y+.02<a[1]<y+h-.02 and max(min(a[0],b[0]),x)<min(max(a[0],b[0]),x+w)-.02
                    self.assertFalse(crossing,f"{edge.get('data-from')}→{edge.get('data-to')} crosses {node}")
            # The visible line starts at its declared source, rather than at a
            # neighboring component concealed underneath an unrouted segment.
            x,y,w,h=nodes[edge.get('data-from')];sx,sy=points[0]
            self.assertTrue((abs(sx-x)<.02 or abs(sx-x-w)<.02) and y-.02<=sy<=y+h+.02 or (abs(sy-y)<.02 or abs(sy-y-h)<.02) and x-.02<=sx<=x+w+.02)
        labels=[e for e in root.iter() if e.get('data-role')=='edge-label']
        self.assertEqual(len(labels),sum(bool(e.get('label')) for e in spec['data']['edges']))
        for label in labels:
            lx,ly,lw,lh=box(label)
            for node,(x,y,w,h) in nodes.items():
                overlap=max(lx,x)<min(lx+lw,x+w)-.02 and max(ly,y)<min(ly+lh,y+h)-.02
                self.assertFalse(overlap,f"Label for {label.get('data-from')}→{label.get('data-to')} covers {node}")
        return root
    def test_architecture_multilingual_labels_and_cross_column_feedback(self):
        spec={'type':'architecture','title':'缓存与在线审查','data':{
            'nodes':[{'id':'cache','label':'缓存','row':0,'col':0},{'id':'checker','label':'在线审查器','row':0,'col':1},{'id':'executor','label':'执行器','row':0,'col':2},{'id':'audit','label':'审计日志','row':1,'col':1}],
            'edges':[{'from':'cache','to':'checker','label':'候选结果'},{'from':'checker','to':'executor','label':'允许'},{'from':'checker','to':'audit','label':'记录判定'},{'from':'audit','to':'cache','label':'更新缓存','kind':'feedback'}]}}
        for width in [1000,1450]:
            with self.subTest(width=width):
                spec['width']=width;self.assert_architecture_geometry(spec)
        # Wider Latin labels reserve actual measured space, too.
        spec['data']['edges'][0]['label']='candidate result'
        self.assert_architecture_geometry(spec)
        self.assert_architecture_geometry(template('architecture'))
    def test_architecture_nonadjacent_edges_avoid_intervening_nodes(self):
        spec={'type':'architecture','width':1400,'data':{
            'nodes':[{'id':f'n{r}{c}','label':f'Stage {r}, {c}','row':r,'col':c} for r in range(3) for c in range(3)],
            'edges':[{'from':'n00','to':'n02'},{'from':'n00','to':'n20'},{'from':'n22','to':'n00'},{'from':'n20','to':'n02'},{'from':'n22','to':'n01','kind':'feedback','label':'revision'}]}}
        self.assert_architecture_geometry(spec)
    def test_long_text_grows_without_discarding_evidence(self):
        spec=template('text_card');short=ET.fromstring(render_schematic(spec))
        spec['data']['cards'][0]['content']='\n'.join('evidence_row_%03d = %d'%(i,i) for i in range(50))
        svg=render_schematic(spec);long=ET.fromstring(svg)
        self.assertGreater(float(long.get('height')),float(short.get('height')))
        self.assertIn('evidence_row_049',text_of(svg))
        spec['height']=100
        with self.assertRaisesRegex(ValueError,'too small'):render_schematic(spec)
    def test_real_image_is_embedded_and_bbox_is_checked(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'screen.png';Image.new('RGB',(200,100),'white').save(path)
            spec={'type':'trajectory','width':700,'_base_dir':temp,'data':{'columns':1,'steps':[{'id':'t1','title':'Real evidence','action':'Recorded action','image':'screen.png','callouts':[{'x':.1,'y':.2,'width':.4,'height':.4}]}]}}
            self.assertIn('data:image/png;base64',render_schematic(spec))
            spec['data']['steps'][0]['callouts'][0]['x']=.9
            with self.assertRaisesRegex(ValueError,'outside'):render_schematic(spec)
            spec['data']['steps'][0]['image']='missing.png'
            with self.assertRaisesRegex(ValueError,'does not exist'):render_schematic(spec)
    def test_mapping_does_not_drop_fields(self):
        spec={'type':'taxonomy','data':{'variant':'mapping','mappings':[{'field':'field_'+str(i),'description':'Definition '+str(i)} for i in range(9)]}}
        svg=render_schematic(spec)
        for i in range(9):self.assertIn('field_'+str(i),text_of(svg));self.assertIn('Definition '+str(i),text_of(svg))
    def test_taxonomy_rejects_invented_multi_parent_tree(self):
        spec=template('taxonomy');spec['data']['edges'].append({'from':'internal','to':'injection'})
        with self.assertRaisesRegex(ValueError,'at most one parent'):render_schematic(spec)
    def test_comparison_has_all_conditions_and_events(self):
        spec=template('comparison');new=copy.deepcopy(spec['data']['columns'][0]);new['id']='review';new['title']='Manual review';new['status']='neutral';spec['data']['columns'].append(new);spec['width']=1200
        svg=render_schematic(spec)
        self.assertIn('Manual review',text_of(svg));self.assertEqual(text_of(svg).count('Outcome'),3)

if __name__=='__main__':unittest.main()
