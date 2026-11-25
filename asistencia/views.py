from datetime import time, timedelta
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.contrib.auth import get_user_model
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from .models import Asistencia, Permiso, Area, Empleado
from .forms import PermisoForm, CorreccionForm, EmpleadoForm
from .models import Auditoria
def rrhh(u): return u.is_superuser or u.groups.filter(name="RRHH").exists()
def jefe(u): return u.groups.filter(name="Jefes").exists()
def perfil(u):
    try: return u.empleado
    except Empleado.DoesNotExist: return None
def auditar(usuario,accion,objeto,detalle=""):
    Auditoria.objects.create(usuario=usuario,accion=accion,objeto=str(objeto),detalle=detalle)
@login_required
def dashboard(request):
    e=perfil(request.user); c={"empleado":e,"recordatorio":request.session.pop("recordatorio_asistencia",None),"puede_gestionar_empleados":rrhh(request.user)}
    if e:
        c.update(asistencias=e.asistencias.all()[:5],permisos=e.permisos.all()[:5],
                 notificaciones=e.permisos.filter(estado__in=["aprobado","rechazado"],decidido__gte=timezone.now()-timedelta(days=7))[:5])
    if rrhh(request.user): c["pendientes"]=Permiso.objects.filter(estado="pendiente").count()
    return render(request,"asistencia/dashboard.html",c)
@login_required
def register_employee(request):
    if not rrhh(request.user): raise PermissionDenied
    form=EmpleadoForm(request.POST or None)
    if request.method=="POST" and form.is_valid():
        data=form.cleaned_data
        User=get_user_model()
        with transaction.atomic():
            user=User.objects.create_user(username=data["username"],email=data["email"],password=data["password"])
            employee=Empleado.objects.create(user=user,dni=data["dni"],nombres=data["nombres"],apellidos=data["apellidos"],cargo=data["cargo"],area=data["area"],fecha_ingreso=data["fecha_ingreso"],contrato=data["contrato"])
            auditar(request.user,"Alta de empleado",f"Empleado #{employee.pk}",f"Área: {employee.area}.")
        messages.success(request,"Empleado registrado.")
        return redirect("register_employee")
    return render(request,"asistencia/employee_form.html",{"form":form})
@login_required
def attendance(request):
    e=perfil(request.user)
    if not e: raise PermissionDenied
    reg=e.asistencias.filter(entrada__date=timezone.localdate()).first()
    if request.method=="POST" and request.POST.get("accion","entrada")=="entrada":
        n=timezone.localtime()
        if n.weekday()>4 or not time(6)<=n.time()<=time(10): messages.error(request,"La entrada se permite en días laborables entre 06:00 y 10:00 (dos horas antes o después del horario de 08:00).")
        elif reg and not reg.salida: messages.error(request,"Ya tienes una entrada pendiente de salida.")
        else:
            registro=Asistencia.objects.create(empleado=e,entrada=n,modificado_por=request.user)
            auditar(request.user,"Registro de entrada",f"Asistencia #{registro.pk}",f"Empleado #{e.pk}; hora: {n.isoformat()}.")
            messages.success(request,"Entrada registrada.")
        return redirect("attendance")
    if request.method=="POST" and request.POST.get("accion")=="salida" and reg and not reg.salida:
        n=timezone.localtime()
        if n<=reg.entrada: messages.error(request,"La salida debe ser posterior a la entrada.")
        elif n.weekday()>4 or not time(15)<=n.time()<=time(19): messages.error(request,"La salida se permite en días laborables entre 15:00 y 19:00.")
        else:
            reg.salida=n; reg.modificado_por=request.user; reg.save()
            auditar(request.user,"Registro de salida",f"Asistencia #{reg.pk}",f"Empleado #{e.pk}; hora: {n.isoformat()}.")
            messages.success(request,"Salida registrada.")
        return redirect("attendance")
    return render(request,"asistencia/attendance.html",{"registro":reg})
