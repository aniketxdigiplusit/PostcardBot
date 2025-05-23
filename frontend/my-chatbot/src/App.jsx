import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { marked } from 'marked';
import image from './postcard.png';
import bot from './postcard.png';


export default function App() {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [priority, setPriority] = useState('');
    const [priorityMessages, setPriorityMessages] = useState({});
    const [topLocations, setTopLocations] = useState([]);
    const [moreLocations, setMoreLocations] = useState([]);
    const [showAllLocations, setShowAllLocations] = useState(false);
    const [topActivities, setTopActivities] = useState([]);
    const [moreActivities, setMoreActivities] = useState([]);
    const [topProperties, setTopProperties] = useState([]);
    const [moreProperties, setMoreProperties] = useState([]);
    const [followups, setFollowups] = useState([]);





    const threadId = "245";

        
  
     useEffect(() => {
        const fetchWelcome = async () => {
            try {
                const res = await axios.get('http://localhost:5000/chat/startup-messages/welcome');
                const msg = res.data.response;
                setMessages(prev => {
                    if (prev.length === 0 || !prev.some(m => m.text === msg)) {
                        return [...prev, { sender: "bot", text: msg }];
                    }
                    return prev;
                });
            } catch (err) {
                console.error("Error fetching welcome message:", err);
            }
        };
    
        fetchWelcome();
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
    console.log("🟢 Backend returned:", res.data);


    const botResponse = res.data.response || "No response from LLM.";
    const followupSuggestions = res.data.followups || [];

    setMessages(prev => [...prev, { sender: "bot", text: botResponse }]);

    if (Array.isArray(followupSuggestions)) {
      setFollowups(followupSuggestions);
    } else {
      setFollowups([]);
    }

  } catch (err) {
    console.error("❌ Error:", err);
    setMessages(prev => [...prev, { sender: "bot", text: "Error talking to backend." }]);
    setFollowups([]);
  } finally {
    setLoading(false);
    setInput("");
  }
};


    const handleKeyPress = (e) => {
        if (e.key === 'Enter') handleSend();
    };

    // ✅ Trigger priority message on button click
    const handlePriorityClick = async (field) => {
        setPriority(field);
        try {
            const res = await axios.get(`http://localhost:5000/chat/startup-messages/${field}`);
            const msg = res.data.response;
            setMessages(prev => {
                if (prev.some(m => m.text === msg)) return prev; // prevent duplicates
                return [...prev, { sender: "bot", text: msg }];
            });
            
            if (field === "location" && res.data.top_locations) {
                setTopLocations(res.data.top_locations);
                setMoreLocations(res.data.more_locations || []);
                setShowAllLocations(false);
                setTopActivities([]);
                setTopProperties([]);
            } else if (field === "activities" && res.data.top_activities) {
                setTopActivities(res.data.top_activities);
                setMoreActivities(res.data.more_activities || []);
                setShowAllLocations(false);
                setTopLocations([]);
                setTopProperties([]);
            } else if (field === "properties" && res.data.top_properties) {
                setTopProperties(res.data.top_properties);
                setMoreProperties(res.data.more_properties || []);
                setShowAllLocations(false);
                setTopLocations([]);
                setTopActivities([]);
            }
                    } 
                    catch (error) {
            console.error("Failed to fetch priority message:", error);
        }
    };
    const handleLocationSelect = async (location) => {
        setMessages(prev => [...prev, { sender: "user", text: location }]);
        setTopLocations([]);
        setMoreLocations([]);
        setShowAllLocations(false);
        setLoading(true);
    
        try {
            const res = await axios.post(`http://localhost:5000/chat/${threadId}`, {
                query: location,
                priority_field: "location"
            });
    
            setMessages(prev => [...prev, { sender: "bot", text: res.data.response }]);
        } catch (err) {
            console.error("Error submitting location:", err);
            setMessages(prev => [...prev, { sender: "bot", text: "Failed to fetch results for this location." }]);
        } finally {
            setLoading(false);
        }
    };
    const handleSendFromButton = async (text) => {
  setMessages(prev => [...prev, { sender: "user", text }]);
  setLoading(true);

  try {
    const res = await axios.post(`http://localhost:5000/chat/${threadId}`, {
      query: text,
      priority_field: priority
    });

    setMessages(prev => [...prev, { sender: "bot", text: res.data.response }]);

    console.log("🔁 Response from backend:", res.data);

    if (res.data.followups && Array.isArray(res.data.followups)) {
      setFollowups(res.data.followups);
    } else {
      setFollowups([]);  // Clear old ones if not returned
    }

  } catch (err) {
    console.error("❌ Error sending button text:", err);
    setMessages(prev => [...prev, { sender: "bot", text: "Error processing your selection." }]);
    setFollowups([]);
  } finally {
    setLoading(false);
  }
};


    const handleFollowupClick = async (text) => {
  setMessages(prev => [...prev, { sender: "user", text }]);
  setLoading(true);

  try {
    const res = await axios.post(`http://localhost:5000/chat/${threadId}`, {
      query: text // ❌ No priority field here
    });

    const botResponse = res.data.chatbot_response || res.data.response || "No response from LLM.";
    const followupSuggestions = res.data.followups || [];

    setMessages(prev => [...prev, { sender: "bot", text: botResponse }]);
    setFollowups(followupSuggestions);  // 👈 update followups
  } catch (err) {
    console.error("❌ Error sending follow-up:", err);
    setMessages(prev => [...prev, { sender: "bot", text: "Error processing follow-up." }]);
  } finally {
    setLoading(false);
  }
};


    


    return (
        <div style={styles.container}>

            <div style={styles.navbar}>
                <div style={styles.navLeft}>
                    <img src={image} alt="Postcard Logo" style={styles.logo} />
                </div>
                <div style={styles.navRight}>
                    <a href="#" style={styles.navItem}>Wanderlust</a>
                    <a href="#" style={styles.navItem}>Stays</a>
                    <a href="#" style={styles.navItem}>Experiences</a>
                    <a href="#" style={styles.navItem}>Interests</a>
                    <a href="#" style={styles.navItem}>Destination Experts</a>
                    
                </div>
                <button style={styles.collectionBtn}>My Collection</button>
            </div>

        <div style={styles.page}>
        <div style={styles.mainWrapper}>
            <div style={styles.chatWrapper}>
                <h2 style={styles.header}>Postcard Travel Chatbot 🌍</h2>

                <div style={styles.chatBox}>
                {messages.map((msg, idx) => (
                <div key={idx} style={{
                    display: 'flex',
                    justifyContent: msg.sender === 'user' ? 'flex-end' : 'flex-start',
                    alignItems: 'flex-start',
                    marginBottom: '12px',
                }}>
                    {msg.sender === 'bot' && (
                    <div style={styles.iconWrapper}>
                        <img src={bot} alt="Bot" style={styles.icon} />
                    </div>
                    )}
                    <div style={{
                    ...styles.message,
                    backgroundColor: msg.sender === 'user' ? '#b69b7f' : '#fff6e5',
                    color: msg.sender === 'user' ? 'white' : '#5a4a3f',
                    }}>
                    <span
                        dangerouslySetInnerHTML={{ __html: marked.parse(msg.text) }}
                        style={{ display: 'inline-block', whiteSpace: 'pre-wrap' }}
                    />
                    </div>
                    {msg.sender === 'user' && (
                    <div style={styles.iconWrapper}>
                        <img src="/user-icon.png" alt="You" style={styles.icon} />
                    </div>
                    )}
                </div>
                ))}


                    {loading && <div style={styles.typing}>⏳ Bot is typing...</div>}

                    {followups.length > 0 && (
                    <div style={{ marginTop: '12px' }}>
                        <p style={{ fontWeight: 'bold', color: '#5a4a3f', fontFamily: "'Georgia', serif" }}>
                        
                        </p>
                        {followups.map((item, idx) => (
                        <button
                            key={idx}
                            onClick={() => handleSendFromButton(item)}
                            style={{
                            margin: '6px',
                            padding: '10px 18px',
                            borderRadius: '20px',
                            backgroundColor: '#ffffff',
                            border: '1px solid #ddd1c1',
                            color: '#5a4a3f',
                            cursor: 'pointer',
                            fontFamily: "'Georgia', serif",
                            transition: 'all 0.2s ease',
                            boxShadow: '0 2px 6px rgba(0,0,0,0.04)',
                            opacity: 0,
                            animation: `fadeInUp 0.4s ease ${idx * 0.1}s forwards`
                            }}
                        >
                            {item}
                        </button>
                        ))}
                    </div>
                    )}


                    {topLocations.length > 0 && (
                        <div style={{ marginTop: '12px' }}>
                            <p style={{ fontWeight: 'bold', color: '#5a4a3f', fontFamily: "'Georgia', serif" }}>
                                ✨ Here are some destinations you can start exploring:
                            </p>
                            {[...(showAllLocations ? [...topLocations, ...moreLocations] : topLocations)].map((loc, idx) => (
                            <button
                                key={idx}
                                onClick={() => handleLocationSelect(loc)}
                                style={{
                                margin: '6px',
                                padding: '10px 18px',
                                borderRadius: '20px',
                                backgroundColor: '#ffffff',
                                border: '1px solid #ddd1c1',
                                color: '#5a4a3f',
                                cursor: 'pointer',
                                fontFamily: "'Georgia', serif",
                                transition: 'all 0.2s ease',
                                boxShadow: '0 2px 6px rgba(0,0,0,0.04)',
                                opacity: 0,
                                animation: `fadeInUp 0.4s ease ${idx * 0.1}s forwards`,
                                }}
                            >
                                {loc}
                            </button>
                            ))}
                            {!showAllLocations && moreLocations.length > 0 && (
                                <button
                                    onClick={() => setShowAllLocations(true)}
                                    style={{
                                        margin: '6px',
                                        padding: '10px 18px',
                                        borderRadius: '20px',
                                        backgroundColor: '#ffffff',
                                        border: '1px dashed #b69b7f',
                                        color: '#5a4a3f',
                                        fontStyle: 'italic',
                                        cursor: 'pointer',
                                        fontFamily: "'Georgia', serif",
                                        transition: 'all 0.2s',
                                    }}
                                >
                                    Show More
                                </button>
                            )}

                        </div>
                    )}
                    {topActivities.length > 0 && (
                    <div style={{ marginTop: '12px' }}>
                        <p style={{ fontWeight: 'bold', color: '#5a4a3f', fontFamily: "'Georgia', serif" }}>
                        🌿 What kind of experiences interest you?
                        </p>
                        {[...(showAllLocations ? [...topActivities, ...moreActivities] : topActivities)].map((activity, idx) => (
                        <button
                            key={idx}
                            onClick={() => handleSendFromButton(activity)}
                            style={{
                            margin: '6px',
                            padding: '10px 18px',
                            borderRadius: '20px',
                            backgroundColor: '#ffffff',
                            border: '1px solid #ddd1c1',
                            color: '#5a4a3f',
                            cursor: 'pointer',
                            fontFamily: "'Georgia', serif",
                            transition: 'all 0.2s ease',
                            boxShadow: '0 2px 6px rgba(0,0,0,0.04)',
                            opacity: 0,
                            animation: `fadeInUp 0.4s ease ${idx * 0.1}s forwards`,
                            }}
                        >
                            {activity}
                        </button>
                        ))}
                        {!showAllLocations && moreActivities.length > 0 && (
                        <button
                            onClick={() => setShowAllLocations(true)}
                            style={{
                            margin: '6px',
                            padding: '10px 18px',
                            borderRadius: '20px',
                            backgroundColor: '#ffffff',
                            border: '1px dashed #b69b7f',
                            color: '#5a4a3f',
                            fontStyle: 'italic',
                            cursor: 'pointer',
                            fontFamily: "'Georgia', serif",
                            transition: 'all 0.2s',
                            }}
                        >
                            Show More
                        </button>
                        )}
                    </div>
                    )}
                    {topProperties.length > 0 && (
                    <div style={{ marginTop: '12px' }}>
                        <p style={{ fontWeight: 'bold', color: '#5a4a3f', fontFamily: "'Georgia', serif" }}>
                        🏨 What kind of stays are you curious about?
                        </p>
                        {[...(showAllLocations ? [...topProperties, ...moreProperties] : topProperties)].map((prop, idx) => (
                        <button
                            key={idx}
                            onClick={() => handleSendFromButton(prop)}
                            style={{
                            margin: '6px',
                            padding: '10px 18px',
                            borderRadius: '20px',
                            backgroundColor: '#ffffff',
                            border: '1px solid #ddd1c1',
                            color: '#5a4a3f',
                            cursor: 'pointer',
                            fontFamily: "'Georgia', serif",
                            transition: 'all 0.2s ease',
                            boxShadow: '0 2px 6px rgba(0,0,0,0.04)',
                            opacity: 0,
                            animation: `fadeInUp 0.4s ease ${idx * 0.1}s forwards`,
                            }}
                        >
                            {prop}
                        </button>
                        ))}
                        {!showAllLocations && moreProperties.length > 0 && (
                        <button
                            onClick={() => setShowAllLocations(true)}
                            style={{
                            margin: '6px',
                            padding: '10px 18px',
                            borderRadius: '20px',
                            backgroundColor: '#ffffff',
                            border: '1px dashed #b69b7f',
                            color: '#5a4a3f',
                            fontStyle: 'italic',
                            cursor: 'pointer',
                            fontFamily: "'Georgia', serif",
                            transition: 'all 0.2s',
                            }}
                        >
                            Show More
                        </button>
                        )}
                    </div>
                    )}
                    

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
                <h4 style={styles.sidebarTitle}>Guide your journey by telling me what matters most:</h4>
                <p style={{
                    fontSize: '0.95rem',
                    marginBottom: '12px',
                    color: '#7a6a58',
                    lineHeight: 1.5,
                    fontFamily: "'Georgia', serif"
                }}>
                    Choose what you'd like me to prioritize first while planning your travel discovery —
                    whether you're drawn to stunning <strong>locations</strong>, soulful <strong>properties</strong>,
                    immersive <strong>experiences</strong>, or inspiring <strong>postcards</strong>.
                </p>
                {["properties", "location", "postcards", "activities"].map((field) => (
                    <button
                        key={field}
                        onClick={() => handlePriorityClick(field)}
                        style={{
                            ...styles.priorityButton,
                            backgroundColor: priority === field ? '#b69b7f' : '#fffaf2',
                            color: priority === field ? '#fff' : '#5a4a3f',
                            borderColor: priority === field ? '#b69b7f' : '#d3c0ab',
                            textTransform: 'capitalize',
                            transition: 'all 0.2s ease-in-out'
                        }}
                    >
                        {field.charAt(0).toUpperCase() + field.slice(1)}
                    </button>
                ))}
             </div>
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
        width: '95%',
        height: '92%',
        backgroundColor: '#f9f4ef',
        borderRadius: '16px',
        boxShadow: '0 10px 30px rgba(0,0,0,0.1)',
    },
    chatWrapper: {
        flex: 3,
        display: 'flex',
        flexDirection: 'column',
        padding: '10px',
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
        marginBottom: '18px'
    },
    chatBox: {
        flex: 1,
        backgroundColor: '#f5ebe0',
        borderRadius: '12px',
        padding: '10px',
        overflowY: 'auto',
        marginBottom: '20px',
        border: '1px solid #e0d6c5'
    },
    message: {
        padding: '14px 20px',
        borderRadius: '20px',
        margin: '10px 0',
        display: 'inline-block',
        maxWidth: '75%',
        fontSize: '1rem',
        fontFamily: "'Georgia', serif",
        backgroundColor: '#fffaf1',
        color: '#3e3e3e',
        boxShadow: '0 1px 4px rgba(0,0,0,0.05)',
    }
    ,
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
    },
    navbar: {
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '12px 32px',
        backgroundColor: '#fffaf2',
        borderBottom: '1px solid #e8dccc',
        fontFamily: "'Georgia', serif",
        boxShadow: '0 2px 6px rgba(0,0,0,0.05)',
      },
      navLeft: {
        display: 'flex',
        alignItems: 'center',
      },
      logo: {
        height: '42px',
        marginRight: '20px',
      },
      navRight: {
        display: 'flex',
        justifyContent: 'center',
        display: 'flex',
        gap: '20px',
        alignItems: 'center',
        flex: 1,
      },
      navItem: {
        color: '#007bff',
        fontWeight: '550',
        fontSize: '1.2rem',
        textDecoration: 'none',
        transition: 'color 0.3s ease',
        fontFamily: "'Georgia', serif",
      },
      collectionBtn: {
        alignItems: 'left',
        justifyContent: 'left',
        backgroundColor: '#007bff',
        color: '#fff',
        padding: '8px 16px',
        borderRadius: '20px',
        fontWeight: 'bold',
        border: 'none',
        cursor: 'pointer',

      },
      container: {
        display: 'flex',
        flexDirection: 'column',
        height: '100vh',
        width: '100vw',
        backgroundColor: '#f9f4ef',
      },

      iconWrapper: {
        width: '40px',
        height: '45px',
        borderRadius: '55%',
        overflow: 'hidden',
        margin: '0 15px',
        flexShrink: 0
      },
      icon: {
        width: '100%',
        height: '100%',
        objectFit: 'cover',
        borderRadius: '50%'
      }
      
      
   

};
