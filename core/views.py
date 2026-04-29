from django.shortcuts import render, redirect, get_object_or_404

from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, TemplateView, DeleteView
)
from django.urls import reverse_lazy
from .models import (Empresa, Evento, Rodada, Representante, Mesa, SolicitacaoAcesso,
                     Interesse, Categoria, EmpresaEvento, Endereco, RelacionamentoEmpresa)
from .forms import (RepresentanteForm, EmpresaForm, CategoriaForm, RelacionamentoForm,
                    InteresseForm, EnderecoForm, SolicitacaoAcessoForm)
from django.views.generic import TemplateView, CreateView, UpdateView, DeleteView
from django.core.exceptions import ValidationError
from datetime import datetime, timedelta, time, date
from django.views import View
from django.contrib import messages
from django.core.paginator import Paginator
from core.services.matchmaking import gerar_todas_as_rodadas
from django.contrib.messages import get_messages
import csv
import re
import math
import random
from django.contrib import messages
from django.db import IntegrityError
from core.services.matchmaking import calcular_afinidade
from core.utils import cor_para_vendedor
from django.contrib.auth.models import Permission
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.contrib.admin.views.decorators import staff_member_required
from django.conf import settings
from django.contrib.auth import logout
from .utils import get_senha_rodanegocios, set_senha_rodanegocios, empresas_tem_relacao
from django.db.models import Q
from collections import defaultdict


# -----------------------------
# Home
# -----------------------------
class HomeView(TemplateView):
    template_name = 'core/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Lista de eventos para exibir os cards
        context['evento'] = Evento.objects.all().order_by('data')
        
        # Pegamos todas as rodadas
        # context['rodadas'] = Rodada.objects.all().order_by('evento__data', 'inicio_ro')
        return context

# -----------------------------
# ACESSO
# -----------------------------
# Configurações do sistema (ex: senha do Rodanegocios)
def configuracao_sistema_view(request):

    contexto = {}

    if request.method == "POST":
        senha_atual = request.POST.get("senha_atual", "").strip()
        nova_senha = request.POST.get("nova_senha", "").strip()
        confirmar = request.POST.get("confirmar", "").strip()

        if senha_atual != get_senha_rodanegocios():
            contexto["erro"] = "Senha atual incorreta."
        elif nova_senha != confirmar:
            contexto["erro"] = "A nova senha e a confirmação não coincidem."
        else:
            set_senha_rodanegocios(nova_senha)
            contexto["sucesso"] = "Senha alterada com sucesso!"

    return render(request, "core/configuracao_sistema.html", contexto)


SENHA_RODANEGOCIOS = "rodanegocios123"  # você define a senha aqui

def acesso_rodanegocios(request):
    
    # Sempre limpa o acesso ao abrir a página de senha
    request.session.pop("acesso_rodanegocios", None)
    
    if request.method == "POST":
        senha_digitada = (request.POST.get("senha") or "").strip()
        senha_correta = get_senha_rodanegocios()
        
        if senha_digitada == senha_correta:
            request.session["acesso_rodanegocios"] = True
            return redirect("core:home")  # ajuste para sua URL inicial

        return render(request, "core/digite_senha.html", {
            "erro": "Senha incorreta."
        })

    return render(request, "core/digite_senha.html")

# Função para sair (limpa a sessão de acesso)
def sair(request):
    # Remove o acesso especial
    request.session.pop("acesso_rodanegocios", None)

    # Faz logout do Django (caso esteja logado)
    logout(request)

    # Redireciona para a tela de senha
    return redirect("/acesso/")

# Função para resetar a senha do Rodanegocios
def reset_senha_rodanegocios(request):
    modo = request.GET.get("modo")  # pode ser "esqueci"
    contexto = {"modo": modo}
    
    if request.method == "POST":
        senha_atual = request.POST.get("senha_atual", "").strip()
        nova_senha = request.POST.get("nova_senha", "").strip()
        confirmar = request.POST.get("confirmar", "").strip()

        senha_correta = get_senha_rodanegocios()
        
        # 1. Se veio do "esqueci a senha", não exige senha atual
        if modo != "esqueci" and senha_atual != senha_correta:
            contexto["erro"] = "Senha atual incorreta."
            return render(request, "core/reset_senha.html", contexto)

        # 2. Confere nova senha
        if nova_senha != confirmar:
            contexto["erro"] = "A nova senha e a confirmação não coincidem."
            return render(request, "core/reset_senha.html", contexto)

        # 3. Grava a nova senha
        set_senha_rodanegocios(nova_senha)
        contexto["sucesso"] = "Senha alterada com sucesso!"
        return render(request, "core/reset_senha.html", contexto)

    return render(request, "core/reset_senha.html", contexto)

# -----------------------------
# EMPRESA 
# -----------------------------
class EmpresaListView(ListView):
    model = Empresa
    form_class = EmpresaForm
    template_name = 'core/empresa_list.html'
    context_object_name = 'empresas'
    paginate_by = 15  # Exibe 20 por página
    ordering = None  # Sem ordenação fixa

    def get_queryset(self):
        qs = super().get_queryset()
        termo = self.request.GET.get("q", "").strip()

        if termo:
            qs = qs.filter(nome__icontains=termo)

        # 🔽 Ordenação
        sort = self.request.GET.get("sort", "nome")

        allowed = {
            "nome": "nome",
            "-nome": "-nome",
            "modalidade": "modalidade",
            "-modalidade": "-modalidade",
            "interesses": "interesses__nome",
            "-interesses": "-interesses__nome",
        }

        order = allowed.get(sort, "nome")
        qs = qs.order_by(order).distinct()

        return qs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Campo de busca
        context["termo"] = self.request.GET.get("q", "")
        
        # Lista de interesses ordenada por nome
        context["interesses"] = Interesse.objects.all().order_by("nome")
        
        # 🔽 Enviar o sort atual para o template
        context["sort"] = self.request.GET.get("sort", "nome")
        
        # 🔽 AQUI ESTÃO OS CONTADORES QUE FALTAVAM
        context["compradores"] = Empresa.objects.filter(modalidade="COMPRADOR").count()
        context["vendedores"] = Empresa.objects.filter(modalidade="VENDEDOR").count()
        
        return context


class EmpresaDetailView(DetailView):
    model = Empresa
    form_class = EmpresaForm
    template_name = 'core/empresa_detail.html'
    context_object_name = 'empresa'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        empresa = self.object

        # Buscar relacionamentos onde ela é A ou B
        relacoes = RelacionamentoEmpresa.objects.filter(
            Q(empresa_a=empresa) | Q(empresa_b=empresa)
        ).select_related("empresa_a", "empresa_b")

        context["relacionamentos"] = relacoes
        return context
 
