from django.conf import settings
from django.http import HttpResponse
from django.urls import path, re_path
import requests


def _proxy(request, target_base, suffix=''):
    url = f"{target_base.rstrip('/')}/{suffix}"
    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in {'host', 'content-length'}
    }
    response = requests.request(
        method=request.method,
        url=url,
        headers=headers,
        params=request.GET,
        data=request.body,
        timeout=30,
    )
    proxied = HttpResponse(response.content, status=response.status_code)
    for key, value in response.headers.items():
        if key.lower() not in {'content-encoding', 'transfer-encoding', 'connection'}:
            proxied[key] = value
    return proxied


def proxy_api(request, path=''):
    return _proxy(request, settings.RESERVATION_SERVICE_URL, path)


def proxy_web(request, path=''):
    return _proxy(request, settings.WEB_APP_URL, path)


urlpatterns = [
    path('api/', proxy_api),
    re_path(r'^api/(?P<path>.*)$', proxy_api),
    path('', proxy_web),
    re_path(r'^(?P<path>.*)$', proxy_web),
]
