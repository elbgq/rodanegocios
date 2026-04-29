from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Home
    path('', views.HomeView.as_view(), name="home"),
    
    # EMPRESAS
    path('empresas/', views.EmpresaListView.as_view(), name='empresa_list'),
    path('empresas/nova/', views.EmpresaCreateView.as_view(), name='empresa_create'),
    path('empresas/<int:pk>/', views.EmpresaDetailView.as_view(), name='empresa_detail'),
    path('empresas/<int:pk>/editar/', views.EmpresaUpdateView.as_view(), name='empresa_update'),
    path("empresa/<int:pk>/excluir/", views.empresa_excluir, name="empresa_excluir"),
    path("empresa/<int:pk>/perfil/", views.empresa_perfil, name="empresa_perfil"),
    path("empresas/importar/", views.empresa_importar, name="empresa_importar"),
    
    # RELACIONAMENTOS ENTRE EMPRESAS
    path("<int:empresa_id>/relacionamentos/", views.empresa_relacionamentos, name="empresa_relacionamentos"),
    path("<int:empresa_id>/relacionamentos/adicionar/", views.adicionar_relacionamento, name="empresa_adicionar_relacionamento"),
    path("<int:empresa_id>/relacionamentos/remover/<int:rel_id>/", views.remover_relacionamento, name="remover_relacionamento"),
    path("relatorios/empresas-relacionadas/", views.relatorio_empresas_relacionadas, name="relatorio_empresas_relacionadas"),
    
    # CATEGORIAS
    path("categorias/", views.categoria_list, name="categoria_list"),
    path("categorias/nova/", views.categoria_create, name="categoria_create"),
    path("categorias/<int:pk>/editar/", views.categoria_update, name="categoria_update"),
    path("categorias/<int:pk>/excluir/", views.categoria_delete, name="categoria_delete"),
    
    # INTERESSES
    path("interesses/", views.InteresseListView.as_view(), name="interesse_list"),
    path("interesses/novo/", views.InteresseCreateView.as_view(), name="interesse_create"),
    path("interesses/<int:pk>/editar/", views.InteresseUpdateView.as_view(), name="interesse_update"),
    path("interesses/<int:pk>/excluir/", views.InteresseDeleteView.as_view(), name="interesse_delete"),
    
    # REPRESENTANTES
    path("empresas/<int:empresa_id>/representantes/novo/",views.RepresentanteCreateView.as_view(),
    name="representante_novo"),
    path("representantes/<int:pk>/editar/",views.RepresentanteUpdateView.as_view(),
    name="representante_editar"),
    path("representantes/<int:pk>/excluir/", views.RepresentanteDeleteView.as_view(),
    name="representante_excluir"),
    path("representantes/importar/<int:empresa_id>/", views.representante_importar, name="representante_importar"),
    
    # EVENTOS
    path('eventos/', views.EventoListView.as_view(), name='evento_list'),
    path('eventos/novo/', views.EventoCreateView.as_view(), name='evento_create'),
    path('eventos/<int:pk>/', views.EventoDetailView.as_view(), name='evento_detail'),
    path('eventos/<int:pk>/editar/', views.EventoUpdateView.as_view(), name='evento_update'),
    path('eventos/<int:pk>/excluir/', views.EventoDeleteView.as_view(), name='evento_confirm_delete'),
    path("evento/<int:evento_id>/participantes/", views.evento_participantes, name="evento_participantes"),
    path("evento/<int:evento_id>/relatorio-inscritos/", views.relatorio_inscritos, name="evento_relatorio_inscritos"),
    path("evento/<int:evento_id>/relatorio-rodadas/", views.rodadas_relatorio, name="rodadas_relatorio"),
    path("evento/<int:evento_id>/ranking-afinidades/", views.ranking_afinidades, name="ranking_afinidades"),
    path("evento/<int:evento_id>/rodadas-confirmar-ranking/", views.rodadas_confirmar_ranking,
    name="rodadas_confirmar_ranking"),
      
    # RODADAS
    path("evento/<int:evento_id>/rodadas/gerar/", views.rodadas_gerar, name="rodadas_gerar"),
    path('evento/<int:evento_id>/rodadas/', views.rodadas_do_evento, name='rodadas_list'),
    path('rodada/<int:rodada_id>/editar/', views.rodadas_editar, name='rodadas_editar'),
    path('rodada/<int:rodada_id>/excluir/', views.rodadas_excluir, name='rodadas_excluir'),
    path("evento/<int:evento_id>/rodadas/debug/", views.rodadas_debug_report, name="rodadas_debug_report"),
    path("evento/<int:evento_id>/rodadas/log/", views.rodadas_log, name="rodadas_log"),

    # MESAS
    path('rodada/<int:rodada_id>/mesas/', views.mesas_da_rodada, name='mesas_da_rodada'),
    path("mesas/<int:pk>/relatorio/", views.mesa_relatorio, name="mesa_relatorio"),
     
    # PAINEL
    path('rodada/<int:rodada_id>/painel/', views.painel_da_rodada, name='painel_rodada'),
    
    # ACESSO
    path("configuracoes/", views.configuracao_sistema_view, name="configuracao_sistema"),
    path("acesso/", views.acesso_rodanegocios, name="acesso_rodanegocios"),
    path("sair/", views.sair, name="sair"),
    path("reset-senha/", views.reset_senha_rodanegocios, name="reset_senha"),
    
    # AGENDAS
    path("evento/<int:evento_id>/empresa/<int:empresa_id>/agenda-comprador/",
        views.agenda_comprador, name="agenda_comprador"),
    path("evento/<int:evento_id>/empresa/<int:empresa_id>/agenda-vendedor/",
        views.agenda_vendedor, name="agenda_vendedor"),
    path("evento/<int:evento_id>/agendas/", views.agendas_empresas_evento,
        name="agendas_empresas_evento"),
]