# VideosDB Julia - Setup Guide

Complete guide for setting up and running the VideosDB Julia project.

## Project Structure

```
videosdb-julia/
├── Project.toml          # Package dependencies and metadata
├── Manifest.toml         # Locked dependency versions (auto-generated)
├── src/
│   ├── VideosDB.jl      # Main module file
│   └── run.jl           # Entry point script
├── test/
│   └── runtests.jl      # Test suite
├── common/
│   ├── firebase/
│   │   └── db-schema.json
│   └── keys/
│       └── testing.json  # Firestore credentials
├── .env                  # Environment variables
└── README.md
```

## Installation

### 1. Install Julia

Download and install Julia 1.9 or later from [julialang.org](https://julialang.org/downloads/)

### 2. Clone/Create Project

```bash
mkdir videosdb-julia
cd videosdb-julia
```

### 3. Create Project.toml

Save the provided `Project.toml` file in your project root.

### 4. Install Dependencies

```bash
julia --project=. -e 'using Pkg; Pkg.instantiate()'
```

Or interactively:

```julia
julia> ] # Enter package mode
pkg> activate .
pkg> instantiate
```

### 5. Install Dependencies

All required dependencies are now included in Project.toml:

```bash
julia --project=. -e 'using Pkg; Pkg.instantiate()'
```

Or interactively:

```julia
julia> ] # Enter package mode
pkg> activate .
pkg> instantiate
```

**Included Dependencies:**
- ✅ **ArgParse** - Command-line argument parsing
- ✅ **HTTP** - HTTP client for API requests
- ✅ **JSON3** - Fast JSON parsing
- ✅ **JSONSchema** - JSON schema validation
- ✅ **Redis** - Redis caching support
- ✅ **TimeZones** - ISO8601 datetime parsing with timezone support
- ✅ **URIs** - URI parsing and manipulation

All dependencies are automatically installed with `Pkg.instantiate()`.

## Configuration

### Environment Variables

Create a `.env` file:

```bash
# YouTube Configuration
YOUTUBE_CHANNEL_ID=UCcYzLCs3zrQIBVHYA1sK2sw
YOUTUBE_API_KEY=your_youtube_api_key_here

# Firebase/Firestore Configuration
FIREBASE_PROJECT=videosdb-testing
VIDEOSDB_CONFIG=testing

# Optional: Firestore Emulator
# FIRESTORE_EMULATOR_HOST=localhost:8080

# Optional: YouTube API URL (for testing/mocking)
# YOUTUBE_API_URL=http://localhost:8000/youtube/v3

# Logging Level
LOGLEVEL=INFO  # DEBUG, INFO, WARN, ERROR, TRACE
```

### Firebase Credentials

Place your Firebase service account JSON file at:
```
common/keys/testing.json
```

### Redis Configuration (Optional but Recommended)

If you want to use Redis for caching (significantly improves performance):

1. **Install Redis:**
```bash
# macOS
brew install redis

# Ubuntu/Debian
sudo apt-get install redis-server

# Or use Docker
docker run -d -p 6379:6379 redis:latest
```

2. **Start Redis:**
```bash
redis-server
```

3. **Configure Redis database** (optional, add to .env):
```bash
REDIS_DB=0  # Redis database number (0-15)
```

The application will automatically connect to Redis on `localhost:6379`. If Redis is unavailable, the application will continue to work without caching.

## Usage

### Basic Commands

**Check for new videos:**
```bash
julia --project=. src/run.jl --check-for-new-videos
```

**With transcripts enabled:**
```bash
julia --project=. src/run.jl -c -e
```

**Load custom .env file:**
```bash
julia --project=. src/run.jl -v .env.production -c
```

**Validate database schema:**
```bash
julia --project=. src/run.jl --validate-db-schema
```

**Export to Firestore emulator:**
```bash
julia --project=. src/run.jl -c -x localhost:8080
```

**Enable Twitter publishing:**
```bash
julia --project=. src/run.jl -c -t
```

**All options combined:**
```bash
julia --project=. src/run.jl \
  --check-for-new-videos \
  --enable-transcripts \
  --enable-twitter-publishing \
  --export-to-emulator-host localhost:8080 \
  --dotenv .env.production
```

### Programmatic Usage

```julia
using VideosDB

# Create downloader with options
options = VideosDB.Downloader.DownloadOptions(
    enable_transcripts = true,
    enable_twitter_publishing = false,
    export_to_emulator_host = "localhost:8080"
)

# Initialize downloader
downloader = VideosDB.Downloader.VideoDownloader(
    options = options,
    channel_id = "UCcYzLCs3zrQIBVHYA1sK2sw"
)

# Run sync
VideosDB.Downloader.check_for_new_videos!(downloader)
```

### Interactive REPL Usage

```julia
julia> using VideosDB

julia> # Create database client
julia> db = VideosDB.DB.DatabaseClient()

julia> # Initialize database
julia> VideosDB.DB.init_db!(db)

julia> # Create YouTube API client
julia> api = VideosDB.YoutubeAPI.YouTubeClient(db)

julia> # Get video info
julia> modified, video = VideosDB.YoutubeAPI.get_video_info(api, "dQw4w9WgXcQ")

julia> # Get channel info
julia> _, channel = VideosDB.YoutubeAPI.get_channel_info(api, "UCcYzLCs3zrQIBVHYA1sK2sw")
```

## Development

### Running Tests

```bash
julia --project=. -e 'using Pkg; Pkg.test()'
```

Or:
```julia
pkg> test
```

### Enable Debug Logging

```bash
export LOGLEVEL=DEBUG
julia --project=. src/run.jl -c
```

### Working with Firestore Emulator

1. Start the emulator:
```bash
gcloud emulators firestore start --host-port=localhost:8080
```

2. Set environment variable:
```bash
export FIRESTORE_EMULATOR_HOST=localhost:8080
```

3. Run the sync:
```bash
julia --project=. src/run.jl -c
```

## Package Development Workflow

### Adding New Dependencies

```julia
pkg> add PackageName
```

### Updating Dependencies

```julia
pkg> update
```

### Checking Package Status

```julia
pkg> status
```

### Removing Dependencies

```julia
pkg> rm PackageName
```

## Performance Optimization

### Precompilation

Julia will precompile packages on first use. To force precompilation:

```bash
julia --project=. -e 'using Pkg; Pkg.precompile()'
```

### Multi-threading

Enable multi-threading for better performance:

```bash
julia --project=. --threads=auto src/run.jl -c
```

Or set specific thread count:
```bash
julia --project=. --threads=4 src/run.jl -c
```

## Troubleshooting

### Package Installation Issues

```julia
pkg> resolve
pkg> update
pkg> build
```

### Clear Package Cache

```bash
rm -rf ~/.julia/compiled/v1.9/VideosDB
```

### Check Package Versions

```julia
pkg> status --manifest
```

### Environment Issues

Make sure you're in the correct project:
```julia
pkg> activate .
```

## Docker Deployment (Optional)

Create a `Dockerfile`:

```dockerfile
FROM julia:1.9

WORKDIR /app

# Copy project files
COPY Project.toml Manifest.toml ./
COPY src/ ./src/
COPY common/ ./common/

# Install dependencies
RUN julia --project=. -e 'using Pkg; Pkg.instantiate()'

# Precompile
RUN julia --project=. -e 'using Pkg; Pkg.precompile()'

# Set entry point
ENTRYPOINT ["julia", "--project=.", "src/run.jl"]
CMD ["--check-for-new-videos"]
```

Build and run:
```bash
docker build -t videosdb-julia .
docker run -e YOUTUBE_API_KEY=your_key videosdb-julia -c -e
```

## Additional Resources

- [Julia Documentation](https://docs.julialang.org/)
- [Julia Package Manager](https://pkgdocs.julialang.org/)
- [ArgParse.jl](https://github.com/carlobaldassi/ArgParse.jl)
- [HTTP.jl](https://github.com/JuliaWeb/HTTP.jl)
- [JSON3.jl](https://github.com/quinnj/JSON3.jl)

## Migration Notes from Python

### Key Differences

1. **Asyncio → Multi-threading**: Julia uses threading instead of async/await
2. **Type annotations**: Optional but recommended in Julia
3. **Package management**: Project.toml replaces requirements.txt
4. **Module system**: Explicit module declarations
5. **Array indexing**: 1-based in Julia vs 0-based in Python

### Missing Implementations

The following features need additional Julia packages or custom implementation:

- **Firestore Client**: Requires Google Cloud Firestore library for Julia
- **Redis**: Requires Redis.jl (included in optional deps)
- **YouTube Transcript API**: No direct equivalent, needs custom implementation
- **Bleach (HTML sanitization)**: Needs custom implementation or HTML.jl
- **ISO8601 Parsing**: TimeZones.jl recommended
- **JSON Schema Validation**: JSONSchema.jl recommended

## License

[Your License Here]

## Contributing

[Your Contributing Guidelines Here]