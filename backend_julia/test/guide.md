# VideosDB.jl - Test Setup Guide

## Test Structure

The test suite is organized to match the Python test structure with comprehensive unit and integration tests.

## Directory Structure

```
test/
├── runtests.jl              # Main test suite
├── test_data/               # Mock API responses (create this)
│   ├── channel-{CHANNEL_ID}.response.json
│   ├── channelSections-{CHANNEL_ID}.response.json
│   ├── playlist-{PLAYLIST_ID}.response.json
│   ├── playlist-{ALL_VIDEOS_ID}.response.json
│   ├── playlist-empty.response.json
│   ├── playlistItems-{PLAYLIST_ID}.response.0.json
│   ├── playlistItems-{PLAYLIST_ID}.response.1.json
│   ├── playlistItems-{ALL_VIDEOS_ID}.response.json
│   └── video-{VIDEO_ID}.response.json (for each video)
└── setup_test_data.jl       # Helper script to fetch test data
```

## Setting Up Test Data

### Option 1: Copy from Python Tests

If you have the Python version running:

```bash
# Copy test data from Python backend
cp -r ../backend/tests/test_data test/
```

### Option 2: Generate Test Data

Create test data files with the following structure:

**Channel Response** (`channel-UCcYzLCs3zrQIBVHYA1sK2sw.response.json`):
```json
{
  "kind": "youtube#channelListResponse",
  "etag": "test_etag",
  "pageInfo": {
    "totalResults": 1,
    "resultsPerPage": 1
  },
  "items": [
    {
      "kind": "youtube#channel",
      "etag": "test_etag",
      "id": "UCcYzLCs3zrQIBVHYA1sK2sw",
      "snippet": {
        "title": "Sadhguru",
        "description": "Test channel",
        "publishedAt": "2006-09-14T16:45:09Z",
        "channelId": "UCcYzLCs3zrQIBVHYA1sK2sw"
      },
      "contentDetails": {
        "relatedPlaylists": {
          "uploads": "UUcYzLCs3zrQIBVHYA1sK2sw"
        }
      },
      "statistics": {
        "viewCount": "1000000",
        "subscriberCount": "500000",
        "videoCount": "1000"
      }
    }
  ]
}
```

## Running Tests

### Basic Test Run

```bash
# Run all tests
julia --project=. test/runtests.jl

# Or using Pkg
julia --project=. -e 'using Pkg; Pkg.test()'
```

### With Performance Tests

```bash
RUN_PERF_TESTS=true julia --project=. test/runtests.jl
```

### With Memory Tests

```bash
RUN_MEMORY_TESTS=true julia --project=. test/runtests.jl
```

### All Tests

```bash
RUN_PERF_TESTS=true RUN_MEMORY_TESTS=true VERBOSE_TESTS=true julia --project=. test/runtests.jl
```

### With Multi-threading

```bash
julia --project=. --threads=auto test/runtests.jl
```

## Test Requirements

### Required Packages

Already included in `Project.toml`:
- Test (standard library)
- JSON3
- HTTP
- Dates
- TimeZones

### Optional for Extended Tests

Add to `[extras]` in Project.toml:
```toml
[extras]
Test = "8dfed614-e22c-5e08-85e1-65c5234f0b40"
BenchmarkTools = "6e4b80f9-dd63-53aa-95a3-0cdb28fa8baf"
Profile = "9abbd945-dff8-562f-b5e8-e1ebf5ef1b79"
```

Install with:
```bash
julia --project=. -e 'using Pkg; Pkg.add("BenchmarkTools")'
```

## Environment Setup for Tests

Create `test/.env` or `common/env/testing.txt`:

```bash
# Test Configuration
YOUTUBE_CHANNEL_ID=UCcYzLCs3zrQIBVHYA1sK2sw
YOUTUBE_API_KEY=test_api_key_for_testing
FIREBASE_PROJECT=demo-project
VIDEOSDB_CONFIG=testing

# Firestore Emulator
FIRESTORE_EMULATOR_HOST=127.0.0.1:46456

# YouTube API Mock URL
YOUTUBE_API_URL=http://localhost:8000/youtube/v3

# Redis Test DB
REDIS_DB=1

# Logging
LOGLEVEL=DEBUG
```

## Setting Up Firestore Emulator for Tests

### Install Firestore Emulator

```bash
# Using gcloud
gcloud components install cloud-firestore-emulator

# Or using npm
npm install -g @google-cloud/firestore-emulator
```

### Start Emulator

```bash
# Start on specific port
gcloud emulators firestore start --host-port=127.0.0.1:46456

# Or in background
gcloud emulators firestore start --host-port=127.0.0.1:46456 &
```

### Clear Emulator Data

```bash
# HTTP DELETE to clear all data
curl -X DELETE "http://127.0.0.1:46456/emulator/v1/projects/demo-project/databases/(default)/documents"
```

