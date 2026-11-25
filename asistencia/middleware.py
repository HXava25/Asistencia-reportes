from datetime import time
from django.contrib import messages
from django.shortcuts import redirect
from django.utils.deprecation import MiddlewareMixin
from django.utils import timezone
from .models import Auditoria, Empleado
class AccountActiveMiddleware:
    def __init__(self,get_response): self.get_response=get_response
    def __call__(self,request):
        if request.user.is_authenticated and not request.user.is_active:
            from django.contrib.auth import logout
            logout(request); return redirect("login")
        return self.get_response(request)
class AttendanceReminderMiddleware:
    def __init__(self,get_response): self.get_response=get_response
    def __call__(self,request):
        if request.user.is_authenticated and not request.path.startswith(("/admin/","/login","/logout")):
            try:
                n=timezone.localtime(); e=request.user.empleado
                if n.weekday()<5 and not e.asistencias.filter(entrada__date=n.date()).exists(): request.session["recordatorio_asistencia"]="Recuerda marcar tu entrada de hoy."
            except Empleado.DoesNotExist:
                pass
        return self.get_response(request)
class AttendanceScheduleMiddleware(MiddlewareMixin):
    def process_view(self,request,view_func,view_args,view_kwargs):
        if request.method!="POST" or request.path!="/asistencia/":
            return None
        ahora=timezone.localtime()
        accion=request.POST.get("accion","entrada")
        if ahora.weekday()>4:
            messages.error(request,"La asistencia solo se puede marcar en días laborables.")
        elif accion=="entrada" and not time(6)<=ahora.time()<=time(10):
            messages.error(request,"La entrada se permite entre 06:00 y 10:00.")
        elif accion=="salida" and not time(15)<=ahora.time()<=time(19):
            messages.error(request,"La salida se permite entre 15:00 y 19:00.")
        else:
            return None
        return redirect("attendance")
class AuditMiddleware:
    def __init__(self,get_response): self.get_response=get_response
    def __call__(self,request):
        response=self.get_response(request)
        if request.method in ("POST","PUT","PATCH","DELETE") and request.user.is_authenticated and not request.path.startswith("/admin/login"): Auditoria.objects.create(usuario=request.user,accion=request.method,objeto=request.path,detalle=f"HTTP {response.status_code}")
        return response
