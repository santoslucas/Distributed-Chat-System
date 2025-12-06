import pytest
import httpx
import websockets
import json
import asyncio
import os
import uuid

AUTH_URL = os.getenv("AUTH_URL", "http://auth-service:8000")
CHAT_HTTP_URL = os.getenv("CHAT_URL_HTTP", "http://chat-service:8001")

CHAT_WS_URL = os.getenv("CHAT_URL_WS", "ws://chat-service:8001").replace("http", "ws") + "/ws"

@pytest.mark.asyncio
async def test_full_chat_flow():
    """
    Cenário:
    1. Registrar Usuário A (Alice) e Usuário B (Bob) no Auth Service.
    2. Logar com ambos para obter Tokens JWT.
    3. Alice e Bob conectam no WebSocket do Chat Service.
    4. Alice envia mensagem para Bob.
    5. Bob recebe a mensagem.
    6. Verificar se a mensagem foi salva no histórico via API.
    """
    
    # Gerar usuários
    run_id = str(uuid.uuid4())[:8]
    user_a = f"alice_{run_id}"
    user_b = f"bob_{run_id}"
    password = "secure_password"

    async with httpx.AsyncClient() as client:
        print(f"\n[1] Registrando usuários: {user_a} e {user_b}")
        resp_a = await client.post(f"{AUTH_URL}/register", json={"username": user_a, "password": password})
        assert resp_a.status_code == 201
        
        resp_b = await client.post(f"{AUTH_URL}/register", json={"username": user_b, "password": password})
        assert resp_b.status_code == 201

        print("[2] Realizando Login...")
        login_a = await client.post(f"{AUTH_URL}/login", json={"username": user_a, "password": password})
        assert login_a.status_code == 200
        token_a = login_a.json()["access_token"]

        login_b = await client.post(f"{AUTH_URL}/login", json={"username": user_b, "password": password})
        assert login_b.status_code == 200
        token_b = login_b.json()["access_token"]

    print("[3] Conectando aos WebSockets...")
    
    async with websockets.connect(f"{CHAT_WS_URL}?token={token_a}") as ws_a, \
               websockets.connect(f"{CHAT_WS_URL}?token={token_b}") as ws_b:
        
        msg_content = f"Hello Bob, this is integration test {run_id}"
        
        print(f"[4] Alice enviando mensagem: '{msg_content}'")
        payload = {
            "to": user_b,
            "msg": msg_content
        }
        await ws_a.send(json.dumps(payload))
        
        print("[5] Aguardando Bob receber...")
        received_msg_json = await ws_b.recv()
        received_data = json.loads(received_msg_json)
        
        assert received_data["from"] == user_a
        assert received_data["msg"] == msg_content
        print(" -> Bob recebeu com sucesso!")

    print("[6] Verificando histórico via API...")
    async with httpx.AsyncClient() as client:
        history_resp = await client.get(
            f"{CHAT_HTTP_URL}/history/{user_b}", 
            params={"token": token_a}
        )
        assert history_resp.status_code == 200
        history_data = history_resp.json()
        
        found = False
        for msg in history_data:
            if msg["content"] == msg_content and msg["sender"] == user_a:
                found = True
                break
        
        assert found is True, "A mensagem não foi encontrada no histórico persistido (MongoDB)"
        print(" -> Mensagem encontrada no MongoDB via API de histórico.")