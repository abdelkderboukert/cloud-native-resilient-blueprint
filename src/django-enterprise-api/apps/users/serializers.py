"""
User REST Serializers
"""

from rest_framework import serializers
from django.contrib.auth.models import User
from apps.users.models import UserProfile


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ["id", "tier", "department", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "is_active", "profile"]
        read_only_fields = ["id", "is_active"]


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    tier = serializers.CharField(write_only=True, required=False, default="standard")
    department = serializers.CharField(write_only=True, required=False, default="")

    class Meta:
        model = User
        fields = ["id", "username", "email", "password", "tier", "department"]

    def create(self, validated_data):
        tier = validated_data.pop("tier", "standard")
        department = validated_data.pop("department", "")
        password = validated_data.pop("password")

        user = User.objects.create_user(
            password=password,
            **validated_data
        )

        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.tier = tier
        profile.department = department
        profile.save()

        return user
