"""Fabrique le PowerPoint de la démo : les mêmes écrans que la vidéo, la narration en notes du présentateur.

    .venv\\Scripts\\python.exe fabriquer.py --images     d'abord, pour (re)générer les écrans
    .venv\\Scripts\\python.exe presentation.py

Une diapositive par plan de la vidéo : les apparitions progressives deviennent des diapositives successives,
qu'on fait défiler comme des animations. Le texte dit dans la vidéo est dans les notes, invisible en projection.
"""
import sys
from pathlib import Path

from pptx import Presentation
from pptx.util import Emu

import scenario

ICI = Path(__file__).parent
IMAGES = ICI / "sortie" / "img"
FINAL = ICI / "sortie" / "RuntimeAsyncDemo.pptx"


def main():
    pres = Presentation()
    pres.slide_width, pres.slide_height = Emu(12_192_000), Emu(6_858_000)   # 16:9, 33,867 × 19,05 cm
    vierge = pres.slide_layouts[6]
    pres.core_properties.title = "Runtime Async (.NET 11) : la démo"
    pres.core_properties.language = "fr-FR"

    nombre = 0
    for no_scene, sc in enumerate(scenario.SCENES):
        for no_plan, texte in enumerate(sc["plans"]):
            image = IMAGES / f"s{no_scene:02}-p{no_plan:02}.png"
            if not image.exists():
                sys.exit(f"Écran manquant : {image}\nLancez d'abord : fabriquer.py --images")
            diapo = pres.slides.add_slide(vierge)
            photo = diapo.shapes.add_picture(str(image), 0, 0, pres.slide_width, pres.slide_height)
            photo.name = f"Écran {scenario.CHAPITRES[sc['chapitre']]} ({no_scene}.{no_plan})"
            diapo.notes_slide.notes_text_frame.text = texte
            nombre += 1

    pres.save(FINAL)
    print(f"Présentation : {FINAL}  ({nombre} diapositives, {FINAL.stat().st_size / 1e6:.1f} Mo)")


if __name__ == "__main__":
    main()
