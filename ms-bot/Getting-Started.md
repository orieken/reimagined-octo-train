# Getting Started with Friday Metrics Bot

This guide provides step-by-step instructions to set up your development environment and run the bot locally.

## Prerequisites

1. **Node.js** - Version 16.x or higher
2. **npm** - Version 7.x or higher
3. **Microsoft Teams** - Access to a Microsoft Teams account
4. **Azure Subscription** - For bot registration and deployment
5. **Azure DevOps** - Access to an Azure DevOps organization/project
6. **ngrok** or **Dev Tunnels** - For local development tunneling

## Setup Steps

### 1. Install Development Tools

```bash
# Install ngrok for tunneling
npm install -g ngrok

# Install Teams Toolkit extension in VS Code
# OR
npm install -g @microsoft/teamsfx-cli
```

### 2. Clone the Repository

```bash
git clone https://github.com/your-org/friday-metrics-bot.git
cd friday-metrics-bot
```

### 3. Install Dependencies

```bash
npm install
```

### 4. Register a New Bot in Azure

1. Go to the [Azure Portal](https://portal.azure.com)
2. Click "Create a resource" and search for "Bot Channels Registration"
3. Fill out the required fields:
    - Bot Handle: `friday-metrics-bot`
    - Subscription: Select your subscription
    - Resource Group: Create new or select existing
    - Location: Select a location close to you
    - Pricing Tier: F0 (Free)
    - Microsoft App ID: Create new
4. Click "Create"
5. Once created, go to the "Settings" blade
6. Make note of the Microsoft App ID and generate a new Client Secret
7. Save both the App ID and Client Secret for later use

### 5. Set Up a Tunnel for Local Development

```bash
# Using ngrok
ngrok http 3978

# OR using Teams Toolkit dev tunnel
teamsfx start dev-tunnel --port 3978
```

Make note of the forwarding URL (e.g., `https://a1b2c3d4.ngrok.io`). You'll need it for the next step.

### 6. Configure Bot Messaging Endpoint

1. Go back to the bot in the Azure Portal
2. In the "Settings" blade, set the Messaging endpoint to:
   ```
   https://your-tunnel-url/api/messages
   ```
3. Click "Save"

### 7. Configure Environment Variables

1. Copy the .env.example file:
   ```bash
   cp .env.example .env
   ```

2. Edit the .env file with your information:
   ```
   # Bot Framework Configuration
   MicrosoftAppId=<your-bot-app-id>
   MicrosoftAppPassword=<your-bot-client-secret>
   
   # Friday Service Configuration
   FRIDAY_API_URL=<your-friday-api-url>
   FRIDAY_API_KEY=<your-friday-api-key>
   
   # Azure DevOps Configuration
   AZURE_DEVOPS_ORG_URL=https://dev.azure.com/your-organization
   AZURE_DEVOPS_PROJECT=your-project
   AZURE_DEVOPS_PAT=<your-personal-access-token>
   ```

### 8. Build and Run the Bot

```bash
# Build the TypeScript code
npm run build

# Start the bot
npm start

# OR for development with auto-reload
npm run dev
```

### 9. Install the Bot in Microsoft Teams

#### Using App Studio:

1. Install the App Studio app in Teams if you haven't already
2. Go to the "Manifest Editor" tab
3. Click "Create a new app"
4. Fill out the required information:
    - App Name: Friday Metrics Bot
    - Version: 1.0.0
    - Short Description: Teams bot for test metrics and Azure DevOps integration
    - Long Description: A Microsoft Teams bot that queries the Friday service API to display test metrics using Adaptive Cards and integrates with Azure DevOps.
    - Developer Name: Your name or organization
    - Website: Your website
    - Privacy Statement URL: URL to your privacy statement
    - Terms of Use URL: URL to your terms of use
5. Configure the bot:
    - Bot ID: Your Bot App ID
    - Scope: Personal, Team, Group Chat
6. Configure the messaging extension (if needed)
7. Click "Test and distribute" and then "Install" to install the bot in Teams

#### Using a Manifest Package:

1. Create a manifest package using the Teams Toolkit
   ```bash
   teamsfx package manifest --env local
   ```
2. In Teams, go to "Apps" > "Manage your apps" > "Upload an app" > "Upload a custom app"
3. Select the generated zip file from the `.fx/manifest` folder
4. Follow the prompts to install the bot

## Testing the Bot

1. In Teams, find the bot in your installed apps
2. Send a message to the bot, such as "help" or "show metrics"
3. The bot should respond with a welcome card or metrics information

## Development Workflow

1. Make changes to the TypeScript code
2. Build the changes:
   ```bash
   npm run build
   ```
3. Run tests:
   ```bash
   npm test
   ```
4. Start the bot:
   ```bash
   npm start
   ```
5. Test your changes in Teams

## Deployment to Azure

### Manual Deployment:

```bash
# Login to Azure
az login

# Deploy the infrastructure
az deployment group create --resource-group <resource-group> --template-file infra/main.bicep --parameters infra/parameters.json

# Build the app
npm run build

# Zip the deployment package
zip -r deployment.zip lib package.json package-lock.json public

# Deploy to Azure Web App
az webapp deployment source config-zip --resource-group <resource-group> --name <app-name> --src deployment.zip
```

### Using GitHub Actions:

1. Set up the required secrets in your GitHub repository
2. Push your changes to the main branch
3. The GitHub Actions workflow will automatically build, test, and deploy to Azure