# Use an official Python runtime as a parent image
FROM public.ecr.aws/docker/library/python:3.12-slim

ARG GUARDRAILS_TOKEN
ARG GUARDRAILS_ENABLED

# Update utilities
RUN apt-get update
RUN apt-get install -y git

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY ./requirements.txt /app/requirements.txt

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

# Set the directory for nltk data
ENV NLTK_DATA=/opt/nltk_data

# Download punkt data
RUN python -m nltk.downloader -d /opt/nltk_data punkt

RUN if [ "$GUARDRAILS_ENABLED" = "true" ]; then \
    guardrails configure --enable-metrics --enable-remote-inferencing --token $GUARDRAILS_TOKEN && \
    guardrails hub install hub://guardrails/exclude_sql_predicates && \
    guardrails hub install hub://guardrails/toxic_language; \
fi

# Copy the rest of the application's code into the container at /app
COPY ./app /app

# Expose the port the app runs on
EXPOSE 8000

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]