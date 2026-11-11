"""Fabrique la vidéo de la démo à partir de scenario.py.

    .venv\\Scripts\\python.exe fabriquer.py              tout : images, voix, montage
    .venv\\Scripts\\python.exe fabriquer.py --images     les images seulement (pour relire les écrans)

Étapes : une page HTML par plan, rendue en image par Edge sans interface ; la narration synthétisée par edge-tts
(voix neurale en ligne) ; un segment vidéo par plan avec ffmpeg ; puis l'assemblage, avec sous-titres et chapitres.
"""
import asyncio
import hashlib
import re
import subprocess
import sys
import time
from pathlib import Path

import scenario

ICI = Path(__file__).parent
SORTIE = ICI / "sortie"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
VOIX = "fr-FR-VivienneMultilingualNeural"
DEBIT = "+0%"
AVANT, APRES, FIN_SCENE = 0.35, 0.45, 0.5      # silences autour de chaque plan, en secondes
FINAL = SORTIE / "RuntimeAsyncDemo.mp4"

# Ce que la voix doit prononcer autrement que ce qui est écrit (les sous-titres gardent le texte d'origine).
PRONONCIATION = [
    (".NET Conf", "dot net conf"), (".NET Core", "dot net core"), ("ASP.NET Core", "A S P dot net core"),
    (".NET", "dot net"), ("C#", "C sharp"), ("OpenAPI", "Open A P I"), ("CoreCLR", "Core C L R"),
    ("MAUI", "Maoui"), ("STS", "S T S"), ("LTS", "L T S"), ("DLL", "D L L"), ("SQL", "S Q L"),
    ("try catch", "try catch"), ("Directory.Build.props", "Directory Build props"),
]


