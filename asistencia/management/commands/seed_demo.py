from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from django.utils import timezone
from datetime import timedelta
from random import randint
from asistencia.models import Area, Empleado, Asistencia, Permiso
class Command(BaseCommand):
    help='Carga datos demostrativos: roles, 10 empleados, 50 asistencias y 10 permisos.'
    def handle(self,*args,**kwargs):
        areas=[Area.objects.get_or_create(nombre=n)[0] for n in ['Sistemas','Contabilidad','Ventas','Logística','RRHH']]
        roles={n:Group.objects.get_or_create(name=n)[0] for n in ['RRHH','Jefes','Contador']}
        jefeuser,_=User.objects.get_or_create(username='jefe.sistemas',defaults={'email':'jefe@tecnoandes.pe','first_name':'Jefe','last_name':'Sistemas'})
        jefeuser.set_password('TecnoAndes2026!'); jefeuser.save(); jefeuser.groups.add(roles['Jefes'])
        for idx in range(10):
            username='empleado%02d'%(idx+1); u,_=User.objects.get_or_create(username=username,defaults={'email':f'{username}@tecnoandes.pe','first_name':f'Persona{idx+1}','last_name':'Demo'})
            u.email=f'{username}@tecnoandes.pe'; u.set_password('Demo2026!'); u.save()
            area=areas[idx%len(areas)]
            Empleado.objects.get_or_create(user=u,defaults={'dni':f'{70000000+idx}','nombres':u.first_name,'apellidos':u.last_name,'cargo':'Analista','area':area,'fecha_ingreso':timezone.localdate()-timedelta(days=idx*120+200),'contrato':'planilla','jefe':idx==0})
        jefeemp=Empleado.objects.get(user=jefeuser) if hasattr(jefeuser,'empleado') else Empleado.objects.create(user=jefeuser,dni='79999999',nombres='Jefe',apellidos='Sistemas',cargo='Jefe de Área',area=areas[0],fecha_ingreso=timezone.localdate()-timedelta(days=900),contrato='planilla',jefe=True)
        for i in range(10):
            emp=Empleado.objects.order_by('id')[i]
            for j in range(5):
                day=timezone.localdate()-timedelta(days=i*5+j+1); start=timezone.make_aware(timezone.datetime.combine(day,timezone.datetime.min.time()).replace(hour=8,minute=randint(0,30)))
                Asistencia.objects.get_or_create(empleado=emp,entrada=start,defaults={'salida':start+timedelta(hours=8,minutes=randint(0,90)),'modificado_por':u})
            d=timezone.localdate()+timedelta(days=i*3+1)
            Permiso.objects.get_or_create(empleado=emp,fecha_inicio=d,defaults={'tipo':'personal','fecha_fin':d,'motivo':'Trámite personal previamente coordinado con el equipo de trabajo.'})
        self.stdout.write(self.style.SUCCESS('Demo listo. admin/admin (crear con createsuperuser), empleado01/Demo2026!, jefe.sistemas/TecnoAndes2026!'))
