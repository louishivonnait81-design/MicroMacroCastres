#!/usr/bin/env python3
"""
test_editor.py — Test automatisé de l'éditeur de grille (fiche 002, partie B).

Ouvre index.html dans Chromium (Playwright), charge exemple_layout.json,
modifie 20 cases au pinceau, vérifie rectangle / seau / ligne droite /
annuler, crée un monument, exporte layout.json, puis valide l'export avec
pipeline/check_layout.py et vérifie que seules les cases attendues ont changé.

Usage : python3 tools/layout-editor/test_editor.py [--headed] [--shots DIR]
Dépendance : pip install playwright   (Chromium déjà installé)
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile

from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
INDEX = os.path.join(HERE, "index.html")
EXAMPLE = os.path.join(HERE, "exemple_layout.json")
CHECK = os.path.join(ROOT, "pipeline", "check_layout.py")


def cell_screen(page, x, y):
    """Coordonnées écran (page) du centre d'une case."""
    r = page.evaluate("(() => { const b = document.getElementById('c').getBoundingClientRect(); return [b.left, b.top]; })()")
    p = page.evaluate(f"window.editor.cellToScreen({x}, {y})")
    return r[0] + p["x"], r[1] + p["y"]


def drag(page, x0, y0, x1, y1, steps=12, modifiers=None):
    sx, sy = cell_screen(page, x0, y0)
    ex, ey = cell_screen(page, x1, y1)
    page.mouse.move(sx, sy)
    page.mouse.down()
    page.mouse.move(ex, ey, steps=steps)
    page.mouse.up()


