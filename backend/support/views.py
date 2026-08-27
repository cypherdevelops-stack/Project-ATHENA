from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .models import HelpAttachment, HelpRequest
from .assistant import answer_help_request


MAX_ATTACHMENTS = 5
MAX_ATTACHMENT_SIZE = 10 * 1024 * 1024


@login_required
@require_POST
def create_help_request_view(request):
    message = request.POST.get('message', '').strip()
    files = request.FILES.getlist('files')

    if not message and not files:
        return JsonResponse({'detail': 'Add a message or attach a file before sending.'}, status=400)
    if len(files) > MAX_ATTACHMENTS:
        return JsonResponse({'detail': f'You can attach up to {MAX_ATTACHMENTS} files.'}, status=400)
    if any(upload.size > MAX_ATTACHMENT_SIZE for upload in files):
        return JsonResponse({'detail': 'Each attachment must be 10 MB or smaller.'}, status=400)

    help_request = HelpRequest.objects.create(user=request.user, message=message)
    for upload in files:
        HelpAttachment.objects.create(request=help_request, file=upload, original_name=upload.name[:255])

    answer = answer_help_request(message)
    return JsonResponse({
        'id': help_request.pk,
        'status': 'received',
        'message': answer.text,
        'intent': answer.intent,
        'grounded': answer.grounded,
        'attachments': [upload.name for upload in files],
        'createdAt': help_request.created_at.isoformat(),
    }, status=201)
