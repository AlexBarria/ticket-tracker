# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set working directory
WORKDIR /code

# Copy the requirements file first
COPY ./requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Copy the rest of the application's code into an 'app' subdirectory
COPY ./app ./app

# Expose the port the app runs on
EXPOSE 8000

# Run the application using an explicit module path
# This tells uvicorn to look for the 'app' package, then the 'main' module inside it.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]