def click_cell(page, x, y, modifiers=None):
    sx, sy = cell_screen(page, x, y)
    for k in modifiers or []:
        page.keyboard.down(k)
    page.mouse.click(sx, sy)
    for k in modifiers or []:
        page.keyboard.up(k)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--shots", help="dossier où enregistrer des captures d'écran")
    a = ap.parse_args()
    if not os.path.exists(EXAMPLE):
        subprocess.check_call([sys.executable, os.path.join(HERE, "make_exemple.py"), EXAMPLE])
    with open(EXAMPLE, encoding="utf-8") as f:
        example = json.load(f)
    cols, rows = example["cols"], example["rows"]
    orig = example["cells"].replace("\n", "")
    failures = []

    def check(cond, label):
        print(("  ok   " if cond else "  ÉCHEC ") + label)
        if not cond:
            failures.append(label)

    with sync_playwright() as p:
        exe = os.environ.get("CHROMIUM_PATH")
        if not exe:
            for cand in ("/opt/pw-browsers/chromium-1194/chrome-linux/chrome", "/opt/pw-browsers/chromium/chrome"):
                if os.path.exists(cand):
                    exe = cand
                    break
        browser = p.chromium.launch(headless=not a.headed, executable_path=exe)
        page = browser.new_page(viewport={"width": 1280, "height": 800}, accept_downloads=True)
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.goto("file://" + INDEX)

        print("chargement")
        page.set_input_files("#fLayout", EXAMPLE)
        page.wait_for_function("window.editor.layout && window.editor.layout.monuments.length === 6")
        check(page.evaluate("window.editor.grid") == orig, "grille chargée identique au fichier")
        check(page.text_content("#fname").strip() == "exemple_layout.json", "nom de fichier affiché")
        st = page.evaluate("window.editor.stats()")
        check(st["share"] == "52.0 %", f"part rues+places+parcs = {st['share']} (attendu 52.0 %)")
        check(st["narrow"] == 52, f"rues étroites = {st['narrow']} (attendu 52, cf. check_layout.py)")
        if a.shots:
            os.makedirs(a.shots, exist_ok=True)
            page.screenshot(path=os.path.join(a.shots, "01_charge.png"))

        print("pinceau : 20 cases en eau")
        page.keyboard.press("w")                      # type eau
        page.keyboard.press("c")                      # crayon
        drag(page, 5, 20, 24, 20, steps=40)           # 20 cases sur la ligne 20 (îlot)
        g = page.evaluate("window.editor.grid")
        painted = [i for i in range(len(g)) if g[i] != orig[i]]
        check(len(painted) == 20 and all(g[i] == "w" for i in painted), f"{len(painted)} cases modifiées en eau")
        check(all(i // cols == 20 and 5 <= i % cols <= 24 for i in painted), "les 20 cases sont celles visées")

        print("rectangle, seau, ligne droite, annuler")
        page.keyboard.press("P")                      # parc
        page.keyboard.press("e")                      # rectangle
        drag(page, 6, 24, 9, 26)
        g = page.evaluate("window.editor.grid")
        check(all(g[y * cols + x] == "P" for y in range(24, 27) for x in range(6, 10)), "rectangle 4×3 en parc")
        page.keyboard.press("q")                      # quai
        page.keyboard.press("g")                      # seau sur la place (p) : 240 cases
        click_cell(page, 40, 20)
        g = page.evaluate("window.editor.grid")
        check(g.count("q") == orig.count("q") + 240 and "p" not in g, "seau : la place passe en quai")
        page.keyboard.press("Meta+z")
        g = page.evaluate("window.editor.grid")
        check(g.count("p") == 240, "annuler restaure la place")
        page.keyboard.press("w"); page.keyboard.press("c")
        click_cell(page, 40, 34)
        click_cell(page, 50, 34, modifiers=["Shift"])   # ligne droite
        g = page.evaluate("window.editor.grid")
        check(all(g[34 * cols + x] == "w" for x in range(40, 51)), "Maj+clic trace une ligne droite de 11 cases")
        page.keyboard.press("Meta+z"); page.keyboard.press("Meta+z")
        g = page.evaluate("window.editor.grid")
        check(g[34 * cols + 45] == orig[34 * cols + 45], "deux annulations retirent la ligne")

        print("monument")
        page.keyboard.press("m")
        drag(page, 60, 4, 69, 9)                      # 10 × 6
        page.wait_for_selector("#monform:not([hidden])")
        page.fill("#mId", "test-monument")
        page.fill("#mLevels", "2")
        page.click("#mOk")
        mons = page.evaluate("window.editor.layout.monuments")
        m = [x for x in mons if x["id"] == "test-monument"]
        check(len(m) == 1 and (m[0]["x"], m[0]["y"], m[0]["w"], m[0]["h"], m[0]["levels"]) == (60, 4, 10, 6, 2),
              f"monument créé : {m}")
        page.keyboard.press("m")
        click_cell(page, 22, 20)                      # clic sur eveche → sélection
        check(page.input_value("#mId") == "eveche", "clic sur un monument existant le sélectionne")
        page.click("#mCancel")
        if a.shots:
            page.keyboard.press("c")
            page.screenshot(path=os.path.join(a.shots, "02_modifie.png"))

        print("export")
        with page.expect_download() as dl:
            page.click("#bExport")
        out = os.path.join(tempfile.mkdtemp(), "layout_export.json")
        dl.value.save_as(out)
        r = subprocess.run([sys.executable, CHECK, out], capture_output=True, text=True)
        print("  " + r.stdout.replace("\n", "\n  ").rstrip())
        check(r.returncode == 0, "check_layout.py accepte l'export")
        with open(out, encoding="utf-8") as f:
            exp = json.load(f)
        ge = exp["cells"].replace("\n", "")
        diff = [i for i in range(len(orig)) if ge[i] != orig[i]]
        check(len(diff) == 20 + 12, f"{len(diff)} cases diffèrent du fichier d'origine (attendu 32 : 20 eau + 12 parc)")
        check(len(exp["monuments"]) == 7 and exp["labels"] == example["labels"], "monuments (7) et labels exportés")
        check(exp["legend"] == example["legend"] and exp["cols"] == cols and exp["rows"] == rows, "légende et dimensions conservées")

        print("nouvelle grille et zoom")
        page.once("dialog", lambda d: d.accept())
        page.click("#bNew")
        check(page.evaluate("window.editor.grid") == "." * (cols * rows), "nouvelle grille vide 106 × 71")
        page.keyboard.press("+")
        check(page.evaluate("window.editor.layout.cols") == 106, "zoom sans erreur")

        check(not errors, "aucune erreur JavaScript : " + "; ".join(errors[:3]))
        browser.close()

    if failures:
        print(f"\n{len(failures)} échec(s)")
        sys.exit(1)
    print("\ntous les tests passent")


if __name__ == "__main__":
    main()
