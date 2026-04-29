from django.contrib import admin
from .models import Evento, Empresa, Representante, Mesa, Interesse, Rodada, EmpresaEvento
from .forms import EmpresaForm, ConfiguracaoSistemaForm


from django.contrib import admin
from .models import ConfiguracaoSistema

# Configuração do admin para a senha do Rodanegocios
@admin.register(ConfiguracaoSistema)
class ConfiguracaoSistemaAdmin(admin.ModelAdmin):
    form = ConfiguracaoSistemaForm
    list_display = ("chave",)
    search_fields = ("chave",)

    # Impede exclusão acidental
    def has_delete_permission(self, request, obj=None):
        return False

    # Impede criação de novas chaves (mantém só 1 senha)
    def has_add_permission(self, request):
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

    
    