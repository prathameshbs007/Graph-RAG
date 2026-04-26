import { UploadPanel } from './components/UploadPanel';

function App() {
  return (
    <div className="min-h-screen bg-gray-50 p-8 font-sans text-gray-900">
      <header className="mb-12 text-center mt-10">
        <h1 className="text-4xl font-extrabold tracking-tight text-gray-900 mb-2">ResearchOS</h1>
        <p className="text-lg text-gray-500">Multi-Modal Graph RAG System</p>
      </header>

      <main>
        <UploadPanel />
      </main>
    </div>
  )
}

export default App;
