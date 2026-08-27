from django.urls import path

from .views import confirmed_demo_order_view, execution_analysis_view, execution_audit_view, execution_orchestration_view, execution_events_view, execution_price_view, execution_signals_view, live_order_view, model_status_view, open_paper_position_view, paper_positions_view, reconcile_execution_view, train_xgboost_view, training_status_view, validate_model_view

urlpatterns = [
    path('analysis', execution_analysis_view, name='execution-analysis'),
    path('orchestration', execution_orchestration_view, name='execution-orchestration'),
    path('events', execution_events_view, name='execution-events'),
    path('audit', execution_audit_view, name='execution-audit'),
    path('reconcile', reconcile_execution_view, name='execution-reconcile'),
    path('train-model', train_xgboost_view, name='execution-train-model'),
    path('train-model/status', training_status_view, name='execution-training-status'),
    path('model-status', model_status_view, name='execution-model-status'),
    path('validate-model', validate_model_view, name='execution-validate-model'),
    path('signals', execution_signals_view, name='execution-signals'),
    path('price', execution_price_view, name='execution-price'),
    path('paper/position', open_paper_position_view, name='execution-open-paper-position'),
    path('paper/positions', paper_positions_view, name='execution-paper-positions'),
    path('live/order', live_order_view, name='execution-live-order'),
    path('live/demo-order', confirmed_demo_order_view, name='execution-confirmed-demo-order'),
]
