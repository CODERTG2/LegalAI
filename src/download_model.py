import os
from sentence_transformers import SentenceTransformer

def download_model():
    model_name = "nomic-ai/nomic-embed-text-v1.5"
    local_path = "src/assets/model"
    
    print(f"Downloading {model_name} to {local_path}...")
    
    if not os.path.exists(local_path):
        os.makedirs(local_path)
        
    model = SentenceTransformer(model_name, trust_remote_code=True)
    model.save(local_path)
    
    print("Model downloaded and saved successfully.")

if __name__ == "__main__":
    download_model()
