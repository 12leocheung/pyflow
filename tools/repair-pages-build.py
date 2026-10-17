#!/usr/bin/env python3
"""Repair PyFlow's historical diff-prefixed HTML and prepare the Pages artifact."""
from pathlib import Path
import subprocess

page = Path('index.html')
html = page.read_text()
# Remove the accidental unified-diff markers from the actual source, so future
# edits and all deployments start from valid HTML.
html = '\n'.join(line[1:] if line.startswith('+') else line for line in html.splitlines()) + '\n'
html = html.replace('drag the + away to disconnect', 'drag a connector away to disconnect')
# Remove visible diff markers, including leading whitespace preserved by HTML parsing.
html = '\n'.join(line.lstrip()[1:] if line.lstrip().startswith('+') else line for line in html.splitlines()) + '\n'

canvas_css = '''
/* Size the canvas to its content and provide an inviting empty state. */
.canvas-inner{width:100%;height:100%;min-width:0;min-height:0}
.canvas-empty[hidden]{display:none}
.canvas-empty{position:absolute;inset:0;z-index:1;display:grid;place-items:center;padding:24px;pointer-events:none}
.canvas-empty-card{width:min(430px,100%);padding:25px;text-align:center;border:1px solid var(--line);border-radius:16px;background:color-mix(in srgb,var(--surface) 94%,transparent);box-shadow:var(--shadow);pointer-events:auto}
.canvas-empty-icon{width:44px;height:44px;margin:0 auto 12px;display:grid;place-items:center;border-radius:14px;background:var(--purple2);color:var(--purple);font-size:21px;font-weight:800}
.canvas-empty h2{margin:0 0 7px;font-size:19px;letter-spacing:-.4px}
.canvas-empty p{margin:0 auto 16px;max-width:330px;color:var(--muted);font-size:12px;line-height:1.65}
.canvas-empty-actions{display:flex;justify-content:center;flex-wrap:wrap;gap:8px}
.canvas-empty-actions button{min-height:40px;padding:0 13px;border:1px solid var(--line);border-radius:9px;background:var(--surface2);color:var(--ink);font-size:11px;font-weight:750}
.canvas-empty-actions .empty-primary{border-color:transparent;background:var(--purple);color:white}
.canvas-empty-actions button:hover{filter:brightness(1.08)}
'''
if '.canvas-empty{' not in html:
    if html.count('</style>') != 1:
        raise SystemExit('Expected exactly one inline stylesheet')
    html = html.replace('</style>', canvas_css + '\n</style>', 1)

canvas_open = '<div class="canvas-wrap" id="canvasWrap" tabindex="0" aria-label="Python node canvas. Drag nodes to arrange them.">'
empty_markup = '<div class="canvas-empty" id="canvasEmpty" hidden><div class="canvas-empty-card"><div class="canvas-empty-icon">＋</div><h2>Your canvas is ready</h2><p>Add a Python block from the toolbox, or load a tiny example project to see how nodes connect and run.</p><div class="canvas-empty-actions"><button class="empty-primary" id="loadSampleProject">Load sample project</button><button id="addFirstBlock">Add a print block</button></div></div></div>'
if 'id="canvasEmpty"' not in html:
    if html.count(canvas_open) != 1:
        raise SystemExit('Could not uniquely locate the canvas container')
    html = html.replace(canvas_open, canvas_open + empty_markup, 1)


def patch(old: str, new: str, label: str) -> None:
    global html
    if new in html:
        return
    count = html.count(old)
    if count != 1:
        raise SystemExit(f'Expected one {label} patch point, found {count}')
    html = html.replace(old, new, 1)


patch("const canvasInner=$('#canvasInner'),canvasWrap=$('#canvasWrap'),wires=$('#wires'),output=$('#output'),runStatus=$('#runStatus'),codeArea=$('#codeArea');",
      "const canvasInner=$('#canvasInner'),canvasWrap=$('#canvasWrap'),wires=$('#wires'),output=$('#output'),runStatus=$('#runStatus'),codeArea=$('#codeArea');\nconst canvasResizeObserver=new ResizeObserver(()=>{syncCanvasSize();drawWires()});canvasResizeObserver.observe(canvasWrap);", 'canvas resize observer')
