from django.contrib import admin, messages
from django.utils import timezone
from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from .models import Area, Empleado, Asistencia, Permiso, Auditoria
class RRHHAdminSite(admin.AdminSite):
    site_header="TecnoAndes · Administración RRHH"
    site_title="Administración RRHH"
    index_title="Operaciones de personas"
    def has_permission(self,request):
        user=request.user
        return user.is_active and (user.is_superuser or user.is_staff or user.groups.filter(name="RRHH").exists())
rrhh_admin_site=RRHHAdminSite(name="admin")
class RRHHAdminMixin:
    def has_module_permission(self,request): return request.user.is_superuser or request.user.groups.filter(name="RRHH").exists()
    def has_view_permission(self,request,obj=None): return self.has_module_permission(request)
    def has_add_permission(self,request): return self.has_module_permission(request)
    def has_change_permission(self,request,obj=None): return self.has_module_permission(request)
    def has_delete_permission(self,request,obj=None): return self.has_module_permission(request)
    def save_model(self,request,obj,form,change):
        action="Modificación" if change else "Creación"
        detail=", ".join(form.changed_data) if change else "Registro creado desde Django Admin."
        super().save_model(request,obj,form,change)
        Auditoria.objects.create(usuario=request.user,accion=f"{action} en Django Admin",objeto=f"{obj._meta.verbose_name} #{obj.pk}",detalle=detail)
    def delete_model(self,request,obj):
        objeto=f"{obj._meta.verbose_name} #{obj.pk}"
        obj.delete()
        Auditoria.objects.create(usuario=request.user,accion="Eliminación en Django Admin",objeto=objeto)
    def delete_queryset(self,request,queryset):
        objetos=[f"{obj._meta.verbose_name} #{obj.pk}" for obj in queryset]
        queryset.delete()
        for objeto in objetos:
            Auditoria.objects.create(usuario=request.user,accion="Eliminación en Django Admin",objeto=objeto)
class EmpleadoAdminForm(forms.ModelForm):
    class Meta:
        model=Empleado
        fields="__all__"
    def clean_cargo(self):
        cargo=self.cleaned_data["cargo"].strip()
        if not cargo: raise ValidationError("El cargo es obligatorio.")
        return cargo
    def clean_fecha_ingreso(self):
        fecha=self.cleaned_data["fecha_ingreso"]
        if fecha>timezone.localdate(): raise ValidationError("La fecha de ingreso no puede ser futura.")
        return fecha
    def clean(self):
        cleaned=super().clean()
        usuario=cleaned.get("user")
        if usuario and not usuario.email.lower().endswith("@tecnoandes.pe"):
            self.add_error("user","El usuario debe tener un correo @tecnoandes.pe.")
        if cleaned.get("area") and cleaned["area"].nombre not in ["Sistemas","Contabilidad","Ventas","Logística","RRHH"]:
            self.add_error("area","Selecciona un área válida de TecnoAndes.")
        return cleaned
class RRHHUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model=get_user_model()
        fields=("username","email","first_name","last_name","groups")
    def clean_email(self):
        email=self.cleaned_data["email"].strip().lower()
        if not email.endswith("@tecnoandes.pe"):
            raise ValidationError("El correo debe pertenecer al dominio @tecnoandes.pe.")
        if get_user_model().objects.filter(email__iexact=email).exists():
            raise ValidationError("Ya existe una cuenta con ese correo.")
        return email
class RRHHUserChangeForm(UserChangeForm):
    def clean_email(self):
        email=self.cleaned_data["email"].strip().lower()
        if not email.endswith("@tecnoandes.pe"):
            raise ValidationError("El correo debe pertenecer al dominio @tecnoandes.pe.")
        if get_user_model().objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise ValidationError("Ya existe una cuenta con ese correo.")
        return email
