import sys
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from compose import compose_svg
from render import render_spec

DUMMY='<svg xmlns="http://www.w3.org/2000/svg" width="300" height="200" viewBox="0 0 300 200"><defs><clipPath id="frame"><rect width="300" height="200"/></clipPath></defs><g clip-path="url(#frame)"><text x="10" y="20">Evidence</text></g></svg>'

class CompositionTests(unittest.TestCase):
    def test_28_panels_keep_all_content_and_unique_ids(self):
        s={'type':'multipanel','width':1400,'height':2100,'layout':{'rows':7,'cols':4},'panels':[{'id':str(i),'row':i//4,'col':i%4} for i in range(28)]}
        svg, manifest=compose_svg(s,lambda p:DUMMY)
        root=ET.fromstring(svg)
        ids=[e.attrib['id'] for e in root.iter() if 'id' in e.attrib]
        self.assertEqual(len(manifest['panels']),28)
        self.assertEqual(svg.count('>Evidence<'),28)
        self.assertEqual(len(ids),len(set(ids)))
        self.assertGreaterEqual(len(ids),28)
        for p in manifest['panels']:
            x,y,w,h=p['slot']
            self.assertLessEqual(x+w,1400)
            self.assertLessEqual(y+h,2100)

    def test_variable_spans_use_the_whole_shared_grid(self):
        spec={'layout':{'rows':2,'cols':2,'gap':20,'column_weights':[2,1]},'panels':[{'id':'a','row':0,'col':0},{'id':'b','row':1,'col':0},{'id':'c','row':0,'col':1,'rowspan':2}]}
        _,m=compose_svg(spec,lambda p:DUMMY)
        a,b,c=m['panels']
        self.assertAlmostEqual(a['slot'][2],b['slot'][2])
        self.assertAlmostEqual(c['slot'][3],a['slot'][3]+b['slot'][3]+20)
        self.assertAlmostEqual(a['slot'][2],2*c['slot'][2])

    def test_export_places_all_28_panels_in_their_slots(self):
        import pymupdf
        colors = ['#246c91', '#d68443', '#4e927b', '#8d6aa8']
        spec = {'width': 1400, 'height': 2100, 'layout': {'rows': 7, 'cols': 4},
                'panels': [{'id': str(i), 'row': i//4, 'col': i%4} for i in range(28)]}
        def colored(panel):
            color = colors[int(panel['id']) % 4]
            return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 200"><rect width="100%" height="100%" fill="{color}"/></svg>'
        svg, manifest = compose_svg(spec, colored)
        with pymupdf.open(stream=svg.encode(), filetype='svg') as doc:
            with pymupdf.open(stream=doc.convert_to_pdf(), filetype='pdf') as pdf:
                pix = pdf[0].get_pixmap(alpha=False)
                for i, panel in enumerate(manifest['panels']):
                    x, y, w, h = panel['rendered_bounds']
                    rgb = pix.pixel(round(x+w/2), round(y+h/2))
                    expected = tuple(int(colors[i % 4][j:j+2], 16) for j in (1, 3, 5))
                    self.assertEqual(rgb, expected, f'panel {i} missing or misplaced after PDF export')

    def test_overlap_and_out_of_bounds_rejected(self):
        for panels in [[{'id':'a','row':0,'col':0},{'id':'b','row':0,'col':0}], [{'id':'a','row':0,'col':2}]]:
            with self.assertRaises(ValueError):
                compose_svg({'layout':{'rows':1,'cols':2},'panels':panels},lambda p:DUMMY)

    def test_wrong_or_missing_data_status_does_not_silently_render(self):
        with self.assertRaisesRegex(ValueError,'data_status'):
            render_spec({'type':'bar'})

    def test_inline_panel_missing_both_inputs_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'exactly one'):
            render_spec({'type':'multipanel','data_status':'illustrative','panels':[{'id':'a'}]})

if __name__=='__main__':unittest.main()
