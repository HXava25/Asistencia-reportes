from datetime import datetime
from unittest.mock import patch
from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.utils import timezone
from .admin import RRHHUserCreationForm
from .forms import EmpleadoForm
from .models import Area, Asistencia, Auditoria, Empleado


class EmployeeRegistrationTests(TestCase):
    def setUp(self):
        self.area=Area.objects.create(nombre="Sistemas")
        self.data={
            "username":"ana.sistemas",
            "password":"S3cure!VeryLongPassword",
            "email":"ana@tecnoandes.pe",
            "dni":"12345678",
            "nombres":"Ana",
            "apellidos":"Prueba",
            "cargo":"Analista",
            "area":self.area.pk,
            "fecha_ingreso":"2020-03-10",
            "contrato":"planilla",
        }

    def test_registration_requires_corporate_email_and_non_future_date(self):
        form=EmpleadoForm({**self.data,"email":"ana@gmail.com"})
        self.assertFalse(form.is_valid())
        self.assertIn("email",form.errors)
        form=EmpleadoForm({**self.data,"fecha_ingreso":"2999-01-01"})
        self.assertFalse(form.is_valid())
        self.assertIn("fecha_ingreso",form.errors)

    def test_registration_creates_user_and_employee_for_rrhh(self):
        hr=User.objects.create_user(username="rrhh",password="Strong!Password2026")
        hr.groups.add(Group.objects.get_or_create(name="RRHH")[0])
        self.client.force_login(hr)
        response=self.client.post("/empleados/nuevo/",self.data)
        self.assertEqual(response.status_code,302)
        employee=Empleado.objects.get(dni="12345678")
        self.assertEqual(employee.user.email,"ana@tecnoandes.pe")
        self.assertTrue(employee.user.check_password(self.data["password"]))

    def test_admin_user_creation_rejects_non_corporate_email(self):
        form=RRHHUserCreationForm({
            "username":"external",
            "email":"external@example.com",
            "first_name":"Demo",
            "last_name":"User",
            "password1":"S3cure!VeryLongPassword",
            "password2":"S3cure!VeryLongPassword",
            "groups":[],
        })
        self.assertFalse(form.is_valid())
        self.assertIn("email",form.errors)

    def test_employee_cannot_open_registration(self):
        user=User.objects.create_user(username="employee",password="Strong!Password2026")
        user.groups.add(Group.objects.get_or_create(name="Empleados")[0])
        self.client.force_login(user)
        self.assertEqual(self.client.get("/empleados/nuevo/").status_code,403)


class AttendanceAndPrivacyTests(TestCase):
    def setUp(self):
        area=Area.objects.create(nombre="Sistemas")
        self.user=User.objects.create_user(username="ana",password="Strong!Password2026",first_name="Ana",last_name="Privada",email="ana@tecnoandes.pe")
        self.employee=Empleado.objects.create(user=self.user,dni="87654321",nombres="Ana",apellidos="Privada",cargo="Analista",area=area,fecha_ingreso="2020-01-01",contrato="planilla")

    @patch("asistencia.middleware.timezone.localtime")
    def test_schedule_middleware_blocks_weekend_attendance(self,mock_localtime):
        mock_localtime.return_value=timezone.make_aware(datetime(2026,1,4,8,0))
        self.client.force_login(self.user)
        response=self.client.post("/asistencia/",{"accion":"entrada"})
        self.assertEqual(response.status_code,302)
        self.assertFalse(Asistencia.objects.exists())

    @patch("asistencia.views.timezone.localtime")
    @patch("asistencia.middleware.timezone.localtime")
    def test_valid_entry_is_timestamped_and_audited(self,middleware_clock,view_clock):
        ahora=timezone.make_aware(datetime(2026,11,25,8,0))
        middleware_clock.return_value=ahora
        view_clock.return_value=ahora
        self.client.force_login(self.user)
        response=self.client.post("/asistencia/",{"accion":"entrada"})
        self.assertEqual(response.status_code,302)
        self.assertEqual(Asistencia.objects.get().entrada,ahora)
        self.assertTrue(Auditoria.objects.filter(accion="Registro de entrada").exists())

    def test_manager_report_masks_personal_data(self):
        entrada=timezone.make_aware(datetime(2026,1,5,8,0))
        Asistencia.objects.create(empleado=self.employee,entrada=entrada,salida=entrada.replace(hour=17))
        manager=User.objects.create_user(username="manager",password="Strong!Password2026")
        Empleado.objects.create(user=manager,dni="11112222",nombres="Jefe",apellidos="Sistemas",cargo="Jefe",area=self.employee.area,fecha_ingreso="2019-01-01",contrato="planilla")
        manager.groups.add(Group.objects.get_or_create(name="Jefes")[0])
        self.client.force_login(manager)
        response=self.client.get("/reportes/")
        self.assertEqual(response.status_code,200)
        self.assertNotContains(response,"87654321")
        self.assertNotContains(response,"Ana Privada")

    def test_rrhh_group_can_enter_admin_without_staff_flag(self):
        hr=User.objects.create_user(username="rrhh-admin",password="Strong!Password2026")
        hr.groups.add(Group.objects.get_or_create(name="RRHH")[0])
        self.client.force_login(hr)
        self.assertEqual(self.client.get("/admin/").status_code,200)
        self.assertEqual(self.client.get("/admin/auth/user/add/").status_code,200)
