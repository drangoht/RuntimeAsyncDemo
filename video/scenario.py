"""Scénario de la vidéo : pour chaque scène, le contenu de l'écran (HTML) et la narration, plan par plan.

Dans le HTML, trois attributs pilotent l'affichage selon le numéro du plan (0, 1, 2…) :
  data-s="n"  l'élément apparaît à partir du plan n ;
  data-h="n"  l'élément disparaît à partir du plan n ;
  data-f="n"  l'élément est mis en évidence pendant le plan n seulement.
"""
import html
import re
from pathlib import Path

CAPTURES = Path(__file__).parent / "captures"

CHAPITRES = [
    "Runtime Async en .NET 11",
    "Une question pour commencer",
    "L'async en trois minutes",
    "Ce que le compilateur génère",
    "La pile d'appels",
    "Les mesures",
    "L'activer, et ses limites",
    ".NET Conf 2026 en bref",
    "Proposition pour le radar",
    "Pour aller plus loin",
]


# ───────────────────────────── aides de mise en forme ─────────────────────────────

def e(texte):
    return html.escape(texte, quote=False)


_MOTS = ("async|await|return|if|else|private|public|static|struct|class|void|var|new|ref|out|try|catch|goto|"
         "decimal|int|bool|string|this|throw|readonly|sealed|typeof")
_JETON = re.compile(r"(//[^\n]*)|(/\*[^\n]*?\*/)|(\"[^\"\n]*\")|\b(%s)\b|"
                    r"\b(Task|ValueTask|Client|Exception|AsyncHelpers|Builder|AsyncMethodBuilder|TaskAwaiter|MaTache|"
                    r"MaTacheBuilder)\b"
                    % _MOTS)
_XML = re.compile(r"(&lt;/?)([\w.]+)(&gt;)")


def cs(ligne):
    """Colore une ligne de C#."""
    morceaux, pos = [], 0
    for m in _JETON.finditer(ligne):
        morceaux.append(e(ligne[pos:m.start()]))
        classe = "com" if m.group(1) or m.group(2) else "str" if m.group(3) else "mot" if m.group(4) else "typ"
        morceaux.append(f'<span class="{classe}">{e(m.group(0))}</span>')
        pos = m.end()
    morceaux.append(e(ligne[pos:]))
    return "".join(morceaux)


def code(source, classe="", attrs=None, xml=False):
    """Bloc de code. `attrs` associe un numéro de ligne (à partir de 1) à des attributs HTML."""
    attrs = attrs or {}
    lignes = []
    for no, ligne in enumerate(source.strip("\n").split("\n"), 1):
        contenu = _XML.sub(r'\1<span class="typ">\2</span>\3', e(ligne)) if xml else cs(ligne)
        lignes.append(f'<span class="l" {attrs.get(no, "")}>{contenu or "&nbsp;"}</span>')
    return f'<pre class="code {classe}">{"".join(lignes)}</pre>'


def ligne_term(ligne, attrs=""):
    classe = ""
    if "← plomberie" in ligne or "← capture" in ligne:
        classe = "pl"
    elif "← le runtime" in ligne:
        classe = "rtl"
    elif ligne.startswith(("══", "──")):
        classe = "tt"
    elif ligne.strip().startswith(("►", "=>")):
        classe = "bil"
    elif ligne.startswith("PS>"):
        classe = "cmd"
    contenu = e(ligne) or "&nbsp;"
    if classe == "cmd":
        contenu = "<b>PS&gt;</b>" + contenu[6:]
    return f'<span class="l {classe}" {attrs}>{contenu}</span>'


def term(titre, blocs, classe="", gros=False):
    """Fenêtre de terminal. `blocs` : liste de (attributs HTML, texte) ou de HTML déjà prêt."""
    corps = []
    for bloc in blocs:
        if isinstance(bloc, str):
            corps.append(bloc)
        else:
            attrs, texte = bloc
            lignes = "".join(ligne_term(l) for l in texte.split("\n"))
            corps.append(f"<span {attrs}>{lignes}</span>")
    return (f'<div class="term {classe}"><div class="barre"><i></i><i></i><i></i><span>{e(titre)}</span></div>'
            f'<pre class="{"g" if gros else ""}">{"".join(corps)}</pre></div>')


def capture(nom):
    return (CAPTURES / f"{nom}.txt").read_text(encoding="utf-8").replace("\r", "")


def deux_modes(nom):
    """Coupe une sortie de voir-il en deux : mode classique, puis Runtime Async."""
    classique, runtime = capture(nom).strip().split("\n\n")
    return classique, runtime


