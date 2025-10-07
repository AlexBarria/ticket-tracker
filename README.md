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
    git clone https://github.com/AlexBarria/ticket-tracker
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

| Service                      | URL                              | Description                                    |
|------------------------------|----------------------------------|------------------------------------------------|
| **Admin UI (Streamlit)**     | `http://localhost:8501`          | The main web interface for admin queries.      |
| **Agent 2 API Docs**         | `http://localhost:8003/docs`     | Swagger UI for the RAG agent API.              |
| **Agent 1 API Docs**         | `http://localhost:8002/docs`     | Swagger UI for the Formatter agent API.        |
| **OCR Service API Docs**     | `http://localhost:8001/docs`     | Swagger UI for the OCR service API.            |
| **Evaluation Service Docs**  | `http://localhost:8006/docs`     | Swagger UI for the Evaluation service API.     |
| **MLflow Tracking UI**       | `http://localhost:5001`          | UI for tracking agent runs and experiments.    |
| **MinIO Console (S3)**       | `http://localhost:9001`          | Web console for browsing the S3 buckets.       |
| **Phoenix Traces UI**        | `http://localhost:6006`          | Observability: traces, LLM spans, token usage. |
| **Guardrails**               | `http://localhost:8005/validate` | Guardrails API to validate prompts             |

## 📈 Observability with Phoenix

This stack includes a Phoenix service for end-to-end tracing across microservices and LLM calls. Use it to inspect request flows, latencies, and token usage.

### How to open

* Phoenix UI: `http://localhost:6006`

### Environment variables (already configured in `docker-compose.yml`)

Each service exports traces to Phoenix via OTLP gRPC:

* `OTEL_SERVICE_NAME`: Logical service name (e.g., `tool-web`, `agent-2-rag`, `agent-1-formatter`, `ocr-service`).
* `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT`: `http://phoenix:4317`
* `OTEL_EXPORTER_OTLP_PROTOCOL`: `grpc`

### What gets traced

* __FastAPI endpoints__: incoming requests and latencies.
* __HTTP clients__: outgoing calls (e.g., `requests`, `httpx`).
* __LLM calls__:
  * `agent-2-rag` orchestrator (LangChain) is instrumented via OpenInference to emit LLM spans and token usage.
  * `agent-2-rag` SQL agent (raw OpenAI client) is instrumented via OpenInference.
  * `tool-web` (web search summarization with OpenAI) is instrumented via OpenInference.


## 🖥️ User Interface & Authentication

The primary interaction with the application is through a web user interface built with Streamlit, accessible at `http://localhost:8501`.

### Authentication Flow

Access to the application is protected and managed by **Auth0**, a robust and secure identity service.

1.  **Login**: Upon accessing the UI, you will be presented with a "Login" button. Clicking it will redirect you to a secure login page hosted by Auth0.
2.  **Credentials**: You must enter the email and password associated with your user account.
3.  **Redirection**: Once your credentials are validated, you will be redirected back to the application with an active session.

### Roles & Permissions

The application uses a role-based access control (RBAC) system to determine which pages and features each user can see. Roles are assigned by a system administrator in the Auth0 dashboard.

* 👤 **`client` Role**: This role is designed for users who only need to upload receipts.
    * **Access**: They can only see the **"Client Uploader"** page to upload their ticket images.

* 👑 **`admin` Role**: This role has full access to all application features.
    * **Full Access**: They can see both the **"Client Uploader"** page and the **"Admin Dashboard"**, which allows them to make natural language queries about expense data.

### Logout Process

The "Logout" button performs a federated logout. This means it terminates the session in both the Streamlit application and Auth0, ensuring your account is completely and securely logged out. When you try to access the application again, you will be required to re-enter your credentials.

---

## 🔍 Web Search Tool

The project includes a web search tool that integrates with the main orchestrator. This tool allows performing web searches and summarizing relevant information.

### Required Configuration

