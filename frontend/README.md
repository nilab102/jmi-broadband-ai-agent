

A modern Next.js frontend for the Voice Agent, built with the same technology stack as the Therapist frontend.

## 🚀 Features

- **Real-time Voice Interaction** - Powered by Pipecat RTVI
- **Tool Call Monitoring** - Real-time display of AI tool usage
- **Modern UI** - Beautiful, responsive interface with Tailwind CSS
- **TypeScript** - Full type safety
- **Next.js 14** - Latest React framework with App Router

## 🛠️ Technology Stack

- **Next.js 14** - React framework
- **TypeScript** - Type safety
- **Tailwind CSS** - Styling
- **Pipecat RTVI** - Real-time voice interface
- **Lucide React** - Icons

## 📦 Installation

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Start the development server:**
   ```bash
   npm run dev
   ```

3. **Open your browser:**
   ```
   http://localhost:3000
   ```

## 🔧 Setup Requirements

### Backend Setup
Make sure your voice backend is running:
```bash
cd ../  # Go to voice directory
python main_simplified.py
```

### Environment
The frontend connects to:
- **Voice Backend**: `http://localhost:8002`
- **Tool WebSocket**: `ws://localhost:8002/ws/tools`
- **Product WebSocket**: `ws://localhost:8002/ws/product_info`

## 🎤 Usage

1. **Connect** - Click "Connect to Voice Agent" to establish RTVI connection
2. **Start Conversation** - Begin voice interaction with the AI
3. **Monitor Tools** - Watch real-time tool calls in the right panel
4. **View Messages** - See conversation history in the left panel

## 📁 Project Structure

```
frontend/
├── app/                    # Next.js App Router
│   ├── globals.css        # Global styles
│   ├── layout.tsx         # Root layout
│   └── page.tsx           # Main page
├── components/            # React components
│   ├── VoiceInterface.tsx # Voice controls
│   └── ConversationDisplay.tsx # Message display
├── lib/                   # Utilities
│   └── voiceClient.ts     # Voice client hook
├── package.json           # Dependencies
├── tailwind.config.js     # Tailwind configuration
└── tsconfig.json          # TypeScript configuration
```

## 🔌 Voice Client Features

The `useVoiceClient` hook provides:

- **RTVI Connection** - Real-time voice interface
- **Tool Monitoring** - WebSocket connection to tool endpoints
- **Message Management** - Conversation history
- **Status Tracking** - Connection and conversation state

## 🎨 UI Components

### VoiceInterface
- Connection controls
- Voice status indicators
- Privacy notices

### ConversationDisplay
- Message history
- Real-time updates
- Message type indicators

## 🚀 Deployment

### Build for Production
```bash
npm run build
npm start
```

### Environment Variables
Create `.env.local` for custom configuration:
```env
NEXT_PUBLIC_VOICE_BACKEND_URL=http://localhost:8002
```

## 🔍 Troubleshooting

### Common Issues

1. **Module Resolution Errors**
   - Ensure all dependencies are installed: `npm install`
   - Clear Next.js cache: `rm -rf .next`

2. **Voice Connection Issues**
   - Check backend is running on port 8002
   - Verify microphone permissions in browser
   - Check browser console for errors

3. **Tool Call Display Issues**
   - Verify WebSocket connections
   - Check backend tool endpoints

### Debug Mode
Enable debug logging in browser console:
```javascript
localStorage.setItem('debug', 'voice-client:*')
```

## 📚 API Reference

### Voice Client Hook
```typescript
const {
  isConnected,
  isInConversation,
  messages,
  connect,
  disconnect,
  startConversation,
  stopConversation
} = useVoiceClient()
```

### Message Types
- `user` - User voice input
- `assistant` - AI responses
- `system` - System messages
- `error` - Error messages
- `tool_call` - Tool activation
- `tool_result` - Tool results

## 🤝 Contributing

1. Follow the existing code style
2. Add TypeScript types for new features
3. Test voice functionality thoroughly
4. Update documentation for changes

## 📄 License

MIT License - see LICENSE file for details
