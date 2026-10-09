from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework_simplejwt.tokens import AccessToken

from core.models import Empresa, Evento

ROTAS_PROTEGIDAS = [
    "/api/empresas/",
    "/api/eventos/",
    "/api/rodadas/",
    "/api/mesas/",
]


class ApiAutenticacaoTests(TestCase):
    def setUp(self):
        self.usuario = User.objects.create_user("api", password="senha-teste-123")
        self.empresa = Empresa.objects.create(nome="Empresa Teste", modalidade="COMPRADOR")
        self.evento = Evento.objects.create(nome="Evento Teste", local="Local")

    def _cabecalho(self):
        return {"HTTP_AUTHORIZATION": f"Bearer {AccessToken.for_user(self.usuario)}"}

    def test_listagens_sem_token_retornam_401(self):
        for rota in ROTAS_PROTEGIDAS:
            with self.subTest(rota=rota):
                self.assertEqual(self.client.get(rota).status_code, 401)

    def test_agendas_sem_token_retornam_401(self):
        rotas = [
            f"/api/agenda/comprador/{self.empresa.id}/{self.evento.id}/",
            f"/api/agenda/vendedor/{self.empresa.id}/{self.evento.id}/",
            f"/api/agenda/evento/{self.evento.id}/empresa/{self.empresa.id}/",
            f"/api/agenda/comprador/evento/{self.evento.id}/{self.empresa.id}/",
        ]
        for rota in rotas:
            with self.subTest(rota=rota):
                self.assertEqual(self.client.get(rota).status_code, 401)

    def test_listagens_com_token_retornam_200(self):
        for rota in ROTAS_PROTEGIDAS:
            with self.subTest(rota=rota):
                self.assertEqual(self.client.get(rota, **self._cabecalho()).status_code, 200)

    def test_token_continua_acessivel_sem_login(self):
        resposta = self.client.post(
            "/api/token/", {"username": "api", "password": "senha-teste-123"}
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertIn("access", resposta.json())
