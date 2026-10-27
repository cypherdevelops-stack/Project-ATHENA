import json
from json import JSONDecodeError

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST


def _json_body(request):
    try:
        body = json.loads(request.body or '{}')
    except JSONDecodeError:
        return None, JsonResponse({'detail': 'Request body must be valid JSON.'}, status=400)

    if not isinstance(body, dict):
        return None, JsonResponse({'detail': 'Request body must be a JSON object.'}, status=400)
    return body, None


def _user_payload(user):
    return {
        'id': str(user.pk),
        'email': user.email,
        'displayName': user.get_full_name() or user.email,
    }


def _session_payload(request):
    if not request.user.is_authenticated:
        return {'user': None}
    return {'user': _user_payload(request.user)}


@ensure_csrf_cookie
@require_GET
def session_view(request):
    return JsonResponse(_session_payload(request))


@require_POST
def login_view(request):
    body, error = _json_body(request)
    if error:
        return error

    login_identifier = str(body.get('email', body.get('username', ''))).strip()
    password = body.get('password', '')
    if not login_identifier or not isinstance(password, str) or not password:
        return JsonResponse({'detail': 'Email or username and password are required.'}, status=400)

    email_user = User.objects.filter(email__iexact=login_identifier).first()
    user = authenticate(request, username=login_identifier, password=password)
    if user is None and email_user and email_user.get_username() != login_identifier:
        user = authenticate(request, username=email_user.get_username(), password=password)

    if user is None or not user.is_active:
        if User.objects.filter(
            Q(email__iexact=login_identifier) | Q(username__iexact=login_identifier),
            is_active=True,
        ).exists():
            return JsonResponse({'detail': 'Incorrect password.'}, status=401)
        return JsonResponse({'detail': 'Invalid email, username, or password.'}, status=401)

    login(request, user)
    return JsonResponse(_session_payload(request))


@require_POST
def signup_view(request):
    body, error = _json_body(request)
    if error:
        return error

    email = str(body.get('email', '')).strip().lower()
    password = body.get('password', '')
    password_confirmation = body.get('passwordConfirmation', '')

    try:
        validate_email(email)
    except ValidationError:
        return JsonResponse({'detail': 'Enter a valid email address.'}, status=400)

    if not isinstance(password, str) or not password:
        return JsonResponse({'detail': 'Password is required.'}, status=400)
    if password != password_confirmation:
        return JsonResponse({'detail': 'Passwords do not match.'}, status=400)
    if User.objects.filter(email__iexact=email).exists() or User.objects.filter(username__iexact=email).exists():
        return JsonResponse({'detail': 'An account with this email already exists.'}, status=409)

    try:
        validate_password(password, user=User(username=email, email=email))
    except ValidationError as validation_error:
        return JsonResponse({'detail': ' '.join(validation_error.messages)}, status=400)

    try:
        user = User.objects.create_user(username=email, email=email, password=password)
    except IntegrityError:
        return JsonResponse({'detail': 'An account with this email already exists.'}, status=409)
    from backend.accounts.models import Account

    Account.objects.create(user=user)
    login(request, user)
    return JsonResponse(_session_payload(request), status=201)


@require_POST
def logout_view(request):
    logout(request)
    return JsonResponse({}, status=204)


@require_POST
def password_reset_view(request):
    body, error = _json_body(request)
    if error:
        return error

    email = str(body.get('email', '')).strip().lower()
    form = PasswordResetForm({'email': email})
    if form.is_valid():
        form.save(request=request, use_https=request.is_secure())

    return JsonResponse({'detail': 'If an account exists, reset instructions will be sent.'})
