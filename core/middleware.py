from django.shortcuts import redirect
from django.urls import reverse


class RodanegociosProtectionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        caminho = request.path
        
        # Libera rotas da API
        if caminho.startswith("/api/"):
            return self.get_response(request)
        
        # Libera as rotas para acesso
        rotas_livres = [
            "/login/",
            "/esqueci-senha/",
            "/redefinir-senha/",
            "/password_change/",
            "/password_change/done/",
            "/admin/",
        ]
        
        
        if any(caminho.startswith(r) for r in rotas_livres):
            return self.get_response(request)

        if not request.user.is_authenticated:
            return redirect("core:login")

        if not request.user.has_perm("core.pode_acessar_rodanegocios"):
            return redirect("core:login")

        return self.get_response(request)
