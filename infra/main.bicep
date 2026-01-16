@description('Azure region for all resources')
param location string = 'eastus2'

@description('Resource name prefix (used for plan + app names)')
param namePrefix string = 'ai-expert-council'

@description('App Service Plan SKU (e.g. B1, P0v3)')
param planSkuName string = 'B1'

@description('Python version for Linux App Service')
param pythonVersion string = '3.11'

@description('Azure AI Foundry inference endpoint URL')
param azureInferenceEndpoint string

@description('Writable data directory for conversation storage (App Service persistent path is under /home)')
param dataDir string = '/home/data/conversations'

@description('Optional: A unique web app name (must be globally unique). If empty, one is generated from prefix.')
param webAppName string = ''

var resolvedWebAppName = empty(webAppName) ? '${namePrefix}-${uniqueString(resourceGroup().id)}' : webAppName
var planName = '${namePrefix}-plan'

resource plan 'Microsoft.Web/serverfarms@2022-09-01' = {
  name: planName
  location: location
  kind: 'linux'
  sku: {
    name: planSkuName
    tier: planSkuName
  }
  properties: {
    reserved: true
  }
}

resource web 'Microsoft.Web/sites@2022-09-01' = {
  name: resolvedWebAppName
  location: location
  kind: 'app,linux'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: plan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'PYTHON|${pythonVersion}'
      appCommandLine: 'gunicorn -k uvicorn.workers.UvicornWorker backend.main:app --bind 0.0.0.0:$PORT --timeout 180'
      healthCheckPath: '/api/health'
      appSettings: [
        {
          name: 'AZURE_INFERENCE_ENDPOINT'
          value: azureInferenceEndpoint
        }
        {
          name: 'DATA_DIR'
          value: dataDir
        }
        {
          name: 'WEBSITE_RUN_FROM_PACKAGE'
          value: '1'
        }
        {
          name: 'SCM_DO_BUILD_DURING_DEPLOYMENT'
          value: 'true'
        }
        {
          name: 'WEBSITES_ENABLE_APP_SERVICE_STORAGE'
          value: 'true'
        }
      ]
    }
  }
}

output webAppNameOut string = web.name
output webAppUrl string = 'https://${web.properties.defaultHostName}'
output webAppPrincipalId string = web.identity.principalId
