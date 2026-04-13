from celery import shared_task
from .services import SmsService

@shared_task
def send_sms_task(phone_number, code):
    return SmsService.send_sms(phone_number, code)