def pile(nom, plomberie_async=False):
    """Pile d'appels capturée, avec les espaces de noms et les paramètres abrégés pour tenir à l'écran."""
    lignes = []
    for ligne in capture(nom).strip().split("\n")[3:]:
        court = re.sub(r"System\.Runtime\.CompilerServices\.|System\.Threading\.|RuntimeAsyncDemo\.Scenarios\.", "",
                       ligne)
        if court.startswith("   at "):
            court = re.sub(r"\(.+\)", "(…)", court).replace("`1", "")
        if "ChaineAppels" in court or "Program" in court:
            classe = "nous"
        elif "AsyncStateMachineBox" in court or "ExecutionContext" in court:
            classe = "pl"
        elif court.strip().startswith("=>"):
            classe = "bil"
        elif court.startswith("──"):
            classe = "tt"
        else:
            classe = "gris"
        lignes.append(f'<span class="l {classe}">{e(court) or "&nbsp;"}</span>')
    return "".join(lignes)


def barre(nom, sous, classique, runtime, txt_cl, txt_rt, attrs=""):
    """Deux barres comparées, la barre classique servant de référence (100 %)."""
    largeur = max(1.0, 100 * runtime / classique)
    if largeur < 22:
        bas = f'<div class="r dehors" style="width:{largeur:.1f}%"><em>{txt_rt}</em></div>'
    else:
        bas = f'<div class="r" style="width:{largeur:.1f}%">{txt_rt}</div>'
    return (f'<div class="rang" {attrs}><div class="nom">{nom}<small>{sous}</small></div><div class="b">'
            f'<div class="c" style="width:100%">{txt_cl}</div>{bas}</div></div>')


# ───────────────────────────── les scènes ─────────────────────────────

SCENES = []


def scene(chapitre, contenu, plans):
    # Centrée verticalement, sauf si un bloc en remplace un autre en cours de scène (le haut bougerait).
    SCENES.append({"chapitre": chapitre, "html": contenu, "plans": plans, "centre": "data-h=" not in contenu})


# 0 ─ Titre
scene(0, """
<div class="pleine">
  <div class="pastille" style="align-self:flex-start">Tech radar · démo</div>
  <h1>Runtime Async<br><span class="acc">.NET 11</span></h1>
  <h2 class="doux">Ce que ça change vraiment, mesuré en direct</h2>
  <div class="cols3" style="margin-top:30px">
    <div class="carte" data-s="1"><h3 class="acc">Comprendre</h3><ul><li>Une question</li><li>L'async en 3 minutes</li></ul></div>
    <div class="carte" data-s="1"><h3 class="acc">Voir</h3><ul><li>Le code généré</li><li>La pile d'appels</li><li>Les mesures</li></ul></div>
    <div class="carte" data-s="1"><h3 class="acc">Décider</h3><ul><li>Activation et limites</li><li>.NET Conf 2026</li><li>Le radar</li></ul></div>
  </div>
</div>
""", [
    "Runtime Async, c'est la nouveauté de .NET 11 qui change la façon dont async et await fonctionnent sous le capot. "
    "Dans cette démo, on va voir ce que ça change vraiment, le mesurer, et décider si ça mérite une place sur notre "
    "radar technique.",
    "Au programme : une question pour commencer, un rappel rapide sur l'asynchronisme, puis trois démonstrations : "
    "le code que le compilateur génère, la pile d'appels, et les mesures. On finira par l'activation, les limites, "
    "un mot sur la .NET Conf 2026, et une proposition pour le radar.",
])

# 1 ─ Accroche
ACCROCHE = """
async Task<decimal> LireRemiseAsync(int idClient)
{
    if (_cache.TryGetValue(idClient, out decimal remise))
        return remise;                                      // ① trouvée en mémoire : aucun await

    return await _baseDeDonnees.LireRemiseAsync(idClient);  // ② sinon : vraie attente
}
"""
scene(1, code(ACCROCHE, attrs={4: 'data-f="1"', 5: 'data-f="1"'}) + """
<h2 data-s="2" data-h="3">Dans le cas ①, un appel crée-t-il des objets en mémoire ?</h2>
<div class="choix" data-s="2" data-h="3">
  <div class="carte"><b>A</b>Aucun</div><div class="carte"><b>B</b>Un</div><div class="carte"><b>C</b>Plusieurs</div>
</div>
<div class="cols" data-s="3">
  <div class="carte cl"><h3 class="cl">.NET 10 : réponse B, un objet</h3>
    La signature promet un <b>Task&lt;decimal&gt;</b>, pas un decimal.<br>Il faut un objet Task pour transporter
    le résultat, <b>à chaque appel</b>.
    <div data-s="4" style="margin-top:22px"><span class="moyen cl">312 Ko</span><br>pour 1 000 commandes</div></div>
  <div class="carte rt" data-s="4"><h3 class="rt">Runtime Async : réponse A, aucun</h3>
    Quand l'appelant est lui aussi async, le résultat lui est passé directement, comme pour une méthode normale.
    <div style="margin-top:22px"><span class="moyen rt">0 octet</span><br>sans changer une ligne de code</div></div>
</div>
<div class="carte petit" data-s="5"><b>Et ValueTask ?</b> Il évite déjà cette allocation, mais il faut changer la
  signature de chaque méthode et de ses appelants. Runtime Async obtient le même effet sans rien toucher.</div>
""", [
    "Commençons par un code que tout le monde a déjà écrit. Une méthode async qui cherche une remise dans un cache. "
    "Si elle la trouve, elle la renvoie tout de suite. Sinon, elle interroge la base de données.",
    "Prenons le premier cas, le plus fréquent : la remise est déjà dans le cache. La méthode lit une valeur en "
    "mémoire et la renvoie. Elle n'exécute aucun await.",
    "D'où la question : dans ce cas, un appel à cette méthode crée-t-il des objets en mémoire, que le ramasse-miettes "
    "devra nettoyer ? Aucun, un, ou plusieurs ? Prenez quelques secondes pour y réfléchir.",
    "La plupart des gens répondent : aucun. Pourtant, en .NET 10, la bonne réponse est : un. La signature promet un "
    "Task de decimal, pas un decimal. Même si le résultat est déjà connu, il faut créer un objet Task pour le "
    "transporter jusqu'à l'appelant, et cela à chaque appel.",
    "Dans notre démo, traiter mille commandes crée ainsi 312 kilo-octets d'objets, uniquement pour transporter des "
    "résultats déjà connus. Avec Runtime Async, on passe à zéro octet, sans changer une seule ligne de code.",
    "Les plus expérimentés penseront à ValueTask. C'est vrai, ValueTask évite déjà cette allocation, mais il faut "
    "changer la signature de chaque méthode et de ses appelants. Runtime Async obtient le même effet sans rien "
    "toucher.",
])

