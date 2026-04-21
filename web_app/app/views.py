import os
from urllib.parse import urlparse

import requests
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils.html import escape
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

DEFAULT_API_BASE_URLS = [
    "http://reservation-service:8001",
    "http://reservation_service:8001",
    "http://localhost:8001",
    "http://127.0.0.1:8001",
]

raw_api_urls = os.environ.get("RESERVATION_SERVICE_URL", "").strip()
if raw_api_urls:
    API_BASE_URLS = [url.strip().rstrip("/") for url in raw_api_urls.split(",") if url.strip()]
else:
    API_BASE_URLS = DEFAULT_API_BASE_URLS


def _reservation_request(method, path, **kwargs):
    last_error = None
    for base_url in API_BASE_URLS:
        try:
            request_kwargs = dict(kwargs)
            headers = dict(request_kwargs.pop("headers", {}) or {})

            parsed = urlparse(base_url)
            hostname = parsed.hostname or ""
            if "_" in hostname and "host" not in {k.lower() for k in headers}:
                host_header = os.environ.get("RESERVATION_SERVICE_HOST_HEADER", "localhost").strip() or "localhost"
                if parsed.port:
                    host_header = f"{host_header}:{parsed.port}"
                headers["Host"] = host_header

            request_kwargs["headers"] = headers
            request_kwargs.setdefault("timeout", 10)
            return requests.request(method, f"{base_url}{path}", **request_kwargs)
        except requests.RequestException as exc:
            last_error = exc
    if last_error:
        raise last_error
    raise requests.RequestException("No reservation service URL configured.")


def _service_unavailable_response(action, _exc):
    return HttpResponse(
        (
            f"<h3>{escape(action)} unavailable</h3>"
            "<p>Could not reach the reservation service.</p>"
            "<p>Please ensure reservation_service is running and reachable.</p>"
            "<p><a href='/login/'>Back to login</a></p>"
        ),
        status=503,
    )


def _extract_error_detail(response, default_message):
    if response.status_code >= 500:
        return "Reservation service encountered an internal error. Please try again."

    try:
        payload = response.json()
        if isinstance(payload, dict):
            detail = payload.get("detail")
            if isinstance(detail, str) and detail.strip():
                return detail.strip()

            serializer_errors = []
            for field, messages in payload.items():
                if isinstance(messages, list):
                    message_text = "; ".join(str(msg) for msg in messages if str(msg).strip())
                else:
                    message_text = str(messages).strip()
                if message_text:
                    serializer_errors.append(f"{field}: {message_text}")
            if serializer_errors:
                return ", ".join(serializer_errors)
    except ValueError:
        pass

    raw_text = (response.text or "").strip()
    lowered = raw_text.lower()
    if "<!doctype html" in lowered or "<html" in lowered:
        return default_message
    if raw_text:
        return raw_text[:300]
    return default_message


def _auth_headers(request):
    token = request.session.get("access_token")
    if not token:
        return None
    return {"Authorization": f"Bearer {token}"}


def _api_request(request, method, path, **kwargs):
    headers = kwargs.pop("headers", {}) or {}
    auth_headers = _auth_headers(request)
    if auth_headers:
        headers.update(auth_headers)
    return _reservation_request(method, path, headers=headers, **kwargs)


def _require_login(request):
    if "access_token" not in request.session:
        return redirect("login")
    return None


@require_http_methods(["GET", "POST"])
@csrf_exempt
def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username", "")
        password = request.POST.get("password", "")
        try:
            response = _reservation_request(
                "POST",
                "/api/token/",
                json={"username": username, "password": password},
            )
        except requests.RequestException as exc:
            return _service_unavailable_response("Login service", exc)
        if response.status_code == 200:
            payload = response.json()
            request.session["access_token"] = payload["access"]
            request.session["refresh_token"] = payload["refresh"]
            request.session["username"] = username
            return redirect("movies")

        error_detail = _extract_error_detail(response, "Login failed.")

        return HttpResponse(
            (
                f"<h3>Login failed</h3><p>{escape(error_detail)}</p>"
                "<p><a href='/login/'>Try again</a> | <a href='/register/'>Create account</a></p>"
            ),
            status=response.status_code,
        )

    return HttpResponse(
        """
        <html><body style='font-family:Arial;max-width:420px;margin:40px auto'>
        <h2>CineBook Login</h2>
        <form method='post'>
          <label>Username</label><br/><input name='username' /><br/><br/>
          <label>Password</label><br/><input type='password' name='password' /><br/><br/>
          <button type='submit'>Login</button>
        </form>
        <p>No account yet? <a href='/register/'>Create one</a></p>
        </body></html>
        """
    )


