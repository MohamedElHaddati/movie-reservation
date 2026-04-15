import jwt
from django.conf import settings
from django.http import JsonResponse


class JWTValidationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith('/api/'):
            auth = request.headers.get('Authorization', '')
            if not auth.startswith('Bearer '):
                return JsonResponse({'detail': 'Missing Bearer token'}, status=401)

            token = auth.split(' ', 1)[1]
            try:
                payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=['HS256'])
            except jwt.PyJWTError:
                return JsonResponse({'detail': 'Invalid token'}, status=401)

            role = payload.get('role')
            if role not in {'admin', 'client'}:
                return JsonResponse({'detail': 'Invalid role'}, status=403)

            request.jwt_payload = payload
        return self.get_response(request)
