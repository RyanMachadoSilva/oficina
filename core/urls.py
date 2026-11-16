from django.urls import path

from . import views

urlpatterns = [
    path("", views.inicio, name="inicio"),
    # pedidos
    path("pedidos/", views.pedidos, name="pedidos"),
    path("pedidos/novo/", views.pedido_form, name="pedido_novo"),
    path("pedidos/<int:pk>/", views.pedido_detalhe, name="pedido_detalhe"),
    path("pedidos/<int:pk>/editar/", views.pedido_form, name="pedido_editar"),
    path("pedidos/<int:pk>/duplicar/", views.pedido_duplicar, name="pedido_duplicar"),
    path("pedidos/<int:pk>/status/", views.pedido_status, name="pedido_status"),
    path("pedidos/<int:pk>/excluir/", views.pedido_excluir, name="pedido_excluir"),
    # clientes
    path("clientes/", views.clientes, name="clientes"),
    path("clientes/novo/", views.cliente_form, name="cliente_novo"),
    path("clientes/<int:pk>/", views.cliente_form, name="cliente_editar"),
    path("clientes/<int:pk>/excluir/", views.cliente_excluir, name="cliente_excluir"),
    path("veiculos/<int:pk>/excluir/", views.veiculo_excluir, name="veiculo_excluir"),
    # mecânicos e catálogo
    path("mecanicos/", views.mecanicos, name="mecanicos"),
    path("mecanicos/novo/", views.mecanico_form, name="mecanico_novo"),
    path("mecanicos/<int:pk>/", views.mecanico_form, name="mecanico_editar"),
    path("pecas-servicos/", views.catalogo, name="catalogo"),
    path("pecas-servicos/novo/", views.catalogo_form, name="catalogo_novo"),
    path("pecas-servicos/<int:pk>/", views.catalogo_form, name="catalogo_editar"),
    # relatórios
    path("relatorios/", views.relatorios, name="relatorios"),
    path("relatorios/excel/", views.relatorios_csv, name="relatorios_csv"),
    # API usada pelas buscas
    path("api/clientes/", views.api_clientes, name="api_clientes"),
    path("api/clientes/novo/", views.api_cliente_criar, name="api_cliente_criar"),
    path("api/clientes/<int:cliente_id>/veiculos/", views.api_veiculo_criar, name="api_veiculo_criar"),
    path("api/modelos/", views.api_modelos, name="api_modelos"),
    path("api/catalogo/", views.api_catalogo, name="api_catalogo"),
    # PWA
    path("manifest.webmanifest", views.manifest, name="manifest"),
    path("sw.js", views.service_worker, name="sw"),
]
