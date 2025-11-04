import streamlit as st
import pandas as pd
import sqlalchemy

from settings import *
from utilities import *

@st.cache_resource
def get_db_engine():
    'Cria a conexão com o banco de dados'
    db_url = "postgresql://challenge:challenge_2024@localhost:5432/challenge_db"
    engine = sqlalchemy.create_engine(db_url)
    return engine

@st.cache_data
def load_data(_engine, query):
    '''
    Faz uma query e retorna um DataFrame com o resultado.
    
    O decorador cache_data faz com que, caso a função seja chamada com o mesmo query, o resultado seja o mesmo, sem fazer a query de novo. Ou seja, asssumimos que o banco de dados não muda ao longo da execução do app.

    _engine, devido ao _, é ignorado (se a função for chamada com a mesma query, mas _engine diferente, o resultado será o mesmo). Isso não é um problema neste projeto, pois temos apenas uma única engine.
    '''

    assert isinstance(_engine, sqlalchemy.Engine)

    try:
        with _engine.connect() as connection:
            df = pd.read_sql(query, connection)
        return df
    except Exception as e:
        if SHOW_ERROR_MESSAGES: st.error(f"Erro ao conectar com o banco de dados: {e}")
        return pd.DataFrame() # Retorna DF vazio em caso de erro