patch("function render(){canvasInner.querySelectorAll('.node').forEach(n=>n.remove());nodes.forEach((n,i)=>{",
      "function render(){canvasInner.querySelectorAll('.node').forEach(n=>n.remove());$('#canvasEmpty').hidden=nodes.length>0;nodes.forEach((n,i)=>{", 'empty-state rendering')
patch("});drawWires();if(activeTab==='code')updateCodeFromNodes();}\nfunction plainDescription",
      "});syncCanvasSize();drawWires();if(activeTab==='code')updateCodeFromNodes();}\nfunction syncCanvasSize(){const width=Math.max(canvasWrap.clientWidth,...nodes.map(n=>n.x+360),520);const height=Math.max(canvasWrap.clientHeight,...nodes.map(n=>n.y+210),360);canvasInner.style.width=width+'px';canvasInner.style.height=height+'px'}\nfunction plainDescription", 'content-sized canvas')
html = html.replace('Math.max(1400,canvasInner.scrollWidth)', 'Math.max(1,canvasInner.scrollWidth)').replace('Math.max(900,canvasInner.scrollHeight)', 'Math.max(1,canvasInner.scrollHeight)')
html = html.replace("el.style.left=n.x+'px';el.style.top=n.y+'px';drawWires();save()", "el.style.left=n.x+'px';el.style.top=n.y+'px';syncCanvasSize();drawWires();save()")
html = html.replace("drag.el.style.left=n.x+'px';drag.el.style.top=n.y+'px';drawWires()", "drag.el.style.left=n.x+'px';drag.el.style.top=n.y+'px';syncCanvasSize();drawWires()")
patch("$$('.tool-node').forEach(btn=>btn.addEventListener('click',()=>addNode(btn.dataset.code.replace(/\\\\n/g,'\\n'),btn.dataset.kind)));",
      "$$('.tool-node').forEach(btn=>btn.addEventListener('click',()=>addNode(btn.dataset.code.replace(/\\\\n/g,'\\n'),btn.dataset.kind)));\n$('#loadSampleProject').onclick=()=>{snapshot();nodes=structuredClone(defaultNodes);connections=structuredClone(defaultConnections);selected=null;render();save();toast('Sample project loaded — press Run to try it')};\n$('#addFirstBlock').onclick=()=>addNode('print(\\\"Hello, world!\\\")','Output',150,100);", 'empty-state actions')
html = html.replace("window.addEventListener('resize',resizeTurtle);", "window.addEventListener('resize',()=>{syncCanvasSize();drawWires();resizeTurtle()});")
required = ['id="canvasEmpty"', 'id="loadSampleProject"', 'id="addFirstBlock"', 'function syncCanvasSize()']
if any(token not in html for token in required):
    raise SystemExit('Canvas feature verification failed')
if any(line.startswith('+') for line in html.splitlines()):
    raise SystemExit('Diff markers remain in the HTML source')
page.write_text(html)

# During Actions, commit the repaired canonical source back to main. The Pages
# artifact is built from these same verified bytes in this run.
if subprocess.run(['git', 'remote', 'get-url', 'origin'], capture_output=True).returncode == 0:
    subprocess.run(['git', 'config', 'user.name', 'github-actions[bot]'], check=True)
    subprocess.run(['git', 'config', 'user.email', '41898282+github-actions[bot]@users.noreply.github.com'], check=True)
    subprocess.run(['git', 'add', 'index.html'], check=True)
    changed = subprocess.run(['git', 'diff', '--cached', '--quiet']).returncode != 0
    if changed:
        subprocess.run(['git', 'commit', '-m', 'Repair PyFlow source and canvas experience'], check=True)
        subprocess.run(['git', 'push', 'origin', 'HEAD:main'], check=True)

Path('_site').mkdir(exist_ok=True)
Path('_site/index.html').write_text(html)
