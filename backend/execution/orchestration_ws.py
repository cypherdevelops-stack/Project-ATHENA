from __future__ import annotations

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from backend.accounts.models import Account
from backend.execution.models import OrchestratorAlert


class OrchestratorConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time orchestration stream.
    
    Streams:
    - Live orchestration decisions
    - Strategy status updates
    - Alerts and notifications
    - Portfolio state changes
    
    Usage (frontend):
    ```javascript
    const ws = new WebSocket('ws://localhost:8000/ws/orchestration/XAUUSD/');
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'orchestration_update') {
            // Handle orchestration decision
        } else if (data.type === 'alert') {
            // Handle alert
        }
    };
    ```
    """
    
    async def connect(self):
        """Accept WebSocket connection and join room for symbol."""
        self.symbol = self.scope['url_route']['kwargs'].get('symbol', 'XAUUSD')
        self.account_id = self.scope['url_route']['kwargs'].get('account_id')
        self.room_group_name = f'orchestration_{self.symbol}'
        
        # Verify user has access to this account
        if self.account_id:
            account = await self._get_account(self.account_id)
            if not account or account.user_id != getattr(self.scope['user'], 'pk', None):
                await self.close()
                return
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send initial connection confirmation
        await self.send(json.dumps({
            'type': 'connection_established',
            'symbol': self.symbol,
            'timestamp': timezone.now().isoformat(),
        }))
    
    async def disconnect(self, close_code):
        """Remove from room group on disconnect."""
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """
        Handle incoming WebSocket messages.
        
        Clients can send:
        - {'action': 'subscribe_alerts'}: Subscribe to alert notifications
        - {'action': 'unsubscribe_alerts'}: Unsubscribe from alerts
        """
        try:
            data = json.loads(text_data)
            action = data.get('action')
            
            if action == 'subscribe_alerts':
                # Client wants alert notifications
                self.send_alerts = True
                await self.send(json.dumps({
                    'type': 'subscription_confirmed',
                    'subscriptions': ['alerts'],
                }))
            elif action == 'unsubscribe_alerts':
                self.send_alerts = False
                await self.send(json.dumps({
                    'type': 'subscription_changed',
                    'subscriptions': [],
                }))
        except json.JSONDecodeError:
            await self.send(json.dumps({
                'type': 'error',
                'message': 'Invalid JSON',
            }))
    
    # Message handlers (called from group_send)
    async def orchestration_update(self, event):
        """Send orchestration update to WebSocket."""
        await self.send(json.dumps({
            'type': 'orchestration_update',
            'payload': event['payload'],
            'timestamp': event.get('timestamp'),
        }))
    
    async def alert_notification(self, event):
        """Send alert notification to WebSocket."""
        await self.send(json.dumps({
            'type': 'alert',
            'severity': event['severity'],
            'alert_type': event['alert_type'],
            'title': event['title'],
            'message': event['message'],
            'timestamp': event.get('timestamp'),
        }))
    
    async def risk_state_change(self, event):
        """Send risk state change to WebSocket."""
        await self.send(json.dumps({
            'type': 'risk_state_change',
            'strategy': event['strategy'],
            'new_state': event['new_state'],
            'reason': event['reason'],
            'timestamp': event.get('timestamp'),
        }))
    
    async def regime_change(self, event):
        """Send regime change to WebSocket."""
        await self.send(json.dumps({
            'type': 'regime_change',
            'regime': event['regime'],
            'timestamp': event.get('timestamp'),
        }))
    
    @database_sync_to_async
    def _get_account(self, account_id: int) -> Account | None:
        """Fetch account from database."""
        try:
            return Account.objects.get(pk=account_id)
        except Account.DoesNotExist:
            return None


class OrchestrationNotificationMixin:
    """
    Mixin for sending notifications through WebSocket.
    
    Usage in orchestrator service:
    ```python
    await send_orchestration_update('XAUUSD', payload)
    await send_orchestration_alert('XAUUSD', 'INFO', 'DECISION_CHANGED', title, message)
    ```
    """
    
    @staticmethod
    async def send_orchestration_update(symbol: str, payload: dict) -> None:
        """Send orchestration update to all connected clients for a symbol."""
        from channels.layers import get_channel_layer
        
        channel_layer = get_channel_layer()
        await channel_layer.group_send(
            f'orchestration_{symbol}',
            {
                'type': 'orchestration_update',
                'payload': payload,
                'timestamp': timezone.now().isoformat(),
            }
        )
    
    @staticmethod
    async def send_orchestration_alert(
        symbol: str,
        severity: str,
        alert_type: str,
        title: str,
        message: str,
    ) -> None:
        """Send alert notification to all connected clients for a symbol."""
        from channels.layers import get_channel_layer
        
        channel_layer = get_channel_layer()
        await channel_layer.group_send(
            f'orchestration_{symbol}',
            {
                'type': 'alert_notification',
                'severity': severity,
                'alert_type': alert_type,
                'title': title,
                'message': message,
                'timestamp': timezone.now().isoformat(),
            }
        )
    
    @staticmethod
    async def send_risk_state_change(
        symbol: str,
        strategy: str,
        new_state: str,
        reason: str,
    ) -> None:
        """Send risk state change to all connected clients for a symbol."""
        from channels.layers import get_channel_layer
        
        channel_layer = get_channel_layer()
        await channel_layer.group_send(
            f'orchestration_{symbol}',
            {
                'type': 'risk_state_change',
                'strategy': strategy,
                'new_state': new_state,
                'reason': reason,
                'timestamp': timezone.now().isoformat(),
            }
        )
    
    @staticmethod
    async def send_regime_change(symbol: str, regime: str) -> None:
        """Send regime change to all connected clients for a symbol."""
        from channels.layers import get_channel_layer
        
        channel_layer = get_channel_layer()
        await channel_layer.group_send(
            f'orchestration_{symbol}',
            {
                'type': 'regime_change',
                'regime': regime,
                'timestamp': timezone.now().isoformat(),
            }
        )
