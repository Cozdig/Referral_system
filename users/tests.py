from django.test import TestCase, Client
from django.core.cache import cache
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch
from .models import User
from .services import AuthService


class UserModelTests(TestCase):
    """Тесты модели пользователя"""

    def setUp(self):
        self.user = User.objects.create_user(phone_number="+79991234567")
        self.user2 = User.objects.create_user(phone_number="+79882223344")

    def test_create_user(self):
        """Тест создания пользователя"""
        self.assertEqual(self.user.phone_number, "+79991234567")
        self.assertTrue(self.user.is_active)
        self.assertFalse(self.user.is_staff)
        self.assertIsNone(self.user.invite_code)

    def test_generate_invite_code(self):
        """Тест генерации инвайт-кода"""
        code = self.user.generate_invite_code()
        self.assertEqual(len(code), 6)
        self.assertTrue(code.isalnum())
        self.assertEqual(self.user.invite_code, code)

    def test_invite_code_unique(self):
        """Тест уникальности инвайт-кода"""
        code1 = self.user.generate_invite_code()
        code2 = self.user2.generate_invite_code()
        self.assertNotEqual(code1, code2)

    def test_activate_valid_invite_code(self):
        """Тест активации валидного инвайт-кода"""
        code = self.user2.generate_invite_code()
        result = self.user.activate_invite_code(code)
        self.assertTrue(result)
        self.assertEqual(self.user.activated_invite_code, code)

    def test_activate_invalid_invite_code(self):
        """Тест активации невалидного кода"""
        with self.assertRaises(ValueError) as context:
            self.user.activate_invite_code("INVALID")
        self.assertIn("Неверный инвайт-код", str(context.exception))

    def test_activate_own_invite_code(self):
        """Тест: нельзя активировать свой код"""
        code = self.user.generate_invite_code()
        with self.assertRaises(ValueError) as context:
            self.user.activate_invite_code(code)
        self.assertIn("свой собственный", str(context.exception))

    def test_activate_code_twice(self):
        """Тест: нельзя активировать код дважды"""
        code = self.user2.generate_invite_code()
        self.user.activate_invite_code(code)

        with self.assertRaises(ValueError) as context:
            self.user.activate_invite_code(code)
        self.assertIn("уже активировали", str(context.exception))

    def test_get_referrals(self):
        """Тест получения списка рефералов"""
        code = self.user.generate_invite_code()
        self.user2.activate_invite_code(code)

        referrals = self.user.get_referrals()
        self.assertEqual(referrals.count(), 1)
        self.assertEqual(referrals.first(), self.user2)

    def test_string_representation(self):
        """Тест строкового представления"""
        self.assertEqual(str(self.user), "+79991234567")


class AuthServiceTests(TestCase):
    """Тесты сервиса авторизации"""

    def setUp(self):
        cache.clear()

    def test_generate_verification_code(self):
        """Тест генерации кода верификации"""
        code = AuthService.generate_verification_code()
        self.assertEqual(len(code), 4)
        self.assertTrue(code.isdigit())

    def test_send_verification_code(self):
        """Тест отправки кода верификации"""
        phone_number = "+79991234567"
        result = AuthService.send_verification_code(phone_number)
        self.assertTrue(result)

        cached_code = cache.get(f"auth_code:{phone_number}")
        self.assertIsNotNone(cached_code)
        self.assertEqual(len(cached_code), 4)

    def test_verify_valid_code(self):
        """Тест верификации валидного кода"""
        phone_number = "+79991234567"
        AuthService.send_verification_code(phone_number)

        cached_code = cache.get(f"auth_code:{phone_number}")
        result = AuthService.verify_code(phone_number, cached_code)

        self.assertTrue(result)
        self.assertIsNone(cache.get(f"auth_code:{phone_number}"))

    def test_verify_invalid_code(self):
        """Тест верификации невалидного кода"""
        phone_number = "+79991234567"
        AuthService.send_verification_code(phone_number)

        result = AuthService.verify_code(phone_number, "9999")
        self.assertFalse(result)

    def test_verify_expired_code(self):
        """Тест верификации просроченного кода"""
        phone_number = "+79991234567"
        AuthService.send_verification_code(phone_number)

        cache.delete(f"auth_code:{phone_number}")

        result = AuthService.verify_code(phone_number, "1234")
        self.assertFalse(result)


