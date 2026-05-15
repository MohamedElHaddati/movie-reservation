import os
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests
from django.http import HttpResponse
from django.shortcuts import redirect, render
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

POSTER_GRADIENTS = [
    "from-indigo-500 to-violet-600",
    "from-rose-500 to-orange-500",
    "from-emerald-500 to-teal-600",
    "from-sky-500 to-cyan-600",
    "from-fuchsia-500 to-pink-600",
]


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


def _service_unavailable_response(request, action):
    return render(
        request,
        "error.html",
        {
            "error_title": f"{action} unavailable",
            "error_message": "Could not reach the reservation service. Please make sure reservation_service is running.",
            "show_nav": "access_token" in request.session,
        },
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


def _movie_initials(title):
    words = [word for word in (title or "").split() if word]
    if not words:
        return "CB"
    return "".join(word[0].upper() for word in words[:2])


def _formatted_showtime(raw_value):
    if not raw_value:
        return "Time TBD"
    try:
        parsed = datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
        return parsed.strftime("%a %d %b · %H:%M")
    except ValueError:
        return raw_value


def _parse_datetime(raw_value):
    if not raw_value:
        return None
    try:
        parsed = datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _decorate_reservation(reservation):
    showtime = reservation.get("showtime_details") or {}
    movie = showtime.get("movie") or {}
    seat_details = reservation.get("seat_details") or []
    showtime_dt = _parse_datetime(showtime.get("datetime"))
    now_utc = datetime.now(timezone.utc)

    if showtime_dt:
        is_upcoming = showtime_dt >= now_utc
        display_showtime = _formatted_showtime(showtime.get("datetime"))
    else:
        is_upcoming = False
        display_showtime = "Time TBD"

    seat_labels = [seat.get("seat_number") for seat in seat_details if seat.get("seat_number")]

    return {
        **reservation,
        "showtime_details": {
            **showtime,
            "movie": movie,
            "display_datetime": display_showtime,
        },
        "seat_details": seat_details,
        "seat_labels": seat_labels,
        "seat_summary": ", ".join(seat_labels) if seat_labels else "No seats",
        "is_upcoming": is_upcoming,
    }


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
        except requests.RequestException:
            return _service_unavailable_response(request, "Login service")
        if response.status_code == 200:
            payload = response.json()
            request.session["access_token"] = payload["access"]
            request.session["refresh_token"] = payload["refresh"]
            request.session["username"] = username
            return redirect("movies")

        error_detail = _extract_error_detail(response, "Login failed.")
        return render(
            request,
            "auth/login.html",
            {"error_message": error_detail, "username": username, "show_nav": False},
            status=response.status_code,
        )

    return render(request, "auth/login.html", {"show_nav": False})


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
        except requests.RequestException:
            return _service_unavailable_response(request, "Registration service")
        if response.status_code in (200, 201):
            return render(
                request,
                "auth/register.html",
                {"account_created": True, "show_nav": False},
                status=201,
            )

        error_detail = _extract_error_detail(response, "Registration failed.")
        return render(
            request,
            "auth/register.html",
            {"error_message": error_detail, "username": username, "email": email, "show_nav": False},
            status=response.status_code,
        )

    return render(request, "auth/register.html", {"show_nav": False})


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
    except requests.RequestException:
        return _service_unavailable_response(request, "Movies API")
    if movies_resp.status_code == 401 or showtimes_resp.status_code == 401:
        return redirect("login")

    movies = movies_resp.json() if movies_resp.ok else []
    showtimes = showtimes_resp.json() if showtimes_resp.ok else []
    grouped_showtimes = {}
    for showtime in showtimes:
        grouped_showtimes.setdefault(showtime["movie"], []).append(
            {
                **showtime,
                "display_datetime": _formatted_showtime(showtime.get("datetime")),
            }
        )

    movie_cards = [
        {
            "movie": movie,
            "showtimes": grouped_showtimes.get(movie["id"], []),
            "poster_gradient": POSTER_GRADIENTS[(movie.get("id", 1) - 1) % len(POSTER_GRADIENTS)],
            "poster_initials": _movie_initials(movie.get("title")),
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


@require_http_methods(["GET"])
def reservations_view(request):
    login_redirect = _require_login(request)
    if login_redirect:
        return login_redirect

    try:
        reservations_resp = _api_request(request, "GET", "/api/reservations/")
    except requests.RequestException:
        return _service_unavailable_response(request, "Reservations API")
    if reservations_resp.status_code == 401:
        return redirect("login")
    if not reservations_resp.ok:
        return render(
            request,
            "error.html",
            {
                "error_title": "Could not load reservations",
                "error_message": _extract_error_detail(reservations_resp, "Failed to fetch reservations."),
            },
            status=reservations_resp.status_code,
        )

    reservations = reservations_resp.json() if reservations_resp.ok else []
    decorated = [_decorate_reservation(reservation) for reservation in reservations]
    upcoming_reservations = [reservation for reservation in decorated if reservation["is_upcoming"]]
    past_reservations = [reservation for reservation in decorated if not reservation["is_upcoming"]]

    return render(
        request,
        "reservations.html",
        {
            "upcoming_reservations": upcoming_reservations,
            "past_reservations": past_reservations,
        },
    )


@require_http_methods(["GET"])
def reservation_detail_view(request, reservation_id):
    login_redirect = _require_login(request)
    if login_redirect:
        return login_redirect

    try:
        reservation_resp = _api_request(request, "GET", f"/api/reservations/{reservation_id}/")
    except requests.RequestException:
        return _service_unavailable_response(request, "Reservation details API")
    if reservation_resp.status_code == 401:
        return redirect("login")
    if reservation_resp.status_code == 404:
        return render(
            request,
            "error.html",
            {
                "error_title": "Reservation not found",
                "error_message": "This reservation does not exist or is not accessible for your account.",
            },
            status=404,
        )
    if not reservation_resp.ok:
        return render(
            request,
            "error.html",
            {
                "error_title": "Could not load reservation",
                "error_message": _extract_error_detail(reservation_resp, "Failed to fetch reservation details."),
            },
            status=reservation_resp.status_code,
        )

    reservation = _decorate_reservation(reservation_resp.json())
    return render(request, "reservation_detail.html", {"reservation": reservation})


@require_http_methods(["GET"])
def reservation_ticket_view(request, reservation_id):
    login_redirect = _require_login(request)
    if login_redirect:
        return login_redirect

    try:
        ticket_resp = _api_request(request, "GET", f"/api/reservations/{reservation_id}/ticket/")
    except requests.RequestException:
        return _service_unavailable_response(request, "Ticket API")
    if ticket_resp.status_code == 401:
        return redirect("login")
    if ticket_resp.status_code == 404:
        return render(
            request,
            "error.html",
            {
                "error_title": "Reservation not found",
                "error_message": "Could not find ticket information for this reservation.",
            },
            status=404,
        )
    if not ticket_resp.ok:
        return render(
            request,
            "error.html",
            {
                "error_title": "Could not load ticket",
                "error_message": _extract_error_detail(ticket_resp, "Failed to load ticket details."),
            },
            status=ticket_resp.status_code,
        )

    payload = ticket_resp.json() if ticket_resp.ok else {}
    reservation = _decorate_reservation(payload.get("reservation") or {})
    ticket = payload.get("ticket") or {}
    return render(
        request,
        "reservation_ticket.html",
        {
            "reservation": reservation,
            "ticket": ticket,
            "resent": request.GET.get("resent") == "1",
        },
    )


@require_http_methods(["GET"])
def reservation_ticket_download_view(request, reservation_id):
    login_redirect = _require_login(request)
    if login_redirect:
        return login_redirect

    inline = request.GET.get("inline") == "1"
    try:
        ticket_download_resp = _api_request(
            request,
            "GET",
            f"/api/reservations/{reservation_id}/ticket/download/",
            params={"download": "0" if inline else "1"},
        )
    except requests.RequestException:
        return _service_unavailable_response(request, "Ticket download API")
    if ticket_download_resp.status_code == 401:
        return redirect("login")
    if not ticket_download_resp.ok:
        return render(
            request,
            "error.html",
            {
                "error_title": "Ticket unavailable",
                "error_message": _extract_error_detail(ticket_download_resp, "The ticket is not available yet."),
            },
            status=ticket_download_resp.status_code,
        )

    response = HttpResponse(
        ticket_download_resp.content,
        content_type=ticket_download_resp.headers.get("Content-Type", "application/pdf"),
    )
    disposition = "inline" if inline else "attachment"
    response["Content-Disposition"] = f'{disposition}; filename="cinebook-ticket-{reservation_id}.pdf"'
    return response


@require_http_methods(["POST"])
def reservation_ticket_resend_view(request, reservation_id):
    login_redirect = _require_login(request)
    if login_redirect:
        return login_redirect

    try:
        resend_resp = _api_request(request, "POST", f"/api/reservations/{reservation_id}/ticket/resend/")
    except requests.RequestException:
        return _service_unavailable_response(request, "Ticket resend API")
    if resend_resp.status_code == 401:
        return redirect("login")
    if not resend_resp.ok:
        return render(
            request,
            "error.html",
            {
                "error_title": "Could not resend ticket",
                "error_message": _extract_error_detail(resend_resp, "Please try again in a moment."),
            },
            status=resend_resp.status_code,
        )
    return redirect(f"/reservations/{reservation_id}/ticket/?resent=1")


def seats_view(request, showtime_id):
    login_redirect = _require_login(request)
    if login_redirect:
        return login_redirect

    try:
        seats_resp = _api_request(request, "GET", f"/api/seats/?showtime={showtime_id}")
        showtime_resp = _api_request(request, "GET", f"/api/showtimes/{showtime_id}/")
    except requests.RequestException:
        return _service_unavailable_response(request, "Seats API")
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
    except requests.RequestException:
        return _service_unavailable_response(request, "Checkout API")
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
    except requests.RequestException:
        return _service_unavailable_response(request, "Reservation API")
    if create_resp.status_code == 401:
        return redirect("login")
    if not create_resp.ok:
        return render(
            request,
            "error.html",
            {
                "error_title": "Reservation failed",
                "error_message": _extract_error_detail(create_resp, "Could not create the reservation."),
            },
            status=create_resp.status_code,
        )

    reservation = create_resp.json()
    try:
        confirm_resp = _api_request(request, "PATCH", f"/api/reservations/{reservation['id']}/confirm/")
    except requests.RequestException:
        return _service_unavailable_response(request, "Confirmation API")
    if not confirm_resp.ok:
        return render(
            request,
            "error.html",
            {
                "error_title": "Confirmation failed",
                "error_message": _extract_error_detail(confirm_resp, "Could not confirm the reservation."),
            },
            status=confirm_resp.status_code,
        )

    confirmed = confirm_resp.json()
    return render(request, "confirmation.html", {"reservation": confirmed})
