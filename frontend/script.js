let token = "";
let ws = null;
let myUser = "";

async function login() {
    const u = document.getElementById('username').value;
    const p = document.getElementById('password').value;
    const status = document.getElementById('auth-status');
    
    status.innerText = "Attempting login/register...";

    try {
        let res = await fetch('http://localhost:8000/login', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({username: u, password: p})
        });
        
        if (res.status === 401) {
            status.innerText = "User not found, registering...";
            res = await fetch('http://localhost:8000/register', {
                method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({username: u, password: p})
            });
            if (res.status === 201) {
                status.innerText = "Registered! Logging in...";

                res = await fetch('http://localhost:8000/login', {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({username: u, password: p})
                });
            } else {
                throw new Error("Registration failed");
            }
        }

        const data = await res.json();
        if (data.access_token) {
            token = data.access_token;
            myUser = u;
            document.getElementById('auth-box').style.display = 'none';
            document.getElementById('chat-box').style.display = 'flex';
            document.getElementById('current-user').innerText = u;
            connectWS();
            loadContacts();
        }
    } catch(e) { 
        console.error(e);
        status.innerText = "Error: " + e.message; 
    }
}

async function loadContacts() {
    try {
        const res = await fetch(`http://localhost:8001/contacts?token=${token}`);
        const contacts = await res.json();
        const listDiv = document.getElementById('contact-list');
        listDiv.innerHTML = "";

        contacts.forEach(contact => {
            const div = document.createElement('div');
            div.className = 'contact-item';
            div.innerText = contact;
            div.onclick = () => selectContact(contact, div);
            listDiv.appendChild(div);
        });
    } catch(e) { console.error("Error loading contacts", e); }
}

function selectContact(name, element) {
    document.getElementById('recipient').value = name;
    
    document.querySelectorAll('.contact-item').forEach(el => el.classList.remove('active'));
    if(element) element.classList.add('active');

    loadHistory();
}

async function loadHistory() {
    const otherUser = document.getElementById('recipient').value;
    const log = document.getElementById('chat-log');
    if (!otherUser) return;

    log.innerHTML = '<div style="text-align:center; color:#888;">Loading...</div>';

    try {
        const res = await fetch(`http://localhost:8001/history/${otherUser}?token=${token}`);
        const messages = await res.json();
        log.innerHTML = '';
        messages.forEach(msg => {
            appendMessage(msg.sender, msg.content, msg.sender === myUser, msg.timestamp);
        });
    } catch (e) { log.innerHTML = 'Error loading history.'; }
}

function connectWS() {
    ws = new WebSocket(`ws://localhost:8001/ws?token=${token}`);
    ws.onmessage = function(event) {
        const data = JSON.parse(event.data);
        const isMe = data.from === "Me"; 
        const senderName = isMe ? myUser : data.from;
        
        const currentRecipient = document.getElementById('recipient').value;
        
        if (isMe || senderName === currentRecipient) {
            appendMessage(senderName, data.msg, isMe, new Date().toISOString());
        }
        
        if (!isMe) loadContacts();
    };
}

function sendMessage() {
    const recipient = document.getElementById('recipient').value;
    const msgInput = document.getElementById('message');
    const msg = msgInput.value;
    
    if (ws && recipient && msg) {
        ws.send(JSON.stringify({to: recipient, msg: msg}));
        msgInput.value = '';
        loadContacts(); 
    }
}

function handleEnter(e) {
    if (e.key === 'Enter') sendMessage();
}

function appendMessage(sender, text, isMe, timestamp) {
    const log = document.getElementById('chat-log');
    const div = document.createElement('div');
    const time = new Date(timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
    
    div.className = 'msg ' + (isMe ? 'sent' : 'received');
    div.innerHTML = `
        ${!isMe ? `<b>${sender}</b><br>` : ''}
        ${text}
        <span class="msg-meta">${time}</span>
    `;
    log.appendChild(div);
    log.scrollTop = log.scrollHeight;
}