"""Public search-engine discovery endpoints."""

from django.http import HttpRequest, HttpResponse
from django.views.decorators.http import require_safe

ROBOTS_POLICY = """User-agent: *
Allow: /
Disallow: /admin/
Disallow: /api/
Disallow: /auth/
Disallow: /dashboard/
Disallow: /notifications/
Disallow: /search/
Sitemap: https://mimir.featurefactory.io/sitemap.xml
"""

SITEMAP_XML = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://mimir.featurefactory.io/</loc>
  </url>
</urlset>
"""


@require_safe
def robots_txt(request: HttpRequest) -> HttpResponse:
    """Return Mimir's public crawler policy.

    :param request: Safe HTTP request supplied by Django.
    :return: Plain-text robots policy with the canonical sitemap URL.
    """
    return HttpResponse(ROBOTS_POLICY, content_type="text/plain; charset=utf-8")


@require_safe
def sitemap_xml(request: HttpRequest) -> HttpResponse:
    """Return the canonical public URL set for Mimir.

    :param request: Safe HTTP request supplied by Django.
    :return: XML sitemap containing only stable public URLs.
    """
    return HttpResponse(SITEMAP_XML, content_type="application/xml; charset=utf-8")