class RRHHUserAdmin(RRHHAdminMixin,DjangoUserAdmin):
    form=RRHHUserChangeForm
    add_form=RRHHUserCreationForm
    fieldsets=(
        ("Credenciales",{"fields":("username","password")}),
        ("Datos corporativos",{"fields":("first_name","last_name","email")}),
        ("Estado y roles",{"fields":("is_active","groups")}),
    )
    add_fieldsets=(
        (None,{"classes":("wide",),"fields":("username","email","first_name","last_name","password1","password2","groups")}),
    )
    list_display=("username","email","first_name","last_name","is_active")
    list_filter=("is_active","groups")
    search_fields=("username","email","first_name","last_name")
    filter_horizontal=("groups",)
    ordering=("username",)
    def get_queryset(self,request): return super().get_queryset(request).prefetch_related("groups")
rrhh_admin_site.register(get_user_model(),RRHHUserAdmin)
@admin.register(Area,site=rrhh_admin_site)
class AreaAdmin(RRHHAdminMixin,admin.ModelAdmin):
    search_fields=["nombre"]
    def has_add_permission(self,request): return False
    def has_change_permission(self,request,obj=None): return False
    def has_delete_permission(self,request,obj=None): return False
@admin.register(Empleado,site=rrhh_admin_site)
class EmpleadoAdmin(RRHHAdminMixin,admin.ModelAdmin):
    form=EmpleadoAdminForm
    list_display=["dni","nombres","apellidos","email_corporativo","cargo","area","contrato","antiguedad","vacaciones_disponibles","horas_extra_total"]; list_filter=["area","contrato"]; search_fields=["dni","nombres","apellidos","user__email"]
    def get_queryset(self,request): return super().get_queryset(request).select_related("user").prefetch_related("asistencias")
    def email_corporativo(self,obj): return obj.email_corporativo
    def antiguedad(self,obj): return obj.antiguedad
    def vacaciones_disponibles(self,obj): return obj.vacaciones_disponibles
    def horas_extra_total(self,obj): return round(sum(asistencia.horas_extra for asistencia in obj.asistencias.all()),2)
@admin.register(Asistencia,site=rrhh_admin_site)
class AsistenciaAdmin(RRHHAdminMixin,admin.ModelAdmin):
    list_display=["empleado","entrada","salida","horas","horas_extra"]; list_filter=["empleado__area","entrada"]; date_hierarchy="entrada"; search_fields=["empleado__nombres","empleado__dni"]
@admin.action(description="Aprobar permisos seleccionados")
def aprobar(modeladmin,request,queryset):
    pendientes=list(queryset.filter(estado="pendiente"))
    ahora=timezone.now()
    queryset.model.objects.filter(pk__in=[p.pk for p in pendientes]).update(estado="aprobado",decidido_por=request.user,decidido=ahora)
    for permiso in pendientes:
        Auditoria.objects.create(usuario=request.user,accion="Decisión de permiso",objeto=f"Permiso #{permiso.pk}",detalle=f"Estado: aprobado; empleado #{permiso.empleado_id}.")
    messages.success(request,f"{len(pendientes)} permisos aprobados.")
@admin.register(Permiso,site=rrhh_admin_site)
class PermisoAdmin(RRHHAdminMixin,admin.ModelAdmin):
    list_display=["empleado","tipo","fecha_inicio","fecha_fin","estado","dias"]; list_filter=["estado","tipo","empleado__area"]; search_fields=["empleado__nombres","empleado__dni"]; actions=[aprobar]
    def get_queryset(self,request):
        queryset=super().get_queryset(request)
        if "estado__exact" not in request.GET:
            queryset=queryset.filter(estado="pendiente")
        return queryset
@admin.register(Auditoria,site=rrhh_admin_site)
class AuditoriaAdmin(RRHHAdminMixin,admin.ModelAdmin):
    list_display=["timestamp","usuario","accion","objeto"]; list_filter=["accion","timestamp"]; readonly_fields=["usuario","accion","objeto","timestamp","detalle"]
