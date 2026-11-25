def roles_portal(request):
    user=request.user
    puede_ver_reportes=user.is_authenticated and (user.is_superuser or user.groups.filter(name__in=["RRHH","Jefes","Contador"]).exists())
    return {"puede_ver_reportes":puede_ver_reportes}
