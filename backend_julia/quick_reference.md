# VideosDB.jl - Quick Reference Guide

## Installation

```bash
# Clone repository
git clone https://github.com/yourusername/VideosDB.jl
cd VideosDB.jl

# Install dependencies
julia --project=. -e 'using Pkg; Pkg.instantiate()'
```

## Configuration

**Create `.env` file:**
```bash
YOUTUBE_CHANNEL_ID=UCcYzLCs3zrQIBVHYA1sK2sw
YOUTUBE_API_KEY=your_youtube_api_key
FIREBASE_PROJECT=your-project-id
VIDEOSDB_CONFIG=production
LOGLEVEL=INFO
```

**Place credentials:**
```bash
common/keys/production.json  # Firebase service account
```

## Command Line Usage

```bash
# Basic sync
julia --project=. src/run.jl -c

# With all options
julia --project=. src/run.jl \
  -c                              # Check for new videos
  -e                              # Enable transcripts
  -t                              # Enable Twitter publishing
  -x localhost:8080               # Export to emulator
  -v .env.production              # Load environment file
  -s                              # Validate schema

# Multi-threaded
julia --project=. --threads=auto src/run.jl -c
```

## Programmatic Usage

### Basic Sync

```julia
using VideosDB

# Create downloader
downloader = VideosDB.Downloader.VideoDownloader(
    channel_id = "UCcYzLCs3zrQIBVHYA1sK2sw"
)

# Run sync
VideosDB.Downloader.check_for_new_videos!(downloader)
```

### With Options

```julia
using VideosDB

options = VideosDB.Downloader.DownloadOptions(
    enable_transcripts = true,
    enable_twitter_publishing = false,
    export_to_emulator_host = "localhost:8080"
)

downloader = VideosDB.Downloader.VideoDownloader(
    options = options,
    channel_id = "UCcYzLCs3zrQIBVHYA1sK2sw"
)

VideosDB.Downloader.check_for_new_videos!(downloader)
```

## Database Operations

```julia
using VideosDB

# Initialize database
db = VideosDB.DB.DatabaseClient()
VideosDB.DB.init_db!(db)

# Set document
video = Dict("id" => "vid123", "title" => "My Video")
VideosDB.DB.set_doc!(db, "videos/vid123", video)

# Get document
doc = VideosDB.DB.get_doc!(db, "videos/vid123")

# Update document
VideosDB.DB.update_doc!(db, "videos/vid123", Dict("views" => 1000))

# Delete document
VideosDB.DB.delete_doc!(db, "videos/vid123")

# List collection
for doc in VideosDB.DB.list_documents(db, "videos")
    println(doc["id"])
end

# Query collection
for doc in VideosDB.DB.collection_stream(
    db, "videos",
    where=("statistics.viewCount", ">", 1000)
)
    println("Popular: $(doc["id"])")
end
```

## YouTube API

```julia
using VideosDB

db = VideosDB.DB.DatabaseClient()
api = VideosDB.YoutubeAPI.YouTubeClient(db)

# Get video info
_, video = VideosDB.YoutubeAPI.get_video_info(api, "dQw4w9WgXcQ")
println(video.snippet.title)

# Get channel info
_, channel = VideosDB.YoutubeAPI.get_channel_info(api, "UCcYzLCs3zrQIBVHYA1sK2sw")

# List playlists
_, playlists = VideosDB.YoutubeAPI.list_channel_playlist_ids(api, "UCcYzLCs3zrQIBVHYA1sK2sw")
for playlist_id in playlists
    println(playlist_id)
end

# Get playlist items
_, items = VideosDB.YoutubeAPI.list_playlist_items(api, "PLxxxxx")
for item in items
    println(item.snippet.title)
end
```

## Testing

```bash
# Run all tests
julia --project=. test/runtests.jl

# With performance tests
RUN_PERF_TESTS=true julia --project=. test/runtests.jl

# With memory profiling
RUN_MEMORY_TESTS=true julia --project=. test/runtests.jl

# Using Pkg
julia --project=. -e 'using Pkg; Pkg.test()'
```

## Redis Setup

