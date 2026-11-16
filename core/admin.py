from django.contrib import admin

from .models import (Cliente, HistoricoStatus, ItemCatalogo, ItemPedido, Marca, Mecanico, Modelo, Parametros,
                     Pedido, Veiculo)


@admin.register(Parametros)
class ParametrosAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not Parametros.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


class ModeloInline(admin.TabularInline):
    model = Modelo
    extra = 1


@admin.register(Marca)
class MarcaAdmin(admin.ModelAdmin):
    search_fields = ["nome"]
    inlines = [ModeloInline]


@admin.register(Modelo)
class ModeloAdmin(admin.ModelAdmin):
    list_display = ["nome", "marca"]
    list_filter = ["marca"]
    search_fields = ["nome", "marca__nome"]


class VeiculoInline(admin.TabularInline):
    model = Veiculo
    extra = 0
    autocomplete_fields = ["modelo"]


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ["nome", "telefone", "documento"]
    search_fields = ["nome", "telefone", "documento", "veiculos__placa"]
    inlines = [VeiculoInline]


@admin.register(Mecanico)
class MecanicoAdmin(admin.ModelAdmin):
    list_display = ["nome", "telefone", "forma_pagamento", "ativo"]
    list_filter = ["ativo"]


@admin.register(ItemCatalogo)
class ItemCatalogoAdmin(admin.ModelAdmin):
    list_display = ["descricao", "tipo", "preco", "ativo"]
    list_filter = ["tipo", "ativo"]
    search_fields = ["descricao"]


class ItemPedidoInline(admin.TabularInline):
    model = ItemPedido
    extra = 0


class HistoricoInline(admin.TabularInline):
    model = HistoricoStatus
    extra = 0
    readonly_fields = ["status", "em", "usuario"]
    can_delete = False


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ["numero", "data", "cliente", "mecanico", "status"]
    list_filter = ["status", "mecanico"]
    search_fields = ["numero", "cliente__nome", "veiculo__placa"]
    date_hierarchy = "data"
    inlines = [ItemPedidoInline, HistoricoInline]
    raw_id_fields = ["cliente", "veiculo"]
