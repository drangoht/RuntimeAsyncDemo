# Déroulé de démo — Runtime Async (.NET 11) pour un tech radar

Une présentation **sans slides** d'environ 30 minutes, construite autour de démos en direct. Chaque étape indique
**quoi lancer**, **ce qu'on doit voir** et **quoi dire**. Les étapes marquées *(optionnel)* se sautent si le temps manque.

| # | Étape | Durée | Public |
|---|---|---|---|
| 0 | [Préparation (la veille)](#0-préparation-la-veille) | — | — |
| 1 | [Accroche : une question](#1-accroche--une-question-2-min) | 2 min | tous |
| 2 | [L'async en 3 minutes](#2-lasync-en-3-minutes-3-min) | 3 min | débutants |
| 3 | [Démo : ce que le compilateur génère](#3-démo--ce-que-le-compilateur-génère-6-min) | 6 min | tous |
| 4 | [Démo : la pile d'appels](#4-démo--la-pile-dappels-4-min) | 4 min | tous |
| 5 | [Démo : les mesures](#5-démo--les-mesures-6-min) | 6 min | tous |
| 6 | [Comment l'activer, et ses limites](#6-comment-lactiver-et-ses-limites-3-min) | 3 min | tous |
| 7 | [.NET Conf 2026 en bref](#7-net-conf-2026-en-bref-3-min) | 3 min | tous |
| 8 | [Proposition pour le radar](#8-proposition-pour-le-radar-2-min) | 2 min | tous |
| — | [Questions probables](#questions-probables-et-réponses) · [Plan B](#plan-b-si-la-démo-plante) | | |

---

## 0. Préparation (la veille)

1. **SDK** : installer le SDK .NET 11 (version finale 11.0.100, sortie le 10 novembre 2026), par exemple avec
   `winget install Microsoft.DotNet.SDK.11`. Le `global.json` du dépôt demande 11.0.100 ou plus récent. Dans le
   dossier du dépôt, vérifier :
   ```powershell
   dotnet --version        # doit afficher 11.0.1xx
   ```
2. **Tout compiler à l'avance**, pour ne pas attendre devant le public :
   ```powershell
   foreach ($m in 'compiler','runtime') {
       dotnet build -c Release src/RuntimeAsyncDemo.Demo -p:AsyncMode=$m
       dotnet build -c Release src/RuntimeAsyncDemo.Scenarios -p:AsyncMode=$m
   }
   dotnet run outils/voir-il.cs -- LireRemiseAsync    # premier lancement plus lent (compilation du script)
   ```
3. **Relancer les benchmarks complets** sur la machine de présentation (~12 min), pour avoir des chiffres frais :
   ```powershell
   dotnet run -c Release --project src/RuntimeAsyncDemo.Benchmarks -- --filter *
   ```
   Les rapports sont dans `BenchmarkDotNet.Artifacts/results/`. Ceux du README ont été mesurés sur la version finale (11.0.0).
4. **Écran** : terminal en police 18 pt minimum, deux terminaux côte à côte (gauche = classique, droite = Runtime
   Async), le README ouvert sur GitHub dans un onglet, `ServiceCommandes.cs` ouvert dans l'éditeur.

> Astuce : préparez dans chaque terminal une variable, puis réutilisez les mêmes commandes des deux côtés.
> ```powershell
> $mode = 'compiler'    # dans le terminal de gauche
> $mode = 'runtime'     # dans le terminal de droite
> ```

---

## 1. Accroche : une question (2 min)

Montrez `LireRemiseAsync` dans `src/RuntimeAsyncDemo.Scenarios/ServiceCommandes.cs` :

```csharp
private async Task<decimal> LireRemiseAsync(Client client)
{
    if (_simulerEntreesSorties) await Task.Yield();
    return client.Remise;
}
```

**Question au public** : *« Quand la remise est en cache, donc sans aucune attente, combien d'objets cette méthode
alloue-t-elle ? »*

Laissez répondre. La plupart diront « zéro », et ce n'est pas vrai :

- **En .NET 10**, un `Task<decimal>` est alloué à chaque appel. Sur un traitement de 1 000 commandes avec 4 niveaux
  d'async chacune, cela fait **312 Ko** de mémoire à nettoyer.
- **Avec Runtime Async en .NET 11**, on alloue **0 octet**, sans changer une ligne de code.

**À dire** : *« Aujourd'hui, on va voir pourquoi, le mesurer en direct, et décider si ça mérite une place sur notre radar. »*

---

## 2. L'async en 3 minutes (3 min)

*À adapter au public : à raccourcir si tout le monde est à l'aise avec async/await.*

**L'image du restaurant** :
- Un serveur, c'est un **thread**. La cuisine, c'est la base de données ou une API.
- **En synchrone**, le serveur attend devant la cuisine. Pour servir 100 tables, il faut 100 serveurs.
- **En asynchrone** (`await`), il transmet la commande, note où il en est, et va servir d'autres tables. Quand le plat
  est prêt, n'importe quel serveur libre reprend la commande.

**Le point clé pour la suite** : pour « noter où il en est », il faut **sauvegarder l'état de la méthode** : à quelle
ligne elle s'est arrêtée et la valeur de ses variables. Une méthode normale ne sait pas faire ça. Ses variables vivent
sur la **pile** du thread, et le thread part servir quelqu'un d'autre.

**Deux idées fausses à désamorcer** :
- *« async rend le code plus rapide »* : non, async permet de servir **plus de requêtes** avec peu de threads.
- *« async, c'est du parallélisme »* : non, `await` attend sans bloquer, il ne lance rien en parallèle.

> Support si besoin : [PILE.md](PILE.md) (la pile expliquée avec des schémas) et la section 1 du README.

---

## 3. Démo : ce que le compilateur génère (6 min)

**À dire** : *« Jusqu'ici, le compilateur C# transformait chaque méthode async en "machine à états". Regardons ce
qu'il y a réellement dans la DLL. »*

```powershell
dotnet run outils/voir-il.cs -- LireRemiseAsync
```

**Ce qu'on voit** :

```
══════════ MODE CLASSIQUE (machine à états) ══════════
   ServiceCommandes.LireRemiseAsync   (63 octets d'IL)
      appelle AsyncTaskMethodBuilder.Create   ← plomberie de la machine à états
      appelle AsyncTaskMethodBuilder.Start    ← plomberie de la machine à états
      appelle AsyncTaskMethodBuilder.get_Task ← plomberie de la machine à états
   <LireRemiseAsync>d__9.MoveNext   (176 octets d'IL)
      appelle Task.Yield
      ...
      appelle AsyncTaskMethodBuilder.AwaitUnsafeOnCompleted
      appelle AsyncTaskMethodBuilder.SetException
      appelle AsyncTaskMethodBuilder.SetResult
      contient un try/catch généré par le compilateur
   ► 2 méthode(s), 239 octets d'IL au total

══════════ RUNTIME ASYNC (.NET 11) ══════════
   ServiceCommandes.LireRemiseAsync   (51 octets d'IL, drapeau « async »)
      appelle Task.Yield
      ...
      appelle AsyncHelpers.UnsafeAwaitAwaiter   ← le runtime gère l'attente ici
      appelle Client.get_Remise
   ► 1 méthode(s), 51 octets d'IL au total
```

**À expliquer, dans l'ordre** :
1. **En mode classique, votre méthode n'existe plus vraiment.** Elle crée un objet `<LireRemiseAsync>d__9`, la
   machine à états, puis le lance. Votre code est déplacé dans `MoveNext()`, découpé en morceaux autour de chaque
   `await`, avec un entier `etat` qui sert de marque-page.
2. **Toute la plomberie est visible** : `Create`, `Start`, `SetResult` pour remplir le `Task`, et `SetException`
   avec un `try/catch` invisible dans votre code source.
3. **En Runtime Async, il reste votre méthode**, presque telle quelle, avec un drapeau « async » dans l'IL. Le
   compilateur ne découpe plus rien : c'est le **runtime (le JIT)** qui sait suspendre et reprendre la méthode.
   Le seul ajout est `AsyncHelpers.UnsafeAwaitAwaiter`, l'endroit où le runtime peut suspendre la méthode.
4. **Taille de l'IL** : 239 octets contre 51.

Pour le public plus expérimenté, montrez le pseudo-C# côte à côte de la **section 5 du README** sur GitHub.

**(optionnel) Deuxième exemple, les exceptions** :

```powershell
dotnet run outils/voir-il.cs -- DescendreEtEchouerAsync
```

À montrer : en mode classique, il y a un `try/catch` généré et un `SetException`. L'exception est **attrapée, rangée
dans le Task, puis relancée** au niveau du dessus, et ainsi de suite à chaque niveau. En Runtime Async, aucun
`try/catch` n'est généré : l'exception **remonte la pile une seule fois**, comme en code synchrone (228 octets contre 30).

---

## 4. Démo : la pile d'appels (4 min)

**À dire** : *« Conséquence visible au quotidien : ce que vous voyez dans le débogueur ou le profileur. »*

Dans les deux terminaux :

```powershell
dotnet run -c Release --project src/RuntimeAsyncDemo.Demo -p:AsyncMode=$mode -- pile
```

| Classique : 10 cadres | Runtime Async : 5 cadres |
|---|---|
| `BaseDeDonneesPileAsync()`<br>`AsyncStateMachineBox.ExecutionContextCallback`<br>`ExecutionContext.RunFromThreadPoolDispatchLoop`<br>`AsyncStateMachineBox.MoveNext`<br>`AsyncStateMachineBox.MoveNext`<br>`AsyncStateMachineBox.ExecuteDirectly`<br>`ThreadPoolWorkQueue.Dispatch`<br>… 3 cadres du pool | `BaseDeDonneesPileAsync()`<br>`ThreadPoolWorkQueue.Dispatch`<br>… 3 cadres du pool |

**À expliquer** : c'est la pile **pendant l'exécution**, juste après une reprise. En mode classique, entre le pool de
threads et votre code, il y a 5 cadres de plomberie async. En Runtime Async, il n'y en a plus.

**Point d'honnêteté**, qui renforce la crédibilité :

```powershell
dotnet run -c Release --project src/RuntimeAsyncDemo.Demo -p:AsyncMode=$mode -- exception
```

La pile d'une **exception** (`ex.StackTrace`) est **identique** dans les deux modes. .NET nettoie ces piles depuis
.NET Core 2.1. Le gain de lisibilité concerne donc le **débogueur, les profileurs et les dumps mémoire**, pas les logs
d'exception.

**(optionnel, non testé) Dans Visual Studio ou Rider** : point d'arrêt sur la ligne `return Environment.StackTrace;`
de `ChaineAppels.BaseDeDonneesPileAsync`, puis comparez la fenêtre « Pile des appels » dans les deux modes.

---

## 5. Démo : les mesures (6 min)

### Mesure rapide (1 s par mode)

```powershell
dotnet run -c Release --project src/RuntimeAsyncDemo.Demo -p:AsyncMode=$mode -- mesures
```

Ordre de grandeur attendu (Ryzen 7 9800X3D) :

| Scénario | Classique | Runtime Async |
|---|---|---|
| Service commandes, tout en cache | ~300 ns · 312 o | **~125 ns · 80 o** |
| Service commandes, vraies attentes | ~2,4 µs · 607 o | **~1,5 µs · 536 o** |
| Chaîne de 10 appels, sans attente | ~500 ns · 791 o | **~180 ns · 72 o** |
| Exception sur 10 niveaux | ~20 µs · 16 Ko | **~5 µs · 1,3 Ko** |

> Ces mesures « maison » au chronomètre servent à **illustrer**, pas à prouver. Les quelques octets restants
> en Runtime Async viennent de la boucle de mesure elle-même. Les chiffres rigoureux viennent de BenchmarkDotNet,
> juste après.

### BenchmarkDotNet en direct (~50 s)

```powershell
dotnet run -c Release --project src/RuntimeAsyncDemo.Benchmarks -- --filter *ExceptionsBench* --iterationCount 3 --warmupCount 1
```

**À expliquer pendant que ça tourne** : BenchmarkDotNet **recompile le projet deux fois**, une fois par mode, avec
`/p:AsyncMode=compiler` puis `runtime`. Il lance chaque version dans un processus séparé, puis compare. C'est le
même code source et le même runtime : seule la compilation des méthodes async change.

### Les résultats complets

Ouvrez la **section 4 du README** sur GitHub, ou les rapports de la veille. Les trois messages à faire passer :

1. **Le plus gros gain concerne le cas le plus courant** : des appels async qui se terminent tout de suite (cache,
   données en mémoire, tampon). On passe de 312 Ko à **0 octet** pour 1 000 commandes, et c'est **2× plus rapide**.
2. **Plus la chaîne est profonde, plus on gagne** : jusqu'à ×4 sur 20 niveaux. Nos architectures en couches
   (contrôleur → service → dépôt → client HTTP, plus les décorateurs de cache, retry et logs) sont exactement ce cas.
3. **Les exceptions** remontent de **2,4 à 4,4 fois plus vite**, avec jusqu'à 17 fois moins de mémoire.

**Le garde-fou à rappeler** : ce sont des gains sur la **mécanique async**, pas sur l'attente. Une requête SQL de
2 ms reste une requête de 2 ms. Le gain se voit sur un service qui traite beaucoup de requêtes : moins de CPU, moins
de ramasse-miettes, donc des latences plus régulières.

---

## 6. Comment l'activer, et ses limites (3 min)

Montrez `Directory.Build.props` :

```xml
<PropertyGroup>
  <TargetFramework>net11.0</TargetFramework>
  <Features>$(Features);runtime-async=on</Features>
</PropertyGroup>
```

**À dire** :
- **Une ligne, zéro changement de code.** Mêmes `async`, `await` et `Task`. Dans un `Directory.Build.props`, elle
  s'applique à toute la solution.
- **Pas besoin de `EnablePreviewFeatures`.** L'annonce officielle le précise.
- **Les bibliothèques de .NET 11 sont déjà compilées en Runtime Async**, même si vous ne l'activez pas pour votre
  code. Vous en profitez donc déjà en partie en passant à .NET 11.

**Les limites, à dire clairement** :
- **C'est encore une fonctionnalité en preview dans la version finale de .NET 11** : *« Runtime Async remains a
  preview feature »* (annonce officielle).
- **Elle n'est pas activée par défaut** pour votre code. Vérifié : sans la ligne, le compilateur génère toujours la
  machine à états.
- **Piège de compilation** : changer `Features` ne déclenche pas de recompilation incrémentale. Faites un
  `dotnet build --no-incremental` après un changement. Ce dépôt sépare les dossiers `artifacts/<mode>/` pour éviter le problème.
- **Comment vérifier que c'est bien actif** : le drapeau `0x2000` sur la méthode (voir `ModeAsync.cs`), ou
  `dotnet run outils/voir-il.cs`.

---

## 7. .NET Conf 2026 en bref (3 min)

La conférence s'est tenue du **10 au 13 novembre 2026** : deux jours avec les équipes produit (10 et 11 novembre),
puis deux jours de sessions communautaires. Programme et replays : <https://www.dotnetconf.net>.

**Ce qu'il faut retenir pour nous** :

| Sujet | L'essentiel |
|---|---|
| **.NET 11** | Version finale sortie le **10 novembre 2026**. STS : **2 ans de support**. |
| **Fin de support** ⚠️ | **.NET 8 et .NET 9 ne sont plus supportés depuis le 10 novembre 2026.** .NET 10 (LTS) reste la cible stable. |
| **C# 15** | **Union types** et **hiérarchies fermées** (`closed`) en version finale. Les nouvelles règles de sécurité mémoire restent en preview. |
| **Runtime Async** | En preview, sur option (voir la démo). Session dédiée : *« .NET Runtime vNext: Memory Safety and Runtime Async »* (Richard Lander, Andy Gocke, 10 novembre). |
| **SDK** | CLI plus rapide (hôte Native AOT, serveur MSBuild), apps en un fichier avec `#:include`, `dotnet test` avec timeouts. |
| **ASP.NET Core** | Validation asynchrone, OpenAPI 3.2 par défaut, unions dans System.Text.Json. |
| **IA** | Microsoft.Extensions.AI, template `dotnet new mcpserver`, Microsoft Agent Framework. |
| **MAUI** | CoreCLR devient le runtime par défaut. |
| **EF Core 11** | Nécessite .NET 11. |

> Transition possible : *« L'outil `voir-il.cs` que je vous ai montré est lui-même une application en un fichier,
> lancée avec `dotnet run fichier.cs` : pas de projet, pas de `.csproj`. »*

Sources : [annonce de .NET 11](https://devblogs.microsoft.com/dotnet/announcing-dotnet-11/),
[annonce GitHub](https://github.com/dotnet/announcements/issues/497), [programme](https://www.dotnetconf.net/agenda).

---

## 8. Proposition pour le radar (2 min)

| Élément | Anneau proposé | Pourquoi |
|---|---|---|
| **Runtime Async** | **Évaluer** | Gains réels et mesurés, sans changement de code, mais encore en preview. À tester sur un service interne non critique avec nos propres mesures, une fois passés à .NET 11. À passer en « Essayer » ou « Adopter » quand il sortira de preview. |
| **.NET 11** | **Essayer** | STS de 2 ans. Intéressant pour C# 15 et les performances, mais .NET 10 (LTS) reste la base stable pour les projets longs. |
| **.NET 8 / .NET 9** | **Arrêter** | Plus supportés depuis le 10 novembre 2026 : à migrer vers .NET 10 en priorité. |
| **C# 15 : union types** | **Essayer** | Remplace avantageusement OneOf, ErrorOr et les hiérarchies maison pour les résultats d'API. |

> Ces anneaux sont une **proposition** à discuter en séance, pas une décision.

---

## Questions probables et réponses

**« Faut-il modifier notre code ? »**
Non, une ligne dans le `.csproj` ou le `Directory.Build.props` suffit. Le code source reste identique.

**« Et nos paquets NuGet compilés à l'ancienne ? »**
Les deux mondes cohabitent. Dans cette démo, en mode classique, notre code appelle les bibliothèques de .NET 11, qui
sont compilées en Runtime Async, et tout fonctionne. Chaque assembly garde son mode.

**« Ça change le comportement de `ConfigureAwait`, `SynchronizationContext` ou `AsyncLocal` ? »**
Le but affiché est de garder exactement la même sémantique : seul le mécanisme change. Comme c'est en preview, faites
tourner vos tests existants avant de l'activer.

**« Pourquoi les piles d'exceptions ne changent pas ? »**
.NET les nettoie déjà depuis .NET Core 2.1. Le gain concerne la pile vivante : débogueur, profileurs, dumps.

**« On gagnera combien en production ? »**
Ça dépend de la part de mécanique async dans votre temps CPU. Sur un service qui attend surtout sa base de données,
le gain sur la latence sera faible. Sur un service très chargé avec des chaînes d'appels profondes et beaucoup de
cache, le gain en CPU et en GC peut être net. La seule bonne réponse est de **mesurer chez nous**, ce qui justifie
l'anneau « Évaluer ».

**« Pourquoi Microsoft ne l'active pas par défaut ? »**
L'annonce dit seulement que la fonctionnalité reste en preview. C'est un changement profond, entre le compilateur et
le JIT : le temps de rodage est normal.

**« Et Native AOT ? »**
La documentation .NET 11 indique que Native AOT et ReadyToRun sont pris en charge. Ce n'est pas testé dans cette démo.

---

## Plan B (si la démo plante)

| Problème | Solution |
|---|---|
| `dotnet` introuvable | Vérifier le PATH, ou utiliser le chemin complet `& "C:\Program Files\dotnet\dotnet.exe"`. |
| Compilation lente ou réseau coupé | Tout est compilé la veille (étape 0). `dotnet run` ne recompile que si un fichier a changé. |
| BenchmarkDotNet trop long ou en erreur | Passer directement aux résultats de la section 4 du README. |
| Tout plante | Le README sur GitHub contient tout : schémas, code côte à côte, résultats et graphiques. |
