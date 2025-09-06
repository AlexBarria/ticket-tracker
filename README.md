# Ticket Tracker 🎟️

Ticket Tracker is a comprehensive system that allows users to upload receipt photos, which are then processed by an OCR model and an AI agent to structure the data into a database. It also provides an interface for administrators to query expense data using natural language.

This project is built on a **microservices architecture**, with services written in Python (using FastAPI and Streamlit). The entire stack is containerized and orchestrated using Docker and Docker Compose.

---

## 🚀 Getting Started

Follow these instructions to get the entire microservices stack running on your local machine.

### Prerequisites

* **Docker** and **Docker Compose**: Ensure you have Docker Desktop (or Docker Engine with the Compose plugin) installed and running. You can download it [here](https://www.docker.com/products/docker-desktop/).

### Installation & Setup

1.  **Clone the repository:**
    ```bash
    git clone <your-repository-url>
    cd TICKET-TRACKER
    ```

2.  **Configure environment variables:**
    The project uses a `.env` file to manage all secrets and configurations. Start by copying the example file.
    ```bash
    cp .env.example .env
    ```
    Now, **edit the `.env` file** and add your actual credentials for the required services (OpenAI API Key, Auth0 details, etc.).

3.  **Build and Run the Services:**
    This single command will build the container images for each microservice and start the entire application stack in detached mode.
    ```bash
    docker-compose up --build -d
    ```
    The initial build might take a few minutes as it downloads base images and installs dependencies for each service.

### ✅ Accessing the Services

Once all the containers are up and running, you can access the different parts of the system at the following URLs:

| Service               | URL                               | Description                                      |
| --------------------- | --------------------------------- | ------------------------------------------------ |
| **Admin UI (Streamlit)** | `http://localhost:8501`           | The main web interface for admin queries.        |
| **Agent 2 API Docs** | `http://localhost:8003/docs`      | Swagger UI for the RAG agent API.                |
| **Agent 1 API Docs** | `http://localhost:8002/docs`      | Swagger UI for the Formatter agent API.          |
| **OCR Service API Docs** | `http://localhost:8001/docs`      | Swagger UI for the OCR service API.              |
| **MLflow Tracking UI** | `http://localhost:5000`           | UI for tracking agent runs and experiments.      |
| **MinIO Console (S3)** | `http://localhost:9001`           | Web console for browsing the S3 buckets.         |

---

## 📂 Project Structure

This project follows a microservices architecture. Each top-level directory represents a self-contained service with its own `Dockerfile` and logic. The `docker-compose.yml` file at the root orchestrates how these services build, run, and communicate.

```
/TICKET-TRACKER
├── .env                  # Holds all secrets & configurations
├── .gitignore
├── agent-1-formatter/    # Microservice: Structures OCR text into JSON
├── agent-2-rag/          # Microservice: Answers admin queries using RAG
├── minio/                # Configuration and data for MinIO (S3 storage)
├── ocr-service/          # Microservice: Extracts raw text from images
├── postgres/             # Configuration and data for PostgreSQL DB
├── ui/                   # Microservice: Streamlit frontend for admins
├── docker-compose.yml    # The master file to build and run all services
├── folders_creation.py   # (Utility script) The generator you used
├── pyproject.toml        # Project metadata (can be used for dev tools)
└── README.md             # This file
```

### Core Services Explained

* `docker-compose.yml`: The central orchestrator. It defines all services, how they connect, which ports they expose, and which volumes they use for data persistence.
* `ui/`: A **Streamlit** application that serves as the graphical user interface for administrators to ask questions. It communicates with `agent-2-rag`.
* `agent-1-formatter/`: A **FastAPI** service that receives raw text from the OCR service, uses an LLM (via OpenAI) to structure it into a predefined JSON format, and saves it to the PostgreSQL database.
* `agent-2-rag/`: A **FastAPI** service that implements the Retrieval-Augmented Generation (RAG) logic. It receives a natural language question from the UI, translates it into a SQL query, fetches data from the database, and generates a human-readable answer.
* `ocr-service/`: A **FastAPI** service that exposes an OCR model. It accepts an image file and returns the extracted raw text.
* `postgres/`: Contains the configuration for the PostgreSQL database, including an `init-db.sql` script that creates the necessary tables on the first run. Data is persisted in a Docker volume.
* `minio/`: Configuration for the MinIO object storage service, which acts as an S3-compatible server for storing the original receipt images.
* **MLflow**: Defined within `docker-compose.yml` but without a dedicated folder. It's configured to run using the official Docker image, with Postgres as its backend store and MinIO as its artifact store.