# 2 ─ L'async en trois minutes
scene(2, """
<h2>Un restaurant : un serveur = un <span class="acc">thread</span>, la cuisine = la base de données</h2>
<div class="cols">
  <div class="carte cl" data-s="1"><h3 class="cl">Synchrone</h3>
    <div style="font-size:54px">🧑‍🍳 ⏳ 🍽️</div>
    Le serveur prend la commande, puis <b>attend devant la cuisine</b>.<br>
    <span class="doux">100 tables = 100 serveurs</span></div>
  <div class="carte rt" data-s="2"><h3 class="rt">Asynchrone (await)</h3>
    <div style="font-size:54px">🧑‍🍳 📝 🏃 🍽️ 🍽️ 🍽️</div>
    Il transmet la commande, <b>note où il en est</b>, et sert d'autres tables.<br>
    <span class="doux">Un serveur libre reprend quand le plat est prêt</span></div>
</div>
<div class="carte acc" data-s="3" data-h="4"><h3 class="acc">📝 La note, c'est l'état de la méthode</h3>
  <ul><li>la ligne où elle s'est arrêtée</li><li>la valeur de ses variables</li>
  <li>Une méthode normale ne sait pas le faire : ses variables vivent sur la <b>pile du thread</b>, et le thread
  est parti</li></ul></div>
<div class="cols" data-s="4">
  <div class="carte"><span class="rouge">✗ « async rend le code plus rapide »</span><br>
    Il permet de servir <b>plus de requêtes</b> avec peu de threads.</div>
  <div class="carte"><span class="rouge">✗ « async, c'est du parallélisme »</span><br>
    await <b>attend sans bloquer</b>, il ne lance rien en parallèle.</div>
</div>
""", [
    "Avant d'aller plus loin, un rappel rapide. Imaginez un restaurant. Un serveur, c'est un thread. La cuisine, "
    "c'est la base de données, ou une API distante.",
    "En synchrone, le serveur prend la commande, puis attend devant la cuisine sans rien faire. Pour servir cent "
    "tables, il faut cent serveurs.",
    "En asynchrone, avec await, le serveur transmet la commande, note où il en est, et part servir d'autres tables. "
    "Quand le plat est prêt, n'importe quel serveur libre reprend la commande.",
    "Le point clé pour la suite, c'est cette note. Pour reprendre plus tard, il faut sauvegarder l'état de la "
    "méthode : la ligne où elle s'est arrêtée, et la valeur de ses variables. Or une méthode normale ne sait pas "
    "faire ça. Ses variables vivent sur la pile du thread, et le thread est parti servir quelqu'un d'autre.",
    "Au passage, deux idées fausses. Async ne rend pas le code plus rapide : il permet de servir plus de requêtes "
    "avec peu de threads. Et async n'est pas du parallélisme : await attend sans bloquer, il ne lance rien en "
    "parallèle.",
])

# 3a ─ Le code source et l'outil
SOURCE_REMISE = """
private async Task<decimal> LireRemiseAsync(Client client)
{
    if (_simulerEntreesSorties) await Task.Yield();
    return client.Remise;
}
"""
scene(3, """
<h2>Jusqu'ici : le compilateur C# fabrique une <span class="cl">machine à états</span></h2>
<div class="doux">Notre méthode, dans <b>ServiceCommandes.cs</b> :</div>
""" + code(SOURCE_REMISE) + """
<div class="doux" data-s="1">Que contient réellement la DLL ? Un outil du dépôt la lit dans les deux modes :</div>
""" + '<div data-s="1">' + term("PowerShell", [("", "PS> dotnet run outils/voir-il.cs -- LireRemiseAsync")],
                                 gros=True) + "</div>", [
    "Jusqu'ici, c'est le compilateur C# qui se chargeait de cette sauvegarde. Il transformait chaque méthode async "
    "en ce qu'on appelle une machine à états. Prenons cette méthode de quatre lignes, tirée de la démo.",
    "Regardons ce qu'il y a réellement dans la DLL, avec un petit outil du dépôt, qui lit le code compilé dans les "
    "deux modes.",
])

