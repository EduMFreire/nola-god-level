O projeto é um sistema de análise de dados de restaurantes, o qual oferece filtros customizáveis usando a biblioteca Streamlit em Python.

# Como executar o programa...

## Primeiro: ligar o SQL
```bash
docker compose up -d postgres
```
(assumindo que os dados já foram gerados)

## Segundo: baixar as dependências do app
```bash
pip install -r "app_requirements.txt"
```

Se for conveniente, pode-se fazer isso dentro de um ambiente virtual Python.
```bash
python -m venv "venv"
call "venv\Scripts\activate.bat"
pip install -r "app_requirements.txt"
```

## Terceiro: executar o app com o Streamlit
```bash
streamlit run App/app.py
```
Ou, se estivermos seguindo a abordagem do ambiente virual Python
```bash
call "venv\Scripts\activate.bat"
streamlit run App/app.py
```

Esses comandos, com a abordagem do ambiente virtual, estão em setup.bat e run.bat, respectivamente.