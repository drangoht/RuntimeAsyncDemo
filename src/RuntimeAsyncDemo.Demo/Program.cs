using System.Diagnostics;
using RuntimeAsyncDemo.Scenarios;

// Démo découpée en étapes, pour une présentation en direct (voir DEMO.md) :
//   dotnet run -c Release --project src/RuntimeAsyncDemo.Demo -p:AsyncMode=compiler -- <étape>
//   dotnet run -c Release --project src/RuntimeAsyncDemo.Demo -p:AsyncMode=runtime  -- <étape>
// Étapes : mode | pile | exception | mesures | tout (par défaut)
// Pour des chiffres rigoureux : le projet RuntimeAsyncDemo.Benchmarks (BenchmarkDotNet).

Console.OutputEncoding = System.Text.Encoding.UTF8;
string etape = args.FirstOrDefault()?.ToLowerInvariant() ?? "tout";

switch (etape)
{
    case "mode": AfficherMode(); break;
    case "pile": AfficherMode(); await AfficherPileVivante(); break;
    case "exception": AfficherMode(); await AfficherPileException(); break;
    case "mesures": AfficherMode(); await AfficherMesures(); break;
    case "tout":
        AfficherMode();
        await AfficherPileException();
        await AfficherPileVivante();
        await AfficherMesures();
        break;
    default:
        Console.WriteLine("Étapes possibles : mode | pile | exception | mesures | tout");
        return 1;
}
return 0;

// ---------------------------------------------------------------------------------------------
// 0. Comment ce code a-t-il réellement été compilé ?
// ---------------------------------------------------------------------------------------------
static void AfficherMode()
{
    Console.WriteLine($"Mode de compilation : {ModeAsync.Libelle}");
    Console.WriteLine($"Classes « machine à états » générées : {ModeAsync.NombreMachinesAEtats}");
    Console.WriteLine();
}

// ---------------------------------------------------------------------------------------------
// 1. La pile d'appels quand une exception remonte de la base de données jusqu'au contrôleur
// ---------------------------------------------------------------------------------------------
static async Task AfficherPileException()
{
    Console.WriteLine("── Pile d'appels d'une exception (Contrôleur → Service → Dépôt → BaseDeDonnées) ──");
    try
    {
        await ChaineAppels.ControleurAsync();
    }
    catch (CommandeInvalideException ex)
    {
        string[] lignes = ex.StackTrace!.Split(Environment.NewLine);
        foreach (string ligne in lignes) Console.WriteLine("   " + ligne.Trim().Split(" in ")[0]);
        Console.WriteLine($"   => {lignes.Length} lignes (.NET nettoie déjà ces piles depuis .NET Core 2.1 : pas de différence ici)");
    }
    Console.WriteLine();
}

// ---------------------------------------------------------------------------------------------
// 2. La pile « vivante » pendant l'exécution : c'est elle que montrent le débogueur,
//    les profileurs (dotTrace, PerfView) et les dumps mémoire.
// ---------------------------------------------------------------------------------------------
static async Task AfficherPileVivante()
{
    Console.WriteLine("── Pile vivante, vue depuis BaseDeDonnées après une attente ──");
    string pile = await ChaineAppels.ControleurPileAsync();
    string[] cadres = pile.Split(Environment.NewLine)
        .Select(l => l.Trim())
        .Where(l => l.StartsWith("at ") && !l.Contains("Environment.get_StackTrace"))
        .Select(l => l.Split(" in ")[0])   // on retire « in fichier:ligne » pour la lisibilité
        .ToArray();
    foreach (string cadre in cadres) Console.WriteLine("   " + cadre);
    int cadresMetier = cadres.Count(c => c.Contains("RuntimeAsyncDemo"));
    Console.WriteLine($"   => {cadres.Length} cadres, dont {cadresMetier} de notre code et {cadres.Length - cadresMetier} de plomberie .NET");
    Console.WriteLine();
}

// ---------------------------------------------------------------------------------------------
// 3. Mesures simples : temps et mémoire allouée par opération
// ---------------------------------------------------------------------------------------------
static async Task AfficherMesures()
{
    Console.WriteLine("── Mesures (moyenne par opération, après préchauffage) ──");
    Console.WriteLine($"   {"Scénario",-52} {"Temps",10} {"Mémoire",10}");

    await Mesurer("Service commandes, tout en cache (1 commande)", 200_000,
        () => new ServiceCommandes(false), (s, i) => s.TraiterAsync(i));

    await Mesurer("Service commandes, avec vraies attentes (1 commande)", 20_000,
        () => new ServiceCommandes(true), (s, i) => s.TraiterAsync(i));

    await Mesurer("Chaîne de 10 appels, sans attente", 200_000,
        () => 0, (_, i) => ChaineAppels.DescendreAsync(10, i));

    await Mesurer("Chaîne de 10 appels, attente tout en bas", 20_000,
        () => 0, (_, i) => ChaineAppels.DescendreEtAttendreAsync(10, i));

    await Mesurer("Exception qui remonte 10 niveaux", 20_000,
        () => 0, async (_, i) =>
        {
            try { return await ChaineAppels.DescendreEtEchouerAsync(10); }
            catch (CommandeInvalideException) { return -1; }
        });
    Console.WriteLine();
}

static async Task Mesurer<TEtat, TResultat>(string nom, int iterations, Func<TEtat> creer, Func<TEtat, int, Task<TResultat>> operation)
{
    TEtat etat = creer();
    for (int i = 0; i < iterations / 4; i++) await operation(etat, i); // préchauffage : le JIT optimise

    GC.Collect();
    long memoireAvant = GC.GetTotalAllocatedBytes(precise: true);
    var chrono = Stopwatch.StartNew();
    for (int i = 0; i < iterations; i++) await operation(etat, i);
    chrono.Stop();
    long octets = GC.GetTotalAllocatedBytes(precise: true) - memoireAvant;

    double ns = chrono.Elapsed.TotalNanoseconds / iterations;
    string temps = ns >= 1000 ? $"{ns / 1000:F2} µs" : $"{ns:F0} ns";
    Console.WriteLine($"   {nom,-52} {temps,10} {octets / iterations,7} o");
}