## Setting Up Redis for Tests

### Use Separate Redis Database

Tests use Redis database 1 (instead of 0) to avoid conflicts:

```bash
# Start Redis
redis-server

# Flush test database
redis-cli -n 1 FLUSHDB

# Or in Julia
using Redis
conn = RedisConnection(db=1)
Redis.flushdb(conn)
```

## Test Categories

### 1. Unit Tests

Test individual functions and modules:
- Utils functions
- DB operations
- YouTube API helpers
- Downloader utilities

### 2. Integration Tests

Test complete workflows:
- Full sync process
- Video processing
- Playlist handling
- Cache operations

### 3. Performance Tests

Benchmark critical operations:
- Slugify performance
- Date parsing
- Duration parsing

### 4. Memory Tests

Profile memory usage:
- Video processing
- Bulk operations
- Cache management

## Continuous Integration

### GitHub Actions Example

Create `.github/workflows/test.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      redis:
        image: redis:latest
        ports:
          - 6379:6379
        options: --health-cmd "redis-cli ping" --health-interval 10s
    
    steps:
    - uses: actions/checkout@v2
    
    - uses: julia-actions/setup-julia@v1
      with:
        version: '1.9'
    
    - name: Install Firestore Emulator
      run: |
        curl -Lo firebase-tools.tar.gz https://firebase.tools/bin/linux/latest
        tar xzf firebase-tools.tar.gz
    
    - name: Start Firestore Emulator
      run: |
        ./firebase emulators:start --only firestore --project demo-project &
        sleep 10
    
    - name: Install dependencies
      run: julia --project=. -e 'using Pkg; Pkg.instantiate()'
    
    - name: Run tests
      run: julia --project=. -e 'using Pkg; Pkg.test()'
      env:
        FIRESTORE_EMULATOR_HOST: 127.0.0.1:8080
        REDIS_DB: 1
```

## Debugging Tests

### Run Specific Test Set

```julia
using Test
using VideosDB

# Run only DB tests
@testset "DB Tests Only" begin
    include("test/runtests.jl")
end
```

### Enable Debug Logging

```bash
LOGLEVEL=DEBUG julia --project=. test/runtests.jl
```

### Interactive Test Debugging

```julia
julia> using Pkg
julia> Pkg.activate(".")
julia> using VideosDB
julia> using Test

# Run individual test
julia> @testset "Single Test" begin
           # Your test code
       end
```

## Test Coverage

### Install Coverage Package

```bash
julia --project=. -e 'using Pkg; Pkg.add("Coverage")'
```

### Generate Coverage Report

```julia
using Coverage

# Collect coverage
coverage = process_folder()

# Generate report
covered_lines, total_lines = get_summary(coverage)
percentage = covered_lines / total_lines * 100

println("Coverage: $(round(percentage, digits=2))%")

# Generate HTML report
writefile("coverage.html", coverage)
```

## Common Test Issues

### Issue: Firestore Emulator Not Found

```bash
# Solution: Install emulator
gcloud components install cloud-firestore-emulator

# Or check if running
ps aux | grep firestore
```

### Issue: Redis Connection Failed

```bash
# Solution: Start Redis
redis-server

# Check if running
redis-cli ping  # Should return "PONG"
```

### Issue: Test Data Not Found

```bash
# Solution: Create test_data directory
mkdir -p test/test_data

# Copy from Python tests
cp -r ../backend/tests/test_data/* test/test_data/
```

### Issue: Package Not Found

```bash
# Solution: Ensure you're in project environment
julia --project=. -e 'using Pkg; Pkg.instantiate()'
```

## Performance Benchmarks

Expected performance targets:

- **Slugify**: < 1 μs per operation
- **Parse Duration**: < 100 ns per operation
- **Parse DateTime**: < 1 μs per operation
- **Full Sync**: < 60 seconds for 100 videos
- **Cache Hit**: < 1 ms per request

## Test Best Practices

1. **Isolation**: Each test should be independent
2. **Cleanup**: Always clean up test data
3. **Mocking**: Use mocks for external services
4. **Deterministic**: Tests should produce same results
5. **Fast**: Unit tests should run in < 1s

## Troubleshooting

### Tests Hang

- Check for infinite loops
- Verify emulator is responding
- Check Redis connection
- Look for deadlocks in concurrent code

### Tests Fail Randomly

- Check for race conditions
- Verify thread safety
- Look for shared mutable state
- Check external service timeouts

### Memory Issues

- Run with memory profiling
- Check for memory leaks
- Verify proper cleanup
- Monitor GC behavior

## Next Steps

1. Set up test data directory
2. Start Firestore emulator
3. Start Redis server
4. Run basic tests
5. Add CI/CD integration
6. Monitor test coverage