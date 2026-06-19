from django.urls import path
from .views import (
    AgendaCompradorAPI,
    AgendaVendedorAPI,
    EmpresaListAPI,
    EventoListAPI,
    AgendaEmpresaEventoAPI,
    RodadaListAPI,
    MesaListAPI,
    AgendaCompradorEventoAPI,
)
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
 

app_name = 'api'

urlpatterns = [
    path('agenda/comprador/<int:empresa_id>/<int:evento_id>/', AgendaCompradorAPI.as_view()),
    path('agenda/vendedor/<int:empresa_id>/<int:evento_id>/', AgendaVendedorAPI.as_view()),
    path('agenda/evento/<int:evento_id>/empresa/<int:empresa_id>/', AgendaEmpresaEventoAPI.as_view()),
    path('agenda/comprador/evento/<int:evento_id>/<int:comprador_id>/', AgendaCompradorEventoAPI.as_view()),
    
    # Listagens gerais
    path('empresas/', EmpresaListAPI.as_view()),
    path('eventos/', EventoListAPI.as_view()),
    path('rodadas/', RodadaListAPI.as_view()),
    path('mesas/', MesaListAPI.as_view()),
    
    # Autenticação JWT
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]

