# Due Diligence Agent - Frontend

A modern React frontend for the Due Diligence Agent with TypeScript, Tailwind CSS, and shadcn/ui components.

## Features

- ✨ Modern chat interface with AI-powered input
- 🎨 Beautiful gradient backgrounds
- 🌙 Dark mode support
- 🔍 Web search toggle functionality
- 📎 File upload support
- ⚡ Real-time backend connection status
- 📱 Responsive design

## Tech Stack

- **React 18** - UI framework
- **TypeScript** - Type safety
- **Tailwind CSS** - Styling
- **shadcn/ui** - UI components
- **Vite** - Build tool
- **Framer Motion** - Animations
- **Lucide React** - Icons

## Setup

1. Install dependencies:
```bash
npm install
```

2. Start the development server:
```bash
npm run dev
```

The app will be available at: http://localhost:5174

## Project Structure

```
src/
├── components/
│   ├── ui/              # shadcn/ui components
│   │   ├── ai-input-with-search.tsx
│   │   └── textarea.tsx
│   └── hooks/           # Custom React hooks
│       └── use-auto-resize-textarea.ts
├── lib/
│   └── utils.ts         # Utility functions (cn for className merging)
├── App.tsx              # Main application component
├── main.tsx             # Application entry point
└── index.css            # Global styles and Tailwind imports
```

## Components

### AIInputWithSearch

A sophisticated input component with:
- Auto-resizing textarea
- Web search toggle with smooth animations
- File upload functionality
- Enter to send (Shift+Enter for new line)
- Beautiful hover effects and transitions

## Building for Production

```bash
npm run build
```

The production build will be in the `dist/` directory.

