using BenchmarkDotNet.Attributes;
using BenchmarkDotNet.Configs;
using BenchmarkDotNet.Jobs;
using BenchmarkDotNet.Running;
using RuntimeAsyncDemo.Scenarios;

// Le MÊME code est compilé deux fois, avec deux réglages MSBuild différents (cf. Directory.Build.props) :
//   « Classique »     : -p:AsyncMode=compiler  → machine à états générée par Roslyn (comportement historique)
//   « RuntimeAsync »  : -p:AsyncMode=runtime   → méthodes async natives, gérées par le runtime .NET 11
// BenchmarkDotNet recompile le projet pour chaque job, puis compare les deux.
//
//   dotnet run -c Release --project src/RuntimeAsyncDemo.Benchmarks -- --filter *
var config = DefaultConfig.Instance
    .AddJob(Job.Default.WithId("Classique")
        .WithArguments([new MsBuildArgument("/p:AsyncMode=compiler")])
        .AsBaseline())
    .AddJob(Job.Default.WithId("RuntimeAsync")
        .WithArguments([new MsBuildArgument("/p:AsyncMode=runtime")]))
    .HideColumns("Arguments")
    .WithOrderer(new BenchmarkDotNet.Order.DefaultOrderer(BenchmarkDotNet.Order.SummaryOrderPolicy.Declared));

BenchmarkSwitcher.FromAssembly(typeof(Program).Assembly).Run(args, config);

/// <summary>Service métier : 1 000 commandes traitées à la suite (4 niveaux d'async par commande).</summary>
[MemoryDiagnoser]
public class ServiceCommandesBench
{
    private ServiceCommandes _service = null!;

    [Params(false, true)]
    public bool VraiesAttentes { get; set; }

    [GlobalSetup]
    public void Preparer()
    {
        _service = new ServiceCommandes(VraiesAttentes);
        Console.WriteLine($"// Mode réellement compilé : {ModeAsync.Libelle}");
    }

    [Benchmark(Description = "1 000 commandes")]
    public async Task<decimal> TraiterMilleCommandes()
    {
        decimal total = 0;
        for (int i = 0; i < 1_000; i++) total += await _service.TraiterAsync(i);
        return total;
    }
}

/// <summary>Coût d'une chaîne d'appels async selon sa profondeur (contrôleur → service → dépôt → …).</summary>
[MemoryDiagnoser]
public class ChaineAppelsBench
{
    [Params(1, 5, 20)]
    public int Profondeur { get; set; }

    [Benchmark(Description = "Sans attente")]
    public Task<int> SansAttente() => ChaineAppels.DescendreAsync(Profondeur, 42);

    [Benchmark(Description = "Attente tout en bas")]
    public Task<int> AvecAttente() => ChaineAppels.DescendreEtAttendreAsync(Profondeur, 42);
}

/// <summary>Une exception métier qui remonte toute la chaîne avant d'être interceptée.</summary>
[MemoryDiagnoser]
public class ExceptionsBench
{
    [Params(1, 5, 20)]
    public int Profondeur { get; set; }

    [Benchmark(Description = "Exception remontée")]
    public async Task<int> ExceptionRemontee()
    {
        try { return await ChaineAppels.DescendreEtEchouerAsync(Profondeur); }
        catch (CommandeInvalideException) { return -1; }
    }
}