# ==============================
class EmpresaCreateView(CreateView):
    model = Empresa
    form_class = EmpresaForm
    template_name = 'core/empresa_form.html'
    success_url = reverse_lazy('core:empresa_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Formulário de endereço
        if "form_endereco" not in context:
            context["form_endereco"] = EnderecoForm()

        # Lista de categorias distintas pelo nome
        categorias = Categoria.objects.filter(
            id__in=Interesse.objects.values_list("categoria", flat=True)
        ).order_by("nome")

        # Interesses agrupados por categoria
        interesses_por_categoria = {
            categoria: Interesse.objects.filter(categoria=categoria)
            for categoria in categorias
        }

        context["categorias_interesses"] = categorias
        context["interesses_por_categoria"] = interesses_por_categoria

        return context
    
    def form_valid(self, form):
        form_endereco = EnderecoForm(self.request.POST)

        if form_endereco.is_valid():
            endereco = form_endereco.save()
            empresa = form.save(commit=False)
            empresa.endereco = endereco
            empresa.save()
            form.save_m2m()
            return super().form_valid(form)

        # Se endereço for inválido, re-renderiza com erros
        return self.render_to_response(
            self.get_context_data(form=form, form_endereco=form_endereco)
        )
         
# ==============================
class EmpresaUpdateView(UpdateView):
    model = Empresa
    form_class = EmpresaForm
    template_name = 'core/empresa_form.html'
    success_url = reverse_lazy('core:empresa_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Captura o next da URL
        next_url = self.request.GET.get("next")
        context["next"] = next_url
        
        empresa = self.object
        endereco = empresa.endereco or Endereco()
        
        # Relacionamentos onde ela é A ou B
        relacoes = RelacionamentoEmpresa.objects.filter(
            Q(empresa_a=empresa) | Q(empresa_b=empresa)
        ).select_related("empresa_a", "empresa_b")

        context["relacionamentos"] = relacoes
         
        # Se o form_endereco já veio do POST, usa ele
        if "form_endereco" not in context:
            context["form_endereco"] = EnderecoForm(instance=endereco)

        # Lista de categorias distintas pelo nome
        categorias = Categoria.objects.filter(
            id__in=Interesse.objects.values_list("categoria", flat=True)
        ).order_by("nome")

        # Interesses agrupados por categoria
        interesses_por_categoria = {
            categoria: Interesse.objects.filter(categoria=categoria)
            for categoria in categorias
        }
 
        context["categorias_interesses"] = categorias
        context["interesses_por_categoria"] = interesses_por_categoria
        
        return context
    
    def form_valid(self, form):
        empresa = form.save(commit=False)
        next_url = self.request.POST.get("next") or None # ← recupera o next enviado no POST
        # Endereço atual ou novo
        endereco = empresa.endereco or Endereco()

        # Form de endereço
        form_endereco = EnderecoForm(self.request.POST, instance=endereco)

        # Salva endereço
        campos_endereco = ["cidade", "estado", "pais"]
        nenhum_campo_preenchido = not any(self.request.POST.get(c) for c in campos_endereco)
        
        if nenhum_campo_preenchido:
            # Remove o endereço da empresa
            empresa.endereco = None
            empresa.save()
            form.save_m2m()
            messages.success(self.request, "Empresa atualizada com sucesso.")
            return redirect(next_url or self.success_url)
        
        # Se o usuário preencheu algo → validar endereço
        if not form_endereco.is_valid():
            messages.error(self.request, "Há erros no endereço. Verifique os campos.")
            return self.render_to_response(
                self.get_context_data(form=form, form_endereco=form_endereco)
            )
        # Endereço válido → salvar
        endereco = form_endereco.save()
        empresa.endereco = endereco


        try:
            empresa.save()
            form.save_m2m()
            messages.success(self.request, "Empresa atualizada com sucesso.")
            return redirect(next_url or self.success_url)

        except Exception as e:
            messages.error(self.request, f"Erro ao salvar empresa: {e}")
            return self.render_to_response(
                self.get_context_data(form=form, form_endereco=form_endereco)
            )

# ==============================
def empresa_excluir(request, pk):
    empresa = get_object_or_404(Empresa, pk=pk)

    if request.method == "POST":
        nome = empresa.nome
        empresa.delete()
        messages.success(request, f"A empresa '{nome}' foi excluída com sucesso.")
        return redirect("core:empresa_list")

    return render(request, "core/empresa_excluir.html", {"empresa": empresa})


# =============================
def empresa_perfil(request, pk):
    empresa = get_object_or_404(Empresa, pk=pk)

    # Agrupa os interesses da empresa por categoria
    categorias = Categoria.objects.all().prefetch_related("interesse_set")

    interesses_por_categoria = []
    for categoria in categorias:
        interesses = empresa.interesses.filter(categoria=categoria)
        if interesses.exists():
            interesses_por_categoria.append((categoria, interesses))

    context = {
        "empresa": empresa,
        "interesses_por_categoria": interesses_por_categoria,
    }

    return render(request, "core/empresa_perfil.html", context)

# -----------------------------
# EMPRESAS - IMPORTAÇÃO DE CSV
# -----------------------------

def limpar_cnpj(valor):
    if not valor:
        return None
    return re.sub(r'\D', '', valor)

def empresa_importar(request):
    if request.method == "POST":
        arquivo = request.FILES.get("arquivo")

        if not arquivo:
            messages.error(request, "Selecione um arquivo CSV.")
            return redirect("core:empresas_importar")

        try:
            decoded = arquivo.read().decode("utf-8").splitlines()
            reader = csv.DictReader(decoded, delimiter=";")

            reader.fieldnames = [
                h.strip().lower().replace("\ufeff", "")
                for h in reader.fieldnames
            ]

            MAPA_MODALIDADE = {
                "comprador": "COMPRADOR",
                "vendedor": "VENDEDOR",
            }

            criadas = 0
            ignoradas = 0 

            for row in reader:
                row = {k.strip().lower(): v for k, v in row.items()}
                nome = (row.get("nome") or "").strip()
                cnpj = limpar_cnpj(row.get("cnpj"))
                site = (row.get("site") or "").strip()
                modalidade_csv = (row.get("modalidade") or "").strip().lower()
                modalidade = MAPA_MODALIDADE.get(modalidade_csv)

                if not nome or not modalidade:
                    ignoradas += 1
                    continue

                rua = (row.get("rua") or "").strip().title()
                numero = (row.get("numero") or "").strip()
                complemento = (row.get("complemento") or "").strip().title()
                bairro = (row.get("bairro") or "").strip().title()
                cidade = (row.get("cidade") or "").strip().title()
                estado = (row.get("estado") or "").strip().title()
                cep = (row.get("cep") or "").strip()
                pais = (row.get("pais") or "").strip().title() or "Brasil"

                endereco, _ = Endereco.objects.get_or_create(
                    rua=rua,
                    numero=numero,
                    complemento=complemento,
                    bairro=bairro,
                    cidade=cidade,
                    estado=estado,
                    pais=pais
                )

                empresa, criada = Empresa.objects.get_or_create(
                    nome=nome,
                    defaults={
                        "cnpj": cnpj,
                        "site": site,
                        "modalidade": modalidade,
                        "endereco": endereco
                    }
                )

                if not criada:
                    empresa.cnpj = cnpj
                    empresa.site = site
                    empresa.modalidade = modalidade
                    # empresa.endereco = endereco

                # 🔥 Validação completa
                empresa.full_clean()
                empresa.save()

                criadas += 1

            messages.success(request, f"{criadas} empresas importadas. {ignoradas} ignoradas.")
            return redirect("core:empresa_list")

        except Exception as e:
            messages.error(request, f"Erro ao processar arquivo: {e}")
            return redirect("core:empresa_importar")

    return render(request, "core/empresa_importar.html")


# -----------------------------
# INTERESSES
# -----------------------------
#===========CATEGORIA DE INTERESSE================

def categoria_list(request):
    categorias = Categoria.objects.all()
    return render(request, "core/categoria_list.html", {"categorias": categorias})

def categoria_create(request):
    if request.method == "POST":
        form = CategoriaForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("core:categoria_list")
    else:
        form = CategoriaForm()

    return render(request, "core/categoria_form.html", {"form": form})

def categoria_update(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)

    if request.method == "POST":
        form = CategoriaForm(request.POST, instance=categoria)
        if form.is_valid():
            form.save()
            return redirect("core:categoria_list")
    else:
        form = CategoriaForm(instance=categoria)

    return render(
        request,
        "core/categoria_form.html",
        {"form": form, "categoria": categoria}
    )

def categoria_delete(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)

    if request.method == "POST":
        categoria.delete()
        return redirect("core:categoria_list")

    return render(
        request,
        "core/categoria_confirm_delete.html",
        {"categoria": categoria}
    )
    
#===========INTERESSES================
class InteresseListView(ListView):
    model = Interesse
    template_name = "core/interesse_list.html"
    context_object_name = "categorias"
    paginate_by = 20  # Exibe 20 por página
    
    def get_queryset(self):
        qs = Categoria.objects.filter(interesse__isnull=False).distinct().order_by("nome")
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        categorias = context["categorias"]
        
        # Carrega interesses de cada categoria
        interesses_por_categoria = {
            categoria.id: categoria.interesse_set.order_by("nome")
            for categoria in categorias
        }

        context["interesses_por_categoria"] = interesses_por_categoria
        return context


class InteresseCreateView(CreateView):
    model = Interesse
    form_class = InteresseForm
    template_name = "core/interesse_form.html"
    success_url = reverse_lazy("core:interesse_list")

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            messages.success(self.request, "Interesse cadastrado com sucesso.")
            return response

        except IntegrityError:
            messages.error(
                self.request,
                "Este interesse já está cadastrado. Escolha outro nome."
            )
            return self.form_invalid(form)

        except Exception as e:
            messages.error(
                self.request,
                f"Erro inesperado ao salvar o interesse: {e}"
            )
            return self.form_invalid(form)

    def form_invalid(self, form):
        # Exibe erros de validação do próprio Django
        for campo, erros in form.errors.items():
            for erro in erros:
                messages.error(self.request, f"{campo}: {erro}")

        return super().form_invalid(form)


class InteresseUpdateView(UpdateView):
    model = Interesse
    form_class = InteresseForm
    template_name = "core/interesse_form.html"
    success_url = reverse_lazy("core:interesse_list")

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            messages.success(self.request, "Interesse atualizado com sucesso.")
            return response

        except IntegrityError:
            messages.error(
                self.request,
                "Já existe um interesse com este nome. Escolha outro nome."
            )
            return self.form_invalid(form)

        except Exception as e:
            messages.error(
                self.request,
                f"Erro inesperado ao atualizar o interesse: {e}"
            )
            return self.form_invalid(form)

    def form_invalid(self, form):
        # Exibe erros de validação do Django
        for campo, erros in form.errors.items():
            for erro in erros:
                messages.error(self.request, f"{campo}: {erro}")

        return super().form_invalid(form)


class InteresseDeleteView(DeleteView):
    model = Interesse
    template_name = "core/interesse_confirm_delete.html"
    success_url = reverse_lazy("core:interesse_list")

    
# -----------------------------
# REPRESENTANTE
# -----------------------------
class RepresentanteCreateView(CreateView):
    model = Representante
    form_class = RepresentanteForm
    template_name = "core/representante_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.empresa = get_object_or_404(Empresa, pk=kwargs["empresa_id"])
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["empresa"] = self.empresa
        return context

    def form_valid(self, form):
        form.instance.empresa = self.empresa
        form.save()
        return redirect("core:empresa_detail", pk=self.empresa.id)

class RepresentanteUpdateView(UpdateView):
    model = Representante
    form_class = RepresentanteForm
    template_name = "core/representante_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["empresa"] = self.object.empresa
        return context

    def get_success_url(self):
        return reverse_lazy("core:empresa_detail", kwargs={"pk": self.object.empresa.id})

class RepresentanteDeleteView(DeleteView):
    model = Representante
    template_name = "core/representante_confirm_delete.html"

    def get_success_url(self):
        return reverse_lazy("core:empresa_detail", kwargs={"pk": self.object.empresa.id})

# -----------------------------
def representante_importar(request, empresa_id):
    empresa = get_object_or_404(Empresa, id=empresa_id)
    if request.method == "POST":
        # Limpa mensagens antigas
        storage = get_messages(request)
        for _ in storage:
            pass

        arquivo = request.FILES.get("arquivo")

        if not arquivo:
            messages.error(request, "Nenhum arquivo enviado.")
            return redirect("core:representante_importar")

        try:
            decoded = arquivo.read().decode("utf-8").splitlines()
        except UnicodeDecodeError:
            messages.error(request, "Erro ao ler o arquivo. Use UTF-8.")
            return redirect("core:representante_importar")

        reader = csv.DictReader(decoded, delimiter=";")

        # Normaliza cabeçalhos
        reader.fieldnames = [
            h.strip().lower().replace("\ufeff", "")
            for h in reader.fieldnames
        ]

        criados = 0
        ignorados = 0
        erros = []

        for idx, row in enumerate(reader, start=2):  # linha 2 = primeira linha de dados
            row = {k.strip().lower(): (v or "").strip() for k, v in row.items()}

            empresa_nome = row.get("empresa")
            nome = row.get("nome")
            cargo = row.get("cargo")

            # Validação básica
            if not empresa_nome:
                erros.append(f"Linha {idx}: Campo 'empresa' vazio.")
                ignorados += 1
                continue

            if not nome:
                erros.append(f"Linha {idx}: Campo 'nome' vazio.")
                ignorados += 1
                continue

            # Busca empresa
            try:
                empresa = Empresa.objects.get(nome__iexact=empresa_nome)
            except Empresa.DoesNotExist:
                erros.append(f"Linha {idx}: Empresa '{empresa_nome}' não encontrada.")
                ignorados += 1
                continue

            # Criação do representante
            try:
                Representante.objects.create(
                    empresa=empresa,
                    nome=nome,
                    cargo=cargo or "",
                )
                criados += 1

            except Exception as e:
                erros.append(f"Linha {idx}: Erro ao criar representante: {e}")
                ignorados += 1

        # Mensagem final
        messages.success(
            request,
            f"{criados} representantes importados. {ignorados} ignorados."
        )

        # Exibe erros, se houver
        if erros:
            for erro in erros:
                messages.error(request, erro)

        return redirect("core:representante_importar")

    return render(request, "core/representante_importar.html", {
        "empresa": empresa
    })

# -----------------------------
# EVENTO
# -----------------------------
class EventoListView(ListView):
    model = Evento
    template_name = 'core/evento_list.html'
    context_object_name = 'eventos'

class EventoCreateView(CreateView):
    model = Evento
    fields = ['nome', 'data', 'local', 'inicio_ev', 'termino_ev', 'descricao']
    template_name = 'core/evento_form.html'
    success_url = reverse_lazy('core:evento_list')

class EventoDetailView(DetailView):
    model = Evento
    template_name = 'core/evento_detail.html'
    context_object_name = 'evento'

class EventoUpdateView(UpdateView):
    model = Evento
    fields = ['nome', 'data', 'local', 'inicio_ev', 'termino_ev', 'descricao']
    template_name = 'core/evento_form.html'
    success_url = reverse_lazy('core:evento_list')


class EventoDeleteView(DeleteView):
    model = Evento
    template_name = 'core/evento_confirm_delete.html'
    success_url = reverse_lazy('core:evento_list')

# -------------------------------
# EMPRESA PARTICIPANTE DE EVENTO
# -------------------------------
def evento_participantes(request, evento_id):
    evento = get_object_or_404(Evento, id=evento_id)
    empresas = Empresa.objects.all()

    # LIMPA MENSAGENS ANTIGAS
    storage = get_messages(request)
    for _ in storage:
        pass

    # Empresas já inscritas
    inscritas = EmpresaEvento.objects.filter(
        evento=evento,
        participa=True
    ).values_list("empresa_id", flat=True)

    total_inscritas = len(inscritas)
    total_empresas = empresas.count()

    compradores_inscritos = Empresa.objects.filter(
        id__in=inscritas,
        modalidade="COMPRADOR"
    ).count()

    vendedores_inscritos = Empresa.objects.filter(
        id__in=inscritas,
        modalidade="VENDEDOR"
    ).count()

    percentual = round((total_inscritas / total_empresas) * 100) if total_empresas > 0 else 0

    # ============================
    # PROCESSAMENTO DO FORMULÁRIO
    # ============================
    if request.method == "POST":
        selecionadas = request.POST.getlist("empresas")

        # -----------------------------------------
        # VERIFICA RELACIONAMENTOS ENTRE SELECIONADAS - ALERTA, MAS NÃO BLOQUEIA
        # -----------------------------------------
        relacionamentos_detectados = []

        for i, empresa_id in enumerate(selecionadas):
            for outra_id in selecionadas[i+1:]:
                if empresas_tem_relacao(int(empresa_id), int(outra_id)):
                    e1 = Empresa.objects.get(id=empresa_id)
                    e2 = Empresa.objects.get(id=outra_id)
                    relacionamentos_detectados.append((e1.nome, e2.nome))

        # Se encontrou relacionamentos, apenas alerta
        if relacionamentos_detectados:
            msg = "Algumas empresas selecionadas já possuem relações prévias:<br>"
            for e1, e2 in relacionamentos_detectados:
                msg += f"• {e1} ↔ {e2}<br>"

            messages.warning(request, mark_safe(msg))
            
        # Validação: mínimo de 10 interesses
        for empresa_id in selecionadas:
            empresa = Empresa.objects.get(id=empresa_id)
            
            if empresa.interesses.count() < 10:
                messages.error(
                    request,
                    f"A empresa '{empresa.nome}' possui menos de 10 interesses marcados. "
                    "Atualize os interesses antes de inscrevê-la."
                )
                return redirect("core:evento_participantes", evento.id)

        # Limpa participações anteriores
        EmpresaEvento.objects.filter(evento=evento).delete()

        # Cria novas participações
        for empresa_id in selecionadas:
            EmpresaEvento.objects.create(
                empresa_id=empresa_id,
                evento=evento,
                participa=True
            )

        messages.success(request, "Participantes atualizados com sucesso.")
        return redirect("core:evento_participantes", evento.id)


    context = {
        "evento": evento,
        "empresas": empresas,
        "inscritas": inscritas,
        "total_inscritas": total_inscritas,
        "total_empresas": total_empresas,
        "compradores_inscritos": compradores_inscritos,
        "vendedores_inscritos": vendedores_inscritos,
        "percentual": percentual,
    }

    return render(request, "core/evento_participantes.html", context)
# -----------------------------------------------
# RELATÓRIO DE PARTICIPANTES INSCRITOS NO EVENTO
# -----------------------------------------------
def relatorio_inscritos(request, evento_id):
    evento = get_object_or_404(Evento, id=evento_id)

    inscritos = Empresa.objects.filter(
        empresaevento__evento=evento,
        empresaevento__participa=True
    ).order_by("modalidade", "nome")

    compradores = inscritos.filter(modalidade="COMPRADOR")
    vendedores = inscritos.filter(modalidade="VENDEDOR")

    context = {
        "evento": evento,
        "inscritos": inscritos,
        "compradores": compradores,
        "vendedores": vendedores,
        "total": inscritos.count(),
    }

    return render(request, "core/evento_relatorio_inscritos.html", context)

# ====================================
# Esta função gera e exibe o ranking de afinidade entre compradores e vendedores.
# Apenas calcula afinidades e prepara dados para exibição.
# Usado exclusivamente para enviar ao template.
# ====================================
def ranking_afinidades(request, evento_id):
    evento = get_object_or_404(Evento, id=evento_id)

    # Carrega compradores e vendedores participantes do evento
    compradores = Empresa.objects.filter(
        modalidade="COMPRADOR",
        empresaevento__evento=evento,
        empresaevento__participa=True
    )

    vendedores = Empresa.objects.filter(
        modalidade="VENDEDOR",
        empresaevento__evento=evento,
        empresaevento__participa=True
    )

    # Cores por vendedor (mesma função usada no relatório)
    cores_vendedores = {v.id: cor_para_vendedor(v.id) for v in vendedores}
    
    # Descobre o top_n
    params = request.session.get("rodadas_params")
    if params and "qtd_rodadas" in params:
        top_n = min(int(params["qtd_rodadas"]), vendedores.count())
    else:
        top_n = vendedores.count()  # fallback: usa todos
    
    # Monta o ranking de afinidades: para cada comprador, uma lista de vendedores
    # ordenada por afinidade. O ranking é uma lista de dicionários, onde cada dicionário
    # tem o comprador e a lista de vendedores ordenada por afinidade.
    ranking = []

    for comprador in compradores:
        lista = []

        # Número total de interesses do comprador (para percentual)
        total_interesses = comprador.interesses.count() or 1
        
        for vendedor in vendedores:
            score = calcular_afinidade(comprador, vendedor)
            
            # Afinidade percentual
            percentual = round((score / total_interesses) * 100)
            
            # Verifica conflito
            conflito = empresas_tem_relacao(comprador.id, vendedor.id)
            
            # Cores
            cor = cores_vendedores.get(vendedor.id, {"solid": "#000", "alpha": "#fff"})
            
            lista.append({
                "vendedor": vendedor,
                "score": score,
                "percentual": percentual,
                "conflito": conflito,
                "cor_solid": cor["solid"],
                "cor_alpha": cor["alpha"],
            })

        # Ordenar do maior para o menor score
        lista.sort(key=lambda x: x["score"], reverse=True)

        # Adiciona ao ranking final apenas os top N vendedores para este comprador.
        ranking.append({
            "comprador": comprador,
            "melhores": lista  # top N vendedores
        })

    # Prepara o contexto para o template, incluindo o ranking e o top_n para exibição.
    context = {
        "evento": evento,
        "ranking": ranking,
        "top_n": top_n,
    }

    # Renderiza a página HTML
    return render(request, "core/ranking_afinidades.html", context)

# ========================================================
def gerar_ranking(evento, top_n):
    compradores = Empresa.objects.filter(
        modalidade="COMPRADOR",
        empresaevento__evento=evento,
        empresaevento__participa=True
    )

    vendedores = Empresa.objects.filter(
        modalidade="VENDEDOR",
        empresaevento__evento=evento,
        empresaevento__participa=True
    )

    ranking = {}

    for c in compradores:
        lista = []
        for v in vendedores:
            # 🔥 BLOQUEIO DE RELACIONAMENTO
            if empresas_tem_relacao(c.id, v.id):
                continue
            score = calcular_afinidade(c, v)
            lista.append((v, score))

        lista.sort(key=lambda x: x[1], reverse=True)

        # 🔥 pega todos os vendedores
        ranking[c.id] = [v for v, score in lista]

    return ranking

# ========================================================
def rodadas_gerar_ranking(request, evento_id):
    evento = get_object_or_404(Evento, id=evento_id)

    if request.method == "POST":
        qtd_rodadas = int(request.POST.get("qtd_rodadas"))

        # limpa rodadas antigas
        Rodada.objects.filter(evento=evento).delete()
        Mesa.objects.filter(rodada__evento=evento).delete()

        # cria rodadas com horários
        criar_rodadas(evento, qtd_rodadas)

        # gera mesas com base no ranking
        gerar_rodadas_por_ranking(evento, qtd_rodadas)

        messages.success(request, "Rodadas geradas com sucesso usando ranking de afinidades.")
        return redirect("core:relatorio_rodadas", evento_id=evento.id)

    return render(request, "core/rodadas_gerar_ranking.html", {"evento": evento})

#==============================
# Esse relatório serve para você (ou qualquer organizador do evento) entender:
# - quais vendedores atingiram o mínimo
# - quais ficaram abaixo
# - por que ficaram abaixo
# - quantos compradores compatíveis cada vendedor tinha
# - quantos encontros foram bloqueados por conflito
# - quantos encontros foram bloqueados por repetição
# - quantas rodadas ainda estavam disponíveis quando o vendedor ficou “travado”
#==============================
from collections import defaultdict

def rodadas_debug_report(request, evento_id):
    evento = get_object_or_404(Evento, id=evento_id)

    compradores = list(Empresa.objects.filter(
        modalidade="COMPRADOR",
        empresaevento__evento=evento,
        empresaevento__participa=True
    ))

    vendedores = list(Empresa.objects.filter(
        modalidade="VENDEDOR",
        empresaevento__evento=evento,
        empresaevento__participa=True
    ))

    rodadas = Rodada.objects.filter(evento=evento).order_by("inicio_ro")

    mesas = Mesa.objects.filter(
        rodada__evento=evento
    ).select_related("rodada", "comprador", "vendedor")

    # Participações reais
    participacoes = defaultdict(int)
    for mesa in mesas:
        participacoes[mesa.vendedor_id] += 1

    # Mínimo esperado
    qtd_rodadas = rodadas.count()
    minimo_por_vendedor = max(1, math.ceil(qtd_rodadas / 2))

    # Diagnóstico por vendedor
    relatorio = []

    for vendedor in vendedores:
        v_id = vendedor.id

        # compradores compatíveis
        compradores_compativeis = []
        compradores_bloqueados_relacao = []
        compradores_bloqueados_repeticao = []

        for c in compradores:

            # conflito de relação
            if empresas_tem_relacao(c.id, v_id):
                compradores_bloqueados_relacao.append(c)
                continue

            # repetição comprador–vendedor
            repetiu = mesas.filter(comprador=c, vendedor=vendedor).exists()
            if repetiu:
                compradores_bloqueados_repeticao.append(c)
                continue

            compradores_compativeis.append(c)

        relatorio.append({
            "vendedor": vendedor,
            "participacoes": participacoes[v_id],
            "atingiu_minimo": participacoes[v_id] >= minimo_por_vendedor,
            "minimo": minimo_por_vendedor,
            "compatíveis": compradores_compativeis,
            "bloqueio_relacao": compradores_bloqueados_relacao,
            "bloqueio_repeticao": compradores_bloqueados_repeticao,
            "total_compativeis": len(compradores_compativeis),
        })

    return render(request, "core/rodadas_debug_report.html", {
        "evento": evento,
        "rodadas": rodadas,
        "relatorio": relatorio,
        "minimo_por_vendedor": minimo_por_vendedor,
    })

# -----------------------------
# RODADAS
# -----------------------------

def rodadas_list(request, evento_id):
    evento = get_object_or_404(Evento, id=evento_id)
    rodadas = evento.rodadas.all().order_by("inicio_ro", "numero")

    return render(request, "core/rodadas_list.html", {
        "evento": evento,
        "rodadas": rodadas,
    })
    
# ===================================================================================
# Esta view é para gerar as rodadas automaticamente usando o algoritmo de matchmaking
# ===================================================================================
def rodadas_gerar(request, evento_id):
    evento = get_object_or_404(Evento, id=evento_id)

    # GET → mostra o formulário
    if request.method != "POST":
        return render(request, "core/rodadas_gerar.html", {
            "evento": evento,
            "duracoes": Rodada.DURACOES
        })
    
    # POST → lê o modo escolhido
    modo = request.POST.get("modo")

    try:
            
        # POST → valida participantes e redireciona para confirmação
        qtd_mesas = int(request.POST["qtd_mesas"])
        duracao = int(request.POST["duracao"])
        inicio_rodadas = request.POST["inicio_rodadas"]
        intervalo = int(request.POST["intervalo"])
        pausa_cada = int(request.POST["pausa_cada"])
        pausa_duracao = int(request.POST["pausa_duracao"])
        qtd_rodadas = int(request.POST["qtd_rodadas"])
    except:
        messages.error(request, "Parâmetros inválidos para geração de rodadas.")
        return redirect("core:rodadas_gerar", evento_id)

    # Guarda os dados do formulário na sessão
    request.session["rodadas_params"] = {
        "qtd_mesas": qtd_mesas,
        "duracao": duracao,
        "inicio_rodadas": inicio_rodadas,
        "intervalo": intervalo,
        "pausa_cada": pausa_cada,
        "pausa_duracao": pausa_duracao,
        "qtd_rodadas": qtd_rodadas,
    }

    # ============================
    # VERIFICAÇÃO DE PARTICIPANTES
    # ============================
    compradores = Empresa.objects.filter(
        modalidade="COMPRADOR",
        empresaevento__evento=evento,
        empresaevento__participa=True
    )

    vendedores = Empresa.objects.filter(
        modalidade="VENDEDOR",
        empresaevento__evento=evento,
        empresaevento__participa=True
    )

    if not compradores.exists() or not vendedores.exists():
        messages.error(
            request,
            "Não é possível gerar rodadas: verifique se há compradores e vendedores inscritos no evento."
        )
        return redirect("core:evento_participantes", evento_id)

    # Opcional: alerta se houver empresas cadastradas mas não inscritas
    total_inscritas = compradores.count() + vendedores.count()
    total_empresas_evento = Empresa.objects.filter(
        empresaevento__evento=evento
    ).count()

    if total_inscritas < total_empresas_evento:
        messages.warning(
            request,
            "Existem empresas cadastradas que não estão inscritas neste evento. "
            "Confirme se isso está correto antes de gerar as rodadas."
        )

    # ============================
    # SE TUDO OK → GERA RODADAS
    # ============================
    if modo == "ranking":
        return redirect("core:rodadas_confirmar_ranking", evento_id)

    return redirect("core:rodadas_confirmar", evento_id)

# ========================================================
def rodadas_confirmar_ranking(request, evento_id):
    evento = get_object_or_404(Evento, id=evento_id)

    # Recupera parâmetros da sessão
    params = request.session.get("rodadas_params")
    if not params:
        messages.error(request, "Parâmetros de geração de rodadas não encontrados.")
        return redirect("core:rodadas_gerar", evento_id)

    qtd_mesas = params["qtd_mesas"]
    duracao = params["duracao"]
    inicio_rodadas = params["inicio_rodadas"]
    intervalo = params["intervalo"]
    pausa_cada = params["pausa_cada"]
    pausa_duracao = params["pausa_duracao"]
    qtd_rodadas = params["qtd_rodadas"]

    # ============================
    # VERIFICAÇÃO DE PARTICIPANTES
    # ============================
    compradores = Empresa.objects.filter(
        modalidade="COMPRADOR",
        empresaevento__evento=evento,
        empresaevento__participa=True
    )

    vendedores = Empresa.objects.filter(
        modalidade="VENDEDOR",
        empresaevento__evento=evento,
        empresaevento__participa=True
    )

    if not compradores.exists() or not vendedores.exists():
        messages.error(
            request,
            "Não é possível gerar rodadas: verifique se há compradores e vendedores inscritos no evento."
        )
        return redirect("core:evento_participantes", evento_id)

    # Remove rodadas anteriores
    Rodada.objects.filter(evento=evento).delete()

    # ============================
    # GERA AS MESAS POR RANKING
    # ============================
    try:
        rodadas, logs = gerar_todas_as_rodadas(
            evento=evento,
            qtd_mesas=qtd_mesas,
            duracao_minutos=duracao,
            inicio_rodadas=inicio_rodadas,
            intervalo_minutos=intervalo,
            pausa_cada=pausa_cada,
            pausa_duracao=pausa_duracao,
            qtd_rodadas=qtd_rodadas,
        )
        
        # Salva logs na sessão
        request.session["rodadas_logs"] = logs
        
    except Exception as e:
        messages.error(request, f"Erro ao gerar rodadas por ranking: {e}")
        return redirect("core:rodadas_gerar", evento_id)

    messages.success(request, "Rodadas geradas com sucesso usando ranking de afinidades!")

    return redirect("core:rodadas_relatorio", evento_id)

# ========================================================
def rodadas_confirmar(request, evento_id):
    evento = get_object_or_404(Evento, id=evento_id)

    # Recupera parâmetros salvos na sessão
    params = request.session.get("rodadas_params")
    if not params:
        messages.error(request, "Nenhum parâmetro encontrado. Preencha o formulário novamente.")
        return redirect("core:rodadas_gerar", evento_id)

    compradores = Empresa.objects.filter(
        modalidade="COMPRADOR",
        empresaevento__evento=evento,
        empresaevento__participa=True
    )

    vendedores = Empresa.objects.filter(
        modalidade="VENDEDOR",
        empresaevento__evento=evento,
        empresaevento__participa=True
    )

    # Bloqueio de segurança
    if compradores.count() == 0 or vendedores.count() == 0:
        messages.error(
            request,
            "Para gerar rodadas, é necessário ter pelo menos 1 comprador e 1 vendedor inscritos."
        )
        return redirect("core:evento_participantes", evento_id)

    # Empresas não inscritas
    inscritas_ids = list(compradores.values_list("id", flat=True)) + \
                    list(vendedores.values_list("id", flat=True))

    nao_inscritas = Empresa.objects.exclude(id__in=inscritas_ids)

    context = {
        "evento": evento,
        "compradores": compradores,
        "vendedores": vendedores,
        "qtd_compradores": compradores.count(),
        "qtd_vendedores": vendedores.count(),
        "nao_inscritas": nao_inscritas,
        "params": params,
    }

    return render(request, "core/rodadas_confirmar.html", context)
 
# ========================================================
def rodadas_do_evento(request, evento_id):
    evento = get_object_or_404(Evento, id=evento_id)
    rodadas = evento.rodadas.all()
    return render(request, 'core/rodadas_list.html', {
        'evento': evento,
        'rodadas': rodadas
    })


def rodadas_editar(request, rodada_id):
    rodada = get_object_or_404(Rodada, id=rodada_id)

    if request.method == "POST":
        rodada.nome = request.POST["nome"]
        rodada.duracao = request.POST["duracao"]
        rodada.save()
        return redirect("core:rodadas_list", rodada.evento.id)

    return render(request, "core/rodadas_editar.html", {
        "rodada": rodada,
        "duracoes": Rodada.DURACOES
    })


def rodadas_excluir(request, rodada_id):
    rodada = get_object_or_404(Rodada, id=rodada_id)
    evento = rodada.evento  # para redirecionar depois

    # Exclui a rodada
    rodada.delete()

    messages.success(request, "Rodada excluída com sucesso!")
    return redirect('core:rodadas_list', evento_id=evento.id)


def rodadas_log(request, evento_id):
    evento = get_object_or_404(Evento, id=evento_id)

    logs = request.session.get("rodadas_logs")

    # Se não há logs na sessão, precisamos verificar se existem rodadas
    if not logs:
        rodadas_existentes = Rodada.objects.filter(evento=evento).exists()

        if rodadas_existentes:
            # OPÇÃO B → existem rodadas, mas não há logs
            messages.warning(
                request,
                "As rodadas existem, mas não há log disponível. "
                "Isso pode ocorrer se a sessão expirou."
            )
            return redirect("core:rodadas_relatorio", evento_id)

        else:
            # OPÇÃO C → não há rodadas e não há logs
            return render(request, "core/rodadas_log.html", {
                "evento": evento,
                "logs": {},
                "mensagem": "Nenhum log disponível. Gere as rodadas para visualizar o log."
            })

    # Se há logs → exibe normalmente
    return render(request, "core/rodadas_log.html", {
        "evento": evento,
        "logs": logs,
    })


# ----------------------------------------------------
# Agenda de Rodadas
# ----------------------------------------------------
def rodadas_relatorio(request, evento_id):
    evento = get_object_or_404(Evento, id=evento_id)

    # COLUNAS: rodadas ordenadas pelo horário
    rodadas = Rodada.objects.filter(evento=evento).order_by("inicio_ro")

    # LINHAS: compradores inscritos
    compradores = (
        Empresa.objects.filter(
            empresaevento__evento=evento,
            empresaevento__participa=True,
            modalidade="COMPRADOR"
        )
        .order_by("nome")
    )

    # ENCONTROS: mesas geradas pelo matchmaking
    mesas = (
        Mesa.objects.filter(rodada__evento=evento)
        .select_related("rodada", "comprador", "vendedor")
    )

    # Criar estrutura: comprador → {rodada_id: vendedor}
    tabela = defaultdict(dict) #{c.id: {} for c in compradores}

    for mesa in mesas:
        if mesa.comprador_id and mesa.vendedor_id:
            tabela[mesa.comprador_id][mesa.rodada_id] = mesa.vendedor

    # 🔥 GERAR CORES PARA CADA VENDEDOR (SEM COLCHETES NO TEMPLATE)
    vendedores = Empresa.objects.filter(
        empresaevento__evento=evento,
        empresaevento__participa=True,
        modalidade="VENDEDOR"
    )

    cores_vendedores = {v.id: cor_para_vendedor(v.id) for v in vendedores}
    
    # Transformar em lista pronta para o template
    linhas = []
    for comprador in compradores:
        celulas = []
        for r in rodadas:
            vend = tabela[comprador.id].get(r.id)
            if vend:
                cor = cores_vendedores.get(vend.id, {"solid": "#000000", "alpha": "#ffffff"})
                celulas.append({
                    "vendedor": vend,
                    "cor_solid": cor["solid"],
                    "cor_alpha": cor["alpha"],
                })
            else:
                celulas.append(None)
        linhas.append({
            "comprador": comprador,
            "celulas": celulas,
        })
            
    context = {
        "evento": evento,
        "rodadas": rodadas,
        "linhas": linhas,
    }

    return render(request, "core/rodadas_relatorio.html", context)

# Agenda das empresa no evento
def agendas_empresas_evento(request, evento_id):
    evento = get_object_or_404(Evento, id=evento_id)

    empresas = (
        Empresa.objects.filter(
            empresaevento__evento=evento,
            empresaevento__participa=True
        )
        .order_by("nome")
    )
    # Adiciona a quantidade de rodadas para cada empresa
    for empresa in empresas:
        empresa.total_rodadas = (
            Mesa.objects.filter(
                rodada__evento=evento,
                comprador=empresa
            ).count()
            +
            Mesa.objects.filter(
                rodada__evento=evento,
                vendedor=empresa
            ).count()
        )

        
    return render(request, "core/agendas_empresas_evento.html", {
        "evento": evento,
        "empresas": empresas,
    })

# Agendo do Comprador
def agenda_comprador(request, empresa_id, evento_id):
    empresa = get_object_or_404(Empresa, id=empresa_id)
    evento = get_object_or_404(Evento, id=evento_id)

    encontros = (
        Mesa.objects
        .filter(rodada__evento=evento, comprador=empresa)
        .select_related("rodada", "vendedor")
        .order_by("rodada__inicio_ro")
    )
 
    return render(request, "core/agenda_comprador.html", {
        "empresa": empresa,
        "evento": evento,
        "encontros": encontros,
    })

# Agenda do Vendedor
def agenda_vendedor(request, empresa_id, evento_id):
    empresa = get_object_or_404(Empresa, id=empresa_id)
    evento = get_object_or_404(Evento, id=evento_id)

    encontros = (
        Mesa.objects
        .filter(rodada__evento=evento, vendedor=empresa)
        .select_related("rodada", "comprador")
        .order_by("rodada__inicio_ro")
    )

    return render(request, "core/agenda_vendedor.html", {
        "empresa": empresa,
        "evento": evento,
        "encontros": encontros,
    })

# -----------------------------
# MESAS
# -----------------------------

def mesas_da_rodada(request, rodada_id):
    rodada = get_object_or_404(Rodada, id=rodada_id)
    mesas = rodada.mesas.all().order_by("numero")
    
    return render(request, "core/mesas_da_rodada.html", {
        "rodada": rodada,
        "mesas": mesas
    })

# -----------------------------
# PAINEL DE RODADAS
# -----------------------------
def painel_da_rodada(request, rodada_id):
    rodada = get_object_or_404(Rodada, id=rodada_id)
    mesas = rodada.mesas.select_related("comprador", "vendedor").all()
    empresas = Empresa.objects.filter(eventos_participantes=rodada.evento)

    # Total de mesas
    total_mesas = mesas.count()

    # Total de reservas = comprador + vendedor
    total_reservas = sum([
        (1 if m.comprador else 0) +
        (1 if m.vendedor else 0)
        for m in mesas
    ])

    # Empresas que já estão em alguma mesa
    empresas_ocupadas_ids = set(
        mesas.values_list("comprador_id", flat=True)
    ) | set(
        mesas.values_list("vendedor_id", flat=True)
    )
 
    # Remove None
    empresas_ocupadas_ids.discard(None)

    # Empresas sem reserva
    empresas_sem_reserva = empresas.exclude(id__in=empresas_ocupadas_ids)

    # Capacidade total = 2 por mesa
    capacidade_total = total_mesas * 2

    ocupacao_percentual = (
        (total_reservas / capacidade_total) * 100
        if capacidade_total > 0 else 0
    )

    # Mesas com vagas e mesas cheias
    mesas_com_vagas = [m for m in mesas if (m.comprador and m.vendedor) is False]
    mesas_cheias = [m for m in mesas if m.comprador and m.vendedor]

    context = {
        "rodada": rodada,
        "mesas": mesas,
        "total_mesas": total_mesas,
        "total_reservas": total_reservas,
        "empresas_sem_reserva": empresas_sem_reserva,
        "ocupacao_percentual": round(ocupacao_percentual, 1),
        "mesas_com_vagas": mesas_com_vagas,
        "mesas_cheias": mesas_cheias,
    }

    return render(request, "core/painel_rodada.html", context)

# -----------------------------
# RELATÓRIO DE AFINIDADES
# -----------------------------

def mesa_relatorio(request, pk):
    mesa = get_object_or_404(Mesa, pk=pk)

    comprador = mesa.comprador
    vendedor = mesa.vendedor

    interesses_comprador = set(comprador.interesses.all()) if comprador else set()
    interesses_vendedor = set(vendedor.interesses.all()) if comprador else set()

    afinidades = interesses_comprador.intersection(interesses_vendedor)
    complementares = interesses_comprador.symmetric_difference(interesses_vendedor)

    # --- Cálculo da compatibilidade ---
    total_unico = interesses_comprador.union(interesses_vendedor)
    if total_unico:
        compatibilidade = round((len(afinidades) / len(total_unico)) * 100)
    else:
        compatibilidade = 0
    # -----------------------------------
    
    context = {
        "mesa": mesa,
        "comprador": comprador,
        "vendedor": vendedor,
        "afinidades": afinidades,
        "complementares": complementares,
        "interesses_comprador": interesses_comprador,
        "interesses_vendedor": interesses_vendedor,
        "compatibilidade": compatibilidade,
    }

    return render(request, "core/mesa_relatorio.html", context)

#================================================
# RELACIONAMENTO ENTRE EMPRESAS
#================================================

def empresa_relacionamentos(request, empresa_id):
    empresa = get_object_or_404(Empresa, id=empresa_id)

    # Relacionamentos onde ela é A ou B
    relacoes = RelacionamentoEmpresa.objects.filter(
        empresa_a=empresa
    ) | RelacionamentoEmpresa.objects.filter(
        empresa_b=empresa
    )

    context = {
        "empresa": empresa,
        "relacoes": relacoes,
    }
    return render(request, "core/empresa_relacionamentos.html", context)

def adicionar_relacionamento(request, empresa_id):
    empresa = get_object_or_404(Empresa, id=empresa_id)

    # 🔥 Bloqueia vendedores de criar relacionamentos
    if empresa.modalidade != "COMPRADOR":
        messages.error(request, "Somente empresas COMPRADORAS podem criar relacionamentos.")
        return redirect("core:empresa_relacionamentos", empresa.id)
    
    if request.method == "POST":
        form = RelacionamentoForm(request.POST, empresa_atual=empresa, initial={"empresa_a": empresa})

        if form.is_valid():
            rel = form.save(commit=False)
            rel.empresa_a = empresa
            rel.save()
            messages.success(request, "Relacionamento adicionado com sucesso.")
            return redirect("core:empresa_relacionamentos", empresa.id)
    else:
        form = RelacionamentoForm(empresa_atual=empresa, initial={"empresa_a": empresa})

    return render(request, "core/empresa_adicionar_relacionamento.html", {
        "empresa": empresa,
        "form": form
    })

def remover_relacionamento(request, empresa_id, rel_id):
    empresa = get_object_or_404(Empresa, id=empresa_id)
    rel = get_object_or_404(RelacionamentoEmpresa, id=rel_id)

    rel.delete()
    messages.success(request, "Relacionamento removido.")
    return redirect("core:empresa_relacionamentos", empresa.id)

# Relatorio de empresas relacionadas

def relatorio_empresas_relacionadas(request):
    # Busca todos os relacionamentos ativos
    relacoes = RelacionamentoEmpresa.objects.select_related(
        "empresa_a", "empresa_b"
    ).order_by("empresa_a__nome", "empresa_b__nome")

    # Agrupamento por empresa_a (comprador)
    agrupado = defaultdict(list)
    
    for rel in relacoes:
        agrupado[rel.empresa_a].append(rel)

    # Converte para dict normal (opcional, apenas para estética)
    agrupado = dict(agrupado)

    context = {
        "relacoes": relacoes,
        "agrupado": agrupado,
    }
    return render(request, "core/relatorio_empresas_relacionadas.html", context)
