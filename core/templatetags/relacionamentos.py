from django import template

register = template.Library()

@register.filter
def tipo_relacao_para(relacionamento, empresa):
    """
    Retorna o tipo de relacionamento do ponto de vista da empresa informada.
    """
    tipo = relacionamento.tipo_relacao

    inversoes = {
        "CLIENTE": "FORNECEDOR",
        "FORNECEDOR": "CLIENTE",
        "PARCEIRO": "PARCEIRO",
        "NEGOCIARAM": "NEGOCIARAM",
    }

    # Se a empresa é a empresa A, mantém o tipo original
    if relacionamento.empresa_a == empresa:
        tipo_final = tipo
    else:
        tipo_final = inversoes.get(tipo, tipo)

    # Retorna o label bonito
    return dict(relacionamento.TIPOS).get(tipo_final, tipo_final)
