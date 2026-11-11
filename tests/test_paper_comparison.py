import copy
import json
from pathlib import Path
import sys
import unittest
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from paper_comparison import render, _rich_lines, CaseTypography
from schematics import SVG


def template(name='comparison'):
    return json.loads((ROOT/'assets/templates'/f'{name}.json').read_text())


class PaperComparisonTests(unittest.TestCase):
    def test_both_variants_keep_editable_content_and_source_reference(self):
        for name in ['comparison','comparison_scenarios']:
            spec=template(name);root=ET.fromstring(render(spec))
            events=[e for e in root.iter() if e.get('data-role')=='case-event']
            self.assertEqual(len(events),sum(len(c['events']) for c in spec['data']['columns']))
            self.assertGreater(len(root.findall('.//{http://www.w3.org/2000/svg}text')),10)
            self.assertIn('ILLUSTRATIVE EXAMPLE',''.join(root.itertext()))
            self.assertIn('figure',spec['style_reference'])

    def test_event_ids_align_even_when_condition_order_changes(self):
        spec=template();spec['data']['columns'][1]['events'].reverse()
        root=ET.fromstring(render(spec));positions={}
        for e in root.iter():
            if e.get('data-role')=='case-event':positions.setdefault(e.get('data-event-id'),[]).append(e.get('data-y'))
        self.assertTrue(all(len(set(ys))==1 for ys in positions.values()))
        self.assertEqual(set(positions),{'request','call','outcome'})

    def test_extra_condition_and_missing_event_do_not_drop_or_invent_rows(self):
        spec=template();third=copy.deepcopy(spec['data']['columns'][0]);third['id']='review';third['title']='Manual review';spec['data']['columns'].append(third);spec['width']=1200
        root=ET.fromstring(render(spec));self.assertEqual(''.join(root.itertext()).count('Outcome'),3)
        spec['data']['columns'][1]['events']=spec['data']['columns'][1]['events'][:-1]
        root=ET.fromstring(render(spec));events=[e for e in root.iter() if e.get('data-role')=='case-event']
        self.assertEqual(len(events),8)
        self.assertIn('—',''.join(root.itertext()))

    def test_cross_line_highlight_retains_all_marked_characters(self):
        svg=SVG({'width':600});svg.typ=CaseTypography({})
        phrase='first important constraint stays private'
        lines=_rich_lines(svg,'Before '+phrase+' after',100,15,False,[{'text':phrase,'color':'#CE3439'}])
        colored=''.join(text for _,spans in lines for text,color in spans if color=='#CE3439')
        self.assertEqual(''.join(colored.split()),''.join(phrase.split()))
        self.assertGreater(sum(any(c=='#CE3439' for _,c in spans) for _,spans in lines),1)

    def test_exported_monospace_highlight_does_not_overlap_following_text(self):
        import pymupdf
        svg=render(template())
        with pymupdf.open(stream=svg.encode(),filetype='svg') as source:
            with pymupdf.open(stream=source.convert_to_pdf(),filetype='pdf') as pdf:
                matches=[]
                for block in pdf[0].get_text('rawdict')['blocks']:
                    for line in block.get('lines',[]):
                        chars=[c for span in line['spans'] for c in span['chars']]
                        if 'ShareSummary(' in ''.join(c['c'] for c in chars):
                            matches.append(chars)
                            for a,b in zip(chars,chars[1:]):self.assertGreaterEqual(b['bbox'][0],a['bbox'][2]-.15)
                self.assertEqual(len(matches),2)

    def test_duplicate_ids_and_undersized_canvas_fail_clearly(self):
        spec=template();spec['data']['columns'][1]['id']=spec['data']['columns'][0]['id']
        with self.assertRaisesRegex(ValueError,'unique'):render(spec)
        spec=template();spec['height']=100
        with self.assertRaisesRegex(ValueError,'too small'):render(spec)
        spec=template();spec['data']['columns'][0]['events'].append(copy.deepcopy(spec['data']['columns'][0]['events'][0]))
        with self.assertRaisesRegex(ValueError,'event IDs'):render(spec)

if __name__=='__main__':unittest.main()
