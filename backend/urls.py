"""
URL configuration for backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('backend.authentication.urls')),
    path('api/account/', include('backend.accounts.urls')),
    path('api/journal/', include('backend.journal.urls')),
    path('api/support/', include('backend.support.urls')),
    path('api/market/', include('backend.market.urls')),
    path('api/news/', include('backend.intelligence.news.urls')),
    path('api/smc/', include('backend.smc.urls')),
    path('api/execution/', include('backend.execution.urls')),
    path('api/backtesting/', include('backend.backtesting.urls')),
    path('api/strategies/scalping/', include('backend.strategies.scalping.urls')),
    path('api/strategies/day-trading/', include('backend.strategies.day_trading.urls')),
    path('accounts/', include('django.contrib.auth.urls')),
]
