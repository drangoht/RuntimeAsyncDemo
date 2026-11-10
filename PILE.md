# La pile d'appels (stack), expliquée simplement

Cette note explique ce qu'est la « pile » dont parle le [README](README.md) : pile d'appels, cadres, *stack trace*…
C'est la clé pour comprendre pourquoi l'async a besoin d'une machine à états, et ce que Runtime Async change.

---

## 1. L'image : une pile d'assiettes

Imaginez une pile d'assiettes dans une cuisine :

- on **pose** une assiette **sur le dessus** ;
- on **retire** toujours l'assiette **du dessus** ;
- on ne retire jamais une assiette du milieu.

La pile d'appels fonctionne exactement comme ça. Chaque fois qu'une méthode en appelle une autre, on pose une
assiette. Quand la méthode se termine, on retire son assiette.

Chaque assiette s'appelle un **cadre** (*stack frame*). Elle contient tout ce dont la méthode a besoin pendant
qu'elle tourne :

```
┌──────────────────────────────────────────────┐
│  Cadre de CalculerPrix                       │
│    • ses paramètres   (client, id)           │
│    • ses variables    (remise, prix)         │
│    • l'adresse de retour : « quand j'ai fini,│
│      revenir dans Traiter, ligne 3 »         │
└──────────────────────────────────────────────┘
```

L'**adresse de retour** est le point le plus important : c'est le « marque-page » qui dit où reprendre dans la
méthode appelante.

---

## 2. Un exemple pas à pas

```csharp
void Main()
{
    int total = Traiter(7);          // ①
    Console.WriteLine(total);        // ⑥
}

int Traiter(int id)
{
    int prix = CalculerPrix(id);     // ②
    return prix + 5;                 // ⑤
}

int CalculerPrix(int id)
{
    int remise = 10;                 // ③
    return 100 - remise;             // ④
}
```

La pile évolue ainsi. Le dessus de la pile est en haut :

```
 ① Main appelle Traiter     ② Traiter appelle         ④ CalculerPrix          ⑤ Traiter              ⑥ retour dans Main
                               CalculerPrix              renvoie 90              renvoie 95

                            ┌──────────────────┐
                            │ CalculerPrix     │
                            │ id=7  remise=10  │  ──►  (cadre retiré)
                            ├──────────────────┤      ┌──────────────────┐
 ┌──────────────────┐       │ Traiter          │      │ Traiter          │
 │ Traiter  id=7    │       │ id=7             │      │ id=7  prix=90    │ ──►  (cadre retiré)
 ├──────────────────┤       ├──────────────────┤      ├──────────────────┤      ┌──────────────────┐
 │ Main             │       │ Main             │      │ Main             │      │ Main  total=95   │
 └──────────────────┘       └──────────────────┘      └──────────────────┘      └──────────────────┘
```

À retenir :

- **Poser et retirer un cadre ne coûte presque rien** : on déplace juste un curseur, il n'y a rien à allouer.
- **Les variables locales vivent dans le cadre.** Quand le cadre est retiré, elles disparaissent.
- **Chaque thread a sa propre pile.** Deux threads ne partagent jamais leurs assiettes.

---

## 3. La pile et le tas : deux rangements différents

Le programme dispose de deux zones de mémoire :

| | La **pile** (*stack*) | Le **tas** (*heap*) |
|---|---|---|
| Image | La pile d'assiettes | Un grand entrepôt |
| Ce qu'on y range | Les cadres des méthodes en cours | Les objets créés avec `new` (`Task`, `List`, `string`…) |
| Durée de vie | Le temps de l'appel de méthode | Tant que quelqu'un s'en sert |
| Qui fait le ménage | Personne : on retire l'assiette, c'est tout | Le **ramasse-miettes** (GC), de temps en temps |
| Coût | Quasi nul | Une allocation, puis du travail pour le GC |

```
        PILE (par thread)                         TAS (partagé)
   ┌────────────────────────┐
   │ CalculerPrix           │
   │   client ──────────────────────────►  [ objet Client « Dupont » ]
   ├────────────────────────┤
   │ Traiter                │
   │   commandes ───────────────────────►  [ List<Commande> ... ]
   └────────────────────────┘
```

Une variable locale qui contient un objet ne contient en fait qu'une **flèche** (une référence) vers l'entrepôt.

C'est pour ça que les benchmarks comptent les **octets alloués** : tout ce qui part dans le tas devra un jour être
nettoyé par le GC. Moins on alloue, moins le GC travaille.

---

## 4. La *stack trace* : une photo de la pile

Quand une exception se produit, .NET prend une **photo de la pile** et la lit de haut en bas :

```
at CalculerPrix(Int32 id)   ← l'assiette du dessus : là où l'erreur s'est produite
at Traiter(Int32 id)        ← qui avait appelé CalculerPrix
at Main()                   ← qui avait appelé Traiter
```

C'est le chemin pour arriver jusqu'à l'erreur. Le débogueur montre la même chose dans sa fenêtre « Pile des
appels » (*Call Stack*).

