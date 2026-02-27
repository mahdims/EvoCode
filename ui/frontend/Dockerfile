# Use a lightweight Python image
FROM python:3.13-alpine

# Set working directory
WORKDIR /app

# Install dependencies directly to keep image size down
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the app code into the container
COPY .streamlit/ .streamlit/
COPY ./src .

# Expose the default Streamlit port
EXPOSE 8501

# Run Streamlit (host must be 0.0.0.0 for Docker)
CMD ["streamlit", "run", "dashboard.py", "--server.address=0.0.0.0"]