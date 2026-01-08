# AI Web Generator

A powerful web page generator powered by multiple AI models (Gemini, Claude, GPT). Create beautiful, responsive websites by describing what you want in natural language.

## Features

- **Multi-Model AI**: Intelligent task routing between different AI models
  - **Google Gemini**: Best for UI/UX design, visual layouts, color schemes
  - **Claude (Anthropic)**: Best for code generation, complex logic, debugging
  - **GPT-4 (OpenAI)**: Best for optimization, refactoring, general tasks

- **Live Preview**: Real-time preview with responsive viewport switching (mobile/tablet/desktop)

- **Code Editor**: Built-in Monaco editor with syntax highlighting

- **Streaming Generation**: Watch AI generate code in real-time

- **Stripe Integration**: Subscription-based pricing with Stripe payments

## Tech Stack

- **Frontend**: Next.js 14, React 18, TypeScript, Tailwind CSS
- **Editor**: Monaco Editor
- **AI**: Google Generative AI, Anthropic Claude, OpenAI GPT-4
- **Payments**: Stripe
- **Database**: File-based storage (Prisma + PostgreSQL ready)

## Getting Started

### Prerequisites

- Node.js 18+
- npm or yarn

### Installation

1. Clone the repository:
```bash
cd web-generator
```

2. Install dependencies:
```bash
npm install
```

3. Set up environment variables:
```bash
cp .env.example .env
```

4. Add your API keys to `.env`:
```env
# AI API Keys
OPENAI_API_KEY="sk-xxx"
ANTHROPIC_API_KEY="sk-ant-xxx"
GOOGLE_AI_API_KEY="xxx"

# Stripe (optional)
STRIPE_SECRET_KEY="sk_test_xxx"
STRIPE_PUBLISHABLE_KEY="pk_test_xxx"
```

5. Run the development server:
```bash
npm run dev
```

6. Open [http://localhost:3000](http://localhost:3000)

## Usage

1. **Select Task Type**: Choose what you want to create (UI Design, Code Generation, etc.)

2. **Choose AI Model**: Let the system auto-select or choose manually:
   - `Auto`: Automatically selects best model for the task
   - `Gemini`: For visual/UI tasks
   - `Claude`: For code generation
   - `GPT-4`: For optimization

3. **Describe Your Idea**: Write a detailed description of what you want to build

4. **Generate**: Click Generate or use streaming for real-time updates

5. **Edit & Preview**: Modify the code and see live preview

6. **Export**: Download as a complete HTML file

## API Endpoints

### POST /api/ai
Generate code with AI
```json
{
  "prompt": "Create a landing page...",
  "taskType": "ui-design",
  "model": "gemini" // optional
}
```

### POST /api/ai/stream
Stream AI generation (SSE)

### CRUD /api/projects
Manage saved projects

### POST /api/stripe/checkout
Create Stripe checkout session

## Model Selection Guide

| Task | Recommended Model | Why |
|------|-------------------|-----|
| Landing pages | Gemini | Visual design strength |
| Component UI | Gemini | Layout expertise |
| API code | Claude | Code generation |
| Bug fixes | Claude | Debugging ability |
| Performance | GPT-4 | Optimization skills |
| Refactoring | GPT-4 | Code analysis |

## Project Structure

```
web-generator/
├── src/
│   ├── app/
│   │   ├── api/           # API routes
│   │   ├── generator/     # Main generator page
│   │   ├── pricing/       # Pricing page
│   │   └── page.tsx       # Home page
│   ├── components/
│   │   ├── editor/        # Code editor
│   │   ├── preview/       # Live preview
│   │   └── ui/            # UI components
│   ├── lib/
│   │   ├── ai-router.ts   # AI model routing
│   │   ├── stripe.ts      # Stripe config
│   │   └── storage.ts     # Data storage
│   └── hooks/
│       └── useAI.ts       # AI hook
├── prisma/
│   └── schema.prisma      # Database schema
└── public/
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | OpenAI API key | Yes (for GPT) |
| `ANTHROPIC_API_KEY` | Anthropic API key | Yes (for Claude) |
| `GOOGLE_AI_API_KEY` | Google AI API key | Yes (for Gemini) |
| `STRIPE_SECRET_KEY` | Stripe secret key | For payments |
| `STRIPE_PUBLISHABLE_KEY` | Stripe publishable key | For payments |
| `DATABASE_URL` | Database connection | For Prisma |

## License

MIT
