using System.Diagnostics;
using RuntimeAsyncDemo.Scenarios;

// Démo rapide (quelques secondes) : à lancer dans les deux modes pour comparer.
//   dotnet run -c Release --project src/RuntimeAsyncDemo.Demo
//   dotnet run -c Release --project src/RuntimeAsyncDemo.Demo -p:AsyncMode=compiler
// Pour des chiffres rigoureux : le projet RuntimeAsyncDemo.Benchmarks (BenchmarkDotNet).

Console.OutputEncoding = System.Text.Encoding.UTF8;
Console.WriteLine($"Mode de compilation : {ModeAsync.Libelle}");
Console.WriteLine($"Classes « machine à états » générées : {ModeAsync.NombreMachinesAEtats}");
Console.WriteLine();

// ---------------------------------------------------------------------------------------------
// 1. La pile d'appels quand une exception remonte de la base de données jusqu'au contrôleur
// ---------------------------------------------------------------------------------------------
Console.WriteLine("── 1. Pile d'appels d'une exception (Contrôleur → Service → Dépôt → BaseDeDonnées) ──");
try
{
    await ChaineAppels.ControleurAsync();
}
catch (CommandeInvalideException ex)
{
    string[] lignes = ex.StackTrace!.Split(Environment.NewLine);
    foreach (string ligne in lignes) Console.WriteLine("   " + ligne.Trim());
    Console.WriteLine($"   => {lignes.Length} lignes (.NET nettoie déjà ces piles depuis .NET Core 2.1 : pas de différence ici)");
}
Console.WriteLine();

// ---------------------------------------------------------------------------------------------
// 1 bis. La pile « vivante » pendant l'exécution : c'est elle que montrent le débogueur,
//        les profileurs (dotTrace, PerfView) et les dumps mémoire.
// ---------------------------------------------------------------------------------------------
Console.WriteLine("── 1 bis. Pile vivante, vue depuis BaseDeDonnées après une attente ──");
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

// ---------------------------------------------------------------------------------------------
// 2. Mesures simples : temps et mémoire allouée par opération
// ---------------------------------------------------------------------------------------------
Console.WriteLine("── 2. Mesures (moyenne par opération, après préchauffage) ──");
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
