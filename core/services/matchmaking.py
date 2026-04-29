from core.models import Empresa, Rodada, Mesa
from django.db import transaction
from datetime import timedelta, datetime
from core.utils import empresas_tem_relacao
import math


#====================================
# Esta função calcula a afinidade entre duas pessoas com base nos interesses que elas
# têm em comum.
#====================================
def calcular_afinidade(a, b):
    interesses_a = set(a.interesses.values_list("id", flat=True))
    interesses_b = set(b.interesses.values_list("id", flat=True))
    return len(interesses_a.intersection(interesses_b))

#====================================
# Esta função implementa uma lógica de matching otimizado entre compradores e vendedores,
# respeitando os seguintes critérios:
# 1. Um comprador e um vendedor por mesa;
# 2. Os vendedores participam de uma mesa por rodada;
# 3. Empresas relacionadas não devem se encontrar;
# 4. Vendedores devem tem participação, no mínimo, de metade da quantidade de rodadas.
#=====================================
def gerar_pares_para_rodada(
    compradores,
    vendedores_disponiveis,
    qtd_mesas,
    participacoes_vendedores,
    minimo_por_vendedor,
    encontros_previos,
    rodada_atual,
    qtd_rodadas,
    log_rodada, # Para log
):
    matriz = []

    log_rodada.append(f"--- Rodada {rodada_atual} ---")
    log_rodada.append(f"Vendedores disponíveis: {[v.nome for v in vendedores_disponiveis]}")
    
    for c in compradores:
        for e in vendedores_disponiveis:

            motivo_exclusao = None
            
            # Critério 3: empresas relacionadas não podem se encontrar
            if empresas_tem_relacao(c.id, e.id):
                motivo_exclusao = "Bloqueado: empresas relacionadas"
            elif e.id in encontros_previos[c.id]:
                motivo_exclusao = "Bloqueado: repetição comprador–vendedor"

            # Critério 5: comprador não pode repetir vendedor em rodadas diferentes
            if motivo_exclusao:
                log_rodada.append(f"[X] {c.nome} → {e.nome}: {motivo_exclusao}")
                continue

            score_base = calcular_afinidade(c, e)
            participacoes = participacoes_vendedores[e.id]

            # quantas rodadas ainda faltam
            rodadas_restantes = qtd_rodadas - rodada_atual + 1
            faltam_para_minimo = max(0, minimo_por_vendedor - participacoes)

            score = score_base
            # vendedor já atingiu o mínimo
            if participacoes >= minimo_por_vendedor:
                # joga lá pra baixo, mas não exclui totalmente
                score -= 10000
                log_rodada.append(
                    f"[↓] {c.nome} → {e.nome}: vendedor já atingiu mínimo ({participacoes})"
                )
            else:
                # vendedor ainda não atingiu o mínimo
                score += 1000
                log_rodada.append(
                    f"[↑] {c.nome} → {e.nome}: vendedor abaixo do mínimo ({participacoes})"
                )
                
                # se ele está em risco de não conseguir mais atingir o mínimo,
                # dá prioridade ABSOLUTA
                if faltam_para_minimo > rodadas_restantes:
                    score += 100000
                    log_rodada.append(
                        f"[!!!] {c.nome} → {e.nome}: vendedor em risco de não atingir mínimo"
                    )

            matriz.append((c, e, score))

    # se não há nenhuma combinação possível, não força nada que quebre regras:
    # apenas retorna vazio e a rodada terá menos mesas
    matriz.sort(key=lambda x: x[2], reverse=True)

    log_rodada.append("Ordenação final por score:")
    for c, e, s in matriz:
        log_rodada.append(f"  {c.nome} → {e.nome}: score {s}")
        
    pares = []
    usados_compradores = set()
    usados_vendedores = set()

    for c, e, scores in matriz:
        if len(pares) >= qtd_mesas:
            break

        # Critério 2: vendedor só 1x por rodada
        if e.id in usados_vendedores:
            log_rodada.append(f"[X] {e.nome} já usado na rodada")
            continue

        # comprador só 1x por rodada
        if c.id in usados_compradores:
            log_rodada.append(f"[X] {c.nome} já usado na rodada")
            continue

        pares.append((c, e))
        usados_compradores.add(c.id)
        usados_vendedores.add(e.id)

        participacoes_vendedores[e.id] += 1
        encontros_previos[c.id].add(e.id)
        log_rodada.append(f"[OK] Par formado: {c.nome} ↔ {e.nome}")

    return pares, usados_vendedores


# ====================================
# Gera todas as rodadas do evento, controlando:
# - horários, pausas, mesas;
# - distribuição de vendedores ao longo das rodadas;
# - cumprimento dos critérios 1 a 7.
# ====================================
def gerar_todas_as_rodadas(
    evento,
    qtd_mesas,
    duracao_minutos,
    inicio_rodadas,
    intervalo_minutos,
    pausa_cada,
    pausa_duracao,
    qtd_rodadas,
):
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

    if len(vendedores) < qtd_mesas:
        raise ValueError(
            f"Impossível completar todas as mesas: há apenas {len(vendedores)} vendedores para {qtd_mesas} mesas."
        )

    minimo_por_vendedor = max(1, math.ceil(qtd_rodadas / 2))

    participacoes_vendedores = {v.id: 0 for v in vendedores}

    # encontros_previos: comprador_id -> set(vendedor_id)
    encontros_previos = {c.id: set() for c in compradores}

    rodadas_criadas = []

    horario_atual = datetime.combine(
        evento.data,
        datetime.strptime(inicio_rodadas, "%H:%M").time()
    )

    logs = {}  # rodada → lista de mensagens
    for numero_rodada in range(1, qtd_rodadas + 1):
        log_rodada = []
        logs[numero_rodada] = log_rodada
        
        vendedores_ordenados = sorted(
            vendedores, key=lambda v: participacoes_vendedores[v.id]
        )
        
        pares, _ = gerar_pares_para_rodada(
            compradores=compradores,
            vendedores_disponiveis=vendedores_ordenados,
            qtd_mesas=qtd_mesas,
            participacoes_vendedores=participacoes_vendedores,
            minimo_por_vendedor=minimo_por_vendedor,
            encontros_previos=encontros_previos,
            rodada_atual=numero_rodada,
            qtd_rodadas=qtd_rodadas,
            log_rodada=log_rodada, 
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

        for i, (comprador, vendedor) in enumerate(pares, start=1):
            Mesa.objects.create(
                rodada=rodada,
                numero=i,
                comprador=comprador,
                vendedor=vendedor
            )

        rodadas_criadas.append(rodada)

        horario_atual = fim_dt + timedelta(minutes=intervalo_minutos)

        if pausa_cada > 0 and numero_rodada % pausa_cada == 0:
            horario_atual += timedelta(minutes=pausa_duracao)

    return rodadas_criadas, logs


# Resumo: "É um algoritmo guloso + organizador de agenda, muito bem estruturado."


