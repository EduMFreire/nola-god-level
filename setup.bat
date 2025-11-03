REM Rodar uma vez para configurar o projeto.

REM Ligar o SQL (presumindo que os dados ja foram gerados).
docker compose up -d postgres

REM Verifica se a pasta venv ja existe. Se nao, cria.
if not exist "venv" (
    echo Criando ambiente virtual (venv)...
    python -m venv "venv"
) else (
    echo Ambiente virtual (venv) ja existe.
)

REM Ativa o venv e instala as bibliotecas. O 'call' e importante para que o script continue apos a ativacao.
call "venv\Scripts\activate.bat"

REM Baixar os requirements do app.
pip install -r "app_requirements.txt"

REM Depois, podemos rodar o streamlit run App/app.py de run.bat sempre que quisermos rodar o app.