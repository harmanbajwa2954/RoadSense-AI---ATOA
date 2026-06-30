FROM python:3.9-slim

# Install system dependencies for OpenCV
RUN apt-get update && apt-get install -y libgl1-mesa-glx libglib2.0-0

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run the Flask app on port 7860 (required by Hugging Face)
CMD ["flask", "run", "--host=0.0.0.0", "--port=7860"]
