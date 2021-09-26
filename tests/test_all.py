import pytest
from httpx import AsyncClient


@pytest.fixture
async def client():
    async with AsyncClient() as client:
        yield client


@pytest.mark.asyncio
async def test_no_404(client):
    r = await client.get("https://www.sadhguru.digital")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_sitemap_exists(client):
    r = await client.request("HEAD", "https://www.sadhguru.digital/sitemap.xml")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_app_loaded(client):
    r = await client.get("https://www.sadhguru.digital")
    assert "Sadhguru wisdom" in r.text


@pytest.mark.asyncio
async def test_http_to_https(client):
    r = await client.get("http://www.sadhguru.digital")
    assert r.url.scheme == "https"
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_non_www_to_www(client):
    r = await client.get("https://sadhguru.digital")
    assert r.url.host == "www.sadhguru.digital"
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_api_no_404(client):
    r = await client.get("https://backend.sadhguru.digital/api")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_ipfs_up(client):
    r = await client.get("https://ipfs.sadhguru.digital")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_ipfs_videos_up(client):
    r = await client.get("https://videos.sadhguru.digital/asdf")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_ipfs_one_video(client):
    r = await client.request("HEAD", 'https://ipfs.sadhguru.digital/ipfs/Qmauotw36R8HqgXpBQcNWr8MQTWqNo32d7h1NUMR8Apdeo')
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_ipfs_videos_one_video(client):
    r = await client.request("HEAD", 'https://videos.sadhguru.digital/Sadhguru%20-%20Living%20Life%20in%20Style%20%5B5Hn2YNJSrIk%5D.mp4')
    assert r.status_code == 200
