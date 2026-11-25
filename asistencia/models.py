from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone
class Area(models.Model):
    nombre=models.CharField(max_length=80,unique=True)
    def __str__(self): return self.nombre
class Empleado(models.Model):
    CONTRATOS=[("planilla","Planilla"),("locacion","Locación")]
    user=models.OneToOneField(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="empleado")
    dni=models.CharField(max_length=8,unique=True,validators=[RegexValidator(r"^\d{8}$","DNI debe tener 8 dígitos")])
    nombres=models.CharField(max_length=100); apellidos=models.CharField(max_length=100); cargo=models.CharField(max_length=100)
    area=models.ForeignKey(Area,on_delete=models.PROTECT,related_name="empleados"); fecha_ingreso=models.DateField(); contrato=models.CharField(max_length=12,choices=CONTRATOS); jefe=models.BooleanField(default=False); salario=models.DecimalField(max_digits=10,decimal_places=2,default=0)
    def __str__(self): return f"{self.nombres} {self.apellidos}"
    @property
    def antiguedad(self):
        hoy=timezone.localdate(); m=(hoy.year-self.fecha_ingreso.year)*12+hoy.month-self.fecha_ingreso.month
        if hoy.day<self.fecha_ingreso.day: m-=1
        return f"{max(0,m)//12} años, {max(0,m)%12} meses"
    @property
    def email_corporativo(self): return self.user.email
    @property
    def vacaciones_disponibles(self): return max(0,30-sum(p.dias for p in self.permisos.filter(tipo="vacaciones",estado="aprobado")))
class Asistencia(models.Model):
    empleado=models.ForeignKey(Empleado,on_delete=models.CASCADE,related_name="asistencias"); entrada=models.DateTimeField(); salida=models.DateTimeField(null=True,blank=True); modificado_por=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,blank=True,on_delete=models.SET_NULL)
    @property
    def horas(self): return round(max(0,(self.salida-self.entrada).total_seconds()/3600),2) if self.salida else 0
    @property
    def horas_extra(self): return round(max(0,self.horas-8),2)
    class Meta: ordering=["-entrada"]
class Permiso(models.Model):
    TIPOS=[(x,x.capitalize()) for x in ["personal","medico","duelo","maternidad/paternidad","otro","vacaciones"]]; ESTADOS=[("pendiente","Pendiente"),("aprobado","Aprobado"),("rechazado","Rechazado")]
    empleado=models.ForeignKey(Empleado,on_delete=models.CASCADE,related_name="permisos"); tipo=models.CharField(max_length=30,choices=TIPOS); fecha_inicio=models.DateField(); fecha_fin=models.DateField(); motivo=models.TextField(); documento=models.CharField(max_length=250,blank=True); estado=models.CharField(max_length=12,choices=ESTADOS,default="pendiente"); solicitado=models.DateTimeField(auto_now_add=True); decidido_por=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,blank=True,on_delete=models.SET_NULL,related_name="permisos_decididos"); decidido=models.DateTimeField(null=True,blank=True)
    @property
    def dias(self): return (self.fecha_fin-self.fecha_inicio).days+1
    class Meta: ordering=["-solicitado"]
class Auditoria(models.Model):
    usuario=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,on_delete=models.SET_NULL); accion=models.CharField(max_length=100); objeto=models.CharField(max_length=120); timestamp=models.DateTimeField(default=timezone.now); detalle=models.TextField(blank=True)
    class Meta: ordering=["-timestamp"]
