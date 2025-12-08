const Chat = (
    async function getUser() {
        const token = getToken();
        if (!token) return;
        try {
            const resp = await fetch('/api/me', { headers: { 'Authorization': 'Bearer ' + token } });
            if (resp.ok) {
                const data = await resp.json();
                return data;
            }
        } catch (e) { /* swallow */ }
    },
    function getChat() {
        getUser();
        question = document.getElementById('question').value;
        // Take API key from database
        API_Key = createRuntimeKey();
        fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + API_Key
            },
            body: JSON.stringify({
                'messages': [
                    {
                        'role': 'user',
                        'content': question
                    }
                ]
            })
        })

    }           
)
    

    
