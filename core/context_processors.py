from django.conf import settings


def empresa(request):
    return {"EMPRESA_NOME": settings.EMPRESA_NOME}
