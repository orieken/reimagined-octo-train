@description('Specifies the location for resources.')
param location string = resourceGroup().location

@description('Prefix for all resource names')
param prefix string = 'fridaybot'

@description('App Service Plan SKU')
param appServicePlanSku string = 'B1'

@description('Bot App ID')
param botId string

@description('Bot App Password')
@secure()
param botPassword string

@description('Friday API URL')
param fridayApiUrl string

@description('Friday API Key')
@secure()
param fridayApiKey string

@description('Azure DevOps Organization URL')
param azureDevOpsOrgUrl string

@description('Azure DevOps Project')
param azureDevOpsProject string

@description('Azure DevOps Personal Access Token')
@secure()
param azureDevOpsPat string

// App Service Plan
resource appServicePlan 'Microsoft.Web/serverfarms@2021-02-01' = {
  name: '${prefix}-plan'
  location: location
  sku: {
    name: appServicePlanSku
  }
  properties: {
    reserved: true
  }
  kind: 'linux'
}

// Web App for Bot
resource webApp 'Microsoft.Web/sites@2021-02-01' = {
  name: '${prefix}-app'
  location: location
  properties: {
    serverFarmId: appServicePlan.id
    siteConfig: {
      linuxFxVersion: 'NODE|16-lts'
      appSettings: [
        {
          name: 'MicrosoftAppId'
          value: botId
        }
        {
          name: 'MicrosoftAppPassword'
          value: botPassword
        }
        {
          name: 'FRIDAY_API_URL'
          value: fridayApiUrl
        }
        {
          name: 'FRIDAY_API_KEY'
          value: fridayApiKey
        }
        {
          name: 'AZURE_DEVOPS_ORG_URL'
          value: azureDevOpsOrgUrl
        }
        {
          name: 'AZURE_DEVOPS_PROJECT'
          value: azureDevOpsProject
        }
        {
          name: 'AZURE_DEVOPS_PAT'
          value: azureDevOpsPat
        }
        {
          name: 'WEBSITE_NODE_DEFAULT_VERSION'
          value: '16.14.0'
        }
        {
          name: 'NODE_ENV'
          value: 'production'
        }
        {
          name: 'LOG_LEVEL'
          value: 'info'
        }
        {
          name: 'APPINSIGHTS_INSTRUMENTATIONKEY'
          value: appInsights.properties.InstrumentationKey
        }
      ]
      healthCheckPath: '/health'
    }
  }
}

// Bot Service Registration
resource botService 'Microsoft.BotService/botServices@2021-05-01-preview' = {
  name: '${prefix}-bot'
  location: 'global'
  sku: {
    name: 'F0'
  }
  kind: 'bot'
  properties: {
    displayName: 'Friday Metrics Bot'
    endpoint: 'https://${webApp.properties.defaultHostName}/api/messages'
    msaAppId: botId
    developerAppInsightKey: appInsights.properties.InstrumentationKey
  }
}

// Teams Channel for Bot
resource botServiceTeamsChannel 'Microsoft.BotService/botServices/channels@2021-05-01-preview' = {
  parent: botService
  name: 'MsTeamsChannel'
  location: 'global'
  properties: {
    properties: {
      isEnabled: true
    }
  }
}

// App Insights
resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: '${prefix}-insights'
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalyticsWorkspace.id
  }
}

// Log Analytics Workspace
resource logAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2020-10-01' = {
  name: '${prefix}-workspace'
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

// Key Vault
resource keyVault 'Microsoft.KeyVault/vaults@2021-06-01-preview' = {
  name: '${prefix}-kv'
  location: location
  properties: {
    enabledForDeployment: true
    enabledForTemplateDeployment: true
    enabledForDiskEncryption: true
    tenantId: subscription().tenantId
    accessPolicies: [
      {
        tenantId: subscription().tenantId
        objectId: webApp.identity.principalId
        permissions: {
          secrets: [
            'get'
            'list'
          ]
        }
      }
    ]
    sku: {
      name: 'standard'
      family: 'A'
    }
  }
}

// Key Vault Secrets
resource botPasswordSecret 'Microsoft.KeyVault/vaults/secrets@2021-06-01-preview' = {
  parent: keyVault
  name: 'BotPassword'
  properties: {
    value: botPassword
  }
}

resource fridayApiKeySecret 'Microsoft.KeyVault/vaults/secrets@2021-06-01-preview' = {
  parent: keyVault
  name: 'FridayApiKey'
  properties: {
    value: fridayApiKey
  }
}

resource azureDevOpsPatSecret 'Microsoft.KeyVault/vaults/secrets@2021-06-01-preview' = {
  parent: keyVault
  name: 'AzureDevOpsPat'
  properties: {
    value: azureDevOpsPat
  }
}

// Outputs
output webAppUrl string = 'https://${webApp.properties.defaultHostName}'
output appInsightsKey string = appInsights.properties.InstrumentationKey
output keyVaultUri string = keyVault.properties.vaultUri