Si la pile grossit sans fin, par exemple avec une méthode qui s'appelle elle-même sans condition d'arrêt, la pile
déborde : c'est le fameux **StackOverflowException**. La pile est petite, environ 1 Mo par thread sous Windows.

---

## 5. Le problème de l'async : l'assiette doit quitter la pile

Prenons une méthode qui attend la base de données :

```csharp
async Task<decimal> TraiterAsync(int id)
{
    decimal remise = 0.1m;
    Client client = await _db.ChargerClientAsync(id);   // attente de 5 ms
    return client.Prix * (1 - remise);
}
```

Pendant l'attente, **le thread est libéré** pour aller servir d'autres requêtes. Or la pile appartient au thread.
S'il repart travailler ailleurs, il va empiler d'autres assiettes **par-dessus**, ou retirer les nôtres.

```
 Avant l'await                Pendant l'attente :                   Après l'attente :
 (thread A)                   le thread A sert quelqu'un d'autre    c'est peut-être le thread B qui reprend

 ┌──────────────────┐         ┌──────────────────┐                  ┌──────────────────┐
 │ TraiterAsync     │         │ AutreRequete     │                  │ TraiterAsync ??? │
 │ remise=0.1       │   ──►   ├──────────────────┤          ──►     │ remise = ?       │
 ├──────────────────┤         │ ...              │                  │ où en étais-je ? │
 │ Contrôleur       │         └──────────────────┘                  └──────────────────┘
 └──────────────────┘
                               Notre assiette n'est plus là !
```

Il faut donc **mettre l'assiette à l'abri ailleurs**, dans le tas, avant de libérer le thread, puis la
**reconstruire** au moment de reprendre. Toute la question est : **comment, et à quel prix ?**

---

## 6. Avant .NET 11 : la machine à états range l'assiette dans le tas

Le compilateur transforme la méthode en objet « machine à états » (voir le README, section 2). Ses variables
locales deviennent des champs de cet objet :

```
        PILE                                   TAS
   ┌─────────────────────┐
   │ MoveNext()          │ ─────────►  [ Machine à états de TraiterAsync ]
   │  (cadre très court) │                 • etat    = 0  (« après le 1er await »)
   └─────────────────────┘                 • remise  = 0.1
                                           • id      = 7
                                           • le Task à compléter
```

Ce qui coûte :

- **Chaque méthode async** de la chaîne a sa machine à états et son `Task`. Avec Contrôleur → Service → Dépôt, cela
  fait trois objets, même quand le résultat était en cache et qu'on n'a rien attendu.
- **La reprise passe par de la plomberie** : `MoveNext`, `AsyncStateMachineBox`, `ExecutionContext`… La pile vue
  au débogueur est remplie de ces cadres techniques (10 cadres dans notre démo).

---

## 7. Avec Runtime Async : le runtime déménage les assiettes seulement si besoin

Le runtime sait qu'une méthode est async. Il la laisse donc tourner **comme une méthode normale**, avec un vrai cadre
sur la pile :

```
 Cas 1 : le résultat est en cache (pas d'attente)

   ┌──────────────────┐
   │ DepotAsync       │  ← cadre normal, retiré normalement
   ├──────────────────┤
   │ ServiceAsync     │     Rien ne part dans le tas.
   ├──────────────────┤     C'est aussi rapide qu'un appel ordinaire.
   │ ControleurAsync  │
   └──────────────────┘
```

```
 Cas 2 : il faut vraiment attendre

   PILE (thread A)                    TAS                                  PILE (thread B), à la reprise
   ┌──────────────────┐
   │ DepotAsync       │ ──┐
   ├──────────────────┤   │   [ copie compacte de DepotAsync ]           ┌──────────────────┐
   │ ServiceAsync     │ ──┼─► [ copie compacte de ServiceAsync ]  ──►    │ DepotAsync       │
   ├──────────────────┤   │   [ copie compacte de ControleurAsync ]      ├──────────────────┤
   │ ControleurAsync  │ ──┘                                              │ ...              │
   └──────────────────┘
    Le déménagement n'a lieu                                            Le runtime remet les
    qu'au moment de l'attente.                                          assiettes sur la pile.
```

Ce qu'on gagne :

- **Sans attente, il n'y a aucun déménagement** : 0 octet alloué, d'où le « 312 Ko → 0 octet » des benchmarks.
- **Avec attente**, le déménagement est plus léger et la reprise ne passe plus par la plomberie `MoveNext` :
  la pile vue au débogueur tombe à 5 cadres.
- **Une exception** remonte la pile comme dans du code normal, au lieu d'être rangée puis relancée à chaque niveau.

---

## 8. En une phrase

> La **pile** est l'endroit rapide où vivent les méthodes **pendant qu'elles tournent**. L'async oblige à sortir une
> méthode de la pile **pendant qu'elle attend**. Avant, le compilateur le faisait **toujours**, à chaque niveau. Avec
> .NET 11, le runtime ne le fait **que lorsque c'est vraiment nécessaire**.
