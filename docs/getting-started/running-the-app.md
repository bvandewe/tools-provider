# Running the Application

Once you have installed the dependencies, you can run the application using Docker Compose.

## Running with Docker

The `Makefile` provides several commands to manage the application services.

- **Start all services**:

    ```bash
    make up
    ```

    This will start the application, database, and other services in the background.

- **View service URLs**:

    ```bash
    make urls
    ```

    This command displays the URLs for the running services, including the main application, API docs, and Keycloak.

- **View logs**:

    ```bash
    make logs-app
    ```

    This will show the logs for the main application service.

- **Stop all services**:

    ```bash
    make down
    ```

    This will stop and remove all running containers.

## Accessing the Application

- **Tools Provider Web App**: [http://localhost:8040](http://localhost:8040)
- **API Docs (Swagger UI)**: [http://localhost:8040/api/docs](http://localhost:8040/api/docs)
- **Agent Host Chat**: [http://localhost:8042](http://localhost:8042)
- **Keycloak Admin Console**: [http://localhost:8041](http://localhost:8041)
  - **Username**: `admin`
  - **Password**: `admin`
- **EventStoreDB**: [http://localhost:2113](http://localhost:2113)
  - **Username**: `admin`
  - **Password**: `changeit`
- **Mongo Express**: [http://localhost:8043](http://localhost:8043)
  - **Username**: `admin@admin.com`
  - **Password**: `admin`

## Server Binding Configuration

For security, the Uvicorn server binds to `127.0.0.1` by default. If you need to expose the API outside of your machine, explicitly override the binding address:

```bash
export APP_HOST=0.0.0.0
export APP_PORT=8080
```

Only use `0.0.0.0` when you understand the networking implications and have secured the environment.
