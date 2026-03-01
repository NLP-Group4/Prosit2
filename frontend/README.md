# Interius Frontend

The frontend for Interius is a dynamic, reactive single-page application built to interface with the agentic generation pipeline.

## Tech Stack
- **Framework**: [React](https://reactjs.org/) + [Vite](https://vitejs.dev/)
- **Language**: [TypeScript](https://www.typescriptlang.org/)
- **Routing**: [TanStack Router](https://tanstack.com/router)
- **Data Fetching**: [TanStack Query](https://tanstack.com/query)
- **Styling**: [Tailwind CSS](https://tailwindcss.com/) + custom animations (Framer Motion)
- **Components**: [shadcn/ui](https://ui.shadcn.com/)

## Architecture

The frontend is designed around a unified Dashboard/Generation workspace (`/generate`) that provides a real-time, side-by-side view of the generation process:
1. **Global Sidebar**: Contains navigation, including a dynamic list of past generated projects fetched continuously via TanStack Query.
2. **Left Panel**: Navigation and history threads.
3. **Center Panel**: The chat interface that streams SSE events from the backend to display agent pipeline progress (`PipelineStage`).
4. **Right Panel**: A split-tab viewer containing:
   - **Design Docs**: Renders Markdown and Mermaid ecosystem definitions.
   - **Generated Code**: Syntax-highlighted code with a "Run API" button to trigger the Sandbox container.
   - **Live API**: An embedded Swagger UI (`localhost:9000/docs`) executing the dynamically generated code.

## Running Locally

To run the frontend development server without Docker:

```bash
cd frontend
npm install
npm run dev
```

The frontend will start at `http://localhost:5173`. We recommend running the full stack via Docker Compose (`docker compose up --build`) at the repository root to ensure the backend and database are correctly synchronized.
