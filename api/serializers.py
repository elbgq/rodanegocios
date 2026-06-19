from rest_framework import serializers
from core.models import Mesa, Empresa, Rodada, Evento


class EmpresaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Empresa
        fields = ['id', 'nome', 'modalidade']
  
class EventoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Evento
        fields = ['id', 'nome', 'data', 'local']

class RodadaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rodada
        fields = ['id', 'nome', 'evento', 'inicio_ro', 'fim_ro']


class MesaSerializer(serializers.ModelSerializer):
    comprador = EmpresaSerializer(read_only=True)
    vendedor = EmpresaSerializer(read_only=True)
    rodada = RodadaSerializer(read_only=True)
    evento = serializers.SerializerMethodField()

    class Meta:
        model = Mesa
        fields = [
            'id',
            'numero',
            'comprador',
            'vendedor',
            'rodada',
            'evento',
            'status'
        ]
    def get_evento(self, obj):
        return EventoSerializer(obj.rodada.evento).data

