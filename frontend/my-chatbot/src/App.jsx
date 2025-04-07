import React, { useState, useEffect } from 'react';
import axios from 'axios';

export default function App() {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [priority, setPriority] = useState('');

    const threadId = "104"; // ✅ hardcoded thread ID
     // 🟡 Greet user on first load
     useEffect(() => {
        const greeting = `
🌟 Welcome to **Postcard Travel Club** – your gateway to conscious luxury travel! 🌟

At Postcard Travel, we believe that travel should be both indulgent and responsible. Our mission is to connect discerning travelers with boutique properties and immersive experiences that celebrate local cultures, histories, and environments, all while promoting responsible tourism. 

✨ **What We Offer:**
- **Curated Stays:** Discover over 200 boutique luxury properties across 30+ countries, each offering unique and authentic experiences.
- **Immersive Experiences:** Engage in activities that allow you to connect deeply with the communities and landscapes you visit, ensuring your travels are meaningful and impactful.
- **Community Connections:** Join a global network of conscious luxury travelers, travel designers, storytellers, and boutique properties dedicated to advancing responsible tourism. 

Whether you're seeking a serene retreat in the Mayan jungle, an adventurous horseback ride in Chile, or an opportunity to meet the Maasai warriors in Kenya, Postcard Travel is here to curate your perfect journey. 

Begin your exploration by sharing your travel aspirations with us. Let's craft experiences that not only fulfill your wanderlust but also contribute positively to the places and people you encounter.

🌍 **Start your conscious luxury journey with Postcard Travel today!**
        `;
        setMessages([{ sender: "bot", text: greeting }]);
    }, []);


    const handleSend = async () => {
        if (!input.trim()) return;

        // Show user message immediately
        setMessages(prev => [...prev, { sender: "user", text: input }]);
        setLoading(true);

        try {
            const res = await axios.post(`http://localhost:5000/chat/${threadId}`, {
                query: input,
                priority_field: priority  // ✅ correct priority value
            });
            console.log("Priority before sending:", priority);


            const botResponse = res.data.response || "No response from LLM.";
            setMessages(prev => [...prev, { sender: "bot", text: botResponse }]);
        } catch (err) {
            console.error("❌ Error sending message:", err);
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
        <div style={{ padding: "20px", fontFamily: "sans-serif", maxWidth: "600px", margin: "auto" }}>
            {/* Header */}
            <h2 style={{ background: "#2f80ed", color: "white", padding: "10px", borderRadius: "4px" }}>Postcard Chatbot</h2>

            {/* Chat */}
            <div style={{ border: "1px solid #ccc", padding: "10px", height: "400px", overflowY: "auto", marginBottom: "10px" }}>
                {messages.map((msg, idx) => (
                    <div key={idx} style={{ textAlign: msg.sender === 'user' ? 'right' : 'left', marginBottom: "8px" }}>
                        <div style={{
                            display: "inline-block",
                            padding: "8px 12px",
                            backgroundColor: msg.sender === 'user' ? "#2f80ed" : "#e0e0e0",
                            color: msg.sender === 'user' ? "#fff" : "#000",
                            borderRadius: "12px"
                        }}>
                            {msg.text}
                        </div>
                    </div>
                ))}
                {loading && <div>Bot is typing...</div>}
            </div>

            {/* Input */}
            <div style={{ display: "flex", marginBottom: "10px" }}>
                <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={handleKeyPress}
                    placeholder="Type a message..."
                    style={{ flex: 1, padding: "10px", borderRadius: "4px", border: "1px solid #ccc" }}
                />
                <button
                    onClick={handleSend}
                    style={{ marginLeft: "8px", padding: "10px 16px", backgroundColor: "#2f80ed", color: "#fff", border: "none", borderRadius: "4px" }}
                >
                    Send
                </button>
            </div>

            {/* Containers */}
            <div style={{ display: "flex", justifyContent: "space-between" }}>
                {["properties", "location", "postcards", "activities"].map((field) => (
                    <div
                        key={field}
                        onClick={() => setPriority(field)}
                        style={{
                            flex: 1,
                            margin: "4px",
                            padding: "8px",
                            background: priority === field ? "#2f80ed" : "#f0f0f0",
                            color: priority === field ? "white" : "black",
                            textAlign: "center",
                            borderRadius: "6px",
                            cursor: "pointer",
                            border: "1px solid #ccc"
                        }}
                    >
                        {field}
                    </div>
                ))}
            </div>
        </div>
    );
}
