// Mock environment variables for testing
process.env.NODE_ENV = 'test';
process.env.FRIDAY_API_URL = 'https://test-api.friday-service.example.com/v1';
process.env.FRIDAY_API_KEY = 'test-api-key';
process.env.MicrosoftAppId = 'test-app-id';
process.env.MicrosoftAppPassword = 'test-app-password';
process.env.AZURE_DEVOPS_ORG_URL = 'https://dev.azure.com/test-organization';
process.env.AZURE_DEVOPS_PROJECT = 'test-project';
process.env.AZURE_DEVOPS_PAT = 'test-pat';

// Global Jest timeout (5 seconds)
jest.setTimeout(5000);