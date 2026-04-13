from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models
import random
import string


class UserManager(BaseUserManager):
    def create_user(self, phone_number, password=None, **extra_fields):
        if not phone_number:
            raise ValueError("Phone number is required")

        user = self.model(phone_number=phone_number, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        return self.create_user(phone_number, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    phone_number = models.CharField(max_length=15, unique=True)
    invite_code = models.CharField(max_length=6, unique=True, null=True, blank=True)
    activated_invite_code = models.CharField(max_length=6, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "phone_number"
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.phone_number

    def generate_invite_code(self):
        characters = string.digits + string.ascii_uppercase
        code = "".join(random.choices(characters, k=6))
        while User.objects.filter(invite_code=code).exists():
            code = "".join(random.choices(characters, k=6))
        self.invite_code = code
        self.save()
        return code

    def activate_invite_code(self, code):
        if self.activated_invite_code:
            raise ValueError("Вы уже активировали инвайт-код")

        if not User.objects.filter(invite_code=code).exists():
            raise ValueError("Неверный инвайт-код")

        if code == self.invite_code:
            raise ValueError("Нельзя активировать свой собственный инвайт-код")

        self.activated_invite_code = code
        self.save()
        return True

    def get_referrals(self):
        return User.objects.filter(activated_invite_code=self.invite_code)

    class Meta:
        db_table = "users"
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
