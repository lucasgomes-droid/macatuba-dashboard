"""
RODAR UMA VEZ, LOCALMENTE, NO SEU COMPUTADOR (não no servidor/cloud).

Isso abre um Chrome de verdade, você faz login normalmente (Google + 2FA se
tiver) e, quando a tela do AppSheet aparecer carregada, volta aqui no
terminal e aperta ENTER. O script salva a sessão autenticada (cookies) em
storage_state.json — NÃO salva sua senha, só a sessão já logada.

O scraper.py (que roda no servidor, sem tela) reusa esse arquivo pra não
precisar fazer login de novo a cada sync. Quando a sessão expirar (o
AppSheet pode pedir login de novo depois de um tempo, ou o Google pode
pedir confirmação "é você mesmo?"), é só rodar este script de novo.

Uso:
    pip install playwright
    playwright install chromium
    python login_setup.py
"""
from pathlib import Path
from playwright.sync_api import sync_playwright

APP_URL = "https://www.appsheet.com/start/cbc846d6-e5b3-4820-828b-531f66c7093f"
STATE_PATH = Path(__file__).resolve().parent / "storage_state.json"


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto(APP_URL)

        print("\n>>> Faça login normalmente na janela do Chrome que abriu.")
        print(">>> Espere a tela do app 'ICC - Gestão Operacional' carregar de verdade.")
        input(">>> Quando estiver logado e vendo os dados, aperte ENTER aqui... ")

        context.storage_state(path=str(STATE_PATH))
        print(f"\nSessão salva em: {STATE_PATH}")
        print("Agora o scraper.py pode rodar sozinho, sem tela, reusando esse arquivo.")

        browser.close()


if __name__ == "__main__":
    main()
