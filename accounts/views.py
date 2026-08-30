from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from .serializers import (
    SendOTPSerializer,
    VerifyOTPSerializer,
    UserSerializer,
    TaskSerializer
)

from .permissions import Isadmin, IsTaskOwner
from .models import Task
from .services import (
    send_otp_service,
    verify_otp_service,
    create_task_service,
    update_task_service
)
from rest_framework import viewsets
from .models import AuditLog
from .serializers import AuditLogSerializer
User = get_user_model()


class SendOTPView(APIView):
    def post(self, request):
        serializer = SendOTPSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        send_otp_service(serializer.validated_data['email'])

        return Response(
            {"message": "OTP sent successfully"},
            status=200
        )

class VerifyOTPView(APIView):
    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        result = verify_otp_service(
            serializer.validated_data['email'],
            serializer.validated_data['otp']
        )

        if "error" in result:
            return Response(result, status=400)

        return Response(result, status=200)


class TestView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"message": "You are logged in",
                         "username":request.user.username
                         })


class UserListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        users = User.objects.filter(role='user')
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)


class TaskCreateView(APIView):
    permission_classes = [IsAuthenticated, Isadmin]

    def post(self, request):
        serializer = TaskSerializer(data=request.data)

        if serializer.is_valid():
            task = create_task_service(
                serializer.validated_data,
                request.user
            )

            return Response(TaskSerializer(task).data, status=201)

        return Response(serializer.errors, status=400)


class TaskListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        if user.role == 'admin':
            tasks = Task.objects.select_related(
                'assigned_to', 'created_by'
            ).filter(created_by=user)
        else:
            tasks = Task.objects.select_related(
                'assigned_to', 'created_by'
            ).filter(assigned_to=user)

        serializer = TaskSerializer(tasks, many=True)

        return Response(serializer.data)


class TaskUpdateView(APIView):
    permission_classes = [IsAuthenticated, IsTaskOwner]

    def patch(self, request, pk):
        try:
            task = Task.objects.get(id=pk)
        except Task.DoesNotExist:
            return Response({"error": "Task not found"}, status=404)

        self.check_object_permissions(request, task)

        updated_task = update_task_service(
            task,
            request.data,
            request.user
        )

        return Response(TaskSerializer(updated_task).data)


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):

    serializer_class = AuditLogSerializer

    def get_queryset(self):
        user = self.request.user

        if user.role == "admin":
            return AuditLog.objects.all()

        return AuditLog.objects.none()