class APITests(TestCase):
    """Тесты API"""

    def setUp(self):
        self.client = APIClient()
        cache.clear()
        self.user = User.objects.create_user(phone_number="+79991234567")
        self.user.generate_invite_code()

    @patch("users.services.SmsService.send_sms")
    def test_request_code_api(self, mock_send_sms):
        """Тест API запроса кода"""
        mock_send_sms.return_value = {"success": True}
        url = "/users/request-api/"
        data = {"phone_number": "+79991112233"}

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["message"], "Verification code sent successfully"
        )
        self.assertEqual(response.data["phone_number"], "+79991112233")

    def test_request_code_api_invalid_phone(self):
        """Тест API с невалидным номером"""
        url = "/users/request-api/"
        data = {"phone_number": ""}

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_verify_code_api(self):
        """Тест API верификации кода"""
        phone_number = "+79991112233"

        AuthService.send_verification_code(phone_number)
        cached_code = cache.get(f"auth_code:{phone_number}")

        url = "/users/verify-api/"
        data = {"phone_number": phone_number, "code": cached_code}

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("user", response.data)
        self.assertIn("invite_code", response.data["user"])

    def test_verify_code_api_invalid_code(self):
        """Тест API с неверным кодом"""
        phone_number = "+79991112233"
        AuthService.send_verification_code(phone_number)

        url = "/users/verify-api/"
        data = {"phone_number": phone_number, "code": "9999"}

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_profile_api_requires_auth(self):
        """Тест: профиль требует авторизации"""
        url = "/users/profile-api/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_profile_api_authenticated(self):
        """Тест API профиля с авторизацией"""
        self.client.force_authenticate(user=self.user)

        url = "/users/profile-api/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["phone_number"], self.user.phone_number)
        self.assertEqual(response.data["invite_code"], self.user.invite_code)

    def test_activate_invite_code_api(self):
        """Тест API активации инвайт-кода"""
        user2 = User.objects.create_user(phone_number="+79882223344")
        user2.generate_invite_code()

        self.client.force_authenticate(user=self.user)

        url = "/users/profile-api/"
        data = {"invite_code": user2.invite_code}
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Invite code activated successfully")

        self.user.refresh_from_db()
        self.assertEqual(self.user.activated_invite_code, user2.invite_code)

    def test_activate_own_invite_code_api(self):
        """Тест API: нельзя активировать свой код"""
        self.client.force_authenticate(user=self.user)

        url = "/users/profile-api/"
        data = {"invite_code": self.user.invite_code}
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_logout_api(self):
        """Тест API выхода"""
        self.client.force_authenticate(user=self.user)

        url = "/users/logout-api/"
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Logged out successfully")


