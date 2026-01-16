#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# deploy_appservice.sh
# Deploy AI Expert Council to Azure App Service (single-host: backend + frontend)
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# ─── Configuration ────────────────────────────────────────────────────────────
RESOURCE_GROUP="${RESOURCE_GROUP:-ai-expert-council-rg}"
LOCATION="${LOCATION:-eastus2}"
BICEP_FILE="infra/main.bicep"
PARAMS_FILE="infra/params.dev.bicepparam"

# Azure AI Foundry resource for RBAC (update this with your resource name)
AI_FOUNDRY_RESOURCE_NAME="${AI_FOUNDRY_RESOURCE_NAME:-aistudiohubeas4430902054}"

# ─── Colors ───────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}   AI Expert Council - Azure App Service Deployment${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"

# ─── Step 1: Create Resource Group ────────────────────────────────────────────
echo -e "\n${YELLOW}[1/5] Creating resource group: ${RESOURCE_GROUP}${NC}"
az group create \
  --name "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --output none
echo -e "${GREEN}✓ Resource group ready${NC}"

# ─── Step 2: Deploy Bicep (App Service Plan + Web App) ────────────────────────
echo -e "\n${YELLOW}[2/5] Deploying infrastructure via Bicep...${NC}"
DEPLOYMENT_OUTPUT=$(az deployment group create \
  --resource-group "$RESOURCE_GROUP" \
  --template-file "$BICEP_FILE" \
  --parameters "$PARAMS_FILE" \
  --query "properties.outputs" \
  --output json)

WEB_APP_NAME=$(echo "$DEPLOYMENT_OUTPUT" | jq -r '.webAppNameOut.value')
WEB_APP_URL=$(echo "$DEPLOYMENT_OUTPUT" | jq -r '.webAppUrl.value')
PRINCIPAL_ID=$(echo "$DEPLOYMENT_OUTPUT" | jq -r '.webAppPrincipalId.value')

echo -e "${GREEN}✓ Infrastructure deployed${NC}"
echo -e "  Web App Name: ${CYAN}$WEB_APP_NAME${NC}"
echo -e "  URL:          ${CYAN}$WEB_APP_URL${NC}"
echo -e "  Principal ID: ${CYAN}$PRINCIPAL_ID${NC}"

# ─── Step 3: Assign RBAC to Azure AI Foundry ──────────────────────────────────
echo -e "\n${YELLOW}[3/5] Granting Managed Identity access to Azure AI Foundry...${NC}"

# Find the AI Foundry resource ID (searches all resource groups in subscription)
AI_FOUNDRY_ID=$(az cognitiveservices account list \
  --query "[?name=='$AI_FOUNDRY_RESOURCE_NAME'].id | [0]" \
  --output tsv 2>/dev/null || echo "")

if [[ -z "$AI_FOUNDRY_ID" ]]; then
  echo -e "${YELLOW}⚠ Could not find AI Foundry resource '$AI_FOUNDRY_RESOURCE_NAME'${NC}"
  echo "  You may need to assign RBAC manually after deployment:"
  echo "  az role assignment create \\"
  echo "    --assignee-object-id $PRINCIPAL_ID \\"
  echo "    --assignee-principal-type ServicePrincipal \\"
  echo "    --role 'Cognitive Services User' \\"
  echo "    --scope <your-ai-foundry-resource-id>"
else
  az role assignment create \
    --assignee-object-id "$PRINCIPAL_ID" \
    --assignee-principal-type ServicePrincipal \
    --role "Cognitive Services User" \
    --scope "$AI_FOUNDRY_ID" \
    --output none 2>/dev/null || echo -e "${YELLOW}(Role may already be assigned)${NC}"
  echo -e "${GREEN}✓ RBAC assigned: Cognitive Services User on $AI_FOUNDRY_RESOURCE_NAME${NC}"
fi

# ─── Step 4: Build & Package Application ──────────────────────────────────────
echo -e "\n${YELLOW}[4/5] Building and packaging application...${NC}"
./scripts/package_appservice_zip.sh
echo -e "${GREEN}✓ Package created: appservice.zip${NC}"

# ─── Step 5: Deploy ZIP to Web App ────────────────────────────────────────────
echo -e "\n${YELLOW}[5/5] Deploying application to App Service...${NC}"
az webapp deploy \
  --resource-group "$RESOURCE_GROUP" \
  --name "$WEB_APP_NAME" \
  --src-path appservice.zip \
  --type zip \
  --output none

echo -e "${GREEN}✓ Application deployed${NC}"

# ─── Done ─────────────────────────────────────────────────────────────────────
echo -e "\n${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ Deployment complete!${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "\n  🌐 Open your app: ${CYAN}$WEB_APP_URL${NC}"
echo -e "  🩺 Health check:  ${CYAN}$WEB_APP_URL/api/health${NC}"
echo -e "\n  To view logs:"
echo -e "    az webapp log tail -g $RESOURCE_GROUP -n $WEB_APP_NAME"
echo ""
