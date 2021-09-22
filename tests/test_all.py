import pytest
from httpx import AsyncClient


@pytest.fixture
async def client():
    async with AsyncClient() as client:
        yield client


# def is_port_open(host, port):

#     a_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

#     location = (host, port)
#     result_of_check = a_socket.connect_ex(location)
#     a_socket.close()
#     if result_of_check == 0:
#         return True
#     else:
#         return False


@pytest.mark.asyncio
async def test_no_404(client):
    r = await client.get("https://www.sadhguru.digital")
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
async def test_videos_up(client):
    r = await client.get("https://videos.sadhguru.digital/asdf")
    assert r.status_code == 404
