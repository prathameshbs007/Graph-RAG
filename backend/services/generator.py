from groq import Groq
from config import settings

class Generator:
    def __init__(self):
        self.api_key = settings.GROQ_API_KEY
        if self.api_key and self.api_key != "your_groq_api_key_here":
            self.client = Groq(api_key=self.api_key)
        else:
            self.client = None

    def generate_answer(self, query: str, sources: list[dict], graph_context: dict, figures: list[dict] = None) -> str:
        if not self.client:
            return "Please configure the Groq API key to generate an answer. (Retrieved context will still show below)."
            
        context_parts = []
        for i, s in enumerate(sources):
            context_parts.append(f"[{i+1}] Paper: {s.get('paper_title')} ({s.get('paper_id')})\nContent: {s.get('chunk_text')}")
        
        # Include figure captions so the LLM can reason about image content
        if figures:
            for j, fig in enumerate(figures):
                caption = fig.get("caption", "")
                title = fig.get("paper_title", "")
                if caption:
                    idx = len(sources) + j + 1
                    context_parts.append(f"[{idx}] [Figure from: {title}]\nCaption/Description: {caption}")
            
        context_str = "\n\n".join(context_parts)
        
        graph_str = f"Related Papers: {', '.join(graph_context.get('related_papers', []))}\nConcepts: {', '.join(graph_context.get('concepts', []))}"
        
        system_prompt = (
            "You are ResearchOS, an AI assistant that analyzes documents, images, and audio.\n"
            "Answer the user's query based ONLY on the provided context.\n"
            "The context may include text from papers, audio transcripts, and image/figure descriptions.\n"
            "CRITICAL: Cite your sources using the reference numbers like [1], [2], etc.\n"
            "If the context does not contain the answer, say 'I don't have enough information'."
        )
        
        user_prompt = f"Context:\n{context_str}\n\nGraph Context:\n{graph_str}\n\nQuery:\n{query}"
        
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=settings.GROQ_MODEL,
                max_tokens=settings.GROQ_MAX_TOKENS
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            print(f"Groq API error: {e}")
            return "Sorry, I could not generate an answer right now due to an LLM API error."

generator = Generator()
