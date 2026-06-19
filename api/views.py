from django.shortcuts import get_object_or_404, render
from rest_framework.views import APIView
from rest_framework.response import Response
from core.models import Empresa, Evento, Mesa, Rodada, EmpresaEvento
from .serializers import (
    EmpresaSerializer,
    EventoSerializer,
    RodadaSerializer,
    MesaSerializer
)
from rest_framework.permissions import IsAuthenticated
    

class AgendaCompradorEventoAPI(APIView):
    def get(self, request, evento_id, comprador_id):
        comprador = get_object_or_404(Empresa, id=comprador_id)
        evento = get_object_or_404(Evento, id=evento_id)

        if comprador.modalidade != "COMPRADOR":
            return Response({"erro": "Esta empresa não é um comprador."}, status=400)

        mesas = (
            Mesa.objects
            .filter(rodada__evento=evento, comprador=comprador)
            .select_related("rodada", "vendedor", "comprador")
            .order_by("rodada__inicio_ro")
        )

        return Response(MesaSerializer(mesas, many=True).data)


class AgendaCompradorAPI(APIView):
    #permission_classes = [IsAuthenticated]

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
    #permission_classes = [IsAuthenticated]
    
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

class EmpresaListAPI(APIView):
    #permission_classes = [IsAuthenticated]
    def get(self, request):
        empresas = Empresa.objects.all().order_by("nome")
        return Response(EmpresaSerializer(empresas, many=True).data)
 
class AgendaEmpresaEventoAPI(APIView):
    def get(self, request, evento_id, empresa_id):
        empresa = Empresa.objects.get(id=empresa_id)

        mesas = Mesa.objects.filter(
            rodada__evento_id=evento_id
        ).filter(
            models.Q(comprador=empresa) | models.Q(vendedor=empresa)
        )

        serializer = MesaSerializer(mesas, many=True)
        return Response(serializer.data)


class EventoListAPI(APIView):
    #permission_classes = [IsAuthenticated]
    def get(self, request):
        eventos = Evento.objects.all().order_by("data")
        return Response(EventoSerializer(eventos, many=True).data)


class RodadaListAPI(APIView):
    #permission_classes = [IsAuthenticated]
    def get(self, request):
        rodadas = Rodada.objects.all().select_related("evento").order_by("inicio_ro")
        return Response(RodadaSerializer(rodadas, many=True).data)


class MesaListAPI(APIView):
    #permission_classes = [IsAuthenticated]
    def get(self, request):
        mesas = (
            Mesa.objects
            .select_related("rodada", "comprador", "vendedor")
            .order_by("rodada__inicio_ro")
        )
        return Response(MesaSerializer(mesas, many=True).data)
    