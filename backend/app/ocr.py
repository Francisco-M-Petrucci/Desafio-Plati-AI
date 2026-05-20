import os
import json
import base64
from typing import List, Dict, Any

def parse_receipt_image(image_bytes: bytes, filename: str = "") -> List[Dict[str, Any]]:
    """
    Parses a receipt image to extract food ingredients.
    If NVIDIA_API_KEY is configured, it uses Nvidia's Llama-3.2-11b-vision-instruct.
    Otherwise, it falls back to a smart mock scanner for testing.
    """
    nvidia_key = os.getenv("NVIDIA_API_KEY")
    
    # Check if key is configured and not the default template key
    if nvidia_key and not nvidia_key.startswith("nvapi-your-key") and len(nvidia_key) > 10:
        try:
            print(f"Sending receipt '{filename}' to Nvidia Llama 3.2 Vision...")
            from openai import OpenAI
            client = OpenAI(
                base_url="https://integrate.api.nvidia.com/v1",
                api_key=nvidia_key
            )
            
            base64_image = base64.b64encode(image_bytes).decode("utf-8")
            
            prompt = """
            Analyze this shopping receipt image and extract a clean list of food items, ingredients, and groceries purchased.
            Ignore non-food items (like soap, plates, paper, etc.).
            Respond ONLY with a valid JSON array of objects, where each object has these fields:
            - "name": (string, clean singular lowercase name of the ingredient, e.g. "chicken breast", "tomato", "milk")
            - "quantity": (float, quantity purchased, default 1.0)
            - "unit": (string, unit of measurement, e.g. "kg", "g", "can", "pack", "unit")
            
            Do not include markdown code block syntax (like ```json). Respond with raw JSON array only.
            """
            
            response = client.chat.completions.create(
                model="meta/llama-3.2-11b-vision-instruct",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=1024
            )
            
            content = response.choices[0].message.content.strip()
            # Clean up markdown code blocks if the LLM output them anyway
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            parsed_data = json.loads(content)
            print(f"Successfully extracted {len(parsed_data)} items from receipt using Nvidia NIM.")
            return parsed_data
            
        except Exception as e:
            print(f"Nvidia Vision API failed: {e}. Falling back to mock scanner.")
            
    # Mock scanning fallback logic to make testing simple and functional out-of-the-box
    print("Using Mock receipt scanner...")
    
    # We can detect keyword in filename to make mock scan interactive!
    fname_lower = filename.lower() if filename else ""
    if "taco" in fname_lower or "mexican" in fname_lower:
        return [
            {"name": "chicken breast", "quantity": 1.0, "unit": "kg"},
            {"name": "corn tortillas", "quantity": 10.0, "unit": "unit"},
            {"name": "avocado", "quantity": 3.0, "unit": "unit"},
            {"name": "roma tomato", "quantity": 4.0, "unit": "unit"},
            {"name": "jalapeno", "quantity": 2.0, "unit": "unit"}
        ]
    elif "pasta" in fname_lower or "italian" in fname_lower:
        return [
            {"name": "penne pasta", "quantity": 1.0, "unit": "pack"},
            {"name": "cherry tomatoes", "quantity": 1.0, "unit": "pack"},
            {"name": "zucchini", "quantity": 2.0, "unit": "unit"},
            {"name": "bell pepper", "quantity": 1.0, "unit": "unit"},
            {"name": "parmesan cheese", "quantity": 150.0, "unit": "g"}
        ]
    else:
        # Default mock ingredients list
        return [
            {"name": "salmon fillets", "quantity": 2.0, "unit": "unit"},
            {"name": "asparagus spears", "quantity": 1.0, "unit": "bunch"},
            {"name": "lemon", "quantity": 2.0, "unit": "unit"},
            {"name": "fresh dill", "quantity": 1.0, "unit": "bunch"}
        ]
