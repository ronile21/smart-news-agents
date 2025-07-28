# Use a lightweight Python image
FROM python:3.11-slim

# Set working directory inside container
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all source code
COPY . .

# Set environment variables (optional fallback if .env not provided)
ENV SLEEP_SECONDS=900

# Run the script
CMD ["python", "thailand_cambodia_news_agent.py"]
