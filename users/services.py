import random
import requests
from django.core.cache import cache
from django.conf import settings
from celery import shared_task
import time


class SmsService:
    @staticmethod
    @shared_task
    def send_sms(phone_number, code):
        time.sleep(random.uniform(1, 2))

        if settings.SMS_API_KEY and settings.SMS_API_USER:
            try:

                response = requests.post(
                    "https://gate.smsaero.ru/v2/sms/send",
                    auth=(settings.SMS_API_USER, settings.SMS_API_KEY),
                    json={
                        "number": phone_number,
                        "text": f"Ваш код подтверждения: {code}",
                        "sign": "SMS Aero",
                    },
                    timeout=10,
                )

                result = response.json()
                print(f"Ответ SMS Aero: {result}")

                if response.status_code == 200 and result.get("success"):
                    print(f"SMS отправлено на {phone_number}")
                    return result
                else:
                    print(f"Ошибка: {result.get('message')}")
                    print(f"имитация Код для {phone_number}: {code}")
                    return {"success": True, "simulated": True}

            except Exception as e:
                print(f"Ошибка: {e}")
                print(f"имитация Код для {phone_number}: {code}")
                return {"success": True, "simulated": True}

        print(f"Код для {phone_number}: {code}")
        return {"success": True, "simulated": True}


class AuthService:
    VERIFICATION_CODE_TTL = 300

    @staticmethod
    def generate_verification_code():
        return str(random.randint(1000, 9999))

    @staticmethod
    def send_verification_code(phone_number):
        code = AuthService.generate_verification_code()
        cache.set(
            f"auth_code:{phone_number}", code, timeout=AuthService.VERIFICATION_CODE_TTL
        )
        SmsService.send_sms.delay(phone_number, code)
        return True

    @staticmethod
    def verify_code(phone_number, code):
        cached_code = cache.get(f"auth_code:{phone_number}")
        if cached_code and cached_code == code:
            cache.delete(f"auth_code:{phone_number}")
            return True
        return False
