from django.shortcuts import get_object_or_404, render
from rest_framework.views import APIView
from rest_framework.response import Response
from core.models import Empresa, Evento, Mesa
from .serializers import MesaSerializer

app_name = 'api'


class AgendaCompradorAPI(APIView):
    def get(self, request, empresa_id, evento_id):
        empresa = get_object_or_404(Empresa, id=empresa_id)
        evento = get_object_or_404(Evento, id=evento_id)

        if empresa.modalidade != "COMPRADOR":
            return Response({"erro": "Esta empresa não é um comprador."}, status=400)

        encontros = (
            Mesa.objects
            .filter(rodada__evento=evento, comprador=empresa)
            .select_related("rodada", "vendedor")
            .order_by("rodada__inicio_ro")
        )

        return Response(MesaSerializer(encontros, many=True).data)


class AgendaVendedorAPI(APIView):
    def get(self, request, empresa_id, evento_id):
        empresa = get_object_or_404(Empresa, id=empresa_id)
        evento = get_object_or_404(Evento, id=evento_id)

        if empresa.modalidade != "VENDEDOR":
            return Response({"erro": "Esta empresa não é um vendedor."}, status=400)

        encontros = (
            Mesa.objects
            .filter(rodada__evento=evento, vendedor=empresa)
            .select_related("rodada", "comprador")
            .order_by("rodada__inicio_ro")
        )

        return Response(MesaSerializer(encontros, many=True).data)
