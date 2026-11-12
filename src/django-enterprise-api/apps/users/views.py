"""User API endpoints and event publishing."""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth.models import User
from apps.users.serializers import UserSerializer, UserRegistrationSerializer
from apps.core.kafka_producer import kafka_producer


class UserViewSet(viewsets.ModelViewSet):
    """Provide user CRUD operations and publish lifecycle events."""

    queryset = User.objects.all().select_related("profile")
    serializer_class = UserSerializer

    def get_serializer_class(self):
        if self.action == "create":
            return UserRegistrationSerializer
        return UserSerializer

    def perform_create(self, serializer):
        user = serializer.save()
        user_data = UserSerializer(user).data
        kafka_producer.publish_user_event(
            event_type="user.registered",
            user_data=user_data,
        )

    def perform_update(self, serializer):
        user = serializer.save()
        user_data = UserSerializer(user).data
        kafka_producer.publish_user_event(
            event_type="user.updated",
            user_data=user_data,
        )

    def perform_destroy(self, instance):
        user_data = {"id": instance.id, "username": instance.username, "status": "deleted"}
        instance.delete()
        kafka_producer.publish_user_event(
            event_type="user.deleted",
            user_data=user_data,
        )
