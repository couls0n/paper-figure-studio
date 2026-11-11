import json
from pathlib import Path
import re
import sys
import unittest
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from paper_architecture import render
from schematics import _segment_hits_rect, _rects_overlap


def template(name='architecture'):
    return json.loads((ROOT/'assets/templates'/f'{name}.json').read_text())


class PaperArchitectureTests(unittest.TestCase):
    def test_both_archetypes_preserve_nodes_edges_and_clear_geometry(self):
        for name in ('architecture','architecture_stages'):
            spec=template(name);root=ET.fromstring(render(spec))
            box=lambda e:tuple(float(e.get(k)) for k in ('x','y','width','height'))
            nodes={e.get('data-node-id'):box(e) for e in root.iter() if e.get('data-role')=='node'}
            edges=[e for e in root.iter() if e.get('data-role')=='edge']
            self.assertEqual(set(nodes),{n['id'] for n in spec['data']['nodes']})
            self.assertEqual(len(edges),len(spec['data']['edges']))
            kinds={e.get('data-kind') for e in root.iter() if e.get('data-role')=='component'}
            self.assertGreaterEqual(len(kinds),4)
            for e in edges:
                coords=[float(v) for v in re.findall(r'-?\d+(?:\.\d+)?',e.find('{http://www.w3.org/2000/svg}path').get('d'))]
                points=list(zip(coords[::2],coords[1::2]))
                for a,b in zip(points,points[1:]):
                    for rect in nodes.values():self.assertFalse(_segment_hits_rect(a,b,rect))
            for e in root.iter():
                if e.get('data-role')=='edge-label':self.assertFalse(any(_rects_overlap(box(e),r) for r in nodes.values()))

    def test_semantic_context_enters_checker_and_reject_returns_to_agent(self):
        root=ET.fromstring(render(template()))
        relations={(e.get('data-from'),e.get('data-to')):e.get('data-semantic') for e in root.iter() if e.get('data-role')=='edge'}
        self.assertEqual(relations['tasks','check'],'retrieve')
        self.assertEqual(relations['check','execute'],'allow')
        self.assertEqual(relations['check','feedback'],'reject')
        self.assertEqual(relations['feedback','agent'],'reject')

    def test_legacy_graph_fields_and_chinese_content_remain_usable(self):
        spec={'type':'architecture','width':1000,'data_status':'illustrative','data':{'nodes':[{'id':'a','label':'输入任务','detail':'保留用户限制'},{'id':'b','label':'检查动作'},{'id':'c','label':'执行工具'}],'edges':[{'from':'a','to':'b'},{'from':'b','to':'c'}]}}
        words=''.join(ET.fromstring(render(spec)).itertext())
        for label in ('输入任务','保留用户限制','检查动作','执行工具'):self.assertIn(label,words)
        self.assertIn('ILLUSTRATIVE EXAMPLE',words)

    def test_invalid_object_semantic_and_half_specified_ports_fail(self):
        for field,value in [('kind','unrecognised'),('semantic','safe-ish'),('from_port','top')]:
            spec=template()
            if field=='kind':spec['data']['nodes'][0][field]=value
            else:spec['data']['edges'][0][field]=value
            with self.assertRaises(ValueError):render(spec)

    def test_title_is_metadata_unless_requested_and_height_is_checked(self):
        spec=template();root=ET.fromstring(render(spec))
        self.assertEqual(root.find('{http://www.w3.org/2000/svg}title').text,spec['title'])
        self.assertNotIn(spec['title'],[e.text for e in root.findall('.//{http://www.w3.org/2000/svg}text')])
        spec['style']['show_title']=True
        self.assertIn(spec['title'],[e.text for e in ET.fromstring(render(spec)).findall('.//{http://www.w3.org/2000/svg}text')])
        spec['height']=100
        with self.assertRaisesRegex(ValueError,'too small'):render(spec)

    def test_table_node_keeps_structured_cells_and_grows_for_wrapped_content(self):
        spec=template('architecture_stages');root=ET.fromstring(render(spec))
        node=next(n for n in spec['data']['nodes'] if n['id']=='definitions')
        cells=[e for e in root.iter() if e.get('data-role')=='table-cell']
        self.assertEqual(len(cells),(1+len(node['rows']))*len(node['columns']))
        for row in [node['columns']]+node['rows']:
            for value in row:self.assertIn(str(value),''.join(root.itertext()))
        old_height=float(next(e for e in root.iter() if e.get('data-role')=='node' and e.get('data-node-id')=='definitions').get('height'))
        node['rows'][0][1]='A longer constraint that must wrap without hiding any source text'
        updated=ET.fromstring(render(spec))
        new_height=float(next(e for e in updated.iter() if e.get('data-role')=='node' and e.get('data-node-id')=='definitions').get('height'))
        self.assertGreater(new_height,old_height)
        node['rows'][0].append('extra')
        with self.assertRaisesRegex(ValueError,'column count'):render(spec)
        node['rows']=[['x',float('nan')]]
        with self.assertRaisesRegex(ValueError,'finite'):render(spec)


if __name__=='__main__':unittest.main()
