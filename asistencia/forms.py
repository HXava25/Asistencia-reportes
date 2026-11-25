from django import forms
from django.contrib.auth import get_user_model, password_validation
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Permiso, Asistencia, Empleado
class PermisoForm(forms.ModelForm):
    class Meta:
        model=Permiso; fields=["tipo","fecha_inicio","fecha_fin","motivo","documento"]
        widgets={"fecha_inicio":forms.DateInput(attrs={"type":"date"}),"fecha_fin":forms.DateInput(attrs={"type":"date"}),"motivo":forms.Textarea(attrs={"rows":4})}
    def __init__(self,*args,empleado=None,**kwargs): self.empleado=empleado; super().__init__(*args,**kwargs)
    def clean(self):
        d=super().clean(); i=d.get("fecha_inicio"); f=d.get("fecha_fin"); tipo=d.get("tipo"); motivo=d.get("motivo","")
        if len(motivo.strip())<30: self.add_error("motivo","El motivo debe tener al menos 30 caracteres.")
        if i and f and f<i: self.add_error("fecha_fin","La fecha final debe ser igual o posterior a la inicial.")
        if i and f and self.empleado:
            qs=Permiso.objects.filter(empleado=self.empleado,estado__in=["pendiente","aprobado"],fecha_inicio__lte=f,fecha_fin__gte=i)
            if self.instance.pk: qs=qs.exclude(pk=self.instance.pk)
            if qs.exists(): self.add_error(None,"Ya tienes un permiso superpuesto.")
            if tipo=="vacaciones" and (f-i).days+1>self.empleado.vacaciones_disponibles: self.add_error(None,"No tienes suficientes días de vacaciones disponibles.")
        return d
class CorreccionForm(forms.ModelForm):
    motivo_correccion=forms.ChoiceField(choices=[("error de sistema","Error de sistema"),("olvido","Olvido"),("otro","Otro")]); justificacion=forms.CharField(widget=forms.Textarea)
    class Meta: model=Asistencia; fields=["entrada","salida"]
    def clean_justificacion(self):
        v=self.cleaned_data["justificacion"].strip()
        if len(v)<50: raise forms.ValidationError("La justificación debe tener al menos 50 caracteres.")
        return v
class EmpleadoForm(forms.Form):
    username=forms.CharField(label="Usuario de acceso",max_length=150)
    password=forms.CharField(label="Contraseña inicial",widget=forms.PasswordInput)
    email=forms.EmailField(label="Email corporativo")
    dni=forms.CharField(label="DNI",max_length=8)
    nombres=forms.CharField(label="Nombres",max_length=100)
    apellidos=forms.CharField(label="Apellidos",max_length=100)
    cargo=forms.CharField(label="Cargo",max_length=100)
    area=forms.ModelChoiceField(label="Área",queryset=None)
    fecha_ingreso=forms.DateField(label="Fecha de ingreso",widget=forms.DateInput(attrs={"type":"date"}))
    contrato=forms.ChoiceField(label="Tipo de contrato",choices=Empleado.CONTRATOS)

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        from .models import Area
        self.fields["area"].queryset=Area.objects.filter(nombre__in=["Sistemas","Contabilidad","Ventas","Logística","RRHH"]).order_by("nombre")

    def clean_username(self):
        username=self.cleaned_data["username"].strip()
        if get_user_model().objects.filter(username__iexact=username).exists():
            raise ValidationError("Ya existe una cuenta con ese usuario.")
        return username

    def clean_email(self):
        email=self.cleaned_data["email"].strip().lower()
        if not email.endswith("@tecnoandes.pe"):
            raise ValidationError("Usa un correo corporativo con dominio @tecnoandes.pe.")
        if get_user_model().objects.filter(email__iexact=email).exists():
            raise ValidationError("Ya existe una cuenta con ese correo.")
        return email

    def clean_dni(self):
        dni=self.cleaned_data["dni"].strip()
        if not dni.isdigit() or len(dni)!=8:
            raise ValidationError("El DNI debe tener exactamente 8 dígitos.")
        if Empleado.objects.filter(dni=dni).exists():
            raise ValidationError("Ya existe un empleado con ese DNI.")
        return dni

    def clean_cargo(self):
        cargo=self.cleaned_data["cargo"].strip()
        if not cargo:
            raise ValidationError("El cargo es obligatorio.")
        return cargo

    def clean_fecha_ingreso(self):
        fecha=self.cleaned_data["fecha_ingreso"]
        if fecha>timezone.localdate():
            raise ValidationError("La fecha de ingreso no puede ser futura.")
        return fecha

    def clean_password(self):
        password=self.cleaned_data["password"]
        User=get_user_model()
        try:
            password_validation.validate_password(password,User(username=self.data.get("username","")))
        except ValidationError as error:
            raise ValidationError(error.messages)
        return password
