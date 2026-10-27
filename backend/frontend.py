from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404
from django.db import transaction
from django.views.decorators.http import require_GET

FRONTEND_INDEX = Path(settings.BASE_DIR) / 'frontend' / 'dist' / 'index.html'


@transaction.non_atomic_requests(using='learning_memory')
@transaction.non_atomic_requests(using='backtesting')
@transaction.non_atomic_requests(using='market_intelligence')
@transaction.non_atomic_requests
@require_GET
def frontend_app(request):
    try:
        return FileResponse(FRONTEND_INDEX.open('rb'), content_type='text/html; charset=utf-8')
    except FileNotFoundError as error:
        raise Http404('Frontend build not found. Run npm run build in the frontend directory.') from error