# 3b ─ La sortie de voir-il
IL_CL, IL_RT = deux_modes("il-remise")
scene(3, term("PowerShell", [
    ("", "PS> dotnet run outils/voir-il.cs -- LireRemiseAsync"),
    ("", IL_CL + "\n"),
    ('data-s="2"', IL_RT),
]), [
    "En mode classique, notre méthode de quatre lignes n'existe plus vraiment. Elle crée un objet, la machine à "
    "états, puis la lance. Notre code a été déplacé dans une méthode MoveNext, et découpé en morceaux autour de "
    "chaque await.",
    "Toute la plomberie est visible, en orange : Create, Start, SetResult pour remplir le Task, et SetException, "
    "avec un try catch que nous n'avons jamais écrit.",
    "Maintenant, le même code, compilé avec Runtime Async. Il ne reste que notre méthode, presque telle quelle, avec "
    "un simple drapeau async. Le compilateur ne découpe plus rien : c'est le runtime qui sait suspendre et reprendre "
    "la méthode.",
    "Résultat : 239 octets de code intermédiaire d'un côté, 51 de l'autre. Presque cinq fois moins.",
])

# 3c ─ Côte à côte
PSEUDO_CL = """
Task<decimal> LireRemiseAsync(Client c)
{
  var m = new <LireRemiseAsync>d__9();
  m.client = c;  m.etat = -1;
  m.builder = Builder<decimal>.Create();
  m.builder.Start(ref m);          // → MoveNext
  return m.builder.Task;
}

struct <LireRemiseAsync>d__9
{
  void MoveNext()
  {
    try
    {
      if (etat == 0) goto Reprise;
      if (_simulerEntreesSorties)
      {
        att = Task.Yield().GetAwaiter();
        if (!att.IsCompleted)
        {
          etat = 0;                // le marque-page
          builder.AwaitUnsafeOnCompleted(ref att, ref this);
          return;                  // suspendue
        }
      Reprise:
        att.GetResult();
      }
      builder.SetResult(client.Remise);
    }
    catch (Exception e) { builder.SetException(e); }
  }
}
"""
PSEUDO_RT = """
// Une seule méthode, marquée « async » dans l'IL
Task<decimal> LireRemiseAsync(Client c)
{
  if (_simulerEntreesSorties)
  {
    var att = Task.Yield().GetAwaiter();
    if (!att.IsCompleted)
      AsyncHelpers.UnsafeAwaitAwaiter(att);
      // ↑ le runtime suspend et reprend ICI
    att.GetResult();
  }
  return c.Remise;
  // ↑ valeur renvoyée directement
}
"""
scene(3, """
<div class="cols" style="align-items:start">
  <div><h3 class="cl" style="margin-bottom:12px">Mode classique : la machine à états</h3>"""
      + code(PSEUDO_CL, "serre", {16: 'data-f="1"', 22: 'data-f="1"', 31: 'data-f="1"', 14: 'data-f="1"'}) + """</div>
  <div><h3 class="rt" style="margin-bottom:12px">Runtime Async (.NET 11)</h3>"""
      + code(PSEUDO_RT, "serre", {8: 'data-f="2"', 9: 'data-f="2"'}) + """
    <div class="cols" style="margin-top:30px" data-s="2">
      <div class="carte cl centre"><span class="moyen cl">239 octets</span><br>2 méthodes + 1 type</div>
      <div class="carte rt centre"><span class="moyen rt">51 octets</span><br>1 méthode</div>
    </div></div>
</div>
""", [
    "Traduit en C#, voici ce que ça donne, côte à côte.",
    "À gauche, la machine à états : un entier qui sert de marque-page, des sauts pour reprendre au bon endroit, et "
    "un try catch.",
    "À droite, notre méthode, avec un seul ajout : l'endroit où le runtime peut suspendre l'exécution.",
])

# 3d ─ Les exceptions
EX_CL, EX_RT = deux_modes("il-echec")
scene(3, term("PowerShell", [
    ("", "PS> dotnet run outils/voir-il.cs -- DescendreEtEchouerAsync"),
    ("", EX_CL + "\n"),
    ('data-s="1"', EX_RT),
]), [
    "Deuxième exemple : une méthode qui échoue. En mode classique, à chaque niveau, l'exception est attrapée, rangée "
    "dans le Task, puis relancée au niveau du dessus.",
    "Avec Runtime Async, aucun try catch n'est généré. L'exception remonte la pile une seule fois, comme en code "
    "synchrone. 228 octets contre 30.",
])

