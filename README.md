[![Build Status](https://img.shields.io/badge/Status-Feature%20Complete-green)](https://github.com/pooch41/kobold-keeper-api)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![GitHub contributors](https://img.shields.io/github/contributors/Pooch41/kobold-keeper-api)](https://github.com/Pooch41/kobold-keeper-api/graphs/contributors)[![Project Maintenance](https://img.shields.io/maintenance/yes/2025)](https://github.com/your-repo/kobold-keeper-api)


# **Kobold Keeper API**

## **🎲 What is Kobold Keeper?**

Kobold Keeper is a powerful, self-hosted API designed to manage and automate dice-rolling tasks for **role-playing game (RPG) sessions**, focusing primarily on game master (GM) utility. It serves as a backend hub for various tools, allowing GMs to centralize data, run complex dice rolls, and review dice rolling statistics per group, character or even globally.  
This project is built with Python and Django Rest Framework (DRF), offering a robust, secure, and scalable foundation for your digital tabletop needs.

### **Key Features**

* **Advanced Dice Roller:** Supports complex algebraic expressions, drop/keep logic, and modifiers (e.g., 3d6 \+ 5, 2d20kh1, 1d8 \+ 5d6 \+ 4).  
* **Roll analytics:** Allows users to review their past and present rolls in terms of raw dice breakdown, averages and comparisons versus statistical averages of the standard dice type.  
* **Secure User Management:** Full authentication and authorization via Django's built-in system and JWT.  
* **Asynchronous Tasks (Celery):** Handles long-running or resource-intensive tasks, such as large data exports or complex simulations, without blocking the main API thread.

## **⚔️ Getting Started (Local Development)**

To run Kobold Keeper locally for development, you'll need **Docker** and **Docker Compose**. This setup ensures all dependencies (**PostgreSQL** database, **Redis** cache, **Celery worker**, and **Celery Beat scheduler**) are managed easily using the `docker-compose.dev.yml` file.

### **Prerequisites**

1. **Docker** and **Docker Compose** installed on your system.  
2. A .env file created in the project root (see ExampleEnv for structure).

### **1\. Clone the Repository**

``git clone \[https://github.com/Pooch41/kobold-keeper-api.git\](https://github.com/Pooch41/kobold-keeper-api.git)``  

``cd kobold-keeper-api``

### **2\. Configure Environment**

Copy the example environment file. This new .env file is already in .gitignore and will **never** be committed.  
cp example.env .env  
#### Edit your new .env file with your local passwords  
#### Set DEBUG=True

### **3\. Build and Run Local Services**

Execute the following command to build the Docker images and start all services (api, worker, beat, db, redis) in detached mode.  
#### Use the \-f flag to specify the dev file  
``docker-compose \-f docker-compose.dev.yml up \--build \-d``

The API will be available @ http://localhost:8000.  
**API Schema (Swagger UI):** http://localhost:8000/api/schema/swagger-ui/

### **4\. Create a Superuser**

In a separate terminal, run this command to create your local admin account:  
``docker-compose \-f docker-compose.dev.yml exec api python manage.py createsuperuser``

## **🚀 Deployment (Remote)**

This project uses a two-file system for safe, repeatable deployments.

* ``docker-compose.dev.yml``: Used **locally** to **build** and **push** images.  
* ``docker-compose.yml``: Used **remotely** (on your server) to **pull** and **run** images.

## **1\. (Local) Build & Push New Images**

After making code changes, you must build the new, secure images and push them to Docker Hub. The .dockerignore file ensures your final images are small and secure (no .env, testing/, or .git files are included).  
#### 1. (Optional) Log in to Docker Hub  
``docker login \--username {your_username}``

#### 2. Build new images using the dev file  
``docker-compose \-f docker-compose.dev.yml build``

#### 3. Push the new images to Docker Hub  
``docker-compose \-f docker-compose.dev.yml push``

## **2\. (Remote) Deploy New Images on Server**

SSH into your AWS server and run the following commands. These use the server's docker-compose.yml file.  
#### 1. Navigate to your project directory  
``cd /path/to/your/project``

#### 2\. Pull the new images you just pushed  
``docker-compose \-f docker-compose.yml pull``

#### 3\. Stop and remove the old containers  
``docker-compose \-f docker-compose.yml down``

#### 4\. Start all services with the new images (in detached mode)  
(This will automatically run migrations first)  

``docker-compose \-f docker-compose.yml up \-d``

#### 5\. Collect any new static files  
``docker-compose \-f docker-compose.yml exec api python manage.py collectstatic \--noinput``

#### 6\. (Optional) Clean up old, unused images  
``docker image prune``

## **🧙‍♂️ Testing**

The project uses **Pytest** for unit and integration testing. Tests are run *inside* the running api container.

### **Running Pytest**

While your local stack is running, open a **second terminal** and run:  
``docker-compose \-f docker-compose.dev.yml exec api pytest``

## **⚙️ Celery Workers & Scheduled Tasks**

The application uses Celery for background processing.

* **Worker:** The worker service executes tasks asynchronously.  
* **Beat:** The beat service is the scheduler that polls the database for periodic tasks.

To monitor the activity of all services:

### **View all logs in real-time**

``docker-compose \-f docker-compose.dev.yml logs \-f``

## **🛠️ Project Structure**

| File | Description |
| :---- | :---- |
| api/ | Main Django app for views, serializers, and models. |
| kobold\_keeper/ | Core Django project settings, URLs, and Celery setup. |
| testing/ | All pytest and unittest files. |
| Dockerfile | The single, multi-stage build recipe for all app images. |
| docker-compose.dev.yml | **Local:** Runs the full stack (app, db, redis) and builds images. |
| docker-compose.yml | **Remote:** Runs the app services only (pulls images). |
| .dockerignore | **Security:** Prevents secrets, tests, and git history from being built into images. |

## **🤝 Contribution**

We welcome contributions\! As an open-source project, your help is invaluable.

1. **Fork** the repository and clone your fork.  
2. Create your feature branch (git checkout \-b feature/new-dice-logic).  
3. Commit your changes (git commit \-am 'Refactor: Improved logic').  
4. Create a new **Pull Request** to the **main development branch**.

### **❗Code Quality Standards**

We enforce strict quality checks using **Pylint**. Before submitting a pull request, please ensure your changes pass the quality checks:  
``docker-compose \-f docker-compose.dev.yml exec api pylint kobold\_keeper api``

## **📜 License**

Kobold Keeper API is released under the MIT License. See the LICENSE file for more details.