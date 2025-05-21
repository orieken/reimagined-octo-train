# Friday Metrics Teams Bot

A Microsoft Teams bot that queries the Friday service API to display test metrics using Adaptive Cards and integrates with Azure DevOps.

## Features

- **Real-time Metrics**: View the latest test metrics for your projects
- **Failed Test Analysis**: Quickly identify and analyze failed tests
- **Trend Visualization**: Track test metrics over time with visual charts
- **Build Comparison**: Compare metrics between builds
- **Azure DevOps Integration**: Link test results with build information and create work items for failed tests
- **Proactive Notifications**: Get notified about important test results

## Architecture

This project follows Clean Architecture principles to maintain separation of concerns and facilitate testing:

### Core Components

#### Domain Layer
- **Entities**: Core business objects (TestMetric, TestReport)
- **Use Cases**: Application-specific business rules for interacting with the domain

#### Adapter Layer
- **FridayServiceAdapter**: Connects to the Friday service API
- **TeamsAdapter**: Handles Teams-specific functionality
- **AzureDevOpsAdapter**: Integrates with Azure DevOps

#### Infrastructure Layer
- **Logger**: Centralized logging using Winston
- **CacheService**: In-memory caching for improved performance
- **ConfigService**: Configuration management

#### Bot Layer
- **MetricsBot**: Main bot activity handler
- **Dialogs**: Conversation flow management
- **AdaptiveCards**: Rich, interactive UI for Teams

## Technology Stack

- **TypeScript** - Typed JavaScript for better developer experience
- **Node.js** - Runtime environment
- **Bot Framework SDK v4** - For building the Teams bot
- **Teams Toolkit** - For simplified Teams integration
- **Adaptive Cards** - For rich, interactive UI in Teams
- **Jest** - For unit and integration testing
- **Winston** - For logging
- **Azure Bot Service** - For hosting the bot
- **Azure App Service** - For hosting the API backend
- **Azure Key Vault** - For secrets management
- **GitHub Actions** - For CI/CD pipeline
- **Azure Bicep** - For infrastructure as code

## Getting Started

### Prerequisites

- Node.js 16.x or higher
- npm 7.x or higher
- Microsoft Teams
- Azure subscription (for deployment)
- Azure DevOps organization/project (for DevOps integration)

### Local Development

1. Clone the repository:
   ```bash
   git clone https://github.com/your-org/friday-metrics-bot.git
   cd friday-metrics-bot
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Set up your environment variables by copying the `.env.example` file:
   ```bash
   cp .env.example .env
   ```

4. Update the `.env` file with your configuration:
   ```
   # Bot Framework Configuration
   MicrosoftAppId=<your-microsoft-app-id>
   MicrosoftAppPassword=<your-microsoft-app-password>
   
   # Friday Service Configuration
   FRIDAY_API_URL=<your-friday-api-url>
   FRIDAY_API_KEY=<your-friday-api-key>
   
   # Azure DevOps Configuration
   AZURE_DEVOPS_ORG_URL=<your-azure-devops-org-url>
   AZURE_DEVOPS_PROJECT=<your-azure-devops-project>
   AZURE_DEVOPS_PAT=<your-azure-devops-personal-access-token>
   ```

5. Start the development server:
   ```bash
   npm run dev
   ```

6. To debug the bot locally, you'll need to use ngrok or the Teams Toolkit provided dev tunnel.

### Testing

Run tests with:
```bash
# Run all tests
npm test

# Run tests with coverage
npm run test:coverage

# Run tests in watch mode
npm run test:watch
```

## Deployment

This project supports deployment to Azure using GitHub Actions for CI/CD:

1. Set up the following secrets in your GitHub repository:
    - `AZURE_CREDENTIALS`: Azure service principal credentials JSON
    - `AZURE_SUBSCRIPTION_ID`: Azure subscription ID
    - `AZURE_RESOURCE_GROUP`: Azure resource group name
    - `BOT_APP_ID`: Bot App ID from Azure
    - `BOT_APP_PASSWORD`: Bot App password from Azure
    - `FRIDAY_API_KEY`: Friday service API key
    - `AZURE_DEVOPS_PAT`: Azure DevOps personal access token

2. Push to the `main` branch to trigger the deployment workflow.

## Using the Bot

Once installed in Teams, you can interact with the bot using the following commands:

- `help`: Show available commands and information
- `metrics [projectId]`: Display the latest test metrics for a project
- `failed [projectId] [buildNumber]`: List tests that failed in a specific build
- `trends [projectId]`: Display charts showing test metrics over time
- `compare [projectId] [buildNumber1] [buildNumber2]`: Compare metrics between builds

## Adaptive Cards

The bot uses Adaptive Cards to present information in a structured and interactive format:

- **Welcome Card**: Shows the available commands and features
- **Metrics Card**: Displays test metrics summary with pass/fail stats
- **Failed Tests Card**: Shows details of failed tests and allows creating work items
- **Chart Card**: Displays trend charts for pass rate, duration, and test count
- **Build Comparison Card**: Shows comparison between two builds

## Azure DevOps Integration

The bot integrates with Azure DevOps to:

1. Link test reports with Azure DevOps builds
2. Display build information alongside test metrics
3. Create work items for failed tests
4. Use Azure DevOps API to access additional build and test information

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -am 'Add my feature'`
4. Push to the branch: `git push origin feature/my-feature`
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.