# 4a ─ La pile vivante
scene(4, """
<h2>La pile pendant l'exécution, juste après une reprise</h2>
<div class="cols" style="grid-template-columns:1.15fr 1fr;align-items:start">
  <div data-s="1">""" + term("Classique", [ligne_term("PS> dotnet run … -p:AsyncMode=compiler -- pile"),
                                           pile("pile-compiler")], "cl") + """</div>
  <div data-s="2">""" + term("Runtime Async", [ligne_term("PS> dotnet run … -p:AsyncMode=runtime -- pile"),
                                               pile("pile-runtime")], "rt") + """</div>
</div>
<div class="cols" style="grid-template-columns:1.15fr 1fr">
  <div class="carte cl centre" data-s="1"><span class="moyen cl">10 cadres</span> dont 5 de plomberie async</div>
  <div class="carte rt centre" data-s="2"><span class="moyen rt">5 cadres</span> notre code, puis le pool</div>
</div>
<div class="doux petit">Sorties réelles ; espaces de noms et paramètres abrégés pour tenir à l'écran.</div>
""", [
    "Conséquence visible au quotidien : la pile d'appels, celle que vous voyez dans le débogueur ou le profileur. "
    "On lance la même commande dans les deux modes.",
    "En mode classique, juste après une reprise, la pile compte dix cadres. Entre le pool de threads et notre code, "
    "il y a cinq cadres de plomberie async, en orange.",
    "Avec Runtime Async, il n'en reste que cinq : notre méthode, posée directement sur le pool de threads.",
])

# 4b ─ Le point d'honnêteté
scene(4, """
<h2>Point d'honnêteté : la pile d'une <span class="acc">exception</span> ne change pas</h2>
<div class="cols" style="align-items:start">
  """ + term("Classique", [pile("exception-compiler")], "cl") + term("Runtime Async", [pile("exception-runtime")], "rt") + """
</div>
<div class="carte acc" data-s="1">.NET nettoie déjà ces piles depuis .NET Core 2.1.<br>
  Le gain de lisibilité concerne le <b>débogueur</b>, les <b>profileurs</b> et les <b>dumps mémoire</b>,
  pas les logs d'exception.</div>
""", [
    "Un point d'honnêteté. La pile d'une exception, celle qu'on lit dans les logs, est strictement identique dans "
    "les deux modes.",
    ".NET nettoie déjà ces piles depuis .NET Core 2.1. Le gain de lisibilité concerne donc le débogueur, les "
    "profileurs et les dumps mémoire, pas les logs d'exception.",
])

# 5a ─ Mesure rapide
def _mesures(nom):
    return "\n".join(capture(nom).strip().split("\n")[3:])


scene(5, """<h2>Mesure rapide, au chronomètre</h2>"""
      + term("Classique", [("", "PS> dotnet run -c Release --project src/RuntimeAsyncDemo.Demo -p:AsyncMode=compiler -- mesures"),
                           ('data-s="1"', _mesures("mesures-compiler"))], "cl")
      + term("Runtime Async", [("", "PS> dotnet run -c Release --project src/RuntimeAsyncDemo.Demo -p:AsyncMode=runtime -- mesures"),
                               ('data-s="1"', _mesures("mesures-runtime"))], "rt")
      + """<div class="carte petit" data-s="2">Ces mesures « maison » servent à <b>illustrer</b>, pas à prouver.
      Les quelques octets restants en Runtime Async viennent de la boucle de mesure elle-même.</div>""", [
    "Passons aux mesures. D'abord une mesure rapide, au chronomètre, intégrée à la démo.",
    "Le service de commandes, quand tout est en cache : 299 nanosecondes en classique, 130 avec Runtime Async. "
    "Une exception qui remonte dix niveaux : 20 microsecondes, contre moins de 6.",
    "Ces mesures maison servent à illustrer, pas à prouver. Pour des chiffres rigoureux, on utilise BenchmarkDotNet.",
])

