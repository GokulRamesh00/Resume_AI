import React, { useState, useRef, useEffect } from 'react';
import { MessageSquare, Send, PlusCircle, Settings, LogOut, FileText, FileUp, Check } from 'lucide-react';
import { Button } from './components/ui/button';
import { Input } from './components/ui/input';

const RAGInterface = () => {
  const [file, setFile] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const fileInputRef = useRef(null);
  const [activeChat, setActiveChat] = useState(null);
  const [savedChats, setSavedChats] = useState([]);
  const [uploadSuccess, setUploadSuccess] = useState(false);
  
  // Example questions
  const exampleQuestions = [
    {
      id: 1,
      text: "How can I improve my resume for a software engineering position?"
    },
    {
      id: 2,
      text: "What skills should I highlight for a marketing role?"
    },
    {
      id: 3,
      text: "Can you suggest better wording for my job responsibilities?"
    }
  ];

  // Preset chats
  const presetChats = [
    {
      id: 1,
      icon: <MessageSquare size={16} />,
      text: "Job application tips"
    },
    {
      id: 2,
      icon: <FileText size={16} />,
      text: "Resume review"
    },
    {
      id: 3,
      icon: <MessageSquare size={16} />,
      text: "Interview preparation"
    }
  ];

  // Load saved chats from localStorage on component mount
  useEffect(() => {
    const storedChats = localStorage.getItem('savedChats');
    if (storedChats) {
      setSavedChats(JSON.parse(storedChats));
    }
  }, []);

  const handleFileUpload = async (event) => {
    const uploadedFile = event.target.files[0];
    if (!uploadedFile) return;
    
    setFile(uploadedFile);
    setIsLoading(true);
    setUploadSuccess(false);

    const formData = new FormData();
    formData.append('file', uploadedFile);

    try {
      const response = await fetch('http://localhost:5000/upload', {
        method: 'POST',
        body: formData,
      });
      const data = await response.json();
      console.log(data.message);
      setUploadSuccess(true);
      
      // Clear the current chat and show a confirmation message
      setMessages([{
        text: `Resume "${uploadedFile.name}" uploaded successfully! You can now ask questions about it.`,
        sender: 'bot'
      }]);
      
      // Clear the active chat since we have a new resume
      setActiveChat(null);
    } catch (error) {
      console.error('Error uploading file:', error);
      setMessages([{
        text: `Error uploading resume. Please try again.`,
        sender: 'bot'
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSendMessage = async () => {
    if (inputMessage.trim() === '') return;

    const newMessage = { text: inputMessage, sender: 'user' };
    const updatedMessages = [...messages, newMessage];
    setMessages(updatedMessages);
    setInputMessage('');
    setIsLoading(true);

    try {
      const response = await fetch('http://localhost:5000/query', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query: inputMessage }),
      });
      const data = await response.json();
      
      // If this is a new chat, create a title based on the first message
      if (!activeChat && savedChats.findIndex(chat => chat.id === activeChat) === -1) {
        const newChatTitle = inputMessage.length > 30 
          ? inputMessage.substring(0, 30) + "..." 
          : inputMessage;
        
        const newChatId = Date.now();
        const newChat = {
          id: newChatId,
          title: newChatTitle,
          messages: updatedMessages,
          lastUpdated: new Date().toISOString()
        };
        
        const updatedSavedChats = [newChat, ...savedChats];
        setSavedChats(updatedSavedChats);
        setActiveChat(newChatId);
        localStorage.setItem('savedChats', JSON.stringify(updatedSavedChats));
      }
      
      // Add the bot response directly instead of simulating typing
      const botResponse = { text: data.response, sender: 'bot' };
      const finalMessages = [...updatedMessages, botResponse];
      setMessages(finalMessages);
      
      // Update the saved chat with the bot response
      if (activeChat) {
        const updatedSavedChats = savedChats.map(chat => {
          if (chat.id === activeChat) {
            return { ...chat, messages: finalMessages, lastUpdated: new Date().toISOString() };
          }
          return chat;
        });
        setSavedChats(updatedSavedChats);
        localStorage.setItem('savedChats', JSON.stringify(updatedSavedChats));
      }
    } catch (error) {
      console.error('Error sending message:', error);
      setMessages([...updatedMessages, { 
        text: "Sorry, I couldn't process your request. Please try again.", 
        sender: 'bot' 
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleNewChat = () => {
    setMessages([]);
    setActiveChat(null);
  };

  const handleExampleQuestion = (question) => {
    setInputMessage(question);
  };

  // Function to generate interview questions based on the resume
  const generateInterviewQuestions = async () => {
    setIsLoading(true);
    try {
      // First check server status
      const statusResponse = await fetch('http://localhost:5000/status');
      const statusData = await statusResponse.json();
      console.log("Server status:", statusData);
      
      // Use the specialized interview_questions endpoint
      const response = await fetch('http://localhost:5000/interview_questions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({})
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        console.error("Error response:", errorData);
        return ["There was an error generating questions based on your resume. Please try again later."];
      }
      
      const data = await response.json();
      
      if (data.error) {
        console.error("Error in response:", data.error);
        return ["There was an error generating questions. The system might be busy, please try again."];
      }
      
      // Parse the response to get individual questions
      let questionsText = data.response;
      let questions = [];
      
      // Try to split the response into individual questions
      if (questionsText.includes('1.')) {
        // Format likely includes numbered list
        questions = questionsText.split(/\d+\./).filter(q => q.trim()).map(q => q.trim());
      } else if (questionsText.includes('\n-')) {
        // Format includes bullet points with dashes
        questions = questionsText.split('\n-').filter(q => q.trim()).map(q => q.trim());
      } else if (questionsText.includes('\n•')) {
        // Format includes bullet points with dots
        questions = questionsText.split('\n•').filter(q => q.trim()).map(q => q.trim());
      } else {
        // Default: split by newlines and hope for the best
        questions = questionsText.split('\n').filter(q => q.trim()).map(q => q.trim());
      }
      
      // If we couldn't parse it well, just use the whole text
      if (questions.length < 2) {
        questions = [questionsText];
      }
      
      return questions;
    } catch (error) {
      console.error('Error generating interview questions:', error);
      return [
        "Unable to generate interview questions at this time.",
        "This could be due to server issues or Redis connection problems.",
        "Please try using the regular chat interface to ask about interview questions instead."
      ];
    } finally {
      setIsLoading(false);
    }
  };

  const handlePresetChat = async (chatId) => {
    setActiveChat(`preset-${chatId}`);
    setMessages([]);
    
    // Handle special preset chat types
    if (chatId === 3) { // Interview preparation
      if (!file && !uploadSuccess) {
        setMessages([{ 
          text: "Please upload your resume first to get personalized interview questions.", 
          sender: 'bot' 
        }]);
        return;
      }
      
      setIsLoading(true);
      setMessages([{ 
        text: "Generating personalized interview questions based on your resume...", 
        sender: 'bot' 
      }]);
      
      // Generate questions based on the resume
      const questions = await generateInterviewQuestions();
      
      // Create messages for each question
      const systemMessage = { 
        text: "Based on your resume, here are some interview questions you might be asked:", 
        sender: 'bot' 
      };
      
      const questionsList = questions.map(q => ({ 
        text: `• ${q}`, 
        sender: 'bot' 
      }));
      
      setMessages([systemMessage, ...questionsList]);
      setIsLoading(false);
    } else if (chatId === 2) { // Resume review
      if (!file && !uploadSuccess) {
        setMessages([{ 
          text: "Please upload your resume first to get a review.", 
          sender: 'bot' 
        }]);
        return;
      }
      
      setMessages([{ 
        text: "I've analyzed your resume. What specific aspects would you like me to review? For example: formatting, content, achievements, or overall impression?", 
        sender: 'bot' 
      }]);
    } else if (chatId === 1) { // Job application tips
      setMessages([{ 
        text: "I can help with your job application! Do you have a specific role or company in mind? Or would you like general tips for applications?", 
        sender: 'bot' 
      }]);
    }
  };
  
  const handleSavedChatClick = (chatId) => {
    const chat = savedChats.find(c => c.id === chatId);
    if (chat) {
      setMessages(chat.messages || []);
      setActiveChat(chatId);
    }
  };
  
  const handleDeleteChat = (chatId, e) => {
    e.stopPropagation();
    const updatedChats = savedChats.filter(chat => chat.id !== chatId);
    setSavedChats(updatedChats);
    localStorage.setItem('savedChats', JSON.stringify(updatedChats));
    
    if (activeChat === chatId) {
      setMessages([]);
      setActiveChat(null);
    }
  };

  return (
    <div className="flex h-screen bg-white">
      {/* Left Sidebar */}
      <div className="w-64 bg-[#1e1e2e] text-white flex flex-col">
        {/* New Chat Button */}
        <div className="p-4">
          <button
            onClick={handleNewChat}
            className="w-full flex items-center justify-center gap-2 bg-[#2d2d3d] hover:bg-[#3d3d4d] py-2 px-3 rounded-md text-sm font-medium"
          >
            <PlusCircle size={16} />
            New Chat
          </button>
        </div>

        {/* Saved Chats */}
        <div className="flex-1 overflow-y-auto px-2 space-y-1">
          {/* Preset Chats */}
          {presetChats.map((chat) => (
            <button
              key={`preset-${chat.id}`}
              onClick={() => handlePresetChat(chat.id)}
              className={`w-full flex items-center gap-2 py-2 px-3 rounded-md text-sm mb-1 text-left ${
                activeChat === `preset-${chat.id}` ? 'bg-[#3d3d4d]' : 'hover:bg-[#2d2d3d]'
              }`}
            >
              {chat.icon}
              {chat.text}
            </button>
          ))}
          
          {savedChats.length > 0 && (
            <div className="border-t border-[#3d3d4d] my-2 pt-2">
              {savedChats.map((chat) => (
                <div
                  key={chat.id}
                  onClick={() => handleSavedChatClick(chat.id)}
                  className={`group w-full flex items-center justify-between py-2 px-3 rounded-md text-sm mb-1 text-left cursor-pointer ${
                    activeChat === chat.id ? 'bg-[#3d3d4d]' : 'hover:bg-[#2d2d3d]'
                  }`}
                >
                  <div className="flex items-center gap-2 truncate">
                    <MessageSquare size={16} />
                    <span className="truncate">{chat.title}</span>
                  </div>
                  <button 
                    className="opacity-0 group-hover:opacity-100 hover:text-red-400"
                    onClick={(e) => handleDeleteChat(chat.id, e)}
                  >
                    &times;
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Bottom buttons */}
        <div className="p-4 border-t border-[#3d3d4d]">
          <button className="w-full flex items-center gap-2 py-2 px-3 rounded-md text-sm hover:bg-[#2d2d3d] mb-2">
            <Settings size={16} />
            Settings
          </button>
          <button className="w-full flex items-center gap-2 py-2 px-3 rounded-md text-sm hover:bg-[#2d2d3d]">
            <LogOut size={16} />
            Sign Out
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="border-b border-gray-200 p-4 flex justify-between items-center">
          <h1 className="text-xl font-semibold text-purple-500">Resume AI Helper</h1>
          <div>
            <input
              type="file"
              ref={fileInputRef}
              className="hidden"
              onChange={handleFileUpload}
              accept=".pdf,.doc,.docx"
            />
            <button
              onClick={() => fileInputRef.current.click()}
              className={`flex items-center gap-2 ${
                uploadSuccess 
                  ? "bg-green-50 text-green-600 hover:bg-green-100"
                  : "bg-purple-50 text-purple-500 hover:bg-purple-100"
              } py-2 px-4 rounded-md text-sm font-medium`}
              disabled={isLoading}
            >
              {uploadSuccess ? (
                <>
                  <Check size={16} />
                  Resume Uploaded
                </>
              ) : (
                <>
                  <FileUp size={16} />
                  Upload Resume
                </>
              )}
            </button>
          </div>
        </div>

        {/* Chat Area */}
        <div className="flex-1 overflow-y-auto p-6 bg-gray-50">
          {messages.length === 0 ? (
            <div className="flex flex-col h-full justify-center items-center">
              <h2 className="text-2xl font-semibold text-gray-700 mb-4">Welcome to Resume AI Helper</h2>
              <p className="text-gray-500 mb-8 text-center max-w-md">
                Upload your resume and ask questions about optimizing your 
                job profile, targeting specific positions, or improving your 
                professional presentation.
              </p>

              <div className="bg-white p-6 rounded-lg shadow-sm w-full max-w-md">
                <h3 className="text-lg font-medium mb-2">Example questions:</h3>
                <ul className="space-y-2">
                  {exampleQuestions.map((q) => (
                    <li key={q.id}>
                      <button 
                        onClick={() => handleExampleQuestion(q.text)}
                        className="text-purple-600 hover:text-purple-800 text-left"
                      >
                        "{q.text}"
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              {messages.map((message, index) => (
                <div 
                  key={index} 
                  className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div 
                    className={`rounded-lg p-3 max-w-[80%] ${
                      message.sender === 'user' 
                        ? 'bg-purple-500 text-white rounded-tr-none' 
                        : 'bg-white border border-gray-200 rounded-tl-none'
                    }`}
                  >
                    {message.text}
                  </div>
                </div>
              ))}
              {isLoading && (
                <div className="flex justify-start">
                  <div className="bg-white border border-gray-200 rounded-lg rounded-tl-none p-3 max-w-[80%]">
                    <div className="flex space-x-2">
                      <div className="w-2 h-2 bg-gray-300 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                      <div className="w-2 h-2 bg-gray-300 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                      <div className="w-2 h-2 bg-gray-300 rounded-full animate-bounce" style={{ animationDelay: '600ms' }}></div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Input Area */}
        <div className="p-4 border-t border-gray-200 bg-white">
          <div className="flex items-center">
            <Input
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              placeholder="Ask a question about your resume..."
              className="flex-1 rounded-full border-gray-300 focus:border-purple-500 focus:ring-purple-500"
              onKeyPress={(e) => e.key === 'Enter' && !isLoading && handleSendMessage()}
              disabled={isLoading}
            />
            <Button
              onClick={handleSendMessage}
              className={`ml-2 ${isLoading ? 'bg-gray-400' : 'bg-purple-500 hover:bg-purple-600'} rounded-full h-10 w-10 flex items-center justify-center`}
              disabled={isLoading || inputMessage.trim() === ''}
            >
              <Send className="h-5 w-5" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default RAGInterface;
