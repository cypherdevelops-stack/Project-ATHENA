import json
import random
from json import JSONDecodeError

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.models import User
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError
from django.db.models import Q
from django.http import JsonResponse
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
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


def _email_verification_key(email: str) -> str:
    return f'athena:email-verification:{email.strip().lower()}'


@require_POST
def send_verification_code_view(request):
    body, error = _json_body(request)
    if error:
        return error

    email = str(body.get('email', '')).strip().lower()
    if not email:
        return JsonResponse({'detail': 'Email is required.'}, status=400)
    try:
        validate_email(email)
    except ValidationError:
        return JsonResponse({'detail': 'Enter a valid email address.'}, status=400)

    code = str(random.randint(1000, 9999)).zfill(4)
    cache.set(_email_verification_key(email), code, timeout=600)
    return JsonResponse({'detail': 'A verification code has been sent to your email.'})


@require_POST
def verify_email_view(request):
    body, error = _json_body(request)
    if error:
        return error

    email = str(body.get('email', '')).strip().lower()
    code = str(body.get('code', '')).strip()
    if not email or not code:
        return JsonResponse({'detail': 'Email and verification code are required.'}, status=400)

    expected_code = cache.get(_email_verification_key(email))
    if expected_code is None or str(expected_code) != code:
        return JsonResponse({'detail': 'The verification code is incorrect or has expired.'}, status=400)

    cache.delete(_email_verification_key(email))
    return JsonResponse({'detail': 'Email verified successfully.'})


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


@require_POST
def verify_password_reset_link_view(request):
    body, error = _json_body(request)
    if error:
        return error

    uid = str(body.get('uid', '')).strip()
    token = str(body.get('token', '')).strip()
    if not uid or not token:
        return JsonResponse({'detail': 'A valid reset link is required.'}, status=400)

    try:
        user_id = force_str(urlsafe_base64_decode(uid))
    except (TypeError, ValueError):
        return JsonResponse({'detail': 'This password reset link is invalid.'}, status=400)

    user = User.objects.filter(pk=user_id).first()
    if user is None or not PasswordResetTokenGenerator().check_token(user, token):
        return JsonResponse({'detail': 'This password reset link is invalid or expired.'}, status=400)

    return JsonResponse({'detail': 'Password reset link is valid.'})


@require_POST
def complete_password_reset_view(request):
    body, error = _json_body(request)
    if error:
        return error

    uid = str(body.get('uid', '')).strip()
    token = str(body.get('token', '')).strip()
    password = body.get('password', '')
    password_confirmation = body.get('passwordConfirmation', '')

    if not uid or not token:
        return JsonResponse({'detail': 'A valid reset link is required.'}, status=400)
    if not isinstance(password, str) or not password:
        return JsonResponse({'detail': 'Password is required.'}, status=400)
    if password != password_confirmation:
        return JsonResponse({'detail': 'Passwords do not match.'}, status=400)

    try:
        user_id = force_str(urlsafe_base64_decode(uid))
    except (TypeError, ValueError):
        return JsonResponse({'detail': 'This password reset link is invalid.'}, status=400)

    user = User.objects.filter(pk=user_id).first()
    if user is None or not PasswordResetTokenGenerator().check_token(user, token):
        return JsonResponse({'detail': 'This password reset link is invalid or expired.'}, status=400)

    try:
        validate_password(password, user=user)
    except ValidationError as validation_error:
        return JsonResponse({'detail': ' '.join(validation_error.messages)}, status=400)

    user.set_password(password)
    user.save(update_fields=['password'])
    return JsonResponse({'detail': 'Your password has been reset.'})
