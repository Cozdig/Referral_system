from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status
from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from .services import AuthService
from .serializers import (
    PhoneNumberSerializer,
    VerificationCodeSerializer,
    InviteCodeSerializer,
    UserProfileSerializer
)
from django.contrib.auth import get_user_model

User = get_user_model()


class RequestCodeAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PhoneNumberSerializer(data=request.data)
        if serializer.is_valid():
            phone_number = serializer.validated_data['phone_number']
            AuthService.send_verification_code(phone_number)
            return Response({
                'message': 'Verification code sent successfully',
                'phone_number': phone_number
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VerifyCodeAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerificationCodeSerializer(data=request.data)
        if serializer.is_valid():
            phone_number = serializer.validated_data['phone_number']
            code = serializer.validated_data['code']

            if AuthService.verify_code(phone_number, code):
                user, created = User.objects.get_or_create(
                    phone_number=phone_number
                )

                if created:
                    user.generate_invite_code()

                request.session['user_id'] = user.id

                return Response({
                    'message': 'Authentication successful',
                    'user': UserProfileSerializer(user).data
                }, status=status.HTTP_200_OK)

            return Response({
                'error': 'Invalid verification code'
            }, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)

    def post(self, request):
        serializer = InviteCodeSerializer(data=request.data)
        if serializer.is_valid():
            invite_code = serializer.validated_data['invite_code']

            try:
                request.user.activate_invite_code(invite_code)
                return Response({
                    'message': 'Invite code activated successfully',
                    'activated_invite_code': request.user.activated_invite_code
                }, status=status.HTTP_200_OK)
            except ValueError as e:
                return Response({
                    'error': str(e)
                }, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        request.session.flush()
        return Response({'message': 'Logged out successfully'})


# Базовые Templates для тестирования
class LoginTemplateView(View):
    def get(self, request):
        return render(request, 'users/login.html')

    def post(self, request):
        phone_number = request.POST.get('phone_number')
        if phone_number:
            AuthService.send_verification_code(phone_number)
            request.session['temp_phone'] = phone_number
            return redirect('verify')
        messages.error(request, 'Phone number is required')
        return render(request, 'users/login.html')


class VerifyTemplateView(View):
    def get(self, request):
        if not request.session.get('temp_phone'):
            return redirect('login')
        return render(request, 'users/verify.html')

    def post(self, request):
        code = request.POST.get('code')
        phone_number = request.session.get('temp_phone')

        if AuthService.verify_code(phone_number, code):
            user, created = User.objects.get_or_create(phone_number=phone_number)
            if created:
                user.generate_invite_code()
            request.session['user_id'] = user.id
            request.session.pop('temp_phone', None)
            return redirect('profile')

        messages.error(request, 'Invalid verification code')
        return render(request, 'users/verify.html')


class ProfileTemplateView(View):
    def get(self, request):
        user_id = request.session.get('user_id')
        if not user_id:
            return redirect('login')

        try:
            user = User.objects.get(id=user_id)
            print(f"DEBUG: User found - ID: {user.id}, Phone: {user.phone_number}")
            print(f"DEBUG: Invite code: {user.invite_code}")
            print(f"DEBUG: Activated code: {user.activated_invite_code}")

            referrals = user.get_referrals()
            print(f"DEBUG: Referrals count: {referrals.count()}")

        except User.DoesNotExist:
            print(f"DEBUG: User with ID {user_id} not found")
            return redirect('login')

        context = {
            'user': user,
            'referrals': referrals
        }
        return render(request, 'users/profile.html', context)

    def post(self, request):
        user_id = request.session.get('user_id')
        if not user_id:
            return redirect('login')

        try:
            user = User.objects.get(id=user_id)
            invite_code = request.POST.get('invite_code')

            print(f"DEBUG: Trying to activate code {invite_code} for user {user.phone_number}")

            try:
                user.activate_invite_code(invite_code)
                messages.success(request, 'Инвайт-код успешно активирован!')
                print(f"DEBUG: Code activated successfully")
            except ValueError as e:
                messages.error(request, str(e))
                print(f"DEBUG: Error - {e}")

        except User.DoesNotExist:
            return redirect('login')

        return redirect('profile')

class LogoutTemplateView(View):
    def post(self, request):
        request.session.flush()
        return redirect('login')