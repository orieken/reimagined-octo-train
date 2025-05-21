# Friday Metrics Teams Bot

A Microsoft Teams bot that queries the Friday service to relay test metrics using Adaptive Cards.

## Project Structure

```
friday-metrics-bot/
├── .github/
│   └── workflows/
│       └── azure-deploy.yml     # GitHub Actions workflow for CI/CD
├── src/
│   ├── adapters/                # External service adapters (Clean Architecture)
│   │   ├── fridayServiceAdapter.js
│   │   └── teamsAdapter.js
│   ├── bot/
│   │   ├── botActivity.js       # Bot activity handlers
│   │   ├── botDialogs.js        # Bot dialog definitions
│   │   └── adaptiveCards/
│   │       ├── metricCard.json  # Adaptive card templates
│   │       └── cardBuilder.js   # Card building utilities
│   ├── config/
│   │   └── config.js            # Configuration management
│   ├── domain/
│   │   ├── entities/            # Domain entities
│   │   │   ├── testMetric.js
│   │   │   └── testReport.js
│   │   ├── services/            # Domain services
│   │   │   └── metricsService.js
│   │   └── useCases/            # Application use cases
│   │       └── getTestMetrics.js
│   ├── infrastructure/          # Infrastructure concerns
│   │   ├── logging/
│   │   │   └── logger.js
│   │   └── persistence/
│   │       └── cacheService.js
│   └── index.js                 # Application entry point
├── test/
│   ├── unit/                    # Unit tests
│   │   ├── adapters/
│   │   ├── bot/
│   │   ├── domain/
│   │   └── infrastructure/
│   └── integration/             # Integration tests
├── .env.example                 # Example environment variables
├── .eslintrc.js                 # ESLint configuration
├── .gitignore                   # Git ignore file
├── package.json                 # NPM package configuration
├── README.md                    # Project documentation
└── terraform/                   # Infrastructure as Code for Azure deployment
    ├── main.tf
    ├── variables.tf
    └── outputs.tf
```

## Core Technologies

- **Node.js** - Runtime environment
- **Bot Framework SDK v4** - For building the Teams bot
- **Adaptive Cards** - For rich, interactive UI in Teams
- **Jest** - For unit and integration testing
- **Azure Bot Service** - For hosting the bot
- **Azure App Service** - For hosting the API backend
- **Azure Key Vault** - For secrets management
- **GitHub Actions** - For CI/CD pipeline
- **Terraform** - For infrastructure as code

## Design Patterns & Principles

- **Clean Architecture** - Separation of concerns with layers (Domain, Application, Infrastructure, Adapters)
- **Dependency Injection** - For loose coupling and testability
- **Repository Pattern** - For data access abstraction
- **Command/Query Responsibility Segregation (CQRS)** - For separation of read and write operations
- **Adapter Pattern** - For interfacing with external services
- **Factory Pattern** - For creating complex objects
- **Strategy Pattern** - For interchangeable algorithms
- **Observer Pattern** - For event handling