@require_http_methods(["GET", "POST"])
@csrf_exempt
def register_view(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        try:
            response = _reservation_request(
                "POST",
                "/api/register/",
                json={"username": username, "email": email, "password": password},
            )
        except requests.RequestException as exc:
            return _service_unavailable_response("Registration service", exc)
        if response.status_code in (200, 201):
            return HttpResponse(
                "<h3>Account created</h3><p>You can now <a href='/login/'>log in</a>.</p>",
                status=201,
            )

        error_detail = _extract_error_detail(response, "Registration failed.")

        return HttpResponse(
            (
                f"<h3>Registration failed</h3><p>{escape(error_detail)}</p>"
                "<p><a href='/register/'>Try again</a> | <a href='/login/'>Back to login</a></p>"
            ),
            status=response.status_code,
        )

    return HttpResponse(
        """
        <html><body style='font-family:Arial;max-width:420px;margin:40px auto'>
        <h2>Create account</h2>
        <form method='post'>
          <label>Username</label><br/><input name='username' required /><br/><br/>
          <label>Email</label><br/><input type='email' name='email' required /><br/><br/>
          <label>Password</label><br/><input type='password' name='password' required /><br/><br/>
          <button type='submit'>Register</button>
        </form>
        <p>Already have an account? <a href='/login/'>Log in</a></p>
        </body></html>
        """
    )


def logout_view(request):
    request.session.flush()
    return redirect("login")


def movies_view(request):
    login_redirect = _require_login(request)
    if login_redirect:
        return login_redirect

    try:
        movies_resp = _api_request(request, "GET", "/api/movies/")
        showtimes_resp = _api_request(request, "GET", "/api/showtimes/")
    except requests.RequestException as exc:
        return _service_unavailable_response("Movies API", exc)
    if movies_resp.status_code == 401 or showtimes_resp.status_code == 401:
        return redirect("login")

    movies = movies_resp.json() if movies_resp.ok else []
    showtimes = showtimes_resp.json() if showtimes_resp.ok else []
    grouped_showtimes = {}
    for showtime in showtimes:
        grouped_showtimes.setdefault(showtime["movie"], []).append(showtime)

    movie_cards = [
        {
            "movie": movie,
            "showtimes": grouped_showtimes.get(movie["id"], []),
        }
        for movie in movies
    ]

    return render(
        request,
        "movies.html",
        {
            "movie_cards": movie_cards,
        },
    )


def seats_view(request, showtime_id):
    login_redirect = _require_login(request)
    if login_redirect:
        return login_redirect

    try:
        seats_resp = _api_request(request, "GET", f"/api/seats/?showtime={showtime_id}")
        showtime_resp = _api_request(request, "GET", f"/api/showtimes/{showtime_id}/")
    except requests.RequestException as exc:
        return _service_unavailable_response("Seats API", exc)
    if seats_resp.status_code == 401 or showtime_resp.status_code == 401:
        return redirect("login")

    seats = seats_resp.json() if seats_resp.ok else []
    showtime = showtime_resp.json() if showtime_resp.ok else {"id": showtime_id}

    return render(request, "seats.html", {"showtime": showtime, "seats": seats})


@require_http_methods(["POST"])
def checkout_view(request, showtime_id):
    login_redirect = _require_login(request)
    if login_redirect:
        return login_redirect

    selected_seats = request.POST.getlist("seat_ids")
    if not selected_seats:
        return redirect("seats", showtime_id=showtime_id)

    try:
        seats_resp = _api_request(request, "GET", f"/api/seats/?showtime={showtime_id}")
        showtime_resp = _api_request(request, "GET", f"/api/showtimes/{showtime_id}/")
    except requests.RequestException as exc:
        return _service_unavailable_response("Checkout API", exc)
    seats = seats_resp.json() if seats_resp.ok else []
    showtime = showtime_resp.json() if showtime_resp.ok else {"id": showtime_id}
    selected = [seat for seat in seats if str(seat["id"]) in selected_seats]

    return render(
        request,
        "checkout.html",
        {"showtime": showtime, "selected_seats": selected, "selected_seat_ids": selected_seats},
    )


@require_http_methods(["POST"])
def confirmation_view(request, showtime_id):
    login_redirect = _require_login(request)
    if login_redirect:
        return login_redirect

    seat_ids = [int(seat_id) for seat_id in request.POST.getlist("seat_ids")]
    try:
        create_resp = _api_request(
            request,
            "POST",
            "/api/reservations/",
            json={"showtime": int(showtime_id), "seats": seat_ids},
        )
    except requests.RequestException as exc:
        return _service_unavailable_response("Reservation API", exc)
    if create_resp.status_code == 401:
        return redirect("login")
    if not create_resp.ok:
        return HttpResponse(f"Reservation failed: {create_resp.text}", status=create_resp.status_code)

    reservation = create_resp.json()
    try:
        confirm_resp = _api_request(request, "PATCH", f"/api/reservations/{reservation['id']}/confirm/")
    except requests.RequestException as exc:
        return _service_unavailable_response("Confirmation API", exc)
    if not confirm_resp.ok:
        return HttpResponse(f"Confirmation failed: {confirm_resp.text}", status=confirm_resp.status_code)

    confirmed = confirm_resp.json()
    return render(request, "confirmation.html", {"reservation": confirmed})
