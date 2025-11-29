import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import jwt
from datetime import datetime
from pymongo import MongoClient
import json
import os

SECRET_KEY = "my_secret_distributed_key"
ALGORITHM = "HS256"

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017/chat_database")

client = MongoClient(MONGO_URL)
db = client.get_database()
messages_collection = db["messages"]

app = FastAPI(title="Chat Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def format_message(message_doc) -> dict:
    return {
        "id": str(message_doc["_id"]),
        "sender": message_doc["sender"],
        "recipient": message_doc["recipient"],
        "content": message_doc["content"],
        "timestamp": message_doc["timestamp"].isoformat()
    }

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, username: str):
        await websocket.accept()
        self.active_connections[username] = websocket

    def disconnect(self, username: str):
        if username in self.active_connections:
            del self.active_connections[username]

    async def send_personal_message(self, message: str, recipient: str):
        if recipient in self.active_connections:
            await self.active_connections[recipient].send_text(message)

manager = ConnectionManager()

async def get_current_user(token: str = Query(...)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return username
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    try:
        username = await get_current_user(token)
    except:
        await websocket.close(code=1008)
        return

    await manager.connect(websocket, username)
    
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            recipient = message_data.get("to")
            content = message_data.get("msg")
            
            if recipient and content:
                new_msg = {
                    "sender": username,
                    "recipient": recipient,
                    "content": content,
                    "timestamp": datetime.utcnow()
                }
                messages_collection.insert_one(new_msg)
                
                response_payload = json.dumps({"from": username, "msg": content})
                await manager.send_personal_message(response_payload, recipient)
                
                await websocket.send_text(json.dumps({"from": "Me", "to": recipient, "msg": content}))
                
    except WebSocketDisconnect:
        manager.disconnect(username)
    except Exception as e:
        print(f"Error: {e}")
        manager.disconnect(username)

@app.get("/history/{other_user}")
def get_history(other_user: str, token: str = Query(...)):
    current_user = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM]).get("sub")
    
    query = {
        "$or": [
            {"sender": current_user, "recipient": other_user},
            {"sender": other_user, "recipient": current_user}
        ]
    }
    
    cursor = messages_collection.find(query).sort("timestamp", 1)
    
    messages = [format_message(msg) for msg in cursor]
    
    return messages

@app.get("/contacts")
def get_contacts(token: str = Query(...)):
    try:
        current_user = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM]).get("sub")
        
        sent_to = messages_collection.distinct("recipient", {"sender": current_user})
        
        received_from = messages_collection.distinct("sender", {"recipient": current_user})
        
        all_contacts = list(set(sent_to + received_from))
        
        if current_user in all_contacts:
            all_contacts.remove(current_user)
            
        return all_contacts
    except Exception as e:
        print(f"Contacts Error: {e}")
        return []

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)