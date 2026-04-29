from django import forms
from .models import (Rodada, Representante, Empresa, Interesse, Categoria, Endereco)
import re

from django import forms
from .models import Empresa, ConfiguracaoSistema, RelacionamentoEmpresa, SolicitacaoAcesso


# Formulário para configurar a senha do Rodanegocios
class ConfiguracaoSistemaForm(forms.ModelForm):
    valor = forms.CharField(
        label="Senha",
        widget=forms.PasswordInput(render_value=True)
    )

    class Meta:
        model = ConfiguracaoSistema
        fields = ["valor"]


class SolicitacaoAcessoForm(forms.ModelForm):
    class Meta:
        model = SolicitacaoAcesso
        fields = ["justificativa"]

class EmpresaForm(forms.ModelForm):
    class Meta:
        model = Empresa
        fields = "__all__"
        widgets = {
            "interesses": forms.CheckboxSelectMultiple(),  # ou forms.SelectMultiple()
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Adiciona classes Bootstrap automaticamente
        for field_name, field in self.fields.items():
            if field.widget.__class__.__name__ not in ["CheckboxSelectMultiple"]:
                field.widget.attrs.update({"class": "form-control"})

    def clean_site(self):
        site = self.cleaned_data.get("site")
        if site and not site.startswith(("http://", "https://")):
            site = "https://" + site
        return site

class EnderecoForm(forms.ModelForm):
    class Meta:
        model = Endereco
        fields = ["rua", "numero", "complemento", "bairro", "cidade", "estado", "cep", "pais"]
        widgets = {
            "rua": forms.TextInput(attrs={"class": "form-control"}),
            "numero": forms.TextInput(attrs={"class": "form-control"}),
            "complemento": forms.TextInput(attrs={"class": "form-control"}),
            "bairro": forms.TextInput(attrs={"class": "form-control"}),
            "cidade": forms.TextInput(attrs={"class": "form-control"}),
            "estado": forms.TextInput(attrs={"class": "form-control"}),
            "cep": forms.TextInput(attrs={"class": "form-control"}),
            "pais": forms.TextInput(attrs={"class": "form-control"}),
        }
 
class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ["nome", "descricao", "ordem"]
        widgets = {
            "nome": forms.TextInput(attrs={"class": "form-control"}),
            "descricao": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "ordem": forms.NumberInput(attrs={"class": "form-control"}),
        }
class InteresseForm(forms.ModelForm):
    class Meta:
        model = Interesse
        fields = ["categoria", "nome"]
        widgets = {
            "categoria": forms.Select(attrs={"class": "form-select"}),
            "nome": forms.TextInput(attrs={"class": "form-control"}),
        }
    
    
class RodadaForm(forms.ModelForm):
    data = forms.DateField(
        input_formats=["%Y-%m-%d"], 
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}), 
        localize=False)

    class Meta:
        model = Rodada
        fields = ["nome", "data", "duracao"]
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Se a data veio do expediente, deixa readonly
        if self.initial.get("data"):
            self.fields["data"].widget.attrs["readonly"] = True


class RepresentanteForm(forms.ModelForm):
    class Meta:
        model = Representante
        fields = ["nome", "cargo", "email", "telefone"]
        
    def clean_email(self):
        email = self.cleaned_data.get('email')

        if email and not forms.EmailField().clean(email):
            raise forms.ValidationError("Informe um e-mail válido.")

        return email

    def clean_telefone(self):
        telefone = self.cleaned_data.get('telefone')

        # Aceita formatos como:
        # 999999999
        # (99) 9999-9999
        # (99) 99999-9999
        # 99 99999-9999
        padrao = r'^\(?\d{2}\)?[\s-]?\d{4,5}-?\d{4}$'

        if telefone and not re.match(padrao, telefone):
            raise forms.ValidationError("Informe um telefone válido. Ex: (11) 98765-4321")

        return telefone

from django import forms
from .models import RelacionamentoEmpresa, Empresa

class RelacionamentoForm(forms.ModelForm):
 
    class Meta:
        model = RelacionamentoEmpresa
        fields = ["empresa_b", "tipo_relacao",]

    def __init__(self, *args, **kwargs):
        empresa_atual = kwargs.pop("empresa_atual", None)
        super().__init__(*args, **kwargs)

        # 🔥 Filtrar apenas vendedores
        qs = Empresa.objects.filter(modalidade="VENDEDOR").order_by("nome")

        # Excluir a própria empresa
        if empresa_atual:
            qs = qs.exclude(id=empresa_atual.id)

        # Aplicar o queryset filtrado
        self.fields["empresa_b"].queryset = qs
        
        # 🔥 Mostrar nome + modalidade no select
        self.fields["empresa_b"].label_from_instance = (
        lambda obj: f"{obj.nome} — {obj.modalidade}"
    )
        
    # Garantir que empresa_a seja COMPRADOR e empresa_b seja VENDEDOR
    def clean(self):
        cleaned_data = super().clean()
        empresa_b = cleaned_data.get("empresa_b")

        # Validar apenas empresa_b aqui
        if empresa_b and empresa_b.modalidade != "VENDEDOR":
            raise forms.ValidationError("A empresa B deve ser VENDEDOR.")

        return cleaned_data

        
