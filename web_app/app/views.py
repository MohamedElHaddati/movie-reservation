import os

import requests
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

API_BASE_URL = os.environ.get("RESERVATION_SERVICE_URL", "http://reservation_service:8001")


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
    return requests.request(method, f"{API_BASE_URL}{path}", headers=headers, timeout=10, **kwargs)


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
        response = requests.post(
            f"{API_BASE_URL}/api/token/",
            json={"username": username, "password": password},
            timeout=10,
        )
        if response.status_code == 200:
            payload = response.json()
            request.session["access_token"] = payload["access"]
            request.session["refresh_token"] = payload["refresh"]
            request.session["username"] = username
            return redirect("movies")
        return HttpResponse(
            "<h3>Login failed</h3><p>Invalid credentials.</p><p><a href='/login/'>Try again</a></p>",
            status=401,
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

    movies_resp = _api_request(request, "GET", "/api/movies/")
    showtimes_resp = _api_request(request, "GET", "/api/showtimes/")
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

    seats_resp = _api_request(request, "GET", f"/api/seats/?showtime={showtime_id}")
    showtime_resp = _api_request(request, "GET", f"/api/showtimes/{showtime_id}/")
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

    seats_resp = _api_request(request, "GET", f"/api/seats/?showtime={showtime_id}")
    showtime_resp = _api_request(request, "GET", f"/api/showtimes/{showtime_id}/")
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
    create_resp = _api_request(
        request,
        "POST",
        "/api/reservations/",
        json={"showtime": int(showtime_id), "seats": seat_ids},
    )
    if create_resp.status_code == 401:
        return redirect("login")
    if not create_resp.ok:
        return HttpResponse(f"Reservation failed: {create_resp.text}", status=create_resp.status_code)

    reservation = create_resp.json()
    confirm_resp = _api_request(request, "PATCH", f"/api/reservations/{reservation['id']}/confirm/")
    if not confirm_resp.ok:
        return HttpResponse(f"Confirmation failed: {confirm_resp.text}", status=confirm_resp.status_code)

    confirmed = confirm_resp.json()
    return render(request, "confirmation.html", {"reservation": confirmed})
