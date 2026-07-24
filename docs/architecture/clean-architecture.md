# Clean Architecture

The system is organized as:

Presentation Layer -> API Layer -> Service Layer -> Business Logic Layer -> Repository Layer -> Database

Each module owns its API routes, controller boundary, service facade, domain package, repository dependencies, schemas, and tests.
