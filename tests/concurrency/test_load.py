import pytest
import asyncio
import aiohttp
import websockets
import json
import time
import random
import os

AUTH_URL = os.getenv("AUTH_URL", "http://localhost:8000")

CHAT_HTTP_URL = os.getenv("CHAT_HTTP_URL", "http://localhost:8001")
CHAT_WS_URL = os.getenv("CHAT_URL", "ws://localhost:8001").replace("http", "ws") + "/ws"

NUM_USERS = 10
MSG_COUNT = 5

async def user_bot(user_id, session, stats):
    username = f"load_user_{user_id}"
    password = "password123"
    
    # 1. Tentar Registrar
    try:
        async with session.post(f"{AUTH_URL}/register", json={"username": username, "password": password}) as resp:
            # 201 = Criado, 400 = Já existe (Aceitável em testes repetidos)
            if resp.status not in [201, 400]:
                stats['errors'].append(f"{username}: Registro falhou status {resp.status}")
                return
    except Exception as e:
        stats['errors'].append(f"{username}: Exceção no Auth: {str(e)}")
        return

    # 2. Realizar Login
    token = None
    start_time = time.time()
    try:
        async with session.post(f"{AUTH_URL}/login", json={"username": username, "password": password}) as resp:
            if resp.status == 200:
                data = await resp.json()
                token = data.get("access_token")
                login_time = time.time() - start_time
                stats['login_times'].append(login_time)
            else:
                stats['errors'].append(f"{username}: Login falhou status {resp.status}")
                return
    except Exception as e:
        stats['errors'].append(f"{username}: Exceção no Login: {str(e)}")
        return

    # 3. Conectar ao WebSocket e Trocar Mensagens
    if token:
        uri = f"{CHAT_WS_URL}?token={token}"
        try:
            async with websockets.connect(uri) as websocket:

                recipient = f"load_user_{(user_id + 1) % NUM_USERS}"
                
                for i in range(MSG_COUNT):
                    msg_content = f"Carga {i} de {username}"
                    payload = json.dumps({"to": recipient, "msg": msg_content})
                    
                    send_start = time.time()
                    await websocket.send(payload)
                    
                    # Espera receber
                    try:
                        await asyncio.wait_for(websocket.recv(), timeout=2.0)
                        latency = time.time() - send_start
                        stats['msg_latencies'].append(latency)
                        stats['msgs_sent'] += 1
                    except asyncio.TimeoutError:
                        stats['errors'].append(f"{username}: Timeout esperando resposta")
                    
                    await asyncio.sleep(random.uniform(0.05, 0.2))
                    
        except Exception as e:
            stats['errors'].append(f"{username}: Erro WebSocket: {str(e)}")

@pytest.mark.asyncio
async def test_chat_load_simulation():
    """
    Testa a capacidade do sistema de suportar múltiplos usuários simultâneos.
    """
    stats = {
        'login_times': [],
        'msg_latencies': [],
        'msgs_sent': 0,
        'errors': []
    }
    
    print(f"\n--- Iniciando Carga: {NUM_USERS} Users x {MSG_COUNT} Msgs ---")
    
    async with aiohttp.ClientSession() as session:
        tasks = [user_bot(i, session, stats) for i in range(NUM_USERS)]
        await asyncio.gather(*tasks)

    # --- ASSERTIONS  ---
    
    # 1. Imprime erros
    if stats['errors']:
        print("\nErros encontrados:")
        for err in stats['errors'][:5]:
            print(f"- {err}")
        print(f"... e mais {len(stats['errors']) - 5} erros.")

    # 2. Verifica se pelo menos 90% dos usuários conseguiram logar
    total_logins = len(stats['login_times'])
    assert total_logins >= (NUM_USERS * 0.9), f"Muitas falhas de login! Apenas {total_logins}/{NUM_USERS} conseguiram."

    # 3. Verifica se mensagens foram trocadas
    expected_msgs = NUM_USERS * MSG_COUNT
    assert stats['msgs_sent'] >= (expected_msgs * 0.9), f"Perda de mensagens alta. Enviadas: {stats['msgs_sent']}/{expected_msgs}"

    # 4. Verifica Performance
    avg_login = sum(stats['login_times']) / total_logins
    assert avg_login < 1.0, f"Login muito lento! Média: {avg_login:.4f}s"

    # Verifica latência
    if stats['msg_latencies']:
        avg_latency = sum(stats['msg_latencies']) / len(stats['msg_latencies'])
        print(f"\nResultados Finais: Login Médio={avg_login:.4f}s | Latência Média={avg_latency:.4f}s")
        assert avg_latency < 0.5, f"Latência de mensagem alta! Média: {avg_latency:.4f}s"