"""
04_comparateur_angles.py — Fiche 005 : choisir l'angle de la caméra.

Rend une grille d'orientations × inclinaisons, chacune cadrée dans la feuille
75 × 110 portrait, puis assemble tout dans une page HTML autonome où Louis
fait glisser deux curseurs pour comparer et lit le taux de remplissage.

Usage :
  python3 pipeline/04_comparateur_angles.py [largeur_px]
Sortie : out/angles_castres.html (+ les PNG dans out/angles/)
"""

import base64
import io
import json
import os
import re
import subprocess
import sys

from PIL import Image

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BLOCKS = os.path.join(HERE, "data", "blocks.json")
RENDER = os.path.join(HERE, "pipeline", "02_build_blender.py")
OUT_DIR = os.path.join(HERE, "out", "angles")
OUT_HTML = os.path.join(HERE, "out", "angles_castres.html")

PAPER_W, PAPER_H = 75.0, 110.0          # feuille, en cm (DECISIONS.md)
PAPER = PAPER_W / PAPER_H
TURNS = [0, 10, 20, 30, 45]             # orientation : rotation de la ville
TILTS = [25, 35, 45, 54.7356]           # inclinaison : 54,7 = isométrie vraie, 0 = plan
THUMB_W = 760                           # largeur des images dans la page


def render(turn, tilt, width_px):
    name = "a_%03d_%03d" % (int(turn), round(tilt * 10))
    png = os.path.join(OUT_DIR, name + ".png")
    env = dict(os.environ, CASTRES_NAME=name)
    r = subprocess.run([sys.executable, RENDER, BLOCKS, OUT_DIR, str(width_px),
                        str(turn), str(tilt), "%.6f" % PAPER],
                       capture_output=True, text=True, env=env)
    m = re.search(r"cadrage : ville ([\d.]+):1, image (\d+) × (\d+), remplissage ([\d.]+)", r.stdout)
    if not m or not os.path.exists(png):
        raise SystemExit("rendu raté (%d°, %.1f°) :\n%s" % (turn, tilt, r.stdout[-2000:] + r.stderr[-2000:]))
    for junk in (name + ".blend", name + ".blend1"):
        j = os.path.join(OUT_DIR, junk)
        if os.path.exists(j):
            os.remove(j)
    return png, dict(ratio=float(m.group(1)), fill=float(m.group(4)))