```bash
# Install Redis
brew install redis              # macOS
sudo apt install redis-server   # Ubuntu

# Start Redis
redis-server

# Test connection
redis-cli ping  # Should return "PONG"

# Flush test database
redis-cli -n 1 FLUSHDB
```

## Firestore Emulator

```bash
# Install
npm install -g firebase-tools

# Start emulator
firebase emulators:start --only firestore --project demo-project

# Set environment
export FIRESTORE_EMULATOR_HOST=localhost:8080

# Clear data
curl -X DELETE "http://localhost:8080/emulator/v1/projects/demo-project/databases/(default)/documents"
```

## Common Tasks

### Check Quota Usage

```julia
using VideosDB

db = VideosDB.DB.DatabaseClient()
stats = VideosDB.DB.get_stats(db)
println(stats)
# Counter READS: 125/45000
# Counter WRITES: 48/19500
```

### Validate Schema

```julia
using VideosDB

db = VideosDB.DB.DatabaseClient()
video = Dict("id" => "vid123", "snippet" => Dict("title" => "Test"))

is_valid = VideosDB.DB.validate_video_schema(db, video)
println("Valid: $is_valid")
```

### Parse Duration

```julia
using VideosDB.Downloader

seconds = parse_duration("PT1H30M45S")  # Returns 5445
```

### Parse DateTime

```julia
using VideosDB.Downloader

dt = parse_datetime_iso("2024-01-15T10:30:00Z")
println(dt)  # ZonedDateTime with UTC timezone
```

### Slugify Text

```julia
using VideosDB.Downloader

slug = slugify("Hello World! 123")  # Returns "hello-world-123"
```

## Environment Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `YOUTUBE_CHANNEL_ID` | YouTube channel to sync | `UCcYzLCs3zrQIBVHYA1sK2sw` |
| `YOUTUBE_API_KEY` | YouTube Data API key | `AIzaSy...` |
| `FIREBASE_PROJECT` | Firebase project ID | `my-project-id` |
| `VIDEOSDB_CONFIG` | Config name for credentials | `production` |
| `LOGLEVEL` | Logging level | `DEBUG`, `INFO`, `WARN`, `ERROR` |
| `FIRESTORE_EMULATOR_HOST` | Emulator address | `localhost:8080` |
| `YOUTUBE_API_URL` | API URL (testing) | `http://localhost:8000/youtube/v3` |
| `REDIS_DB` | Redis database number | `0` (default) |

## Troubleshooting

### Redis Connection Failed
```bash
# Check if running
redis-cli ping

# Start Redis
redis-server

# Application will work without Redis (just slower)
```

### Firestore Connection Failed
```bash
# Check credentials file exists
ls common/keys/production.json

# Verify project ID
echo $FIREBASE_PROJECT

# Try emulator
export FIRESTORE_EMULATOR_HOST=localhost:8080
```

### YouTube Quota Exceeded
```julia
# Check quota usage
stats = VideosDB.DB.get_stats(db)

# Wait 24 hours or use different API key
# Use emulator for testing
```

### Tests Failing
```bash
# Ensure emulator is running
firebase emulators:start --only firestore

# Ensure Redis is running
redis-server

# Clear test data
redis-cli -n 1 FLUSHDB
curl -X DELETE "http://localhost:8080/emulator/v1/projects/demo-project/databases/(default)/documents"

# Run tests
julia --project=. test/runtests.jl
```

## Performance Tips

1. **Use multi-threading**: `julia --threads=auto`
2. **Enable Redis caching**: 76% quota reduction
3. **Batch operations**: Group related updates
4. **Use queries**: Don't scan entire collections
5. **Precompile**: `Pkg.precompile()` after updates

## Dependencies

**Core:**
- Julia 1.9+
- Firestore.jl 0.3+
- Redis.jl 2.0+
- JSONSchema.jl 1.0+
- TimeZones.jl 1.0+

**Optional:**
- Redis server (recommended)
- Firestore emulator (for testing)

## Links

- [GitHub Repository](https://github.com/yourusername/VideosDB.jl)
- [Firestore.jl](https://github.com/joshday/Firestore.jl)
- [YouTube Data API](https://developers.google.com/youtube/v3)
- [Firebase Console](https://console.firebase.google.com)
- [Julia Documentation](https://docs.julialang.org)

## License

MIT License - See LICENSE file