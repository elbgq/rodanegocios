from django.urls import path
from .views import (
    AgendaCompradorAPI,
    AgendaVendedorAPI,
    EmpresaListAPI,
    EventoListAPI,
    RodadaListAPI,
    MesaListAPI
)

app_name = 'api'

urlpatterns = [
    path('agenda/comprador/<int:empresa_id>/<int:evento_id>/', AgendaCompradorAPI.as_view()),
    path('agenda/vendedor/<int:empresa_id>/<int:evento_id>/', AgendaVendedorAPI.as_view()),
    
    # Listagens gerais
    path('empresas/', EmpresaListAPI.as_view()),
    path('eventos/', EventoListAPI.as_view()),
    path('rodadas/', RodadaListAPI.as_view()),
    path('mesas/', MesaListAPI.as_view()),
]
