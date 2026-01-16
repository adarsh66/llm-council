using './main.bicep'

param location = 'eastus2'
param namePrefix = 'ai-expert-council'
param planSkuName = 'B1'
param pythonVersion = '3.11'

// Set this from your .env
param azureInferenceEndpoint = 'https://aistudiohubeas4430902054.services.ai.azure.com/models'

// Writable persistent path on Linux App Service
param dataDir = '/home/data/conversations'

// Optionally set a globally unique name; if left empty Bicep will generate one.
param webAppName = ''

// Resource ID of your existing Azure AI Foundry resource for RBAC assignment.
// Format: /subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.CognitiveServices/accounts/{name}
// Leave empty to skip RBAC in Bicep and assign manually via CLI instead.
param aiFoundryResourceId = 'aistudiohubeas4430902054'
