from django.urls import path

from base.consumers import ChatConsumer

websocket_urlpatterns = [
    path('ws/chat/<int:conversation_id>/', ChatConsumer.as_asgi()),
]
