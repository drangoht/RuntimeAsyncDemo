using System.Reflection;
using System.Runtime.CompilerServices;

namespace RuntimeAsyncDemo.Scenarios;

/// <summary>
/// Dit comment ce code a réellement été compilé, en regardant le résultat plutôt que la configuration.
/// </summary>
public static class ModeAsync
{
    /// <summary>
    /// Runtime Async : la méthode porte le drapeau IL « async » (MethodImplAttributes.Async = 0x2000)
    /// et il n'y a plus de classe machine à états générée.
    /// Mode classique : attribut [AsyncStateMachine] + classe imbriquée « &lt;Methode&gt;d__N ».
    /// </summary>
    public static bool EstRuntimeAsync
    {
        get
        {
            MethodInfo m = typeof(ServiceCommandes).GetMethod(nameof(ServiceCommandes.TraiterAsync))!;
            return ((int)m.MethodImplementationFlags & 0x2000) != 0
                && m.GetCustomAttribute<AsyncStateMachineAttribute>() is null;
        }
    }

    public static string Libelle => EstRuntimeAsync
        ? "Runtime Async (.NET 11 : le runtime gère l'async)"
        : "Classique (le compilateur génère une machine à états)";

    /// <summary>Classes « machine à états » générées par le compilateur dans cet assembly.</summary>
    public static int NombreMachinesAEtats =>
        typeof(ModeAsync).Assembly.GetTypes().Count(t => typeof(IAsyncStateMachine).IsAssignableFrom(t));
}