def lancer(*args, **kw):
    return subprocess.run([str(a) for a in args], check=True, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", **kw)


def duree(fichier):
    r = lancer("ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", fichier)
    return float(r.stdout.strip())


# ───────────────────────────── images ─────────────────────────────

def page(scene, no_scene, no_plan):
    regles = []
    for n in range(no_plan + 1, 12):
        regles.append(f'[data-s="{n}"]{{visibility:hidden}}')
    for n in range(0, no_plan + 1):
        regles.append(f'[data-h="{n}"]{{display:none}}')
    regles.append(f'[data-f="{no_plan}"]{{background:rgba(139,123,255,.22);box-shadow:0 0 0 2px #8b7bff}}')
    chap = scene["chapitre"]
    avancement = 100 * (no_scene + 1) / len(scenario.SCENES)
    entete = "" if chap == 0 else (f'<header><span class="chap"><b>{chap}</b>{scenario.e(scenario.CHAPITRES[chap])}'
                                   f'</span><span class="marque">Runtime Async · .NET 11</span></header>')
    return (f'<!doctype html><html lang="fr"><meta charset="utf-8"><link rel="stylesheet" href="../../style.css">'
            f'<style>{"".join(regles)}</style><body>{entete}'
            f'<main class="{"milieu" if scene["centre"] else ""}">{scene["html"]}</main>'
            f'<footer style="width:{avancement:.1f}%"></footer></body></html>')


def rendre_images(plans):
    (SORTIE / "html").mkdir(parents=True, exist_ok=True)
    (SORTIE / "img").mkdir(exist_ok=True)
    for p in plans:
        p["html"].write_text(page(p["scene"], p["no_scene"], p["no_plan"]), encoding="utf-8")
        p["img"].unlink(missing_ok=True)
        lancer(EDGE, "--headless", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
               "--window-size=1920,1080", f"--user-data-dir={SORTIE / 'edge-profil'}",
               f"--screenshot={p['img']}", p["html"].as_uri())
        for _ in range(100):                      # Edge rend parfois la main avant d'avoir écrit le fichier
            if p["img"].exists() and p["img"].stat().st_size > 0:
                break
            time.sleep(0.1)
        else:
            sys.exit(f"Edge n'a pas produit {p['img']}")
        print("image", p["nom"])


# ───────────────────────────── voix ─────────────────────────────

def a_prononcer(texte):
    for ecrit, dit in PRONONCIATION:
        texte = texte.replace(ecrit, dit)
    return texte


async def synthetiser(plans):
    import edge_tts
    (SORTIE / "audio").mkdir(exist_ok=True)
    for p in plans:
        dit = a_prononcer(p["texte"])
        cle = hashlib.sha1(f"{VOIX}|{DEBIT}|{dit}".encode("utf-8")).hexdigest()[:16]
        p["audio"] = SORTIE / "audio" / f"{cle}.mp3"
        if not p["audio"].exists():
            provisoire = p["audio"].with_suffix(".tmp")
            for essai in range(5):                # le service refuse parfois une requête : on réessaie
                try:
                    await edge_tts.Communicate(dit, VOIX, rate=DEBIT).save(str(provisoire))
                    break
                except Exception as erreur:
                    print("voix ", p["nom"], "nouvel essai :", type(erreur).__name__)
                    await asyncio.sleep(2 + 2 * essai)
            else:
                sys.exit(f"Synthèse impossible pour {p['nom']} : {dit[:60]}…")
            provisoire.replace(p["audio"])
            print("voix ", p["nom"])
        p["duree_audio"] = duree(p["audio"])


# ───────────────────────────── montage ─────────────────────────────

def monter_segments(plans):
    (SORTIE / "seg").mkdir(exist_ok=True)
    for p in plans:
        fin = FIN_SCENE if p["dernier"] else 0
        total = AVANT + p["duree_audio"] + APRES + fin
        video = "fade=t=in:st=0:d=0.3,format=yuv420p" if p["no_plan"] == 0 else "format=yuv420p"
        lancer("ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-framerate", "30", "-i", p["img"],
               "-i", p["audio"], "-filter_complex",
               f"[0:v]{video}[v];[1:a]adelay={int(AVANT * 1000)}:all=1,apad[a]",
               "-map", "[v]", "-map", "[a]", "-t", f"{total:.3f}", "-r", "30",
               "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-tune", "stillimage",
               "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2", p["seg"])
        p["duree"] = duree(p["seg"])
        print("plan ", p["nom"], f"{p['duree']:.1f} s")


def decouper(texte, maxi=84):
    """Découpe une narration en sous-titres courts, aux fins de phrase puis aux virgules."""
    morceaux = []
    for phrase in re.split(r"(?<=[.?!])\s+", texte.strip()):
        while len(phrase) > maxi:
            coupes = [m.end() for m in re.finditer(r"[,:;] ", phrase) if 25 <= m.end() <= maxi]
            coupe = coupes[-1] if coupes else phrase.rfind(" ", 0, maxi) + 1
            morceaux.append(phrase[:coupe].strip())
            phrase = phrase[coupe:]
        morceaux.append(phrase.strip())
    return [m for m in morceaux if m]


def horodatage(t):
    h, reste = divmod(int(round(t * 1000)), 3_600_000)
    m, reste = divmod(reste, 60_000)
    s, ms = divmod(reste, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def ecrire_sous_titres_et_chapitres(plans):
    srt, chapitres, t, no = [], [], 0.0, 0
    for p in plans:
        if p["no_plan"] == 0 and (not chapitres or chapitres[-1][1] != p["scene"]["chapitre"]):
            chapitres.append((t, p["scene"]["chapitre"]))
        morceaux = decouper(p["texte"])
        total = sum(len(m) for m in morceaux)
        debut = t + AVANT
        for m in morceaux:
            fin = debut + p["duree_audio"] * len(m) / total
            no += 1
            srt.append(f"{no}\n{horodatage(debut)} --> {horodatage(fin)}\n{m}\n")
            debut = fin
        t += p["duree"]
    (SORTIE / "RuntimeAsyncDemo.srt").write_text("\n".join(srt), encoding="utf-8")

    meta = [";FFMETADATA1", "title=Runtime Async (.NET 11) : la démo", "language=fra"]
    for i, (debut, chap) in enumerate(chapitres):
        fin = chapitres[i + 1][0] if i + 1 < len(chapitres) else t
        meta += ["[CHAPTER]", "TIMEBASE=1/1000", f"START={int(debut * 1000)}", f"END={int(fin * 1000)}",
                 f"title={scenario.CHAPITRES[chap]}"]
    (SORTIE / "chapitres.txt").write_text("\n".join(meta) + "\n", encoding="utf-8")
    lignes = [f"{int(d // 60)}:{int(d % 60):02}  {scenario.CHAPITRES[c]}" for d, c in chapitres]
    (SORTIE / "chapitres-lisibles.txt").write_text("\n".join(lignes) + "\n", encoding="utf-8")
    return t


def assembler(plans):
    liste = SORTIE / "liste.txt"
    liste.write_text("".join(f"file 'seg/{p['seg'].name}'\n" for p in plans), encoding="utf-8")
    brut = SORTIE / "brut.mp4"
    lancer("ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", liste, "-c", "copy", brut,
           cwd=SORTIE)
    lancer("ffmpeg", "-y", "-loglevel", "error", "-i", brut, "-i", SORTIE / "RuntimeAsyncDemo.srt",
           "-i", SORTIE / "chapitres.txt", "-map", "0:v", "-map", "0:a", "-map", "1:0", "-map_metadata", "2",
           "-map_chapters", "2", "-c:v", "copy", "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "160k",
           "-ar", "48000", "-c:s", "mov_text",
           "-metadata:s:s:0", "language=fra", "-metadata:s:a:0", "language=fra", "-movflags", "+faststart", FINAL)
    brut.unlink()


def main():
    plans = []
    for no_scene, sc in enumerate(scenario.SCENES):
        for no_plan, texte in enumerate(sc["plans"]):
            nom = f"s{no_scene:02}-p{no_plan:02}"
            plans.append({"scene": sc, "no_scene": no_scene, "no_plan": no_plan, "texte": texte, "nom": nom,
                          "dernier": no_plan == len(sc["plans"]) - 1,
                          "html": SORTIE / "html" / f"{nom}.html", "img": SORTIE / "img" / f"{nom}.png",
                          "seg": SORTIE / "seg" / f"{nom}.mp4"})
    mots = sum(len(p["texte"].split()) for p in plans)
    print(f"{len(scenario.SCENES)} scènes, {len(plans)} plans, {mots} mots de narration")

    rendre_images(plans)
    if "--images" in sys.argv:
        return
    asyncio.run(synthetiser(plans))
    monter_segments(plans)
    total = ecrire_sous_titres_et_chapitres(plans)
    assembler(plans)
    print(f"Vidéo : {FINAL}  ({int(total // 60)} min {int(total % 60):02} s, "
          f"{FINAL.stat().st_size / 1e6:.1f} Mo)")


if __name__ == "__main__":
    main()
