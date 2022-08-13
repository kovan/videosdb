import pytest
from urllib.request import urlopen, Request


def test_no_404():
    r = urlopen("https://www.sadhguru.digital")
    assert r.code == 200


def test_sitemap_exists():
    r = urlopen(Request("HEAD", "https://www.sadhguru.digital/sitemap.xml"))
    assert r.code == 200


def test_app_loaded():
    r = urlopen("https://www.sadhguru.digital")
    assert "Sadhguru wisdom" in r.text


def test_http_to_https():
    r = urlopen("http://www.sadhguru.digital")
    assert r.url.scheme == "https"
    assert r.code == 200


def test_non_www_to_www():
    r = urlopen("https://sadhguru.digital")
    assert r.url.host == "www.sadhguru.digital"
    assert r.code == 200


def test_api_no_404():
    r = urlopen("https://backend.sadhguru.digital/api")
    assert r.code == 200


def test_ipfs_up():
    r = urlopen("https://ipfs.sadhguru.digital")
    assert r.code == 404


def test_ipfs_videos_up():
    r = urlopen("https://videos.sadhguru.digital/asdf")
    assert r.code == 404


def test_ipfs_one_video():
    r = urlopen(
        'https://ipfs.sadhguru.digital/ipfs/QmYi7wrRFKVCcTB56A6Pep2j31Q5mHfmmu21RzHXu25RVR')
    assert r.code == 200


def test_ipfs_videos_one_video():
    r = urlopen(Request(
        "HEAD", 'https://videos.sadhguru.digital/Sadhguru%20-%20Living%20Life%20in%20Style%20%5B5Hn2YNJSrIk%5D.mp4'))
    assert r.code == 200
