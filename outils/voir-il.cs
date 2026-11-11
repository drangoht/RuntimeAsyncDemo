#:property PublishAot=false
#:property Nullable=enable

// Montre, pour une méthode de RuntimeAsyncDemo.Scenarios, ce que le compilateur a réellement produit
// dans chaque mode : méthodes générées, taille de l'IL et appels effectués.
//
//   dotnet build -c Release src/RuntimeAsyncDemo.Scenarios -p:AsyncMode=compiler
//   dotnet build -c Release src/RuntimeAsyncDemo.Scenarios -p:AsyncMode=runtime
//   dotnet run outils/voir-il.cs -- LireRemiseAsync
//   dotnet run outils/voir-il.cs -- DescendreEtEchouerAsync
//
// C'est aussi un exemple d'« application en un fichier » (dotnet run fichier.cs), nouveauté de .NET 10/11.

using System.Reflection;
using System.Reflection.Emit;
using System.Runtime.Loader;

string methode = args.FirstOrDefault() ?? "LireRemiseAsync";
string racine = Path.GetFullPath(Path.Combine(AppContext.GetData("EntryPointFileDirectoryPath") as string ?? ".", ".."));

Console.OutputEncoding = System.Text.Encoding.UTF8;
var codesOp = typeof(OpCodes).GetFields().Select(f => (OpCode)f.GetValue(null)!).ToDictionary(o => o.Value);

foreach (string mode in new[] { "compiler", "runtime" })
{
    string dll = Path.Combine(racine, "artifacts", mode, "bin", "RuntimeAsyncDemo.Scenarios", "Release", "net11.0", "RuntimeAsyncDemo.Scenarios.dll");
    string titre = mode == "compiler" ? "MODE CLASSIQUE (machine à états)" : "RUNTIME ASYNC (.NET 11)";
    Console.WriteLine($"══════════ {titre} ══════════");
    if (!File.Exists(dll))
    {
        Console.WriteLine($"   DLL absente. Compilez d'abord : dotnet build -c Release src/RuntimeAsyncDemo.Scenarios -p:AsyncMode={mode}");
        continue;
    }

    // Un contexte de chargement par mode : les deux DLL portent le même nom
    var contexte = new AssemblyLoadContext(mode, isCollectible: true);
    Assembly assembly = contexte.LoadFromAssemblyPath(dll);
    const BindingFlags tout = BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.Static | BindingFlags.DeclaredOnly;

    var trouvees = new List<MethodBase>();
    foreach (Type type in assembly.GetTypes())
    {
        trouvees.AddRange(type.GetMethods(tout).Where(m => m.Name == methode));
        // La machine à états générée : une classe imbriquée « <Methode>d__N » avec sa méthode MoveNext
        if (type.Name.StartsWith($"<{methode}>"))
            trouvees.AddRange(type.GetMethods(tout).Where(m => m.Name == "MoveNext"));
    }
    if (trouvees.Count == 0) { Console.WriteLine($"   Méthode « {methode} » introuvable."); continue; }

    int totalIl = 0;
    foreach (MethodBase m in trouvees)
    {
        byte[] il = m.GetMethodBody()!.GetILAsByteArray()!;
        totalIl += il.Length;
        bool async = ((int)m.MethodImplementationFlags & 0x2000) != 0;
        Console.WriteLine($"   {m.DeclaringType!.Name}.{m.Name}   ({il.Length} octets d'IL{(async ? ", drapeau « async »" : "")})");
        foreach (string appel in Appels(m, il)) Console.WriteLine($"      {appel}");
    }
    Console.WriteLine($"   ► {trouvees.Count} méthode(s), {totalIl} octets d'IL au total");
    Console.WriteLine();
    contexte.Unload();
}

// Parcourt l'IL et rend les appels, levées d'exception et blocs try/catch, lisiblement
IEnumerable<string> Appels(MethodBase m, byte[] il)
{
    int i = 0;
    while (i < il.Length)
    {
        short valeur = il[i] == 0xFE ? (short)(0xFE00 | il[i + 1]) : il[i];
        OpCode op = codesOp[valeur];
        i += op.Size;
        int tailleOperande = op.OperandType switch
        {
            OperandType.InlineNone => 0,
            OperandType.ShortInlineBrTarget or OperandType.ShortInlineI or OperandType.ShortInlineVar => 1,
            OperandType.InlineVar => 2,
            OperandType.InlineI8 or OperandType.InlineR => 8,
            OperandType.InlineSwitch => 4 + 4 * BitConverter.ToInt32(il, i),
            _ => 4,
        };
        if (op.OperandType == OperandType.InlineMethod)
        {
            MethodBase cible = m.Module.ResolveMethod(BitConverter.ToInt32(il, i), m.DeclaringType!.GetGenericArguments(), null)!;
            string nomType = cible.DeclaringType!.Name.Split('`')[0];
            string remarque = nomType switch
            {
                "AsyncTaskMethodBuilder" or "AsyncMethodBuilderCore" => "   ← plomberie de la machine à états",
                "AsyncHelpers" => "   ← le runtime gère l'attente ici",
                _ => "",
            };
            yield return $"appelle {nomType}.{cible.Name}{remarque}";
        }
        else if (op.Name == "throw") yield return "lève une exception";
        i += tailleOperande;
    }
    if (m.GetMethodBody()!.ExceptionHandlingClauses.Count > 0)
        yield return "contient un try/catch généré par le compilateur   ← capture puis range l'exception";
}
