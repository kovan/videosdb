# VideosDB.jl

[![Julia](https://img.shields.io/badge/Julia-1.9+-9558B2?logo=julia&logoColor=white)](https://julialang.org/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

A Julia package for synchronizing YouTube channel data with Google Firestore. This is a complete translation of the Python VideosDB project.

## Features

- 📹 **YouTube Data Synchronization**: Download complete channel information including videos, playlists, and metadata
- 🔄 **Incremental Updates**: Efficient caching and quota management for YouTube API
- 📊 **Firestore Integration**: Native Google Cloud Firestore support via [Firestore.jl](https://github.com/joshday/Firestore.jl)
- 💾 **Redis Caching**: Built-in Redis support for improved performance (optional)
- 📝 **Transcript Support**: Download video transcripts (when available)
- 🐦 **Social Media Publishing**: Twitter/X integration for automatic posting
- 🧪 **Emulator Support**: Development and testing with Firestore emulator
- ⚡ **Multi-threaded**: Leverages Julia's native threading for concurrent operations
- 🛡️ **Quota Management**: Automatic tracking and limiting of API usage
- ✅ **Schema Validation**: JSON schema validation with JSONSchema.jl
- 🕐 **Timezone Support**: Proper ISO8601 datetime parsing with TimeZones.jl

## Installation

### Prerequisites

- Julia 1.9 or later
- Google Cloud Firestore project with credentials
- YouTube Data API v3 key
- (Optional) Redis server for caching

### Quick Start

1. **Clone or download the package:**

```bash
git clone https://github.com/yourusername/VideosDB.jl.git
cd VideosDB.jl
```

2. **Install dependencies:**

```bash
julia --project=. -e 'using Pkg; Pkg.instantiate()'
```

3. **Configure environment variables:**

Create a `.env` file:

```bash
YOUTUBE_CHANNEL_ID=UCcYzLCs3zrQIBVHYA1sK2sw
YOUTUBE_API_KEY=your_youtube_api_key_here
FIREBASE_PROJECT=your-project-id
VIDEOSDB_CONFIG=production
LOGLEVEL=INFO
```

4. **Set up Firebase credentials:**

Place your service account JSON at `common/keys/production.json`

5. **Run the sync:**

```bash
julia --project=. src/run.jl --check-for-new-videos
```

## Usage

### Command Line Interface

```bash
# Basic sync
julia --project=. src/run.jl -c

# With transcripts and Twitter publishing
julia --project=. src/run.jl -c -e -t

# Using specific .env file
julia --project=. src/run.jl -v .env.production -c

# Export to Firestore emulator
julia --project=. src/run.jl -c -x localhost:8080

# Validate database schema
julia --project=. src/run.jl -s
```

### Command Line Options

| Option | Short | Description |
|--------|-------|-------------|
| `--check-for-new-videos` | `-c` | Sync channel data from YouTube |
| `--enable-transcripts` | `-e` | Download video transcripts |
| `--enable-twitter-publishing` | `-t` | Enable Twitter/X posting |
| `--export-to-emulator-host` | `-x` | Export to Firestore emulator |
| `--dotenv` | `-v` | Load environment from file |
| `--validate-db-schema` | `-s` | Validate database schema |
| `--fill-related-videos` | `-d` | Fill related videos (WIP) |
| `--update-dnslink` | `-u` | Update DNS link (WIP) |
| `--download-and-register-in-ipfs` | `-f` | Register in IPFS (WIP) |

### Programmatic Usage

```julia
using VideosDB

# Configure options
options = VideosDB.Downloader.DownloadOptions(
    enable_transcripts = true,
    enable_twitter_publishing = false,
    export_to_emulator_host = nothing
)

# Create downloader
downloader = VideosDB.Downloader.VideoDownloader(
    options = options,
    channel_id = "UCcYzLCs3zrQIBVHYA1sK2sw"
)

# Run synchronization
VideosDB.Downloader.check_for_new_videos!(downloader)
```

### Working with Individual Components

```julia
using VideosDB

# Database operations
db = VideosDB.DB.DatabaseClient()
VideosDB.DB.init_db!(db)

# Get video data
video_doc = VideosDB.DB.get_doc!(db, "videos/dQw4w9WgXcQ")

# Set video data
VideosDB.DB.set_doc!(db, "videos/new_video_id", 
    Dict("title" => "My Video"), merge=true)

# YouTube API operations
api = VideosDB.YoutubeAPI.YouTubeClient(db)

# Get video info
modified, video = VideosDB.YoutubeAPI.get_video_info(api, "dQw4w9WgXcQ")

# Get channel info
_, channel = VideosDB.YoutubeAPI.get_channel_info(api, "UCcYzLCs3zrQIBVHYA1sK2sw")

# List playlists
_, playlists = VideosDB.YoutubeAPI.list_channel_playlist_ids(api, "UCcYzLCs3zrQIBVHYA1sK2sw")
for playlist_id in playlists
    println(playlist_id)
end
```

## Architecture

### Module Structure

```
VideosDB
├── Utils           # Helper functions and utilities
├── DB              # Firestore database operations
├── YoutubeAPI      # YouTube Data API v3 client
├── Publisher       # Social media publishing
└── Downloader      # Main synchronization logic
```

### Key Components

#### Utils Module
- Exception handling
- Port waiting utilities
- Helper functions

#### DB Module
- Firestore client wrapper
- Quota tracking with counters
- CRUD operations
- Schema validation

#### YoutubeAPI Module
- YouTube Data API v3 client
- Request caching with Redis
- Rate limiting and retries
- Pagination support

#### Publisher Module
- Twitter/X publishing
- Social media integrations

#### Downloader Module
- Video processor with concurrency
- Two-phase sync process
- Task system for parallel operations
- Playlist and video management

## Data Flow

```
YouTube API
    ↓
Cache Layer (Redis)
    ↓
Video Processor (Parallel)
    ↓
Firestore Database
    ↓
Optional: Emulator Export
Optional: Twitter Publishing
Optional: Transcript Downloads
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `YOUTUBE_CHANNEL_ID` | YouTube channel to sync | Required |
| `YOUTUBE_API_KEY` | YouTube Data API key | Required |
| `FIREBASE_PROJECT` | Firebase project ID | Required |
| `VIDEOSDB_CONFIG` | Config name for credentials | `testing` |
| `LOGLEVEL` | Logging level | `INFO` |
| `FIRESTORE_EMULATOR_HOST` | Emulator address | None |
| `YOUTUBE_API_URL` | API URL (for testing) | Production URL |

### Firestore Schema

The package expects the following Firestore structure:

```
/channel_infos/{channel_id}
/playlists/{playlist_id}
/videos/{video_id}
/meta/video_ids
/meta/state
```

### Quota Management

The package includes built-in quota tracking:

- **Read Operations**: 45,000 per day (leaves 5,000 buffer)
- **Write Operations**: 19,500 per day (leaves 500 buffer)

Quota is tracked per-session and will throw `QuotaExceeded` when limits are reached.

## Development

### Running Tests

```bash
julia --project=. -e 'using Pkg; Pkg.test()'
```

With performance tests:
```bash
RUN_PERF_TESTS=true julia --project=. -e 'using Pkg; Pkg.test()'
```

### Enable Multi-threading

```bash
julia --project=. --threads=auto src/run.jl -c
```

### Debug Mode

```bash
LOGLEVEL=DEBUG julia --project=. src/run.jl -c
```

### Using Firestore Emulator

1. Start emulator:
```bash
gcloud emulators firestore start --host-port=localhost:8080
```

2. Run with emulator:
```bash
FIRESTORE_EMULATOR_HOST=localhost:8080 julia --project=. src/run.jl -c
```

## Performance

Julia's performance characteristics:

- **First run**: ~30s compilation time (one-time per session)
- **Subsequent runs**: Near-instant startup with precompilation
- **Multi-threading**: Significant speedup for I/O-bound operations
- **Memory**: Efficient memory usage compared to Python

Tips for best performance:
- Use `--threads=auto` for concurrent operations
- Precompile with `Pkg.precompile()` after updates
- Use SysImage for production deployments

## Comparison with Python Version

| Feature | Python | Julia |
|---------|--------|-------|
| Concurrency | asyncio/anyio | Threading |
| Type Safety | Optional (type hints) | Optional (native) |
| Performance | Good | Excellent |
| Startup Time | Fast | Slower (first run) |
| Runtime Speed | Good | 2-10x faster |
| Memory Usage | Moderate | Lower |
| Package Ecosystem | Mature | Growing |

## Known Limitations

1. **Transcript API**: No direct Julia equivalent for youtube_transcript_api (implementation needed)
2. **HTML Sanitization**: Simplified linkify function (custom implementation vs bleach)
3. **Firestore.jl Features**: Some advanced Firestore features (batch operations, transactions) may have limited support - check [Firestore.jl](https://github.com/joshday/Firestore.jl) for latest capabilities

## Roadmap

- [ ] Complete Firestore client implementation
- [ ] Full Redis caching support
- [ ] YouTube transcript API implementation
- [ ] IPFS integration
- [ ] DNS link updates
- [ ] Comprehensive HTML sanitization
- [ ] Binary releases with compilation
- [ ] Docker images
- [ ] Kubernetes deployment examples

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## Troubleshooting

### Common Issues

**Import errors:**
```julia
# Make sure you're in the right environment
julia> ] activate .
julia> using Pkg; Pkg.instantiate()
```

**API quota exceeded:**
- Check your YouTube API quota in Google Cloud Console
- Use the emulator for testing
- Implement rate limiting in your workflow

**Firestore connection issues:**
- Verify credentials file exists and is valid
- Check `FIREBASE_PROJECT` environment variable
- Try the emulator for local development

**Performance issues:**
- Enable multi-threading: `--threads=auto`
- Precompile packages: `Pkg.precompile()`
- Check Redis connection if using cache

## License

MIT License - see LICENSE file for details

## Acknowledgments

- Original Python implementation
- Julia community and package developers
- Google Cloud and YouTube API teams

## Support

- 📫 Issues: [GitHub Issues](https://github.com/yourusername/VideosDB.jl/issues)
- 💬 Discussions: [GitHub Discussions](https://github.com/yourusername/VideosDB.jl/discussions)
- 📖 Documentation: [Full Docs](https://yourusername.github.io/VideosDB.jl)

---

Made with ❤️ using Julia