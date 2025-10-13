# JMI Broadband AI Agent

An intelligent AI agent for broadband comparison with voice and text conversation capabilities. Built with Python FastAPI backend and Next.js frontend, featuring Google Gemini Multimodal AI for natural voice interactions.

## 🌟 Features

- 🎤 **Voice Conversation**: Natural voice interactions powered by Google Gemini Live
- 💬 **Text Chat**: LangChain-based text conversation interface
- 🔍 **Broadband Comparison**: Intelligent broadband plan search and recommendations
- 📊 **Real-time Scraping**: Live data from broadband comparison websites
- 🎯 **Smart Recommendations**: AI-powered deal analysis and scoring
- 🔄 **WebSocket Support**: Real-time bidirectional communication
- 🔒 **Secure HTTPS**: SSL/TLS encrypted connections

## ⚡ Quick Setup

Get started in under 5 minutes! (Environment files are already configured in the repository)

### One-Command Setup

**Backend** (Terminal 1):
```bash
python3.13 -m venv venv && source venv/bin/activate && pip install -r jmi_broadband_agent/requirements.txt && python main.py
```

**Frontend** (Terminal 2):
```bash
cd frontend && npm install && npm run dev
```

### Step-by-Step Setup

#### Backend Setup
```bash
# 1. Create Python virtual environment
python3.13 -m venv venv

# 2. Activate virtual environment
source venv/bin/activate  # On macOS/Linux
# OR
venv\Scripts\activate  # On Windows

# 3. Install dependencies
pip install -r jmi_broadband_agent/requirements.txt

# 4. Run the backend
python main.py
```

Backend will be running on `https://localhost:8200` 🚀

#### Frontend Setup
```bash
# 1. Navigate to frontend directory
cd frontend

# 2. Install dependencies
npm install

# 3. Run the development server
npm run dev
```

Frontend will be running on `https://localhost:3000` 🎉

> **Note**: Environment variables are already configured in the repository (`.env` and `frontend/env.local`). Just update the API keys if needed.

---

## 📋 Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.13** or higher
- **Node.js 18.x** or higher
- **npm** or **yarn**
- **PostgreSQL** (for database functionality)
- **Git**

## 🛠️ Installation & Setup

### Backend Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd jmi-broadband-ai-agent
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r jmi_broadband_agent/requirements.txt
   ```

3. **Set up environment variables**
   
   The `.env` file is already included in the repository. Update it with your API keys:
   ```env
   # ===========================================
   # BACKEND ENVIRONMENT CONFIGURATION
   # ===========================================

   # Environment Mode
   ENVIRONMENT=development  # Options: development, production

   # Google API Configuration
   GOOGLE_API_KEY=your_google_api_key_here

   # Development URLs
   DEV_BACKEND_URL=https://localhost:8200
   DEV_FRONTEND_URL=https://localhost:3000

   # Production URLs (if deploying)
   PROD_BACKEND_URL=https://your-production-domain:8200
   PROD_FRONTEND_URL=https://your-production-domain:3000

   # SSL Configuration (optional - will use default cert.pem/key.pem)
   SSL_CERT_PATH=./cert.pem
   SSL_KEY_PATH=./key.pem
   SSL_VERIFY=False

   # Database Configuration (Supabase or PostgreSQL)
   DATABASE_URL=your_database_connection_string

   # Langfuse Configuration (optional - for tracing and analytics)
   LANGFUSE_PUBLIC_KEY=your_langfuse_public_key
   LANGFUSE_SECRET_KEY=your_langfuse_secret_key
   LANGFUSE_HOST=https://cloud.langfuse.com

   # Additional API Keys (optional)
   DEEPGRAM_API_KEY=your_deepgram_api_key  # For STT fallback
   ELEVENLABS_API_KEY=your_elevenlabs_api_key  # For TTS fallback
   CARTESIA_API_KEY=your_cartesia_api_key  # For TTS fallback
   ```

4. **SSL Certificates** (Optional - only if not included in repo)
   
   If SSL certificates are not included, generate them for local HTTPS:
   
   **Option 1: Using OpenSSL**
   ```bash
   cd jmi_broadband_agent
   openssl req -x509 -newkey rsa:4096 -nodes \
     -keyout key.pem \
     -out cert.pem \
     -days 365 \
     -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
   ```

   **Option 2: Using mkcert** (Recommended)
   ```bash
   # Install mkcert
   brew install mkcert  # macOS
   # choco install mkcert  # Windows
   
   # Create certificates
   mkcert -install
   cd jmi_broadband_agent
   mkcert localhost 127.0.0.1 ::1
   mv localhost+2.pem cert.pem
   mv localhost+2-key.pem key.pem
   ```

### Frontend Setup

1. **Navigate to frontend directory**
   ```bash
   cd frontend
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Configure environment variables**
   
   The `env.local` file is already included in the repository with default settings. Modify if needed for your environment.

