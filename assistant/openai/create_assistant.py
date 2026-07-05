from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

class AssistantManager:
    
    def __init__(self):
        import httpx
        
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in .env file")
        
        http_client = httpx.Client(
            timeout=120.0,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
        
        self.client = OpenAI(
            api_key=api_key,
            http_client=http_client,
            max_retries=2
        )
        
        self.vector_store_id = os.getenv('VECTOR_STORE_ID')
        if not self.vector_store_id:
            raise ValueError("VECTOR_STORE_ID not found in .env file. Run upload_to_vectorstore.py first.")
    
    def create_assistant(self):
        print("Creating OpenAI Assistant...")
        
        system_prompt = """You are OptiBot, the customer-support bot for OptiSigns.com.
                        • Tone: helpful, factual, concise.
                        • Only answer using the uploaded docs.
                        • Max 5 bullet points; else link to the doc.
                        • Cite up to 3 "Article URL:" lines per reply."""
        
        print(f"[*] Using Vector Store ID: {self.vector_store_id}\n[*] Creating assistant...")
        
        try:
            assistant = self.client.beta.assistants.create(
                name="OptiBot",
                instructions=system_prompt,
                model=os.getenv("OPENAI_ASSISTANT_MODEL", "gpt-4o-mini"),
                tools=[{"type": "file_search"}],
                tool_resources={
                    "file_search": {
                        "vector_store_ids": [self.vector_store_id]
                    }
                }
            )
            
            print(f"\n[OK] Assistant created: {assistant.id} ({assistant.model})")
            
            return assistant
            
        except Exception as e:
            print(f"[ERROR] Failed to create assistant: {e}")
            return None
    
    def get_assistant(self, assistant_id):
        """Retrieve assistant details"""
        try:
            assistant = self.client.beta.assistants.retrieve(assistant_id)
            return assistant
        except Exception as e:
            print(f"[ERROR] Failed to retrieve assistant: {e}")
            return None


def main():
    """Main execution - create assistant"""
    manager = AssistantManager()
    assistant = manager.create_assistant()
    if not assistant:
        print("[ERROR] Failed to create assistant")
        return 1
    
    print(f"\n[DONE] Save this to .env: ASSISTANT_ID={assistant.id}")
    
    return 0


if __name__ == "__main__":
    exit(main())
