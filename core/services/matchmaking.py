from core.models import Empresa, Rodada, Mesa
from django.db import transaction
from datetime import timedelta, datetime
from core.utils import empresas_tem_relacao
import math
import time



#====================================
# Esta função calcula a afinidade entre duas empresas com base nos interesses que elas
# têm em comum. Utilizada pelas views e não para gerar as rodadas.
#====================================
def calcular_afinidade(a, b):
    interesses_a = set(a.interesses.values_list("id", flat=True))
    interesses_b = set(b.interesses.values_list("id", flat=True))
    return len(interesses_a.intersection(interesses_b))

# Função 1 — gerar_pares_para_rodada (versão turbo + logs mínimos)
def gerar_pares_para_rodada(
    compradores,
    vendedores_disponiveis, 
    qtd_mesas,
    participacoes_vendedores,
    minimo_por_vendedor,
    encontros_previos,
    rodada_atual,
    qtd_rodadas,
    afinidades,
    #log_rodada
):
    pares = []
    usados_vendedores = set()

    # log_rodada.append(f"Rodada {rodada_atual}")

    for c in compradores:
        melhor = None
        melhor_score = -999999999

        for e in vendedores_disponiveis:

            if e.id in usados_vendedores:
                continue
            if empresas_tem_relacao(c.id, e.id):
                continue
            if e.id in encontros_previos[c.id]:
                continue

            score_base = afinidades[(c.id, e.id)]

            # cálculo rápido do score
            participacoes = participacoes_vendedores[e.id]
            rodadas_restantes = qtd_rodadas - rodada_atual + 1
            faltam_para_minimo = max(0, minimo_por_vendedor - participacoes)

            score = score_base
            if participacoes >= minimo_por_vendedor:
                score -= 10000
            else:
                score += 1000
                if faltam_para_minimo > rodadas_restantes:
                    score += 100000

            if score > melhor_score:
                melhor = e
                melhor_score = score

        if melhor:
            pares.append((c, melhor))
            usados_vendedores.add(melhor.id)
            participacoes_vendedores[melhor.id] += 1
            encontros_previos[c.id].add(melhor.id)

            #log_rodada.append(f"{c.nome} ↔ {melhor.nome}")

        if len(pares) >= qtd_mesas:
            break

    return pares

# Função 2 — gerar_todas_as_rodadas (versão turbo + mesa fixa + afinidades pré‑calculadas)

def gerar_todas_as_rodadas(
    evento,
    qtd_mesas,
    duracao_minutos,
    inicio_rodadas,
    intervalo_minutos,
    pausa_cada,
    pausa_duracao,
    qtd_rodadas,
    eventos_anteriores=None,
):
    compradores = list(Empresa.objects.filter(
        modalidade="COMPRADOR",
        empresaevento__evento=evento,
        empresaevento__participa=True
    ).order_by("nome"))

    # mesa fixa por comprador
    mesa_por_comprador = {c.id: i for i, c in enumerate(compradores, start=1)}

    vendedores = list(Empresa.objects.filter(
        modalidade="VENDEDOR",
        empresaevento__evento=evento,
        empresaevento__participa=True
    ))
    
    if len(vendedores) < qtd_mesas:
        raise ValueError(
            f"Impossível completar todas as mesas: há apenas {len(vendedores)} vendedores para {qtd_mesas} mesas."
        )

    minimo_por_vendedor = max(1, math.ceil(qtd_rodadas / 2))

    participacoes_vendedores = {v.id: 0 for v in vendedores}
    
    encontros_previos = {c.id: set() for c in compradores}

    # carregar encontros anteriores dos eventos selecionados
    if eventos_anteriores is not None and eventos_anteriores.exists():
        encontros_anteriores = (
            Mesa.objects
            .filter(
                comprador__in=compradores,
                vendedor__in=vendedores,
                rodada__evento__in=eventos_anteriores,
            )
            .values_list("comprador_id", "vendedor_id")
            .distinct()
        )
        for comprador_id, vendedor_id in encontros_anteriores:
            encontros_previos[comprador_id].add(vendedor_id)
        
    # 🔥 Pré-carrega interesses (zero queries depois disso)
    interesses_compradores = {
        c.id: set(c.interesses.values_list("id", flat=True))
        for c in compradores
    }

    interesses_vendedores = {
        v.id: set(v.interesses.values_list("id", flat=True))
        for v in vendedores
    }

    # 🔥 Pré-calcula afinidades (apenas 2006 cálculos)
    afinidades = {
        (c.id, v.id): len(interesses_compradores[c.id] & interesses_vendedores[v.id])
        for c in compradores
        for v in vendedores
    }

    rodadas_criadas = []
    #logs = {}

    horario_atual = datetime.combine(
        evento.data,
        datetime.strptime(inicio_rodadas, "%H:%M").time()
    )

    for numero_rodada in range(1, qtd_rodadas + 1):
        #log_rodada = []
        #logs[numero_rodada] = log_rodada

        vendedores_ordenados = sorted(
            vendedores, key=lambda v: participacoes_vendedores[v.id]
        )

        pares = gerar_pares_para_rodada(
            compradores,
            vendedores_ordenados,
            qtd_mesas,
            participacoes_vendedores,
            minimo_por_vendedor,
            encontros_previos,
            numero_rodada,
            qtd_rodadas,
            afinidades,
            #log_rodada
        )

        inicio = horario_atual.time()
        fim_dt = horario_atual + timedelta(minutes=duracao_minutos)
        fim = fim_dt.time()

        rodada = Rodada.objects.create(
            evento=evento,
            nome=f"Rodada {numero_rodada}",
            duracao=duracao_minutos,
            inicio_ro=inicio,
            fim_ro=fim
        )

        for comprador, vendedor in pares:
            Mesa.objects.create(
                rodada=rodada,
                numero=mesa_por_comprador[comprador.id],
                comprador=comprador,
                vendedor=vendedor
            )

        rodadas_criadas.append(rodada)

        horario_atual = fim_dt + timedelta(minutes=intervalo_minutos)

        if pausa_cada > 0 and numero_rodada % pausa_cada == 0:
            horario_atual += timedelta(minutes=pausa_duracao)

    return rodadas_criadas
