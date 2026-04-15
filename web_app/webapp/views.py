import requests
from django.conf import settings
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect, render


def _api_headers():
    headers = {'Content-Type': 'application/json'}
    if settings.CLIENT_JWT:
        headers['Authorization'] = f'Bearer {settings.CLIENT_JWT}'
    return headers


def movies_view(request):
    response = requests.get(f"{settings.GATEWAY_URL}/api/movies/", headers=_api_headers(), timeout=15)
    movies = response.json() if response.ok else []
    return render(request, 'movies.html', {'movies': movies})


def seats_view(request, showtime_id):
    response = requests.get(
        f"{settings.GATEWAY_URL}/api/showtimes/{showtime_id}/seats/",
        headers=_api_headers(),
        timeout=15,
    )
    seats = response.json() if response.ok else []
    return render(request, 'seats.html', {'showtime_id': showtime_id, 'seats': seats})


def checkout_view(request):
    if request.method == 'GET':
        showtime_id = request.GET.get('showtime_id')
        seat_ids = request.GET.getlist('seat_ids')
        return render(request, 'checkout.html', {'showtime_id': showtime_id, 'seat_ids': seat_ids})

    showtime_id = request.POST.get('showtime_id')
    seat_ids = request.POST.getlist('seat_ids')
    user_id = request.POST.get('user_id', 'client-001')
    user_email = request.POST.get('user_email', 'client@cinebook.local')

    if not showtime_id or not seat_ids:
        return HttpResponseBadRequest('Missing showtime or seats')

    create_response = requests.post(
        f"{settings.GATEWAY_URL}/api/reservations/",
        headers=_api_headers(),
        json={
            'user_id': user_id,
            'user_email': user_email,
            'showtime_id': int(showtime_id),
            'seat_ids': [int(s) for s in seat_ids],
        },
        timeout=20,
    )
    if not create_response.ok:
        return render(
            request,
            'checkout.html',
            {'error': create_response.text, 'showtime_id': showtime_id, 'seat_ids': seat_ids},
        )

    reservation = create_response.json()
    reservation_id = reservation['id']

    confirm_response = requests.post(
        f"{settings.GATEWAY_URL}/api/reservations/{reservation_id}/confirm/",
        headers=_api_headers(),
        timeout=20,
    )
    if not confirm_response.ok:
        return render(
            request,
            'checkout.html',
            {'error': confirm_response.text, 'showtime_id': showtime_id, 'seat_ids': seat_ids},
        )

    return redirect('confirmation', reservation_id=reservation_id)


def confirmation_view(request, reservation_id):
    return render(request, 'confirmation.html', {'reservation_id': reservation_id})
