import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from paper_trajectory import render, TraceCanvas, _lines

ROOT=Path(__file__).resolve().parents[1]
NS='{http://www.w3.org/2000/svg}'

class PaperTrajectoryTests(unittest.TestCase):
    def spec(self,name='trajectory'):
        return json.loads((ROOT/'assets/templates'/f'{name}.json').read_text())

    def test_both_archetypes_preserve_all_step_ids_and_annotations(self):
        for name in ['trajectory','trajectory_annotated']:
            spec=self.spec(name);svg=render(spec);root=ET.fromstring(svg)
            ids=[e.get('data-step') for e in root.iter() if e.get('data-role')=='trace-step']
            self.assertEqual(ids,[s['id'] for s in spec['data']['steps']])
            self.assertEqual(sum(e.get('data-role')=='screenshot' for e in root.iter()),len(ids))
            if name.endswith('annotated'):
                text=''.join(root.itertext())
                for s in spec['data']['steps']:
                    self.assertIn('annotation · '+s['id'],text)
                self.assertIn('policy_violation',text)

    def test_real_image_ratio_and_callout_geometry_are_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'screen.png';Image.new('RGB',(640,360),'white').save(path)
            spec={'type':'trajectory','width':1000,'data_status':'observed','_base_dir':temp,'data':{'steps':[{'id':'record-4','action':'click [12]','image':'screen.png','callouts':[{'x':.2,'y':.3,'width':.4,'height':.2}]}]}}
            root=ET.fromstring(render(spec));image=next(root.iter(NS+'image'));rect=next(e for e in root.iter() if e.get('data-role')=='callout')
            ix,iy,iw,ih=[float(image.get(k)) for k in ('x','y','width','height')]
            self.assertAlmostEqual(iw/ih,640/360)
            for actual,expected in zip([float(rect.get(k)) for k in ('x','y','width','height')],[ix+.2*iw,iy+.3*ih,.4*iw,.2*ih]):self.assertAlmostEqual(actual,expected,places=2)
            self.assertNotIn('ILLUSTRATIVE UI',''.join(root.itertext()))

    def test_invalid_step_identity_or_callout_is_rejected(self):
        spec=self.spec();spec['data']['steps'][1]['id']=spec['data']['steps'][0]['id']
        with self.assertRaisesRegex(ValueError,'unique'):render(spec)
        for invalid in [dict(x=-.1,y=.2,width=.3,height=.2),dict(x=.8,y=.2,width=.3,height=.2),dict(x=True,y=.2,width=.3,height=.2)]:
            spec=self.spec();spec['data']['steps'][0]['callouts']=[invalid]
            with self.assertRaises(ValueError):render(spec)

    def test_annotations_require_evidence_and_real_images_do_not_fall_back(self):
        spec=self.spec();spec['data']['variant']='annotated_run'
        with self.assertRaisesRegex(ValueError,'requires'):render(spec)
        spec=self.spec();s=spec['data']['steps'][0];s.pop('illustration');s['image']='absent.png'
        with self.assertRaisesRegex(ValueError,'does not exist'):render(spec)

    def test_a_highlight_survives_a_wrapped_trace_line(self):
        spec=self.spec();spec['data']['steps'][0]['highlights']=[{'text':'Internal budget: 42 units.','color':'#BA2C29'}]
        root=ET.fromstring(render(spec))
        group=next(e for e in root.iter() if e.get('data-role')=='trace-step' and e.get('data-step')=='t1')
        red=''.join(e.text or '' for e in group.iter(NS+'tspan') if e.get('fill')=='#BA2C29')
        self.assertIn('Internal budget: 42 units.',red)

    def test_legacy_steps_work_and_visible_title_is_opt_in(self):
        spec={'type':'trajectory','title':'Metadata title','data_status':'illustrative','data':{'steps':[{'id':'t','title':'Step 1','action':'Read','observation':'Visible','illustration':{'label':'Example page','lines':['A short value']}}]}}
        root=ET.fromstring(render(spec))
        self.assertEqual(root.find(NS+'title').text,'Metadata title')
        self.assertNotIn('Metadata title',[e.text for e in root.iter(NS+'text')])
        spec['style']={'show_title':True}
        self.assertIn('Metadata title',[e.text for e in ET.fromstring(render(spec)).iter(NS+'text')])

    def test_word_wrap_preserves_words_indentation_and_punctuation(self):
        canvas=TraceCanvas({'type':'trajectory','width':1000})
        examples=[
            '    "evidence": "Unrequested notes field was modified.",',
            '    "retained_issue": "Unrequested note remains."',
            'Observation: The update appears in the activity feed.',
            '    中文说明：任务已经完成，但无关字段仍然存在。',
        ]
        for raw in examples:
            with self.subTest(raw=raw):
                lines=_lines(canvas,raw,170,11.2,True)
                self.assertEqual(''.join(lines),raw)
                self.assertTrue(lines[0].startswith(raw[:len(raw)-len(raw.lstrip())]))
                for line in lines:
                    self.assertLessEqual(canvas.typ.width(line,11.2,True),170+.01)
                    self.assertNotIn(line.strip(),{'.',',','。','，',';',':','!','?'})
                for token in ('field','modified','remains','Observation','activity','feed'):
                    if token in raw:self.assertTrue(any(token in line for line in lines),token)

    def test_long_identifier_uses_bounded_fallback_without_losing_characters(self):
        canvas=TraceCanvas({'type':'trajectory','width':1000})
        raw='    identifier_'+'x'*90+'.'
        lines=_lines(canvas,raw,130,11.2,True)
        self.assertEqual(''.join(lines),raw)
        self.assertGreater(len(lines),2)
        self.assertTrue(lines[0].startswith('    '))
        self.assertNotEqual(lines[-1].strip(),'.')
        self.assertTrue(all(canvas.typ.width(line,11.2,True)<=130+.01 for line in lines))

    def test_annotations_align_to_their_step_and_long_verdicts_expand_the_row(self):
        spec=self.spec('trajectory_annotated')
        def geometry(value):
            root=ET.fromstring(render(value))
            steps={e.get('data-step'):e for e in root.iter() if e.get('data-role')=='trace-step'}
            annotations={e.get('data-step'):e for e in root.iter() if e.get('data-role')=='trace-annotation'}
            for sid,annotation in annotations.items():
                self.assertEqual(float(annotation.get('data-top')),float(steps[sid].get('data-top')))
                self.assertLessEqual(float(annotation.get('data-bottom')),float(steps[sid].get('data-bottom')))
            for a,b in zip(value['data']['steps'],value['data']['steps'][1:]):
                self.assertGreater(float(steps[b['id']].get('data-top')),float(steps[a['id']].get('data-bottom')))
            return steps
        short=geometry(spec)
        spec['data']['steps'][1]['annotation']={'details':['Long observed verdict entry '+str(i) for i in range(35)]}
        long=geometry(spec)
        self.assertGreater(float(long['step-2'].get('data-top')),float(short['step-2'].get('data-top')))

if __name__=='__main__':unittest.main()
