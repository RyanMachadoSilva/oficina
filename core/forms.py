from decimal import Decimal

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
        widgets = {"preco": forms.NumberInput(attrs={"step": "0.01", "min": "0", "max": "999999.99"})}

    def clean_preco(self):
        preco = self.cleaned_data["preco"]
        if preco is not None and (preco < 0 or preco > Decimal("999999.99")):
            raise forms.ValidationError("O preço deve ficar entre R$ 0,00 e R$ 999.999,99.")
        return preco
