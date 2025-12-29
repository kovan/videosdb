# VideosDb F# Port

Port completo a F# (.NET 8) del proyecto `videosdb`.

Contenido:
- src/VideosDb: librería core (F#)
- src/VideosDb.Cli: CLI para ejecutar el flujo (F#)
- tests/VideosDb.Tests: pruebas (xUnit)

Quick start (desde la raíz `backend`):

```bash
# Restore and build
cd fsharp
dotnet restore
dotnet build

# Run tests
dotnet test ./tests/VideosDb.Tests/VideosDb.Tests.fsproj

# Run CLI (ejemplo: check for new videos)
dotnet run -p ./src/VideosDb.Cli/VideosDb.Cli.fsproj -- -c --dotenv ../common/env/testing.txt
```

Docker (imagen ligera):

```bash
docker build -t videosdb-fsharp -f fsharp/Dockerfile .
docker run --env YOUTUBE_API_KEY="your_key" videosdb-fsharp -- -c
```

Notas:
- **Integraciones reales:** ahora existen adaptadores reales para producción (Firestore, IPFS HTTP API, Twitter via Tweetinvi). Para usarlos, configura las variables de entorno listadas abajo y asegúrate de tener un archivo de credenciales de Google (service account) accesible.

Required environment variables for production integration:

- `GOOGLE_APPLICATION_CREDENTIALS` — path al JSON de servicio (usado por `Google.Cloud.Firestore` y Google APIs)
- `FIRESTORE_PROJECT` — ID del proyecto Firestore
- `IPFS_HOST` — IP/host del daemon IPFS (por defecto `127.0.0.1`)
- `IPFS_PORT` — puerto del daemon (por defecto `5001`)
- `TWITTER_CONSUMER_KEY`, `TWITTER_CONSUMER_SECRET`, `TWITTER_ACCESS_TOKEN`, `TWITTER_ACCESS_SECRET` — credenciales para publicar en Twitter
- `YOUTUBE_API_KEY` — API key para llamadas a YouTube Data API

Notas adicionales:
- `FirestoreAdapter` usa `Google.Cloud.Firestore` (lectura/escritura async). Asegúrate de exportar `GOOGLE_APPLICATION_CREDENTIALS` o tener las credenciales en el entorno de CI.
- `IpfsAdapter` usa la API HTTP expuesta por el daemon IPFS (`/api/v0/*`).
- `TwitterPublisherAdapter` utiliza `Tweetinvi` y requiere las credenciales arriba.

Integración opcional: la actualización de DNS (`dnslink`) usando Google Cloud DNS no está automatizada aún; si te interesa la puedo añadir también.

- CI: workflow de GitHub Actions en `.github/workflows/dotnet.yml` que construye y ejecuta tests.
