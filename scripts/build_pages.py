"""Generate static, directly addressable portfolio pages from shared layout and content."""
from pathlib import Path
import json
from html import escape
ROOT=Path(__file__).resolve().parents[1]

def build_pages(data=None):
    if data is None:data=json.loads((ROOT/'content/projects.json').read_text())
    template=(ROOT/'templates/page.html').read_text()
    pages={'home':'Selected Work','about':'About','creative':'Creative','creative-direction':'Creative Direction','production':'Production','interactive':'Interactive','vibecoding':'Vibecoding','mixed-reality':'Mixed Reality','stills':'Stills','photography':'Photography','poster':'Poster'}
    for c in data['categories']:
        for p in c['projects']:
            if p.get('section') not in {'photography','poster'}:pages['project-'+p['id']]=p['title']['en']
    for page,title in pages.items():
        html=template.replace('data-page="home"',f'data-page="{escape(page,quote=True)}"').replace('<title>Xin(Robynn)Shen — Selected Work</title>',f'<title>{escape(title)} — Xin(Robynn)Shen</title>')
        (ROOT/'dist'/('index.html' if page=='home' else page+'.html')).write_text(html)
    valid={('index.html' if page=='home' else page+'.html') for page in pages}
    for output in (ROOT/'dist').glob('project-*.html'):
        if output.name not in valid:output.unlink()
    return len(pages)

if __name__=='__main__':print('Generated',build_pages(),'pages')
