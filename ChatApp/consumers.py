import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Room, Message


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # make a unique group name per room
        self.room_name = f"room_{self.scope['url_route']['kwargs']['room_name']}"
        # join the group
        await self.channel_layer.group_add(self.room_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        # leave the group
        await self.channel_layer.group_discard(self.room_name, self.channel_name)

    async def receive(self, text_data):
        # called when a message is received from WebSocket
        text_data_json = json.loads(text_data)
        message = text_data_json.get('message')
        sender = text_data_json.get('sender')
        room_name = text_data_json.get('room_name')

        # broadcast to group — this will call send_message on each consumer in the group
        await self.channel_layer.group_send(
            self.room_name,
            {
                'type': 'send_message',    # maps to the async def send_message(...)
                'message': {
                    'sender': sender,
                    'message': message,
                    'room_name': room_name
                }
            }
        )

    async def send_message(self, event):
        # called when group_send sends an event with type 'send_message'
        data = event['message']
        # save message to DB (synchronously via wrapper)
        await self.create_message(data=data)

        response_data = {
            'sender': data['sender'],
            'message': data['message']
        }
        # send the JSON back to the WebSocket client
        await self.send(text_data=json.dumps({'message': response_data}))

    @database_sync_to_async
    def create_message(self, data):
        # DB operations must run in sync code, so we use database_sync_to_async
        get_room_by_name = Room.objects.get(room_name=data['room_name'])
        # optional: prevent duplicates if desired (PDF used a filter check)
        if not Message.objects.filter(message=data['message'], room=get_room_by_name, sender=data['sender']).exists():
            new_message = Message(room=get_room_by_name, sender=data['sender'], message=data['message'])
            new_message.save()
