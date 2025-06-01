# Uvision for competitors image representation

# Files 
import os
# Formats
import re
import base64
import json
import yaml
# Models
import openai
from openai import OpenAI
 

DATA_PATH = '/da/'
RESPONSES_PATH = '/responses/'
ERRORS_PATH = '/errors/'
SYSTEM_PROMPT_PATH = '/prompts/prompt.yaml'
TEMPLATE_PROMPT_PATH = '/prompts/coeus_structure.ts'
EXAMPLE_RESPONSE_PATH = '/prompts/example.json'
MODEL='gpt-4.1'

 
 
client = OpenAI()

# Basic Functions

# Load the YAML file
def load_yaml(file_path):
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)

# Function to encode the image
def encode_image(image_path):
  with open(image_path, 'rb') as image_file:
    return base64.b64encode(image_file.read()).decode('utf-8')

def extract_json(text):
   # Extract JSON using regex
  match = re.search(r'\{.*\}', text, re.DOTALL)
  if match:
      json_str = match.group(0)
      try:
          data = json.loads(json_str)
          return data
      except json.JSONDecodeError as e:
          print("Failed to parse JSON:", e)
          raise ValueError(text)
  else:
      print("No JSON found in the response.",f'[{text}]')
      raise ValueError(text)


def save_response(file_name, text,path=RESPONSES_PATH):
    # Save to a text file
    with open(path+file_name, "w") as file:
        file.write(text)

# Main Functions


def get_prompt(system_prompt=SYSTEM_PROMPT_PATH, template_file=TEMPLATE_PROMPT_PATH, example_file=EXAMPLE_RESPONSE_PATH):
   # Example usage
  config = load_yaml(system_prompt)['promptConfiguration']
  template = ""
  example = ""
  with open(template_file, 'r') as file:
    template = file.read()
  config['template'] = template
  with open(example_file, 'r') as file:
    example = file.read()
  config['example'] = example
  return config

def generate_description(prompt, base64_images, file_names, model=MODEL):
    images_data = [
        {"type": "image_url", "image_url": {"url": f"data:image/{file_format};base64,{base64_image}"}}
        for base64_image, file_format in base64_images
    ]

    messages = [
        {"role": "system", "content": str(prompt['instructions'])},
        {"role": "system", "content": str(prompt['knowledgeBase'])},
        {"role": "system", "content": str(prompt['businessRules'])},
        {"role": "system", "content": f"{prompt['context']}\n{prompt['template']}"},
        {"role": "system", "content": f"RESPONSE EXAMPLE: {prompt['example']}"},
        {"role": "user", "content": [
            {"type": "text", "text": "Help me get the information of these images."},
            {"type": "text", "text": f"The file names are: {', '.join(file_names)}"},
            *images_data,
        ]},
    ]

    full_response = client.chat.completions.create(
        model=model,
        messages=messages,
    )
    return full_response.choices[0].message.content

def process_images(image_paths, prompt):
    base64_images = []
    file_names = []

    for image_path in image_paths:
        base64_image = encode_image(image_path)
        file_format = os.path.splitext(image_path)[1][1:]  # Extract file format
        base64_images.append((base64_image, file_format))
        file_names.append(os.path.basename(image_path))

    try:
        response = generate_description(prompt, base64_images, file_names)
        json_text = json.dumps(extract_json(response), indent=2)
        save_response(f"{file_names[0]}_response.json", json_text)
    except ValueError as raw_response:
        save_response(f"{file_names[0]}_error.txt", str(raw_response), ERRORS_PATH)

# Main Script
if __name__ == "__main__":
    prompt = get_prompt()

    for item in os.listdir(DATA_PATH):
        item_path = os.path.join(DATA_PATH, item)

        if os.path.isfile(item_path):  # Process individual image
            print(f"Processing single image: {item}")
            process_images([item_path], prompt)

        elif os.path.isdir(item_path):  # Process folder with multiple images
            print(f"Processing folder: {item}")
            images_in_folder = [
                os.path.join(item_path, f) for f in os.listdir(item_path)
                if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
            ]
            if images_in_folder:
                process_images(images_in_folder, prompt)
            else:
                print(f"No valid images in folder: {item_path}")