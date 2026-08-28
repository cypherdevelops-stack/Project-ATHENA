from django.urls import path

from .views import adaptive_statistics_view, current_news_view, news_reactions_view, news_snapshots_view, provider_health_view

urlpatterns = [
    path('current', current_news_view, name='news-current'),
    path('snapshots', news_snapshots_view, name='news-snapshots'),
    path('reactions', news_reactions_view, name='news-reactions'),
    path('adaptive', adaptive_statistics_view, name='news-adaptive'),
    path('providers/health', provider_health_view, name='news-provider-health'),
]