@login_required
def correct_attendance(request,pk):
    if not rrhh(request.user): raise PermissionDenied
    a=get_object_or_404(Asistencia,pk=pk); f=CorreccionForm(request.POST or None,instance=a)
    if request.method=="POST" and f.is_valid():
        if f.cleaned_data.get("salida") and f.cleaned_data["salida"]<=f.cleaned_data["entrada"]: f.add_error("salida","La salida debe ser posterior a la entrada.")
        else:
            f.save(); a.modificado_por=request.user; a.save(update_fields=["modificado_por"])
            auditar(request.user,"Corrección de asistencia",f"Asistencia #{a.pk}",f"Motivo: {f.cleaned_data['motivo_correccion']}. {f.cleaned_data['justificacion']}")
            messages.success(request,"Asistencia corregida y registrada en auditoría."); return redirect("reports")
    return render(request,"asistencia/correction.html",{"form":f,"registro":a})
@login_required
def request_leave(request):
    e=perfil(request.user)
    if not e: raise PermissionDenied
    f=PermisoForm(request.POST or None,empleado=e)
    if request.method=="POST" and f.is_valid():
        p=f.save(commit=False); p.empleado=e; p.save()
        auditar(request.user,"Solicitud de permiso",f"Permiso #{p.pk}",f"Empleado #{e.pk}; tipo: {p.tipo}; fechas: {p.fecha_inicio} a {p.fecha_fin}.")
        messages.success(request,"Solicitud enviada.")
        return redirect("leave_list")
    return render(request,"asistencia/leave_form.html",{"form":f,"dias":e.vacaciones_disponibles})
@login_required
def leave_list(request):
    e=perfil(request.user)
    if rrhh(request.user): qs=Permiso.objects.all()
    elif jefe(request.user) and e: qs=Permiso.objects.filter(empleado__area=e.area)
    elif e: qs=Permiso.objects.filter(empleado=e)
    else: qs=Permiso.objects.none()
    return render(request,"asistencia/leave_list.html",{"permisos":qs,"puede_aprobar":rrhh(request.user) or jefe(request.user),"puede_ver_personales":rrhh(request.user)})
@login_required
def leave_decision(request,pk):
    p=get_object_or_404(Permiso,pk=pk,estado="pendiente"); e=perfil(request.user)
    if not rrhh(request.user) and not (jefe(request.user) and e and e.area_id==p.empleado.area_id): raise PermissionDenied
    if request.method=="POST":
        decision=request.POST.get("decision")
        if decision not in ("aprobar","rechazar"):
            messages.error(request,"La decisión indicada no es válida.")
            return redirect("leave_list")
        p.estado="aprobado" if decision=="aprobar" else "rechazado"; p.decidido_por=request.user; p.decidido=timezone.now(); p.save()
        auditar(request.user,"Decisión de permiso",f"Permiso #{p.pk}",f"Estado: {p.estado}; empleado #{p.empleado_id}.")
        messages.success(request,"Solicitud actualizada.")
    return redirect("leave_list")
@login_required
def reports(request):
    if not (rrhh(request.user) or request.user.groups.filter(name="Contador").exists() or jefe(request.user)): raise PermissionDenied
    qs=Asistencia.objects.select_related("empleado","empleado__area"); e=perfil(request.user)
    if jefe(request.user) and not rrhh(request.user):
        if not e: raise PermissionDenied
        qs=qs.filter(empleado__area=e.area)
    if request.GET.get("fecha"): qs=qs.filter(entrada__date=request.GET["fecha"])
    if request.GET.get("area"): qs=qs.filter(empleado__area_id=request.GET["area"])
    datos=list(qs)
    if rrhh(request.user):
        out="\n".join(f"{x.empleado.dni},{x.empleado},{x.entrada},{x.salida or ''},{x.horas},{x.horas_extra}" for x in datos)
    else:
        out="\n".join(f"Empleado #{x.empleado_id},{x.entrada},{x.salida or ''},{x.horas},{x.horas_extra}" for x in datos)
    extras={}
    for registro in datos:
        clave=(registro.empleado_id,str(registro.empleado) if rrhh(request.user) else f"Colaborador #{registro.empleado_id}")
        extras[clave]=extras.get(clave,0)+registro.horas_extra
    return render(request,"asistencia/reports.html",{"registros":datos,"areas":Area.objects.all() if not jefe(request.user) or rrhh(request.user) else Area.objects.filter(pk=e.area_id),"export":out,"puede_corregir":rrhh(request.user),"puede_ver_personales":rrhh(request.user),"horas_extra_por_empleado":[{"empleado":nombre,"horas":round(horas,2)} for (_,nombre),horas in extras.items()]})
