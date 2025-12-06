import pytest
from playwright.sync_api import Page, expect

FRONTEND_URL = "http://localhost:8080" 

def test_frontend_login_flow(page: Page):
    """
    Testa se a página carrega, se o login libera a tela de chat
    e se elementos visuais aparecem.
    """
    # 1. Acessar a página
    page.goto(FRONTEND_URL)
    
    # Verifica se o título está correto
    expect(page).to_have_title("Distributed Chat System")
    
    # 2. Preencher Login (Usa um user aleatório ou fixo de teste)
    page.fill("#username", "frontend_user")
    page.fill("#password", "123456")
    
    # 3. Clicar no botão de Login
    # Configurar um listener para pegar o alert/dialogo se houver, ou esperar a mudança de DOM
    with page.expect_response(lambda response: "login" in response.url and response.status == 200):
        page.click("button:has-text('Login / Register')")

    # 4. Verificar se a tela de Chat apareceu (id="chat-box" perde o display:none)
    chat_box = page.locator("#chat-box")
    expect(chat_box).to_be_visible(timeout=5000)
    
    # 5. Verificar se o nome do usuário aparece no topo
    current_user_span = page.locator("#current-user")
    expect(current_user_span).to_have_text("frontend_user")

def test_frontend_send_message(page: Page):
    # Setup: Logar primeiro
    page.goto(FRONTEND_URL)
    page.fill("#username", "frontend_user_a")
    page.fill("#password", "123")
    page.click("button:has-text('Login')")
    page.locator("#chat-box").wait_for(state="visible")
    
    # 1. Selecionar destinatário
    page.fill("#recipient", "frontend_user_b")
    
    # 2. Digitar mensagem
    test_msg = "Hello from Playwright"
    page.fill("#message", test_msg)
    
    # 3. Enviar
    page.click("button:has-text('Send')")
    
    # 4. Verificar se a mensagem apareceu no log 
    chat_log = page.locator("#chat-log")
    expect(chat_log).to_contain_text(test_msg)