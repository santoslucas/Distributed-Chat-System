import pytest
from datetime import datetime
import mongomock
from unittest.mock import MagicMock, patch
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

with patch('pymongo.MongoClient', new=mongomock.MongoClient):
    from chat_service import format_message, messages_collection

def test_format_message_structure():
    """Testa se a função format_message retorna o dicionário correto"""
    mock_doc = {
        "_id": "507f1f77bcf86cd799439011",
        "sender": "alice",
        "recipient": "bob",
        "content": "Hello",
        "timestamp": datetime(2023, 1, 1, 12, 0, 0)
    }
    
    result = format_message(mock_doc)
    
    assert result["id"] == "507f1f77bcf86cd799439011"
    assert result["sender"] == "alice"
    assert result["timestamp"] == "2023-01-01T12:00:00"

def test_message_persistence():
    """Testa se conseguimos inserir e recuperar do banco mockado"""
    
    messages_collection.delete_many({})
    
    new_msg = {
        "sender": "user_a",
        "recipient": "user_b",
        "content": "Teste de persistência",
        "timestamp": datetime.utcnow()
    }
    
    insert_result = messages_collection.insert_one(new_msg)
    
    saved_msg = messages_collection.find_one({"_id": insert_result.inserted_id})
    
    assert saved_msg is not None
    assert saved_msg["content"] == "Teste de persistência"
    assert saved_msg["sender"] == "user_a"

def test_get_history_logic():
    """Simula a query de histórico entre dois usuários"""
    messages_collection.delete_many({})
    
    msg1 = {"sender": "alice", "recipient": "bob", "content": "Hi", "timestamp": datetime(2023, 1, 1)}
    msg2 = {"sender": "bob", "recipient": "alice", "content": "Hello", "timestamp": datetime(2023, 1, 2)}
    msg3 = {"sender": "alice", "recipient": "charlie", "content": "Ignored", "timestamp": datetime(2023, 1, 3)}
    
    messages_collection.insert_many([msg1, msg2, msg3])
    
    current_user = "alice"
    other_user = "bob"
    
    query = {
        "$or": [
            {"sender": current_user, "recipient": other_user},
            {"sender": other_user, "recipient": current_user}
        ]
    }
    
    cursor = messages_collection.find(query).sort("timestamp", 1)
    results = list(cursor)
    
    assert len(results) == 2
    assert results[0]["content"] == "Hi"
    assert results[1]["content"] == "Hello"

    assert all(r["recipient"] != "charlie" for r in results)