def encode(png):
    im = Image.open(png).convert("L")
    im = im.resize((THUMB_W, round(THUMB_W * im.size[1] / im.size[0])), Image.LANCZOS)
    im = im.convert("P", palette=Image.ADAPTIVE, colors=32)
    buf = io.BytesIO()
    im.save(buf, format="PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


HTML = """<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8">
<title>Castres — choix de l'angle</title>
<style>
 :root { --ink:#1b1b1b; --line:#d5d5d5; --accent:#1f5fbf; }
 * { box-sizing:border-box; }
 body { margin:0; font:14px/1.5 -apple-system,Segoe UI,Roboto,sans-serif; color:var(--ink);
        background:#f4f4f4; display:flex; min-height:100vh; }
 aside { width:320px; flex:none; background:#fff; border-right:1px solid var(--line); padding:18px; }
 main { flex:1; display:flex; align-items:center; justify-content:center; padding:20px; }
 h1 { font-size:17px; margin:0 0 14px; }
 h2 { font-size:12px; letter-spacing:.08em; text-transform:uppercase; color:#777;
      margin:20px 0 6px; font-weight:600; }
 input[type=range] { width:100%; }
 .val { font-variant-numeric:tabular-nums; font-weight:600; }
 .hint { color:#666; font-size:12.5px; }
 figure { margin:0; background:#fff; border:1px solid #bbb; box-shadow:0 2px 12px rgba(0,0,0,.09);
          max-height:calc(100vh - 40px); }
 img { display:block; height:auto; max-height:calc(100vh - 42px); width:auto; }
 table { border-collapse:collapse; width:100%; margin-top:6px; font-size:12.5px; }
 td, th { padding:3px 4px; text-align:right; border-bottom:1px solid #eee; }
 th:first-child, td:first-child { text-align:left; }
 td.on { background:var(--accent); color:#fff; border-radius:3px; }
 .big { font-size:26px; font-weight:700; }
 kbd { font:11px Menlo,monospace; background:#eee; border:1px solid #ccc; border-radius:3px; padding:0 4px; }
</style></head><body>
<aside>
 <h1>Castres — choix de l'angle</h1>
 <p class="hint">Chaque image est cadrée dans la feuille __PW__ × __PH__ cm portrait.
 Le blanc autour de la ville, c'est du papier perdu.</p>

 <h2>Orientation</h2>
 <input type="range" id="sTurn" min="0" max="__NT__" step="1" value="2">
 <div>rotation de la ville : <span class="val" id="vTurn"></span></div>
 <p class="hint">0° : les rues partent droit vers le haut. 45° : vue de coin, façades des deux côtés.</p>

 <h2>Inclinaison</h2>
 <input type="range" id="sTilt" min="0" max="__NI__" step="1" value="1">
 <div>hauteur de l'œil : <span class="val" id="vTilt"></span></div>
 <p class="hint">25° : très plongeant, presque un plan. 54,7° : isométrie vraie, comme MicroMacro.</p>

 <h2>Remplissage de la feuille</h2>
 <div class="big" id="vFill"></div>
 <table id="grid"></table>
 <p class="hint">Flèches <kbd>←</kbd><kbd>→</kbd> orientation, <kbd>↑</kbd><kbd>↓</kbd> inclinaison.</p>
</aside>
<main><figure><img id="img" alt="rendu"></figure></main>
<script>
const DATA = __DATA__;
const TURNS = __TURNS__, TILTS = __TILTS__;
let i = 2, j = 1;
const $ = id => document.getElementById(id);
function fmt(x) { return (Math.round(x * 10) / 10).toString().replace('.', ',') + '°'; }
function key(a, b) { return a + '_' + b; }
function draw() {
  const t = TURNS[i], k = TILTS[j], d = DATA[key(t, k)];
  $('img').src = d.src;
  $('vTurn').textContent = fmt(t);
  $('vTilt').textContent = fmt(k);
  $('vFill').textContent = Math.round(d.fill) + ' %';
  $('sTurn').value = i; $('sTilt').value = j;
  let h = '<tr><th>incl. \\\\ orient.</th>' + TURNS.map(t => '<th>' + fmt(t) + '</th>').join('') + '</tr>';
  TILTS.forEach((k2, jj) => {
    h += '<tr><th>' + fmt(k2) + '</th>' + TURNS.map((t2, ii) =>
      '<td class="' + (ii === i && jj === j ? 'on' : '') + '">' +
      Math.round(DATA[key(t2, k2)].fill) + '</td>').join('') + '</tr>';
  });
  $('grid').innerHTML = h;
}
$('sTurn').oninput = e => { i = +e.target.value; draw(); };
$('sTilt').oninput = e => { j = +e.target.value; draw(); };
document.querySelectorAll('#grid').forEach(() => {});
addEventListener('keydown', e => {
  if (e.key === 'ArrowLeft') i = Math.max(0, i - 1);
  else if (e.key === 'ArrowRight') i = Math.min(TURNS.length - 1, i + 1);
  else if (e.key === 'ArrowUp') j = Math.min(TILTS.length - 1, j + 1);
  else if (e.key === 'ArrowDown') j = Math.max(0, j - 1);
  else return;
  e.preventDefault(); draw();
});
addEventListener('click', e => { if (e.target.id === 'img') { i = (i + 1) % TURNS.length; draw(); } });
draw();
</script></body></html>
"""


def main():
    width_px = int(sys.argv[1]) if len(sys.argv) > 1 else 900
    os.makedirs(OUT_DIR, exist_ok=True)
    data = {}
    for tilt in TILTS:
        for turn in TURNS:
            png, info = render(turn, tilt, width_px)
            data["%g_%g" % (turn, tilt)] = dict(src=encode(png), fill=info["fill"], ratio=info["ratio"])
            print("  %3d° / %5.1f° → remplissage %4.1f %%, ville %.2f:1" % (turn, tilt, info["fill"], info["ratio"]))
    html = (HTML.replace("__DATA__", json.dumps(data))
                .replace("__TURNS__", json.dumps(TURNS))
                .replace("__TILTS__", json.dumps(TILTS))
                .replace("__NT__", str(len(TURNS) - 1))
                .replace("__NI__", str(len(TILTS) - 1))
                .replace("__PW__", "%g" % PAPER_W).replace("__PH__", "%g" % PAPER_H))
    open(OUT_HTML, "w", encoding="utf-8").write(html)
    print("écrit %s (%.1f Mo, %d rendus)" % (OUT_HTML, os.path.getsize(OUT_HTML) / 1e6, len(data)))


if __name__ == "__main__":
    main()
