from django.contrib import admin
from core.models import (Evento, Empresa, Representante, Mesa, Interesse,
                         Rodada, EmpresaEvento, Configuracao)
from .forms import EmpresaForm


from django.contrib import admin


@admin.register(Configuracao)
class ConfiguracaoAdmin(admin.ModelAdmin):
    list_display = (
        #"senha_rodanegocios",
        "email_recuperacao",
        "identificador_usuario"
    )

    def has_add_permission(self, request):
        # Impede adicionar mais de 1 registro
        return not Configuracao.objects.exists()

    def has_delete_permission(self, request, obj=None):
        # Impede deletar o registro
        return False

@admin.register(Evento)
class EventoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'data', 'inicio_ev', 'termino_ev')
    search_fields = ('nome',)

@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    form: EmpresaForm
    list_display = ('nome', 'segmento')
    search_fields = ('nome', 'segmento')

@admin.register(EmpresaEvento)
class EmpresaEventoAdmin(admin.ModelAdmin):
    list_display = ('empresa', 'evento', 'participa')
    list_filter = ('evento', 'participa')
    
@admin.register(Representante)
class RepresentanteAdmin(admin.ModelAdmin):
    list_display = ('nome', 'empresa', 'email')
    search_fields = ('nome', 'empresa__nome', 'email')  

@admin.register(Rodada)
class RodadaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'evento', 'duracao', 'inicio_ro', 'fim_ro')
    search_fields = ('nome', 'evento__nome')

@admin.register(Mesa)
class MesaAdmin(admin.ModelAdmin):
    list_display = ('numero', 'rodada', 'comprador', 'vendedor')
    search_fields = ('numero',)

@admin.register(Interesse)
class InteresseAdmin(admin.ModelAdmin):
    list_display = ('nome',)
    search_fields = ('nome',)   

    
    