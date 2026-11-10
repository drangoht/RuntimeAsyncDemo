namespace RuntimeAsyncDemo.Scenarios;

public sealed record Client(int Id, string Nom, decimal Remise);

/// <summary>
/// Un service « comme en entreprise » : chaque étape est async parce qu'elle POURRAIT faire une E/S
/// (base, cache distribué, API), mais en pratique la plupart des appels sont servis par un cache mémoire
/// et se terminent tout de suite. C'est le cas le plus fréquent dans une vraie application.
/// </summary>
public sealed class ServiceCommandes
{
    private readonly Dictionary<int, Client> _cacheClients = new();
    private readonly bool _simulerEntreesSorties;
    private decimal _totalEnregistre;

    /// <param name="simulerEntreesSorties">
    /// false : tout est en cache, aucun await ne suspend (chemin « chaud »).
    /// true  : chaque accès suspend vraiment la méthode (Task.Yield), comme une vraie E/S.
    /// </param>
    public ServiceCommandes(bool simulerEntreesSorties)
    {
        _simulerEntreesSorties = simulerEntreesSorties;
        for (int i = 0; i < 100; i++)
            _cacheClients[i] = new Client(i, $"Client {i}", (i % 5) * 0.05m);
    }

    public decimal TotalEnregistre => _totalEnregistre;

    /// <summary>Point d'entrée : 4 niveaux d'appels async imbriqués.</summary>
    public async Task<decimal> TraiterAsync(int idCommande)
    {
        Client client = await ChargerClientAsync(idCommande % 100);
        decimal prix = await CalculerPrixAsync(client, idCommande);
        await EnregistrerAsync(prix);
        return prix;
    }

    private async Task<Client> ChargerClientAsync(int idClient)
    {
        if (_simulerEntreesSorties) await Task.Yield();
        return _cacheClients[idClient];
    }

    private async Task<decimal> CalculerPrixAsync(Client client, int idCommande)
    {
        decimal remise = await LireRemiseAsync(client);
        return (100 + idCommande % 50) * (1 - remise);
    }

    private async Task<decimal> LireRemiseAsync(Client client)
    {
        if (_simulerEntreesSorties) await Task.Yield();
        return client.Remise;
    }

    private async Task EnregistrerAsync(decimal prix)
    {
        if (_simulerEntreesSorties) await Task.Yield();
        _totalEnregistre += prix;
    }
}
