FROM python:3.9

WORKDIR /code

# Copy requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Copy the rest of the application code
COPY ./app/ ./app

# Expose port (use 8000 for non-root usage)
EXPOSE 8000

# Run as a non-root user for better security (optional)
RUN useradd -m appuser
USER appuser

# Run the FastAPI app using Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