class TemplateViewsTests(TestCase):
    """Тесты шаблонов"""

    def setUp(self):
        self.client = Client()
        cache.clear()
        self.user = User.objects.create_user(phone_number="+79991234567")
        self.user.generate_invite_code()

    def test_login_page(self):
        """Тест страницы логина"""
        response = self.client.get("/users/login/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "users/login.html")

    def test_login_post(self):
        """Тест отправки номера телефона"""
        response = self.client.post("/users/login/", {"phone_number": "+79991112233"})
        self.assertRedirects(response, "/users/verify/")
        self.assertIn("temp_phone", self.client.session)

    def test_verify_page_requires_temp_phone(self):
        """Тест: страница верификации требует номер в сессии"""
        response = self.client.get("/users/verify/")
        self.assertRedirects(response, "/users/login/")

    def test_verify_post_valid_code(self):
        """Тест верификации с правильным кодом"""
        phone_number = "+79991112233"
        AuthService.send_verification_code(phone_number)
        cached_code = cache.get(f"auth_code:{phone_number}")

        session = self.client.session
        session["temp_phone"] = phone_number
        session.save()

        response = self.client.post("/users/verify/", {"code": cached_code})

        self.assertRedirects(response, "/users/profile/")

        user = User.objects.filter(phone_number=phone_number).first()
        self.assertIsNotNone(user)
        self.assertIsNotNone(user.invite_code)

    def test_profile_page_requires_auth(self):
        """Тест: страница профиля требует авторизации"""
        response = self.client.get("/users/profile/")
        self.assertRedirects(response, "/users/login/")

    def test_profile_page_authenticated(self):
        """Тест страницы профиля с авторизацией"""
        session = self.client.session
        session["user_id"] = self.user.id
        session.save()

        response = self.client.get("/users/profile/")

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "users/profile.html")
        self.assertContains(response, self.user.phone_number)
        self.assertContains(response, self.user.invite_code)

    def test_activate_invite_code_in_profile(self):
        """Тест активации кода через профиль"""
        user2 = User.objects.create_user(phone_number="+79882223344")
        user2.generate_invite_code()

        session = self.client.session
        session["user_id"] = self.user.id
        session.save()

        response = self.client.post(
            "/users/profile/", {"invite_code": user2.invite_code}
        )

        self.assertRedirects(response, "/users/profile/")

        self.user.refresh_from_db()
        self.assertEqual(self.user.activated_invite_code, user2.invite_code)

    def test_logout(self):
        """Тест выхода из системы"""
        session = self.client.session
        session["user_id"] = self.user.id
        session.save()

        response = self.client.post("/users/logout/")
        self.assertRedirects(response, "/users/login/")
        self.assertIsNone(self.client.session.get("user_id"))


class IntegrationTests(TestCase):
    """Интеграционные тесты"""

    def setUp(self):
        self.client = Client()
        cache.clear()

    def test_full_registration_flow(self):
        """Тест полного цикла регистрации"""
        phone_number = "+79991112233"

        response = self.client.post("/users/login/", {"phone_number": phone_number})
        self.assertRedirects(response, "/users/verify/")

        cached_code = cache.get(f"auth_code:{phone_number}")
        self.assertIsNotNone(cached_code)

        response = self.client.post("/users/verify/", {"code": cached_code})
        self.assertRedirects(response, "/users/profile/")

        response = self.client.get("/users/profile/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, phone_number)

        user = User.objects.filter(phone_number=phone_number).first()
        self.assertIsNotNone(user)
        self.assertIsNotNone(user.invite_code)

    def test_referral_flow(self):
        """Тест полного цикла реферальной системы"""
        # Регистрируем пользователя 1
        phone1 = "+79991112233"
        self.client.post("/users/login/", {"phone_number": phone1})
        code1 = cache.get(f"auth_code:{phone1}")
        self.client.post("/users/verify/", {"code": code1})

        user1 = User.objects.get(phone_number=phone1)
        invite_code1 = user1.invite_code

        self.client.post("/users/logout/")

        # Регистрируем пользователя 2
        phone2 = "+79994445566"
        self.client.post("/users/login/", {"phone_number": phone2})
        code2 = cache.get(f"auth_code:{phone2}")
        self.client.post("/users/verify/", {"code": code2})

        user2 = User.objects.get(phone_number=phone2)

        # Пользователь 2 активирует код пользователя 1
        response = self.client.post("/users/profile/", {"invite_code": invite_code1})
        self.assertRedirects(response, "/users/profile/")

        user2.refresh_from_db()
        self.assertEqual(user2.activated_invite_code, invite_code1)

        self.client.post("/users/logout/")

        # Логинимся как пользователь 1
        self.client.post("/users/login/", {"phone_number": phone1})
        code1_new = cache.get(f"auth_code:{phone1}")
        self.client.post("/users/verify/", {"code": code1_new})

        response = self.client.get("/users/profile/")
        self.assertContains(response, phone2)
