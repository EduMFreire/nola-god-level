def format_money(x):
    'x é um número ou None. Retorna uma string representando uma quantidade de dinheiro.'
    if x == None: return 'R$ 0.00'
    else:
        return f'R$ {x:.2f}'
    
def format_time(x):
    'x é um número ou None. Retorna uma string'
    if x == None: return '-'
    else:
        return f'{x:.1f} min'