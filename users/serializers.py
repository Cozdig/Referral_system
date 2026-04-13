from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()


class PhoneNumberSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15)


class VerificationCodeSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15)
    code = serializers.CharField(max_length=4)


class InviteCodeSerializer(serializers.Serializer):
    invite_code = serializers.CharField(max_length=6)


class UserProfileSerializer(serializers.ModelSerializer):
    referrals = serializers.SerializerMethodField()
    has_activated_invite_code = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "phone_number",
            "invite_code",
            "activated_invite_code",
            "has_activated_invite_code",
            "referrals",
            "created_at",
        ]

    def get_referrals(self, obj):
        return [user.phone_number for user in obj.get_referrals()]

    def get_has_activated_invite_code(self, obj):
        return bool(obj.activated_invite_code)
