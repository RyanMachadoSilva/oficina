from django import forms

from .models import Cliente, ItemCatalogo, Mecanico


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ["nome", "telefone", "documento", "email", "endereco", "observacao"]
        widgets = {"observacao": forms.Textarea(attrs={"rows": 2})}


class MecanicoForm(forms.ModelForm):
    class Meta:
        model = Mecanico
        fields = ["nome", "telefone", "forma_pagamento", "ativo"]


class ItemCatalogoForm(forms.ModelForm):
    class Meta:
        model = ItemCatalogo
        fields = ["descricao", "tipo", "preco", "ativo"]
        widgets = {"preco": forms.NumberInput(attrs={"step": "0.01", "min": "0"})}