class Main:
    'Representa toda a página'

    def __init__(self):
        'Constrói toda a página'
        # Configuração da Página e layout da aplicação
        st.set_page_config(
            page_title="Nola Analytics",
            page_icon="🍔",
            layout="wide"
        )

        st.title("SaborBI")
        st.write("Análise de dados de restaurantes.")

        # Pegar a engine do SQL
        self.engine = get_db_engine()

        # Construir listas com todos os produtos, canais, lojas...
        stores_df = self.load_data("SELECT id, name FROM stores ORDER BY name")
        self.stores_list = stores_df['name'].tolist()

        products_df = self.load_data("SELECT id, name FROM products ORDER BY name")
        self.products_list = products_df['name'].tolist()

        channels_df = self.load_data("SELECT id, name FROM channels ORDER BY name")
        self.channels_list = channels_df['name'].tolist()

        status_df = self.load_data("SELECT DISTINCT sale_status_desc FROM sales")
        # .dropna() remove qualquer status nulo que possa ter sido gerado
        self.status_list = status_df['sale_status_desc'].dropna().tolist()

        # BARRA LATERAL (FILTROS)
        self.selected_stores, self.selected_products, self.selected_channels, self.selected_statuses, self.selected_day_numbers, self.start_date, self.end_date, self.time_start, self.time_end = self.build_sidebar()

        # ABAS PRINCIPAIS
        self.tab_overview, self.tab_products, self.tab_stores = st.tabs(["Visão geral", "Análise de produtos", "Análise de lojas"])
        
        self.build_tab_overview()
        self.build_tab_products()
        self.build_tab_stores()

    def load_data(self, query):
        return load_data(self.engine, query)

    def build_sidebar(self):
        '''
        Constrói a barra lateral da página, e retorna uma tupla com o input dado nela.
        '''

        st.sidebar.header("Filtros globais")
        # Carrega dados para os filtros (ex: lista de lojas)

        stores_list = self.stores_list
        products_list = self.products_list
        channels_list = self.channels_list

        # Widgets de Filtro
        selected_stores = st.sidebar.multiselect(
            "Lojas:",
            options=stores_list,
            help="Deixe em branco para selecionar todas as lojas.",
            placeholder='Escolha lojas'
        )
        selected_products = st.sidebar.multiselect(
            "Produtos:",
            options = products_list,
            help="Filtra para considerar apenas as vendas contendo os produtos selecionados. O faturamento de outros produtos vendidos nessas mesmas vendas continua sendo considerado. Deixe em branco para selecionar todos os produtos.",
            placeholder='Escolha produtos'
        )
        selected_channels = st.sidebar.multiselect(
            "Canais:",
            options=channels_list,
            help="Deixe em branco para selecionar todos os canais.",
            placeholder='Escolha canais'
        )

        selected_statuses = st.sidebar.multiselect(
            "Status da Venda:",
            options=self.status_list,
            default=['COMPLETED'], # Começa mostrando apenas vendas completas
            placeholder="Selecione os status de venda",
            help='O "faturamento" de vendas canceladas é o preço hipotético da venda, caso se concretizasse.'
        )

        selected_day_names = st.sidebar.multiselect(
            "Dias da semana:",
            options=WEEK_DAYS_MAP.keys(),
            help="Deixe em branco para selecionar todos os dias.",
            placeholder="Escolha dias da semana"
        )

        # Selecionar nada significa selecionar tudo
        if selected_stores == []: selected_stores = stores_list
        if selected_products == []: selected_products = products_list
        if selected_channels == []: selected_channels = channels_list
        if selected_statuses == []: selected_statuses = self.status_list
        if selected_day_names == []:
            selected_day_numbers = list(WEEK_DAYS_MAP.values())
        else:
            selected_day_numbers = [WEEK_DAYS_MAP[k] for k in selected_day_names]

        # Filtro de data
        dates = st.sidebar.date_input(
            "Período:",
            value=(pd.to_datetime(MIN_DATE), pd.to_datetime('today')), # Exemplo
            min_value=pd.to_datetime(MIN_DATE),
            max_value=pd.to_datetime('today')
        ) # Se o range foi selecionado totalmente, dates é uma tupla start_date, end_date. Senão, é uma tupla com apenas o start_date

        if len(dates) == 0:
            start_date = pd.to_datetime(MIN_DATE)
            end_date = pd.to_datetime('today')
        elif len(dates) == 1:
            start_date = dates[0]
            end_date = pd.to_datetime('today')
        else:
            start_date = dates[0]
            end_date = dates[1]

        # Filtro de horário
        time_range_start, time_range_end = st.sidebar.slider(
            "Intervalo de horário:",
            min_value=0,
            max_value=24,
            value=(0, 24), # Default: (00:00, 24:00)
            format="%d:00h", # Formata os labels do slider
        )

        # Para debug: mostra os filtros selecionados
        if DEBUG_SHOW_FILTERS:
            st.sidebar.subheader("Debug Info")
            st.sidebar.write("Filtros Ativos:")
            st.sidebar.json({
                "lojas": selected_stores,
                "canais": selected_channels,
                "data_inicio": str(start_date),
                "data_fim": str(end_date)
            })

        return selected_stores, selected_products, selected_channels, selected_statuses, selected_day_numbers, start_date, end_date, time_range_start, time_range_end

    def get_where_sql(self):
        'Constrói a cláusula WHERE baseada nos filtros e retorna. Assume que nenhum filtro está vazio (aplicamos a lógica empty=all para garantir isso nos demais métodos)'
        assert len(self.selected_stores) > 0
        assert len(self.selected_stores) > 0

        # Lógica de Query
        # Pega a lista total de produtos para comparar
        all_products_list = self.products_list

        where_clauses = [
            f"st.name IN ({', '.join([f"'{s}'" for s in self.selected_stores])})",
            f"ch.name IN ({', '.join([f"'{c}'" for c in self.selected_channels])})",
            f"s.created_at BETWEEN '{self.start_date}' AND '{self.end_date}'",
            f"EXTRACT(HOUR FROM s.created_at) BETWEEN {self.time_start} AND {self.time_end - 1}" # Subtraímos 1 porque BETWEEN é inclusivo
        ]

        # Só adiciona o filtro de produto se o usuário NÃO selecionou "todos"
        if len(self.selected_products) != len(all_products_list):
            # Constrói a subquery
            product_filter_subquery = f"""
                s.id IN (
                    SELECT DISTINCT ps.sale_id
                    FROM product_sales ps
                    JOIN products p ON ps.product_id = p.id
                    WHERE p.name IN ({', '.join([f"'{p}'" for p in self.selected_products])})
                )
            """
            where_clauses.append(product_filter_subquery)

        if len(self.selected_day_numbers) < 7:
            dias_sql_list = ','.join(map(str, self.selected_day_numbers))
            where_clauses.append(f"EXTRACT(DOW FROM s.created_at) IN ({dias_sql_list})")

        if len(self.selected_statuses) != len(self.status_list):
            # Se o usuário selecionou algo, filtre por isso
            status_sql_list = ', '.join([f"'{s}'" for s in self.selected_statuses])
            where_clauses.append(f"s.sale_status_desc IN ({status_sql_list})")

        # Junta com 'AND' se houver filtros
        where_sql = "WHERE " + " AND ".join(where_clauses)
        return where_sql

    def build_tab_overview(self):
        'Constrói a aba de visão geral.'
        where_sql = self.get_where_sql()

        with self.tab_overview:
            st.header("Visão geral de performance")

            # Exemplo de Query para KPIs
            kpi_query = f"""
                SELECT
                    COUNT(s.id) as total_vendas,
                    SUM(s.total_amount) as faturamento_total,
                    AVG(s.total_amount) as ticket_medio,
                    AVG(s.delivery_seconds / 60.0) as avg_tempo_entrega_min
                FROM sales s
                JOIN stores st ON s.store_id = st.id
                JOIN channels ch ON s.channel_id = ch.id
                {where_sql}
            """

            kpi_data = self.load_data(kpi_query)

            if not kpi_data.empty:
                # Pega a primeira (e única) linha dos resultados
                kpis = kpi_data.iloc[0]

                # --- Mostra os KPIs ---
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Faturamento total", format_money(kpis['faturamento_total']))
                col2.metric("Total de vendas", f"{kpis['total_vendas']:.0f} vendas")
                col3.metric("Ticket médio", format_money(kpis['ticket_medio']))
                col4.metric("Tempo de entrega", format_time(kpis['avg_tempo_entrega_min']))
            else:
                st.warning("Nenhum dado encontrado para os filtros selecionados.")

            # Gráfico de Linha
            st.subheader("Faturamento por dia")
            chart_query = f"""
                SELECT
                    DATE(s.created_at) as dia,
                    SUM(s.total_amount) as faturamento
                FROM sales s
                JOIN stores st ON s.store_id = st.id
                JOIN channels ch ON s.channel_id = ch.id
                {where_sql}
                GROUP BY dia
                ORDER BY dia
            """
            chart_data = self.load_data(chart_query)

            if not chart_data.empty:
                chart_data = chart_data.set_index('dia')
                st.line_chart(chart_data)
            else:
                st.warning("Nenhum dado para o gráfico.")

    def build_tab_products(self):
        'Constrói a aba de análise de produtos'
        where_sql = self.get_where_sql()

        with self.tab_products:
            st.header("Análise de produtos")

            st.write("Principais produtos baseados nos filtros globais.")

            product_query = f"""
                SELECT
                    p.name as produto,
                    COUNT(ps.id) as quantidade_vendida,
                    SUM(ps.total_price) as faturamento_produto
                FROM product_sales ps
                JOIN products p ON ps.product_id = p.id
                JOIN sales s ON ps.sale_id = s.id
                JOIN stores st ON s.store_id = st.id
                JOIN channels ch ON s.channel_id = ch.id
                {where_sql}
                GROUP BY p.name
                ORDER BY faturamento_produto DESC
            """
            if LIMIT_LIST_VIEW:
                product_query += f"\nLIMIT {LIMIT_LIST_VIEW_AMOUNT}"

            product_data = self.load_data(product_query)

            if not product_data.empty:
                st.dataframe(product_data, use_container_width=True)

                # Botão de Exportar (Critério 4)
                st.download_button(
                    label="Exportar Relatório de Produtos (CSV)",
                    data=product_data.to_csv(index=False).encode('utf-8'),
                    file_name='relatorio_produtos.csv',
                    mime='text/csv',
                )
            else:
                st.warning("Nenhum produto encontrado para os filtros selecionados.")

    def build_tab_stores(self):
        'Constrói a aba de análise de lojas.'
        where_sql = self.get_where_sql()

        with self.tab_stores:
            st.header("Análise de lojas")
            st.write("Performance das lojas baseada nos filtros globais.")

            # Query SQL focada em agrupar por loja
            store_query = f"""
                SELECT
                    st.name as loja,
                    COUNT(s.id) as total_vendas,
                    SUM(s.total_amount) as faturamento_total,
                    AVG(s.total_amount) as ticket_medio,
                    AVG(s.delivery_seconds / 60.0) as avg_tempo_entrega_min
                FROM sales s
                JOIN stores st ON s.store_id = st.id
                JOIN channels ch ON s.channel_id = ch.id
                {where_sql}
                GROUP BY st.name
                ORDER BY faturamento_total DESC
            """
            
            if LIMIT_LIST_VIEW:
                store_query += f"\nLIMIT {LIMIT_LIST_VIEW_AMOUNT}"

            store_data = self.load_data(store_query)

            if not store_data.empty:
                # Exibe os dados da loja
                st.dataframe(store_data, use_container_width=True)

                # Botão de Exportar (Critério 4)
                st.download_button(
                    label="Exportar Relatório de Lojas (CSV)",
                    data=store_data.to_csv(index=False).encode('utf-8'),
                    file_name='relatorio_lojas.csv',
                    mime='text/csv',
                )
            else:
                st.warning("Nenhuma loja encontrada para os filtros selecionados.")

Main()