import React, { useState, useEffect } from 'react';
import axios from 'axios';

export default function App() {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [priority, setPriority] = useState('');
    const threadId = "117";

    useEffect(() => {
        const greeting = `
🌟 Welcome to **Postcard Travel Club** – your gateway to conscious luxury travel! 🌟

At Postcard Travel, we believe that travel should be both indulgent and responsible. Our mission is to connect discerning travelers with boutique properties and immersive experiences that celebrate local cultures, histories, and environments, all while promoting responsible tourism.

✨ **What We Offer:**
- **Curated Stays**
- **Immersive Experiences**
- **Community Connections**

🌍 Start your conscious luxury journey today!
        `;
        setMessages([{ sender: "bot", text: greeting }]);
    }, []);

    const handleSend = async () => {
        if (!input.trim()) return;

        setMessages(prev => [...prev, { sender: "user", text: input }]);
        setLoading(true);

        try {
            const res = await axios.post(`http://localhost:5000/chat/${threadId}`, {
                query: input,
                priority_field: priority
            });

            const botResponse = res.data.response || "No response from LLM.";
            setMessages(prev => [...prev, { sender: "bot", text: botResponse }]);
        } catch (err) {
            console.error("❌ Error:", err);
            setMessages(prev => [...prev, { sender: "bot", text: "Error talking to backend." }]);
        } finally {
            setLoading(false);
            setInput("");
        }
    };

    const handleKeyPress = (e) => {
        if (e.key === 'Enter') handleSend();
    };

    return (
        <div style={styles.page}>
            <div style={styles.mainWrapper}>
                <div style={styles.chatWrapper}>
                    <h2 style={styles.header}>Postcard Travel Chatbot 🌍</h2>

                    <div style={styles.chatBox}>
                        {messages.map((msg, idx) => (
                            <div key={idx} style={{ textAlign: msg.sender === 'user' ? 'right' : 'left' }}>
                                <div style={{
                                    ...styles.message,
                                    backgroundColor: msg.sender === 'user' ? '#b69b7f' : '#fff6e5',
                                    color: msg.sender === 'user' ? 'white' : '#5a4a3f',
                                }}>
                                    {msg.text}
                                </div>
                            </div>
                        ))}
                        {loading && <div style={styles.typing}>⏳ Bot is typing...</div>}
                    </div>

                    <div style={styles.inputArea}>
                        <input
                            type="text"
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={handleKeyPress}
                            placeholder="Ask about properties, locations, experiences..."
                            style={styles.input}
                        />
                        <button onClick={handleSend} style={styles.sendButton}>Send</button>
                    </div>
                </div>

                <div style={styles.prioritySidebar}>
                    <h4 style={styles.sidebarTitle}>Filter by:</h4>
                    {["properties", "location", "postcards", "activities"].map((field) => (
                        <button
                            key={field}
                            onClick={() => setPriority(field)}
                            style={{
                                ...styles.priorityButton,
                                backgroundColor: priority === field ? '#b69b7f' : '#fffaf2',
                                color: priority === field ? '#fff' : '#5a4a3f',
                                borderColor: priority === field ? '#b69b7f' : '#d3c0ab'
                            }}
                        >
                            {field.charAt(0).toUpperCase() + field.slice(1)}
                        </button>
                    ))}
                </div>
            </div>
        </div>
    );
}

const styles = {
    page: {
        width: '100vw',
        height: '100vh',
        backgroundColor: '#f9f4ef',
        fontFamily: "'Georgia', serif",
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        overflow: 'hidden',
    },
    mainWrapper: {
        display: 'flex',
        width: '90%',
        height: '90%',
        backgroundColor: '#f9f4ef',
        borderRadius: '16px',
        boxShadow: '0 10px 30px rgba(0,0,0,0.1)',
    },
    chatWrapper: {
        flex: 3,
        display: 'flex',
        flexDirection: 'column',
        padding: '20px',
    },
    prioritySidebar: {
        flex: 1,
        borderLeft: '1px solid #e0d6c5',
        padding: '20px',
        backgroundColor: '#f5ebe0',
        borderTopRightRadius: '16px',
        borderBottomRightRadius: '16px',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'flex-start',
        gap: '12px',
    },
    sidebarTitle: {
        fontSize: '1rem',
        fontWeight: 'bold',
        marginBottom: '8px',
        color: '#5a4a3f'
    },
    header: {
        textAlign: 'center',
        color: '#5a4a3f',
        fontSize: '2rem',
        fontWeight: 600,
        marginBottom: '16px'
    },
    chatBox: {
        flex: 1,
        backgroundColor: '#f5ebe0',
        borderRadius: '12px',
        padding: '20px',
        overflowY: 'auto',
        marginBottom: '20px',
        border: '1px solid #e0d6c5'
    },
    message: {
        padding: '12px 18px',
        borderRadius: '20px',
        margin: '8px 0',
        display: 'inline-block',
        maxWidth: '75%',
        fontSize: '1rem',
        whiteSpace: 'pre-wrap',
        lineHeight: 1.5,
    },
    typing: {
        fontStyle: 'italic',
        color: '#8e7b6c',
        marginTop: '12px',
    },
    inputArea: {
        display: 'flex',
        gap: '10px',
        alignItems: 'center',
    },
    input: {
        flex: 1,
        padding: '14px 16px',
        borderRadius: '10px',
        border: '1px solid #c1b1a0',
        fontSize: '1rem',
        backgroundColor: '#fffaf2',
        color: '#4b3f36'
    },
    sendButton: {
        backgroundColor: '#b69b7f',
        color: 'white',
        border: 'none',
        padding: '14px 20px',
        borderRadius: '10px',
        cursor: 'pointer',
        fontWeight: 'bold'
    },
    priorityButton: {
        padding: '10px 14px',
        borderRadius: '8px',
        border: '2px solid',
        fontWeight: 'bold',
        cursor: 'pointer',
        fontSize: '0.95rem',
        width: '100%',
        textAlign: 'left',
    }
};
