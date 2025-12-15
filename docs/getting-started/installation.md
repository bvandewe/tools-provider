# Installation

This guide will walk you through setting up the project for local development.

## Prerequisites

Before you begin, ensure you have the following installed:

- **Docker and Docker Compose**: For running the application and its services in a containerized environment.
- **Python 3.12+**: For running the application locally.
- **Poetry**: For managing Python dependencies.
- **Node.js 18+**: For building the frontend assets.

## Installation Steps

1. **Clone the repository**:

    ```bash
    git clone https://github.com/bvandewe/tools-provider.git
    cd tools-provider
    ```

2. **Install Python dependencies**:
    Use Poetry to install the required Python packages.

    ```bash
    make setup
    ```

    This command will create virtual environments for both tools-provider and agent-host, and install all dependencies.

3. **Install pre-commit hooks**:
    This project uses pre-commit hooks to enforce code quality. Install them by running:

    ```bash
    make install-hooks
    ```

4. **Build UI assets**:
    The frontend assets are built using Parcel.

    ```bash
    make build-ui
    ```

## Using as a Template

This repository is designed to be used as a template for new projects.

1. **Create a new repository from this template**:
    Click the "Use this template" button on the GitHub repository page to create a new repository with the same structure and files.

2. **Rename the project**:
    After cloning your new repository, run the `rename_project.py` script to update the project name throughout the codebase.

    ```bash
    python scripts/rename_project.py --new-name "Your New Project Name"
    ```

    This will replace all occurrences of "Starter App" and its variants (e.g., `starter-app`, `starter_app`) with your new project name. It is recommended to run with the `--dry-run` flag first to see the changes before they are applied.
