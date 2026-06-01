from django.urls import path
from .views import AgendaCompradorAPI, AgendaVendedorAPI

app_name = 'api'

urlpatterns = [
    path('agenda/comprador/<int:empresa_id>/<int:evento_id>/', AgendaCompradorAPI.as_view()),
    path('agenda/vendedor/<int:empresa_id>/<int:evento_id>/', AgendaVendedorAPI.as_view()),
]