1. **Tavily API Key**: The tool uses the Tavily API for web searches. You need to obtain an API key from [Tavily](https://tavily.com/).

2. **Environment Variables**: Add the following variable to your `.env` file:
   ```
   TAVILY_API_KEY=your_api_key_here
   ```

3. **Orchestrator Integration**: The tool is configured to be called by the `agent-2-rag` service through the URL `http://tool-web:8000/search`.

---

## 📊 Evaluation System

The system includes a comprehensive evaluation service that monitors and tracks the quality of both Agent 1 (OCR) and Agent 2 (RAG) over time.

### Agent 1 (OCR) Evaluation

Admins can evaluate OCR quality through the **"Ticket Review & Correction"** tab in the Admin Dashboard:

1. **Review Queue**: Shows tickets flagged with `need_verify = TRUE` that don't yet have ground truth
2. **Side-by-Side Comparison**: Displays the original receipt image alongside the OCR-extracted data
3. **Ground Truth Entry**: Admin provides the correct merchant, date, amount, and item details
4. **Automatic Evaluation**: System compares OCR output against ground truth and calculates:
   - **Exact Match Metrics**: Merchant name, date, and amount accuracy
   - **Item Extraction Metrics**: Precision, recall, and F1 score for items
   - **LLM-as-Judge Metrics**: Semantic similarity and overall quality assessment
5. **Auto-Approval**: Ticket is automatically approved and removed from review queue

### Agent 2 (RAG) Evaluation

Admins can evaluate RAG quality in two ways:

**Real-time Evaluation** (via "LLM Chat" tab):
1. Enable the "📊 Evaluate Quality" checkbox when asking a question
2. Optionally provide expected answer for more accurate evaluation
3. System evaluates the response using RAGAS metrics and displays results immediately

**Batch Evaluation** (via "Metrics Dashboard"):
1. Navigate to the Metrics Dashboard and select "Agent 2 (RAG)"
2. Trigger evaluation runs using the sidebar controls:
   - **Sample Evaluation**: Test with 5-10 queries for quick validation (~1-2 minutes)
   - **Full Evaluation**: Run all test queries for comprehensive assessment (~5-10 minutes)
3. Results are stored and displayed with historical trends

**RAGAS Metrics** (both methods):
- **Faithfulness**: Factual accuracy based on retrieved database context
- **Answer Relevance**: How well the answer addresses the question
- **Context Precision**: Relevance of retrieved information
- **Context Recall**: Completeness of information retrieval

### Metrics Dashboard

The **"Metrics Dashboard"** page provides comprehensive analytics for both agents:

- **Metric Category Selector**: Switch between Agent 1 (OCR) and Agent 2 (RAG) metrics
- **Summary Metrics**: Overall performance indicators and success rates
- **Detailed Breakdown**: Granular metrics for each evaluation dimension
- **Recent Runs Table**: Historical evaluation runs with individual scores
- **Trends Chart**: Performance over time visualization
- **Trigger Controls** (Agent 2 only): Run sample or full evaluations on demand

### Evaluation Service API Endpoints

The evaluation service exposes RESTful APIs for both programmatic access and dashboard integration:

#### Agent 2 (RAG) Endpoints
- `POST /api/v1/evaluation/realtime` - Evaluate a single query in real-time
- `POST /api/v1/evaluation/run` - Trigger full evaluation run
- `POST /api/v1/evaluation/sample` - Trigger sample evaluation
- `GET /api/v1/evaluation/runs` - List recent evaluation runs
- `GET /api/v1/evaluation/runs/{run_id}` - Get detailed run results
- `GET /api/v1/metrics/summary` - Get RAG evaluation summary
- `GET /api/v1/metrics/trends` - Get historical trends

#### Agent 1 (OCR) Endpoints
- `POST /api/v1/evaluation/agent1/realtime` - Evaluate a single ticket in real-time
- `GET /api/v1/metrics/agent1/summary` - Get OCR evaluation summary
- `GET /api/v1/metrics/agent1/runs` - List recent OCR evaluation runs
- `GET /api/v1/metrics/agent1/trends` - Get OCR quality trends

Full API documentation is available at `http://localhost:8006/docs`.

---

## 🔩 For Developers: Managing the Database Schema

During development, the structure of the database may change (e.g., adding a new column to the `tickets` table). Because the database data is persisted locally in the `postgres/data` directory, these changes won't be applied automatically.

If you make a change to the database schema in `agent-1-formatter/app/models.py` or `postgres/init--db.sql`, you must **reset the database** for the changes to take effect.

**To reset the database:**

1.  Stop all running containers:
    ```bash
    docker-compose down
    ```
2.  Delete the local PostgreSQL data directory:
    ```bash
    rm -rf postgres/data
    ```
3.  Restart the application. The `init-db.sql` script will run again and create the tables with the new schema.
    ```bash
    docker-compose up -d
    ```

---
### Database Schema

#### The `tickets` Table

All structured receipt information is stored in the `tickets` table. Here is a description of its main fields:

| Column              | Data Type            | Description                                                                                                     |
|:--------------------|:---------------------|:----------------------------------------------------------------------------------------------------------------|
| `id`                | SERIAL (Primary Key) | A unique identifier for each ticket record.                                                                     |
| `merchant_name`     | VARCHAR(255)         | The name of the store or business, extracted by the LLM.                                                        |
| `transaction_date`  | DATE                 | The date of the transaction (e.g., '2025-09-07').                                                               |
| `total_amount`      | NUMERIC(10, 2)       | The final total amount of the purchase.                                                                         |
| `items`             | JSONB                | A JSON array containing the list of purchased items. Each item is an object with a `description` and a `price`. |
| `category`          | VARCHAR(100)         | The expense category (e.g., 'Groceries', 'Restaurant') as determined by the LLM.                                |
| `s3_path`           | VARCHAR(512)         | The full S3 path to the original receipt image stored in MinIO.                                                 |
| `user_id`           | VARCHAR(255)         | The unique ID of the user (from Auth0) who uploaded the ticket.                                                 |
| `need_verify`       | BOOLEAN              | Indicates if the ticket needs verification from an admin.                                                       |
| `approved`          | BOOLEAN              | Indicates if the ticket OCR was validated and approved.                                                         |
| `has_ground_truth`  | BOOLEAN              | Indicates if corrected values have been saved for this ticket.                                                  |
| `created_at`        | TIMESTAMP            | The timestamp when the record was inserted into the database.                                                   |

Agents don't have direct access to `tickets` table, instead they interact with a view that only shows the approved tickets.

#### The `ticket_ground_truth` Table

Stores admin-corrected values for tickets that have been reviewed and evaluated:

| Column               | Data Type            | Description                                           |
|:---------------------|:---------------------|:------------------------------------------------------|
| `id`                 | SERIAL (Primary Key) | Unique identifier for each ground truth record.       |
| `ticket_id`          | INTEGER (UNIQUE)     | Foreign key to the tickets table.                     |
| `corrected_merchant` | VARCHAR(255)         | The correct merchant name as verified by admin.       |
| `corrected_date`     | DATE                 | The correct transaction date.                         |
| `corrected_amount`   | NUMERIC(10, 2)       | The correct total amount.                             |
| `corrected_items`    | JSONB                | The correct list of items with descriptions & prices. |
| `corrected_by`       | VARCHAR(255)         | User ID of the admin who made the correction.         |
| `created_at`         | TIMESTAMP            | When the ground truth was saved.                      |

#### Evaluation Tables

The system includes dedicated tables for tracking evaluation metrics:

- **`evaluation_runs`** & **`evaluation_results`**: Track Agent 2 (RAG) RAGAS evaluation metrics
- **`agent1_evaluation_runs`** & **`agent1_evaluation_results`**: Track Agent 1 (OCR) quality metrics

---

## 📂 Project Structure

This project follows a microservices architecture. Each top-level directory represents a self-contained service with its own `Dockerfile` and logic. The `docker-compose.yml` file at the root orchestrates how these services build, run, and communicate.

```
/TICKET-TRACKER
├── .env                  # Holds all secrets & configurations
├── .gitignore
├── agent-1-formatter/    # Microservice: Structures OCR text into JSON
├── agent-2-rag/          # Microservice: Answers admin queries using RAG
├── evaluation-service/   # Microservice: Evaluates Agent 1 (OCR) & Agent 2 (RAG) quality
├── guardrails/           # Microservice: Validates prompts with Guardrails
├── minio/                # Configuration and data for MinIO (S3 storage)
├── ocr-service/          # Microservice: Extracts raw text from images
├── postgres/             # Configuration and data for PostgreSQL DB
├── ui/                   # Microservice: Streamlit frontend for admins
├── tool-web/             # Microservice: Web search and summarization tool
├── docker-compose.yml    # The master file to build and run all services
├── folders_creation.py   # (Utility script) The generator you used
├── pyproject.toml        # Project metadata (can be used for dev tools)
└── README.md             # This file
```

### Core Services Explained

* `docker-compose.yml`: The central orchestrator. It defines all services, their networks, ports, and volumes for data persistence.
* `ui/`: A **Streamlit** application serving as the frontend. It handles user authentication via Auth0 and provides views based on user roles. When a file is uploaded, the UI sends the file and the user's **`id_token`** to the Agent 1 service.
* `agent-1-formatter/`: A **FastAPI** service that acts as the primary ingestion and workflow orchestrator. Its responsibilities include:
    1.  Receiving an uploaded file and `id_token` from the UI.
    2.  Validating the token to get the user's unique ID.
    3.  Uploading the original receipt image to a user-specific folder in **MinIO**.
    4.  Calling the `ocr-service` to get the raw text.
    5.  Using an OpenAI LLM (e.g., GPT-4o) to parse the raw text into a structured JSON object.
    6.  Validating the LLM's output against a Pydantic schema.
    7.  Saving the final structured data to the **PostgreSQL** database.
* `agent-2-rag/`: A **FastAPI** service that will implement the Retrieval-Augmented Generation (RAG) logic. It will receive a natural language question, translate it into a SQL query, fetch data from the database, and generate a human-readable answer.
* `guardrails/`: A **FastAPI** service that exposes a Guardrails validation endpoint. It ensures that prompts adhere to predefined constraints, enhancing reliability and safety.
* `ocr-service/`: A **FastAPI** service that exposes a text recognition model. It's a specialized "tool" service whose only job is to accept an image file and return the extracted raw text, preserving line breaks. It uses the **EasyOCR** library to perform this task.
* `tool-web/`: A **FastAPI** service that provides a web search and summarization tool. It uses the Tavily API to perform web searches and OpenAI to summarize the results.
* `evaluation-service/`: A **FastAPI** service that evaluates the quality of both agents:
    * **Agent 1 (OCR)**: Compares OCR-extracted data against admin-provided ground truth using:
        - Deterministic metrics (exact match for merchant, date, amount)
        - Item extraction metrics (precision, recall, F1 score)
        - LLM-as-Judge metrics (semantic similarity, overall quality)
    * **Agent 2 (RAG)**: Evaluates natural language answers using RAGAS metrics:
        - Faithfulness (factual accuracy based on retrieved context)
        - Answer Relevance (how well the answer addresses the question)
        - Context Precision (relevance of retrieved context)
        - Context Recall (completeness of information retrieval)
    * Stores all evaluation results in PostgreSQL for trend analysis
    * Provides APIs for the Metrics Dashboard to display evaluation metrics
* `postgres/`: Contains the configuration for the PostgreSQL database, including an `init-db.sql` script that creates the necessary tables on the first run.
* `minio/`: Configuration for the MinIO object storage service, which acts as an S3-compatible server for storing the original receipt images.
* **MLflow**: Defined within `docker-compose.yml`. It's configured to run using the official Docker image, with Postgres as its backend store and MinIO as its artifact store for experiment tracking.
