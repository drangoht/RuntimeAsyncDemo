using System.Runtime.CompilerServices;

namespace RuntimeAsyncDemo.Scenarios;

public sealed class CommandeInvalideException(string message) : Exception(message);

/// <summary>
/// Une chaîne d'appels async de profondeur réglable : Controleur → Service → Depot → ... → Source.
/// NoInlining empêche le JIT de fusionner les niveaux, pour que chaque niveau compte vraiment.
/// </summary>
public static class ChaineAppels
{
    // ----- 1. Appels imbriqués qui se terminent tout de suite (aucune vraie attente) -----

    [MethodImpl(MethodImplOptions.NoInlining)]
    public static async Task<int> DescendreAsync(int profondeur, int valeur)
    {
        if (profondeur == 0) return valeur + 1;
        return await DescendreAsync(profondeur - 1, valeur) + 1;
    }

    // ----- 2. Même chaîne, mais le niveau le plus bas attend vraiment (suspension) -----

    [MethodImpl(MethodImplOptions.NoInlining)]
    public static async Task<int> DescendreEtAttendreAsync(int profondeur, int valeur)
    {
        if (profondeur == 0)
        {
            await Task.Yield(); // rend la main, comme une lecture disque ou réseau
            return valeur + 1;
        }
        return await DescendreEtAttendreAsync(profondeur - 1, valeur) + 1;
    }

    // ----- 3. Une exception levée tout en bas qui remonte à travers chaque niveau -----

    [MethodImpl(MethodImplOptions.NoInlining)]
    public static async Task<int> DescendreEtEchouerAsync(int profondeur)
    {
        if (profondeur == 0) throw new CommandeInvalideException("Quantité négative");
        return await DescendreEtEchouerAsync(profondeur - 1) + 1;
    }

    // ----- 4. Une vraie chaîne nommée, pour lire la pile d'appels -----

    [MethodImpl(MethodImplOptions.NoInlining)]
    public static async Task<string> ControleurAsync() => await ServiceAsync();

    [MethodImpl(MethodImplOptions.NoInlining)]
    private static async Task<string> ServiceAsync() => await DepotAsync();

    [MethodImpl(MethodImplOptions.NoInlining)]
    private static async Task<string> DepotAsync() => await BaseDeDonneesAsync();

    [MethodImpl(MethodImplOptions.NoInlining)]
    private static async Task<string> BaseDeDonneesAsync()
    {
        await Task.Yield();
        throw new CommandeInvalideException("La commande 42 n'existe pas");
    }

    // ----- 5. Même chaîne, mais on photographie la pile « vivante » (ce que voient débogueur et profileurs) -----

    [MethodImpl(MethodImplOptions.NoInlining)]
    public static async Task<string> ControleurPileAsync() => await ServicePileAsync();

    [MethodImpl(MethodImplOptions.NoInlining)]
    private static async Task<string> ServicePileAsync() => await DepotPileAsync();

    [MethodImpl(MethodImplOptions.NoInlining)]
    private static async Task<string> DepotPileAsync() => await BaseDeDonneesPileAsync();

    [MethodImpl(MethodImplOptions.NoInlining)]
    private static async Task<string> BaseDeDonneesPileAsync()
    {
        await Task.Yield();             // la méthode reprend sur un thread du pool…
        return Environment.StackTrace;  // …que voit-on de la pile à cet instant ?
    }
}