## 🚀 Running the Application

### Start Backend Server

From the project root directory:

```bash
python main.py
```

The backend will start on `https://localhost:8200`

**Available Endpoints:**
- Health Check: `https://localhost:8200/voice/health`
- Connection Info: `https://localhost:8200/voice/connect`
- WebSocket (Voice): `wss://localhost:8200/voice/ws`
- WebSocket (Text): `wss://localhost:8200/voice/ws/text-conversation`
- WebSocket (Tools): `wss://localhost:8200/voice/ws/tools`

### Start Frontend Development Server

From the frontend directory:

```bash
cd frontend
npm run dev
```

The frontend will start on `https://localhost:3000`

### Access the Application

1. Open your browser and navigate to: `https://localhost:3000`
2. Accept the self-signed certificate warning (for development)
3. Start chatting with the AI agent via text or voice!

## 🔧 Development Scripts

### Backend

```bash
# Run the server
python main.py

# Check database structure (from scripts/)
python scripts/check_table_structure.py

# Debug contract patterns
python scripts/debug_contract_patterns.py

# Test data insertion and search
python scripts/data_insert&search.py
```

### Frontend

```bash
# Development server
npm run dev

# Development server with HTTPS
npm run dev:https

# Build for production
npm run build

# Start production server
npm start

# Lint code
npm run lint
```

## 📦 Dependencies

### Backend Key Dependencies

- **FastAPI**: Web framework for building APIs
- **Uvicorn**: ASGI server for FastAPI
- **Pipecat**: Framework for voice AI pipelines
- **LangChain**: Framework for LLM applications
- **Google Generative AI**: Gemini LLM integration
- **WebSockets**: Real-time communication
- **PostgreSQL/Supabase**: Database
- **Playwright**: Web scraping
- **RapidFuzz**: Fuzzy string matching

### Frontend Key Dependencies

- **Next.js 14**: React framework
- **React 18**: UI library
- **TypeScript**: Type-safe JavaScript
- **Tailwind CSS**: Utility-first CSS framework
- **Pipecat Client**: Voice agent client
- **Lucide React**: Icon library
- **Daily.co**: WebRTC for voice

## 🏗️ Project Structure

```
jmi-broadband-ai-agent/
├── main.py                          # Backend startup script
├── jmi_broadband_agent/             # Backend application
│   ├── config/                      # Configuration
│   │   ├── environment.py           # Environment management
│   │   └── settings.py              # Application settings
│   ├── core/                        # Core functionality
│   │   ├── agent_manager.py         # Tool registry & routing
│   │   ├── conversation_manager.py  # Conversation state
│   │   ├── router.py                # FastAPI routes
│   │   ├── text_agent.py            # Text conversation agent
│   │   ├── voice_agent.py           # Voice conversation agent
│   │   └── websocket_registry.py    # WebSocket management
│   ├── tools/                       # AI agent tools
│   │   ├── base_tool.py             # Base tool interface
│   │   └── broadband_tool.py        # Broadband search tool
│   ├── services/                    # Business logic services
│   │   ├── postal_code_service.py   # Postcode validation
│   │   ├── scraper_service.py       # Web scraping
│   │   ├── url_generator_service.py # URL generation
│   │   ├── recommendation_service.py# Deal recommendations
│   │   └── database_service.py      # Database operations
│   ├── functions/                   # Function modules
│   │   └── broadband/               # Broadband operations
│   ├── lib/                         # Utilities
│   │   ├── fuzzy_postal_code.py     # Postcode fuzzy matching
│   │   └── jmi_scrapper.py          # Web scraper
│   └── utils/                       # Helpers
│       ├── langfuse_tracing.py      # Tracing & analytics
│       └── validators.py            # Input validation
├── frontend/                        # Next.js frontend
│   ├── app/                         # Next.js app directory
│   │   ├── page.tsx                 # Main page
│   │   └── layout.tsx               # Root layout
│   ├── components/                  # React components
│   │   ├── VoiceInterface.tsx       # Voice chat UI
│   │   ├── TextConversation.tsx     # Text chat UI
│   │   ├── BroadbandToolResults.tsx # Results display
│   │   └── ...                      # Other components
│   ├── lib/                         # Frontend utilities
│   │   ├── config.ts                # Configuration
│   │   ├── voiceClient.ts           # Voice client
│   │   ├── pageContext.tsx          # Page context
│   │   └── userContext.tsx          # User context
│   └── env.local                    # Frontend environment variables
└── scripts/                         # Utility scripts
    ├── check_table_structure.py     # Database checks
    ├── debug_contract_patterns.py   # Debugging tools
    └── data_insert&search.py        # Data operations
```