# 5b ─ BenchmarkDotNet en direct
scene(5, """<h2>BenchmarkDotNet : même code, même runtime, deux compilations</h2>"""
      + term("PowerShell", [("", "PS> dotnet run -c Release --project src/RuntimeAsyncDemo.Benchmarks -- --filter *ExceptionsBench*")])
      + """
<table data-s="1">
  <tr><th>Exception remontée</th><th>Mode</th><th class="n">Profondeur</th><th class="n">Temps moyen</th>
      <th class="n">Ratio</th><th class="n">Mémoire allouée</th><th class="n">Ratio</th></tr>
  <tr><td></td><td class="cl">Classique</td><td class="n">1</td><td class="n">4,01 µs</td><td class="n">1,00</td><td class="n">1 640 o</td><td class="n">1,00</td></tr>
  <tr><td></td><td class="rt"><b>RuntimeAsync</b></td><td class="n">1</td><td class="n"><b>1,45 µs</b></td><td class="n"><b>0,36</b></td><td class="n"><b>464 o</b></td><td class="n"><b>0,28</b></td></tr>
  <tr><td></td><td class="cl">Classique</td><td class="n">5</td><td class="n">11,07 µs</td><td class="n">1,00</td><td class="n">6 488 o</td><td class="n">1,00</td></tr>
  <tr><td></td><td class="rt"><b>RuntimeAsync</b></td><td class="n">5</td><td class="n"><b>2,91 µs</b></td><td class="n"><b>0,26</b></td><td class="n"><b>760 o</b></td><td class="n"><b>0,12</b></td></tr>
  <tr data-f="1"><td></td><td class="cl">Classique</td><td class="n">20</td><td class="n">32,37 µs</td><td class="n">1,00</td><td class="n">39 576 o</td><td class="n">1,00</td></tr>
  <tr data-f="1"><td></td><td class="rt"><b>RuntimeAsync</b></td><td class="n">20</td><td class="n"><b>7,62 µs</b></td><td class="n"><b>0,24</b></td><td class="n"><b>2 376 o</b></td><td class="n"><b>0,06</b></td></tr>
</table>
<div class="doux petit" data-s="1">Série courte lancée en direct (3 itérations, environ 50 secondes), Ryzen 7 9800X3D, runtime 11.0.0.</div>
""", [
    "BenchmarkDotNet recompile le projet deux fois, une fois par mode, lance chaque version dans un processus séparé, "
    "puis compare. C'est le même code source et le même runtime : seule la compilation des méthodes async change.",
    "Voici le résultat pour les exceptions. Sur vingt niveaux, on passe de 32 microsecondes à moins de 8, et la "
    "mémoire allouée est divisée par près de dix-sept.",
])

# 5c ─ Résultats complets
scene(5, """
<h2>Série complète : trois messages</h2>
<div class="carte dense"><h3><span class="pastille">1</span>&nbsp; Le plus gros gain est sur le cas le plus courant
  <span class="doux petit">&nbsp; 1 000 commandes, tout en cache</span></h3><div class="barres">"""
      + barre("Temps", "", 60.1, 30.0, "Classique · 60,1 µs", "Runtime Async · 30,0 µs")
      + barre("Mémoire allouée", "", 312, 0, "Classique · 312 Ko", "0 octet") + """</div></div>
<div class="carte dense" data-s="1"><h3><span class="pastille">2</span>&nbsp; Plus la chaîne est profonde, plus on gagne
  <span class="doux petit">&nbsp; appels sans attente</span></h3><div class="barres">"""
      + barre("Profondeur 5", "", 55, 24, "55 ns", "24 ns · ×2,3")
      + barre("Profondeur 20", "", 253, 58, "253 ns", "58 ns · ×4,4") + """</div></div>
<div class="carte dense" data-s="2"><h3><span class="pastille">3</span>&nbsp; Les exceptions remontent bien plus vite
  <span class="doux petit">&nbsp; 20 niveaux</span></h3><div class="barres">"""
      + barre("Temps", "", 32.14, 7.32, "32,1 µs", "7,3 µs · ×4,4")
      + barre("Mémoire allouée", "", 39576, 2376, "39 576 octets", "2 376 octets · 17 fois moins") + """</div></div>
""", [
    "Sur la série complète, trois messages. Premier message : le plus gros gain concerne le cas le plus courant, "
    "des appels async qui se terminent tout de suite. Pour mille commandes en cache, on passe de 312 kilo-octets à "
    "zéro, et c'est deux fois plus rapide.",
    "Deuxième message : plus la chaîne d'appels est profonde, plus on gagne. Jusqu'à quatre fois plus rapide sur "
    "vingt niveaux. Nos architectures en couches, contrôleur, service, dépôt, client HTTP, sont exactement dans "
    "ce cas.",
    "Troisième message : les exceptions remontent de deux à quatre fois plus vite, avec jusqu'à dix-sept fois moins "
    "de mémoire.",
])

# 5d ─ Le garde-fou
scene(5, """
<div class="pleine">
  <h2>Le garde-fou</h2>
  <div class="carte acc" style="font-size:38px">Ces gains portent sur la <b>mécanique async</b>, pas sur l'attente.
    <div class="doux" style="margin-top:14px">Une requête SQL de 2 ms reste une requête de 2 ms.</div></div>
  <div class="cols3" data-s="1">
    <div class="carte centre"><span class="moyen rt">−</span><br>de processeur</div>
    <div class="carte centre"><span class="moyen rt">−</span><br>de ramasse-miettes</div>
    <div class="carte centre"><span class="moyen rt">+</span><br>de latences régulières</div>
  </div>
</div>
""", [
    "Un garde-fou, tout de même. Ces gains portent sur la mécanique async, pas sur l'attente elle-même. Une requête "
    "SQL de deux millisecondes reste une requête de deux millisecondes.",
    "Le gain se voit sur un service très sollicité : moins de processeur, moins de ramasse-miettes, donc des "
    "latences plus régulières.",
])

