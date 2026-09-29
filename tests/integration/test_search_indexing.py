"""Public search-indexing contract for Mimir."""

from django.urls import reverse


def test_landing_with_search_indexing_exposes_verification_and_canonical(client):
    """The public landing page proves ownership and declares its canonical URL."""
    response = client.get(reverse("index"))

    assert response.status_code == 200
    assert b'name="google-site-verification"' in response.content
    assert b'content="tasyhteYK4pTnMjwnunq70M8ph-pBphFoK83kvTsfj8"' in response.content
    assert b'rel="canonical" href="https://mimir.featurefactory.io/"' in response.content


def test_robots_with_safe_request_returns_public_crawl_contract(client):
    """Robots policy exposes the sitemap without inviting private-route crawling."""
    response = client.get(reverse("robots_txt"))

    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/plain")
    assert b"User-agent: *" in response.content
    assert b"Disallow: /admin/" in response.content
    assert b"Sitemap: https://mimir.featurefactory.io/sitemap.xml" in response.content


def test_sitemap_with_safe_request_returns_canonical_public_url(client):
    """Sitemap publishes only Mimir's stable public landing URL."""
    response = client.get(reverse("sitemap_xml"))

    assert response.status_code == 200
    assert response["Content-Type"].startswith("application/xml")
    assert b"<loc>https://mimir.featurefactory.io/</loc>" in response.content


def test_indexing_endpoints_with_post_reject_unsafe_method(client):
    """Read-only indexing endpoints fail closed for unsafe methods."""
    assert client.post(reverse("robots_txt")).status_code == 405
    assert client.post(reverse("sitemap_xml")).status_code == 405
