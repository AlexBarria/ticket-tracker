# ticket-tracker
Ticket Tracker is a demo system that lets users upload receipt photos, processes them with OCR and an agent that structures the data into a database, and allows admins to query expenses in natural language.

This project is built using Python, FastAPI, and AI agents, and is designed to be containerized with Docker.

---

## 🚀 Getting Started

Follow these instructions to get the project set up and running on your local machine.

### Prerequisites

* Python 3.10+
* [Poetry](https://python-poetry.org/docs/#installation) for dependency management.
* [Docker](https://www.docker.com/products/docker-desktop/) and Docker Compose (for running the database and other services).

### Installation & Setup

1.  **Clone the repository:**
    ```bash
    git clone <your-repository-url>
    cd ticket-tracker
    ```

2.  **Install dependencies:**
    Poetry will create a virtual environment and install all the packages defined in `pyproject.toml`.
    ```bash
    poetry install
    ```

3.  **Configure environment variables:**
    Create a `.env` file in the root directory by copying the example file. You should create a `.env.example` to guide other developers.
    ```bash
    cp .env.example .env
    ```
    Now, edit the `.env` file and add your credentials (Database URL, OpenAI API Key, S3 bucket info, etc.).

4.  **Start services with Docker:**
    This command will start the Postgres database and any other services defined in `docker-compose.yml`.
    ```bash
    docker-compose up -d
    ```

5.  **Run the application:**
    Use `uvicorn` to run the FastAPI server. The `--reload` flag will automatically restart the server when you make code changes.
    ```bash
    poetry run uvicorn src.ticket_tracker.main:app --reload
    ```
    The API will be available at `http://127.0.0.1:8000`.

---

## 📂 Project Structure

The project follows a modern, scalable structure, separating concerns into distinct modules.

```
ticket-tracker/
├── .env                  # (You create this) Holds secret keys & config
├── .gitignore
├── Dockerfile            # Defines the application's container image
├── docker-compose.yml    # Orchestrates services (API, DB, etc.)
├── pyproject.toml        # Poetry's dependency and project manager
├── README.md             # This file
├── notebooks/            # Jupyter notebooks for experimentation
├── scripts/              # One-off utility scripts (e.g., db setup)
├── tests/                # All application tests
└── src/
    └── ticket_tracker/
        ├── main.py       # FastAPI app entry point
        ├── api/          # API layer (endpoints and routing)
        ├── agents/       # Core business logic and workflows
        ├── core/         # Project config and Pydantic schemas
        ├── db/           # Database models, sessions, and CRUD
        ├── services/     # Wrappers for external services (OCR, LLM, S3)
        └── utils/        # Helper functions
```

### Core Directories Explained

* `src/ticket_tracker/`: The main Python package for the application.
    * **`api/`**: Contains all FastAPI code. The `endpoints` sub-directory defines the actual API routes for users (`receipts.py`) and admins (`admin.py`).
    * **`agents/`**: The brain of the application. This is where the multi-step logic from the architecture diagram lives.
        * `receipt_processing_agent.py`: Implements **Agent 1** for the OCR -> LLM -> DB pipeline.
        * `query_analysis_agent.py`: Implements **Agent 2** for the RAG-based query system.
    * **`services/`**: Provides clean interfaces to external systems. For example, `ocr.py` might contain a function that takes an image and returns text, hiding the specific library used. `llm.py` handles prompt formatting and calls to the OpenAI API.
    * **`db/`**: Handles all database interactions.
        * `models.py`: Defines the database tables using SQLAlchemy ORM.
        * `crud.py`: Contains reusable functions for creating, reading, updating, and deleting data (e.g., `create_receipt(...)`).
    * **`core/`**: Holds application-wide code.
        * `config.py`: Manages settings and secrets loaded from the `.env` file.
        * `schemas.py`: Defines the Pydantic data models used for API validation and data structuring.
* `tests/`: Contains unit and integration tests for the application.
* `scripts/`: Useful for operational tasks like seeding your database with initial data.
* `notebooks/`: A sandbox for experimenting with models, prompts, and data before formalizing the code into the `src` directory.