# 6 ─ Activation et limites
PROPS = """
<PropertyGroup>
  <TargetFramework>net11.0</TargetFramework>
  <Features>$(Features);runtime-async=on</Features>
</PropertyGroup>
"""
scene(6, """<h2>Une ligne dans <span class="acc">Directory.Build.props</span>, zéro changement de code</h2>"""
      + code(PROPS, attrs={3: 'data-f="0"'}, xml=True) + """
<div class="cols">
  <div class="carte rt" data-s="1"><h3 class="rt">Les bonnes nouvelles</h3><ul>
    <li>Mêmes async, await et Task</li><li>Pas besoin de EnablePreviewFeatures</li>
    <li>Les bibliothèques de .NET 11 sont <b>déjà compilées</b> en Runtime Async</li></ul></div>
  <div class="carte cl" data-s="2"><h3 class="cl">Les limites</h3><ul>
    <li>Encore <b>en preview</b> dans la version finale de .NET 11</li>
    <li><b>Pas activée par défaut</b> pour notre code</li>
    <li data-s="3">Piège : pas de recompilation incrémentale<br><span class="doux petit">dotnet build --no-incremental</span></li>
    <li data-s="3">Vérifier : drapeau async (0x2000) sur la méthode</li></ul></div>
</div>
""", [
    "Comment l'activer ? Une seule ligne dans le fichier projet, ou dans un Directory.Build.props pour toute la "
    "solution. Aucun changement de code : mêmes async, mêmes await, mêmes Task.",
    "Bonne nouvelle : les bibliothèques de .NET 11 sont déjà compilées en Runtime Async. On en profite donc en "
    "partie dès le passage à .NET 11.",
    "Maintenant, les limites. C'est encore une fonctionnalité en preview dans la version finale de .NET 11, et elle "
    "n'est pas activée par défaut pour notre code.",
    "Un piège pratique : changer cette option ne déclenche pas de recompilation incrémentale. Il faut forcer une "
    "recompilation complète. Et pour vérifier que c'est bien actif, on regarde le drapeau async sur la méthode, "
    "comme le fait notre outil.",
])

# 6 bis ─ Ce qui garde la machine à états (vérifié sur le SDK 11.0.100)
TASK_LIKE = """
// Type « task-like » : il désigne son builder
[AsyncMethodBuilder(typeof(MaTacheBuilder))]
public readonly struct MaTache(Task tache)
{
    public TaskAwaiter GetAwaiter()
        => tache.GetAwaiter();
}

// Create, Start, SetResult, SetException…
public sealed class MaTacheBuilder { /* … */ }

// Machine à états générée, comme avant
public async MaTache EnvoyerAsync()
{
    await Task.Yield();
}
"""
scene(6, """<h2>Ce qui garde la <span class="cl">machine à états</span> du compilateur</h2>
<div class="cols" style="grid-template-columns:1fr 1.22fr">
  <div style="display:flex;flex-direction:column;gap:26px">
    <div class="carte cl"><h3 class="cl">Même avec l'option activée</h3><ul>
      <li><b>async void</b><br><span class="doux petit">gestionnaires d'événements</span></li>
      <li><b>Itérateurs asynchrones</b><br><span class="doux petit">IAsyncEnumerable&lt;T&gt; avec await et yield return</span></li>
      <li><b>Types task-like personnalisés</b><br><span class="doux petit">tout type désigné par [AsyncMethodBuilder] : UniTask (Unity)…</span></li>
    </ul></div>
    <div class="carte rt" data-s="2"><h3 class="rt">Passent bien en Runtime Async</h3><ul>
      <li>Task, Task&lt;T&gt;, ValueTask, ValueTask&lt;T&gt;</li>
      <li>Lambdas et fonctions locales async</li>
      <li>Vérifié sur le SDK 11.0.100, drapeau 0x2000</li>
    </ul></div>
  </div>
  <div data-s="1">""" + code(TASK_LIKE, "moyen-code", {2: 'data-f="1"', 13: 'data-f="1"'}) + """</div>
</div>
""", [
    "Dernière limite : certaines méthodes async gardent la machine à états du compilateur, même avec l'option "
    "activée. Les méthodes async void, qu'on trouve dans les gestionnaires d'événements. Les itérateurs asynchrones, "
    "qui renvoient un IAsyncEnumerable avec await et yield return. Et les méthodes qui renvoient un type task-like "
    "personnalisé.",
    "Un type task-like, c'est un type qu'une méthode async peut renvoyer à la place de Task. Grâce à l'attribut "
    "AsyncMethodBuilder, il désigne le builder que le compilateur doit appeler : Create, Start, SetResult, et ainsi de "
    "suite. L'exemple le plus connu est UniTask, dans Unity. Pour ces types, le compilateur génère toujours la machine "
    "à états.",
    "Nous l'avons vérifié avec le SDK final : ces trois cas gardent leur machine à états, alors que Task, ValueTask, "
    "les lambdas et les fonctions locales async passent bien en Runtime Async. Rien de bloquant : ces méthodes "
    "fonctionnent comme avant, elles ne profitent simplement pas du gain.",
])

