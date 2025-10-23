# Kobold Keeper API

[![Build Status](https://img.shields.io/badge/Status-Feature%20Complete-green)](https://github.com/pooch41/kobold-keeper-api)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Project Maintenance](https://img.shields.io/maintenance/yes/2025)](https://github.com/pooch41/kobold-keeper-api)
[![GitHub contributors](https://img.shields.io/github/contributors/Pooch41/kobold-keeper-api)](https://github.com/Pooch41/kobold-keeper-api/graphs/contributors)[![Project Maintenance](https://img.shields.io/maintenance/yes/2025)](https://github.com/your-repo/kobold-keeper-api)

---

## 🎲 What is Kobold Keeper?

Kobold Keeper is a powerful, self-hosted API designed to manage and automate dice-rolling tasks for **role-playing game (RPG) sessions**, focusing primarily on game master (GM) utility. It serves as a backend hub for various tools, allowing GMs to centralize data, run complex dice rolls, and review dice rolling statistics per group, character or even globally.

This project is built with Python and Django Rest Framework (DRF), offering a robust, secure, and scalable foundation for your digital tabletop needs.

### Key Features

* **Advanced Dice Roller:** Supports complex algebraic expressions, `drop/keep` logic, and modifiers (e.g., `3d6 + 5`, `2d20kh1`, `4dF`).
* **Roll analytics:** Allows users to review their past and present rolls in terms of raw dice breakdown, averages and comparisons versus statistical averages of the standard dice type
* **Secure User Management:** Full authentication and authorization via Django's built-in system and custom JWT logic.
* **Asynchronous Tasks (Celery):** Handles long-running or resource-intensive tasks, such as large data exports or complex simulations, without blocking the main API thread.

---

## ⚔️ Getting Started

To run Kobold Keeper locally for development or as a self-hosted instance, you'll need **Docker** and **Docker Compose**. This setup ensures all dependencies (PostgreSQL database, Redis cache, Celery worker) are managed easily.

### Prerequisites

1.  **Docker** and **Docker Compose** installed on your system.
2.  A `.env` file created in the project root (see `Example.env` for structure).

### 1. Clone the Repository

```bash
git clone [https://github.com/Pooch41/kobold-keeper-api.git](https://github.com/Pooch41/kobold-keeper-api.git)
cd kobold-keeper-api
```

### 2. Configure Environment

Copy the example environment file and update the variables for production or development use.

```bash
cp Example.env .env
# Edit .env to set secure keys, database credentials, and any external service tokens.
```

### 3. Build and Run Services

Execute the following command to build the Docker images and start all required services (API, PostgreSQL, Redis, Celery):
```bash
docker compose up --build
```

The API will be available @ http://localhost:8000.

### 4. Apply Migrations

Once the services are running, apply the database migrations to set up your tables:

```bash
docker compose exec api python manage.py migrate
```

## 🛠️ Project Structure

This project follows a standard Django structure with clearly defined application responsibilities:

| Directory | Description |
| :--- | :--- |
| `api/` | Main application logic for Django REST Framework views, serializers, and permissions, including business logic related to dice rolling and authentication. |
| `kobold_keeper/` | Core Django settings, URLs, and root configuration for the entire project. |
| `docs/` | **Future home for dedicated documentation (e.g., `API_REFERENCE.md`).** |
| `docker-compose.yml` | Defines the multi-container environment (API, DB, Cache, Worker). |

---

## 🤝 Contribution

We welcome contributions! As an open-source project, your help is invaluable for improving stability, adding features, and refining the user experience.

1.  **Fork** the repository and clone your fork.
2.  Create your feature branch (e.g., `git checkout -b feature/new-dice-logic`).
3.  Commit your changes (`git commit -am 'Refactor: Improved logic for drop/keep rolls'`).
4.  Create a new **Pull Request** to the **main development branch**.

### ❗Code Quality Standards

We enforce strict quality checks using **Pylint**. Before submitting a pull request, please ensure your changes pass the quality checks:

```bash
docker compose run --rm api pylint api kobold_keeper
```

## 📜 License

Kobold Keeper API is released under the MIT License. See the `LICENSE` file for more details.

