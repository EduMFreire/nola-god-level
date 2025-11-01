import streamlit as st
import pandas as pd
import sqlalchemy

from settings import *
from utilities import *

# Conexão com o banco de dados
@st.cache_resource
def get_db_engine():
    db_url = "postgresql://challenge:challenge_2024@localhost:5432/challenge_db"
    engine = sqlalchemy.create_engine(db_url)
    return engine

class Main:
    'Representa toda a página'
    def load_data(self, query):
        'Faz uma query e retorna um DataFrame com o resultado'
        try:
            with self.engine.connect() as connection:
                df = pd.read_sql(query, connection)
            return df
        except Exception as e:
            if DEBUG_SHOW_ERROR_MESSAGES: st.error(f"Erro ao conectar com o banco de dados: {e}")
            return pd.DataFrame() # Retorna DF vazio em caso de erro

    def __init__(self):
        'Constrói toda a página'
        # Configuração da Página e layout da aplicação
        st.set_page_config(
            page_title="Nola Analytics",
            page_icon="🍔",
            layout="wide"
        )

        st.title("🍔 Nola God-Level Analytics")
        st.write("Análise de dados de vendas para a Dona Maria.")

        # Pegar a engine do SQL
        self.engine = get_db_engine()

        # BARRA LATERAL (FILTROS)
        self.selected_stores, self.selected_channels, self.start_date, self.end_date = self.build_sidebar()

        # ABAS PRINCIPAIS
        self.tab_overview, self.tab_products = st.tabs(["Visão Geral", "Análise de Produtos"])
        
        self.build_tab_overview()
        self.build_tab_products()

    def build_sidebar(self):
        '''
        Constrói a barra lateral da página, e retorna o input dado nela.
        Isto é, retorna uma tupla (selected_stores: list, selected_channels: list, start_date: str, end_date: str)
        '''

        st.sidebar.header("Filtros Globais")
        # Carrega dados para os filtros (ex: lista de lojas)
        # Esta query só roda uma vez graças ao cache
        stores_df = self.load_data("SELECT id, name FROM stores ORDER BY name")
        stores_list = stores_df['name'].tolist()

        channels_df = self.load_data("SELECT id, name FROM channels ORDER BY name")
        channels_list = channels_df['name'].tolist()

        # Widgets de Filtro
        selected_stores = st.sidebar.multiselect(
            "Lojas:",
            options=stores_list,
            help="Deixe em branco para selecionar todas as lojas."
        )

        selected_channels = st.sidebar.multiselect(
            "Canais:",
            options=channels_list,
            help="Deixe em branco para selecionar todos os canais."
        )

        # Selecionar nada significa selecionar tudo
        if selected_stores == []: selected_stores = stores_list
        if selected_channels == []: selected_channels = channels_list

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

        return selected_stores, selected_channels, start_date, end_date

    def get_where_sql(self):
        'Constrói a cláusula WHERE baseada nos filtros e retorna'
        assert len(self.selected_stores) > 0
        assert len(self.selected_stores) > 0

        # Lógica de Query
        
        # Se self.selected_stores estiver vazio, o que quero?
        where_clauses = [
            f"st.name IN ({', '.join([f"'{s}'" for s in self.selected_stores])})",
            f"ch.name IN ({', '.join([f"'{c}'" for c in self.selected_channels])})",
            f"s.created_at BETWEEN '{self.start_date}' AND '{self.end_date}'"
        ]

        # Junta com 'AND' se houver filtros
        where_sql = " AND ".join(where_clauses)
        if where_sql:
            where_sql = "WHERE " + where_sql

        return where_sql

    def build_tab_overview(self):
        where_sql = self.get_where_sql()

        with self.tab_overview:
            st.header("Visão Geral de Performance")

            # --- Exemplo de Query para KPIs ---
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
                AND s.sale_status_desc = 'COMPLETED'
            """

            kpi_data = self.load_data(kpi_query)

            if not kpi_data.empty:
                # Pega a primeira (e única) linha dos resultados
                kpis = kpi_data.iloc[0]

                # --- Mostra os KPIs ---
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Faturamento Total", format_money(kpis['faturamento_total']))
                col2.metric("Total de Vendas", f"{kpis['total_vendas']} vendas")
                col3.metric("Ticket Médio", format_money(kpis['ticket_medio']))
                col4.metric("Tempo de Entrega", format_time(kpis['avg_tempo_entrega_min']))
            else:
                st.warning("Nenhum dado encontrado para os filtros selecionados.")

            # --- Gráfico de Linha (Exemplo) ---
            st.subheader("Faturamento por Dia")
            chart_query = f"""
                SELECT
                    DATE(s.created_at) as dia,
                    SUM(s.total_amount) as faturamento
                FROM sales s
                JOIN stores st ON s.store_id = st.id
                JOIN channels ch ON s.channel_id = ch.id
                {where_sql}
                AND s.sale_status_desc = 'COMPLETED'
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
        where_sql = self.get_where_sql()

        with self.tab_products:
            st.header("Análise de Produtos")

            st.write("Top produtos baseados nos filtros globais.")

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
                AND s.sale_status_desc = 'COMPLETED'
                GROUP BY p.name
                ORDER BY faturamento_produto DESC
                LIMIT 50
            """

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

Main()