# 7 ─ .NET Conf 2026
scene(7, """
<h2>.NET Conf 2026 <span class="doux">· du 10 au 13 novembre</span></h2>
<div class="cols">
  <div class="carte rt"><h3 class="rt">.NET 11</h3>Version finale le <b>10 novembre 2026</b><br>
    STS : <b>2 ans de support</b></div>
  <div class="carte rouge" data-s="1"><h3 class="rouge">⚠ Fin de support</h3><b>.NET 8 et .NET 9</b> ne sont plus
    supportés depuis le 10 novembre 2026<br><span class="doux">.NET 10 (LTS) reste la cible stable</span></div>
</div>
<div class="cols">
  <div class="carte" data-s="2"><h3 class="acc">C# 15</h3>Types union et hiérarchies fermées (closed)</div>
  <div class="carte" data-s="2"><h3 class="acc">Runtime Async</h3>Session dédiée : « Memory Safety and Runtime
    Async », Richard Lander et Andy Gocke</div>
</div>
<div class="cols3 petit" data-s="3">
  <div class="carte"><b>SDK</b><br>CLI plus rapide, applications en un seul fichier</div>
  <div class="carte"><b>ASP.NET Core</b><br>OpenAPI 3.2 par défaut, validation asynchrone</div>
  <div class="carte"><b>MAUI</b><br>CoreCLR devient le runtime par défaut</div>
</div>
""", [
    "Un mot sur la .NET Conf 2026, qui s'est tenue du 10 au 13 novembre. .NET 11 est sorti en version finale le "
    "10 novembre. C'est une version STS, avec deux ans de support.",
    "Point d'attention : .NET 8 et .NET 9 ne sont plus supportés depuis cette même date. .NET 10, la version LTS, "
    "reste la cible stable.",
    "Côté langage, C# 15 apporte les types union et les hiérarchies fermées. Et Runtime Async a eu sa session "
    "dédiée, présentée par Richard Lander et Andy Gocke.",
    "À noter aussi : une ligne de commande plus rapide, les applications en un seul fichier, OpenAPI 3.2 par défaut "
    "dans ASP.NET Core, et CoreCLR qui devient le runtime par défaut de MAUI. D'ailleurs, l'outil que vous avez vu "
    "tout à l'heure est lui-même une application en un seul fichier.",
])

# 8 ─ Le radar
scene(8, """
<h2>Proposition pour le radar</h2>
<table style="font-size:30px">
  <tr><th style="width:420px">Élément</th><th style="width:240px">Anneau proposé</th><th>Pourquoi</th></tr>
  <tr><td><b>Runtime Async</b></td><td><span class="pastille">Évaluer</span></td>
      <td>Gains réels et mesurés, sans changement de code, mais encore en preview. À tester sur un service interne
      non critique.</td></tr>
  <tr data-s="1"><td><b>.NET 11</b></td><td><span class="pastille rt">Essayer</span></td>
      <td>C# 15 et performances. .NET 10 (LTS) reste la base stable pour les projets longs.</td></tr>
  <tr data-s="2"><td><b>.NET 8 / .NET 9</b></td><td><span class="pastille rouge">Arrêter</span></td>
      <td>Plus supportés depuis le 10 novembre 2026 : migrer vers .NET 10 en priorité.</td></tr>
  <tr data-s="2"><td><b>C# 15 : types union</b></td><td><span class="pastille rt">Essayer</span></td>
      <td>Remplace OneOf, ErrorOr et les hiérarchies maison pour les résultats d'API.</td></tr>
</table>
<div class="carte acc centre" data-s="3">Ces anneaux sont une <b>proposition</b>, à discuter ensemble.</div>
""", [
    "Alors, que proposer pour notre radar ? Runtime Async, dans l'anneau Évaluer : des gains réels et mesurés, sans "
    "changement de code, mais encore en preview. À tester sur un service interne non critique, avec nos propres "
    "mesures.",
    ".NET 11, dans l'anneau Essayer : intéressant pour C# 15 et les performances, mais .NET 10 reste la base stable "
    "pour les projets longs.",
    ".NET 8 et .NET 9, dans l'anneau Arrêter : ils ne sont plus supportés, il faut migrer vers .NET 10 en priorité. "
    "Enfin, les types union de C# 15, dans l'anneau Essayer.",
    "Ces anneaux sont une proposition, à discuter ensemble.",
])

# 9 ─ Fin
scene(9, """
<div class="pleine">
  <h1 style="font-size:80px">Tout est dans le dépôt</h1>
  <div class="carte acc" style="font-family:var(--mono);font-size:44px">github.com/drangoht/RuntimeAsyncDemo</div>
  <div class="cols3">
    <div class="carte"><h3 class="acc">README</h3>Explications, schémas, résultats</div>
    <div class="carte"><h3 class="acc">DEMO.md</h3>Le déroulé complet de cette démo</div>
    <div class="carte"><h3 class="acc">Le code</h3>Scénarios, benchmarks, outil voir-il</div>
  </div>
  <h2 class="doux">Merci. Place aux questions.</h2>
</div>
""", [
    "Tout ce que vous avez vu est disponible dans le dépôt RuntimeAsyncDemo, sur GitHub : le code, les benchmarks, "
    "les schémas, et le déroulé complet de cette démo. Merci, et place aux questions.",
])