## 🔐 Environment Variables Reference

### Required Backend Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `ENVIRONMENT` | Environment mode | `development` or `production` |
| `GOOGLE_API_KEY` | Google Gemini API key | `AIza...` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@host:5432/db` |

### Optional Backend Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DEV_BACKEND_URL` | Development backend URL | `https://localhost:8200` |
| `DEV_FRONTEND_URL` | Development frontend URL | `https://localhost:3000` |
| `SSL_CERT_PATH` | SSL certificate path | `./cert.pem` |
| `SSL_KEY_PATH` | SSL key path | `./key.pem` |
| `LANGFUSE_PUBLIC_KEY` | Langfuse public key | - |
| `LANGFUSE_SECRET_KEY` | Langfuse secret key | - |
| `DEEPGRAM_API_KEY` | Deepgram STT API key | - |
| `ELEVENLABS_API_KEY` | ElevenLabs TTS API key | - |

### Required Frontend Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `NEXT_PUBLIC_ENVIRONMENT` | Environment mode | `development` |
| `NEXT_PUBLIC_DEV_BACKEND_URL` | Development backend URL | `https://localhost:8200` |

## 🐛 Troubleshooting

### SSL Certificate Errors

If you encounter SSL errors:
1. Make sure certificates are generated in `jmi_broadband_agent/` directory
2. Check that `NODE_TLS_REJECT_UNAUTHORIZED=0` is set in frontend env.local
3. Accept the self-signed certificate warning in your browser

### Backend Won't Start

1. **Check Python version**: `python --version` (should be 3.13+)
2. **Verify environment variables**: Make sure `.env` file exists and has `GOOGLE_API_KEY`
3. **Check port availability**: Port 8200 should not be in use
4. **View logs**: Check console output for specific error messages

### Frontend Connection Issues

1. **Verify backend is running**: Check `https://localhost:8200/voice/health`
2. **Check CORS settings**: Ensure backend allows frontend origin
3. **WebSocket connection**: Check browser console for WebSocket errors
4. **Environment variables**: Verify `NEXT_PUBLIC_DEV_BACKEND_URL` is correct

### Database Errors

1. **Check PostgreSQL connection**: Verify `DATABASE_URL` is correct
2. **Test connection**: Run `scripts/check_table_structure.py`
3. **Database permissions**: Ensure user has proper permissions

### Import Errors

If you get module import errors:
```bash
# Make sure you're in the project root
cd /path/to/jmi-broadband-ai-agent

# Reinstall dependencies
pip install -r jmi_broadband_agent/requirements.txt
```

## 📚 Additional Resources

- [Architecture Overview](./ARCHITECTURE_OVERVIEW.md) - Detailed system architecture
- [Broadband Tool Documentation](./jmi_broadband_agent/functions/broadband/README.md) - Broadband tool features
- [Scripts README](./scripts/README.md) - Utility scripts documentation

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Commit your changes: `git commit -m 'Add some feature'`
4. Push to the branch: `git push origin feature/your-feature-name`
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Google Gemini**: For advanced multimodal AI capabilities
- **Pipecat**: For voice AI pipeline framework
- **LangChain**: For LLM application framework
- **FastAPI**: For modern Python web framework
- **Next.js**: For React framework

## 📞 Support

For issues, questions, or contributions:
- Open an issue on GitHub
- Check the [troubleshooting section](#-troubleshooting)
- Review the [architecture documentation](./ARCHITECTURE_OVERVIEW.md)

---

**Built with ❤️ using Python, FastAPI, Next.js, and Google Gemini AI**

**Last Updated**: October 2025 | **Version**: 2.0.0

