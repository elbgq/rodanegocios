from core.models import Empresa, Rodada, Mesa
from django.db import transaction
from datetime import timedelta, datetime
from core.utils import empresas_tem_relacao
import math
import time



#====================================
# Esta função calcula a afinidade entre duas empresas com base nos interesses comuns que elas
# têm. Utilizada pelas views e não para gerar as rodadas.
#====================================
def calcular_afinidade(a, b):
    interesses_a = set(a.interesses.values_list("id", flat=True))
    interesses_b = set(b.interesses.values_list("id", flat=True))
    return len(interesses_a.intersection(interesses_b))

# Função 1 — gerar_pares_para_rodada (versão turbo + logs mínimos)
# Ela é um algoritmo de matchmaking que tenta montar pares comprador–vendedor
# para uma rodada de reuniões, respeitando várias regras e prioridades.
# Seu objetivo é gerar uma lista de pares (comprador, vendedor) para uma rodada, obedecendo:
# - limite de mesas (qtd_mesas)
# - evitar encontros repetidos
# - evitar empresas com relação prévia
# - garantir que vendedores atinjam um mínimo de participações
# - priorizar vendedores com menos participações
# - usar afinidades para melhorar a qualidade dos encontros

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
):
    # Guarda os pares formados e impede que um vendedor seja usado duas vezes na mesma rodada.
    pares = []
    usados_vendedores = set()

    # Para cada comprador, o algoritmo procura o melhor vendedor possível.
    for c in compradores:
        melhor = None
        melhor_score = -999999999

        # Para cada vendedor, ele verifica:
        # Regras de exclusão imediata
        # - já foi usado na rodada
        # - tem relação prévia com o comprador
        # - já se encontraram antes
        # - Se qualquer uma for verdadeira, ele ignora esse vendedor.
        
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

            # Aqui está o coração do matchmaking.
            # Ele começa com a afinidade como base, mas depois ajusta o score para garantir que:
            # - vendedores sem participações tenham prioridade máxima;
            # - vendedores que já atingiram o mínimo sejam penalizados para dar chance aos outros;
            # - vendedores que estão longe de atingir o mínimo e têm poucas rodadas restantes sejam fortemente priorizados.
            
            score = score_base
            # PRIORIDADE ABSOLUTA: vendedores sem nenhuma participação.
            # Isso garante que todos os vendedores tenham pelo menos uma reunião antes de qualquer um ter uma segunda.
            if participacoes == 0:
                score += 999999  # prioridade máxima
            
            # Evita que vendedores “populares” recebam encontros demais.
            # O que isso significa na prática:
            # - Se o vendedor já atingiu o mínimo → ele é despriorizado (penalidade de -10000).
            # - Se o vendedor ainda não atingiu → ele ganha um bônus (+1000).
            # -Se o vendedor corre risco de não atingir o mínimo → ele vira prioridade máxima (+100000).
            
            if participacoes >= minimo_por_vendedor:
                score -= 10000
            
            # Se o vendedor corre risco de não atingir o mínimo.
            # Se ele não for escolhido agora, não conseguirá bater a meta.
            else:
                score += 1000
                if faltam_para_minimo > rodadas_restantes:
                    score += 100000
            
            # O vendedor com maior score é selecionado.
            if score > melhor_score:
                melhor = e
                melhor_score = score
        # Registra o par formado e atualiza os estados para garantir que as regras sejam respeitadas nas próximas iterações.
        if melhor:
            pares.append((c, melhor))
            usados_vendedores.add(melhor.id)
            participacoes_vendedores[melhor.id] += 1
            encontros_previos[c.id].add(melhor.id)

        # Quando atinge o número de mesas, pára.
        if len(pares) >= qtd_mesas:
            break
    
    # Retorna uma lista de pares: (comprador, vendedor) para a rodada atual, formada de acordo com as regras e prioridades definidas.
    return pares

# Função 2 — gerar_todas_as_rodadas (versão turbo + mesa fixa + afinidades pré‑calculadas)
# Ela é a orquestradora geral do matchmaking: monta TODAS as rodadas, chama a função anterior
# para gerar os pares de cada rodada e cria os registros no banco.
# O que esta função faz?
# 1. Carrega compradores e vendedores do evento;
# 2. Define regras e estruturas de controle;
# 3. Calcula afinidades entre todos os compradores e vendedores;
# 4. Para cada rodada:
# - ordena vendedores por participações;
# - chama gerar_pares_para_rodada;
# - cria a rodada no banco;
# - cria as mesas no banco;
# - avança o horário;
# - aplica pausas se necessário.
# 5. Retorna a lista de rodadas criadas;
# É a função “mãe” que controla todo o processo.

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
    # Carrega compradores e vendedores do evento
    compradores = list(Empresa.objects.filter(
        modalidade="COMPRADOR",
        empresaevento__evento=evento,
        empresaevento__participa=True
    ).order_by("nome"))

    vendedores = list(Empresa.objects.filter(
        modalidade="VENDEDOR",
        empresaevento__evento=evento,
        empresaevento__participa=True
    ))
    
     # Define Mesa fixa por comprador. Assim, Cada comprador sempre fica na mesma mesa em todas as rodadas.
    mesa_por_comprador = {c.id: i for i, c in enumerate(compradores, start=1)}
    
    # Se não houver vendedores suficientes para preencher todas as mesas, o matchmaking não pode acontecer.
    if len(vendedores) < qtd_mesas:
        raise ValueError(
            f"Impossível completar todas as mesas: há apenas {len(vendedores)} vendedores para {qtd_mesas} mesas."
        )

    # Inicializa estruturas de controle
    # O mínimo de participações por vendedor é calculado para garantir que, mesmo que a distribuição seja desigual, todos tenham a chance de participar de um número razoável de rodadas.
    minimo_por_vendedor = max(1, math.ceil(qtd_rodadas / 2))
    # Contadores de participações para garantir que vendedores sejam distribuídos de forma justa.
    participacoes_vendedores = {v.id: 0 for v in vendedores}
    # Encontros prévios é um dicionário que, para cada comprador, mantém um conjunto de vendedores com quem ele já se encontrou em eventos anteriores. Isso é crucial para evitar repetições e garantir diversidade nos encontros.
    encontros_previos = {c.id: set() for c in compradores}

    # Carregar encontros anteriores dos eventos selecionados
    # Evitar repetições entre eventos selecionados e o evento atual
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
        # O que isso significa:
        # - Vendedores com 0 participações recebem prioridade absoluta.
        # - Vendedores com poucas participações aparecem primeiro na lista.
        # - Vendedores com muitas participações são naturalmente empurrados para o fim.
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

# Agora juntando tudo: como o score realmente é moldado.
# Quando o algoritmo avalia um vendedor para um comprador, ele faz algo assim:
# - Já se encontraram? → descarta imediatamente.
# - Vendedor já foi usado nesta rodada? → descarta.
# - Vendedor tem relação proibida com o comprador? → descarta.
# - Calcula score base pela afinidade → interesses em comum.
# - Aplica regras de distribuição justa
# - nunca participou? → prioridade máxima
# - participou pouco? → bônus
# - participou muito? → penalidade
# - corre risco de não atingir o mínimo? → prioridade altíssima
# - Escolhe o vendedor com maior score
