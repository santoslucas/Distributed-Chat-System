import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import jwt
from datetime import datetime
import json

SECRET_KEY = "my_secret_distributed_key"
ALGORITHM = "HS256"
DATABASE_URL = "sqlite:///./messages.db" 

Base = declarative_base()
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class MessageDB(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    sender = Column(String, index=True)
    recipient = Column(String, index=True)
    content = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Chat Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

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
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...), db: Session = Depends(get_db)):
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
                new_msg = MessageDB(sender=username, recipient=recipient, content=content)
                db.add(new_msg)
                db.commit()
                
                response_payload = json.dumps({"from": username, "msg": content})
                await manager.send_personal_message(response_payload, recipient)
                
                await websocket.send_text(json.dumps({"from": "Me", "to": recipient, "msg": content}))
                
    except WebSocketDisconnect:
        manager.disconnect(username)
    except Exception as e:
        print(f"Error: {e}")
        manager.disconnect(username)

@app.get("/history/{other_user}")
def get_history(other_user: str, token: str = Query(...), db: Session = Depends(get_db)):
    current_user = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM]).get("sub")
    
    messages = db.query(MessageDB).filter(
        ((MessageDB.sender == current_user) & (MessageDB.recipient == other_user)) |
        ((MessageDB.sender == other_user) & (MessageDB.recipient == current_user))
    ).order_by(MessageDB.timestamp).all()
    
    return messages

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)