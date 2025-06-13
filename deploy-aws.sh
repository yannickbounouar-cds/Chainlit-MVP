#!/bin/bash

# AWS App Runner Deployment Script for Chainlit App
# Much simpler than ECS - App Runner handles most of the infrastructure!

set -e

# Configuration
AWS_REGION="us-east-1"
APP_RUNNER_SERVICE_NAME="chainlit-app"
ECR_REPO_NAME="chainlit-app"
AWS_PROFILE=""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --profile)
            AWS_PROFILE="$2"
            shift 2
            ;;
        --region)
            AWS_REGION="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [--profile PROFILE_NAME] [--region REGION]"
            echo "  --profile: AWS CLI profile to use (optional)"
            echo "  --region:  AWS region (default: us-east-1)"
            echo "  --help:    Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}❌ Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Set AWS CLI profile flag if provided
AWS_CLI_ARGS=""
if [[ -n "$AWS_PROFILE" ]]; then
    AWS_CLI_ARGS="--profile $AWS_PROFILE"
    echo -e "${BLUE}Using AWS profile: $AWS_PROFILE${NC}"
fi

echo -e "${GREEN}🚀 Starting AWS App Runner deployment for Chainlit app...${NC}"
echo -e "${BLUE}Region: $AWS_REGION${NC}"

# Check if AWS CLI is configured
if ! aws sts get-caller-identity $AWS_CLI_ARGS &>/dev/null; then
    if [[ -n "$AWS_PROFILE" ]]; then
        echo -e "${RED}❌ Error: AWS CLI profile '$AWS_PROFILE' not configured or invalid.${NC}"
        echo -e "${YELLOW}Available profiles:${NC}"
        aws configure list-profiles 2>/dev/null || echo "No profiles found"
    else
        echo -e "${RED}❌ Error: AWS CLI not configured. Please run 'aws configure' first.${NC}"
    fi
    exit 1
fi

# Get AWS account ID
ACCOUNT_ID=$(aws sts get-caller-identity $AWS_CLI_ARGS --query Account --output text)
ECR_URI="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}"

echo -e "${YELLOW}📦 Building and pushing Docker image to ECR...${NC}"

# Create ECR repository if it doesn't exist
if ! aws ecr describe-repositories --repository-names ${ECR_REPO_NAME} --region ${AWS_REGION} $AWS_CLI_ARGS &>/dev/null; then
    echo -e "${BLUE}Creating ECR repository...${NC}"
    aws ecr create-repository --repository-name ${ECR_REPO_NAME} --region ${AWS_REGION} $AWS_CLI_ARGS
fi

# Get ECR login token
aws ecr get-login-password --region ${AWS_REGION} $AWS_CLI_ARGS | docker login --username AWS --password-stdin ${ECR_URI}

# Build and tag Docker image
docker build -t ${ECR_REPO_NAME} .
docker tag ${ECR_REPO_NAME}:latest ${ECR_URI}:latest

# Push image to ECR
docker push ${ECR_URI}:latest

echo -e "${GREEN}✅ Docker image pushed successfully!${NC}"

# Create App Runner service configuration
cat > apprunner-service.json << EOF
{
  "ServiceName": "${APP_RUNNER_SERVICE_NAME}",
  "SourceConfiguration": {
    "ImageRepository": {
      "ImageIdentifier": "${ECR_URI}:latest",
      "ImageConfiguration": {
        "Port": "8000",
        "RuntimeEnvironmentVariables": {
          "CHAINLIT_HOST": "0.0.0.0",
          "CHAINLIT_PORT": "8000",
          "AZURE_OPENAI_ENDPOINT": "https://platform-core-hackathon-ndtibpy.openai.azure.com",
          "AZURE_OPENAI_DEPLOYMENT": "openai-gpt4o-mini",
          "AZURE_OPENAI_API_VERSION": "2025-01-01-preview"
        }
      },
      "ImageRepositoryType": "ECR"
    },
    "AutoDeploymentsEnabled": true
  },
  "InstanceConfiguration": {
    "Cpu": "0.25 vCPU",
    "Memory": "0.5 GB"
  }
}
EOF

echo -e "${YELLOW}🔄 Checking if App Runner service exists...${NC}"

# Check if service already exists
SERVICE_ARN=$(aws apprunner list-services --query "ServiceSummaryList[?ServiceName=='${APP_RUNNER_SERVICE_NAME}'].ServiceArn" --output text --region ${AWS_REGION} $AWS_CLI_ARGS)

if [[ -n "$SERVICE_ARN" ]] && aws apprunner describe-service --service-arn "$SERVICE_ARN" --region ${AWS_REGION} $AWS_CLI_ARGS &>/dev/null; then
    echo -e "${BLUE}Service exists, updating...${NC}"
    # Update existing service
    aws apprunner start-deployment \
        --service-arn "$SERVICE_ARN" \
        --region ${AWS_REGION} $AWS_CLI_ARGS
else
    echo -e "${BLUE}Creating new App Runner service...${NC}"
    # Create new service
    aws apprunner create-service \
        --cli-input-json file://apprunner-service.json \
        --region ${AWS_REGION} $AWS_CLI_ARGS
fi

echo -e "${GREEN}✅ App Runner deployment initiated!${NC}"
echo -e "${YELLOW}📝 Next steps:${NC}"

# Update instructions to include profile flag if used
PROFILE_FLAG=""
if [[ -n "$AWS_PROFILE" ]]; then
    PROFILE_FLAG=" --profile $AWS_PROFILE"
fi

echo -e "1. Set your Azure OpenAI API key in AWS Systems Manager Parameter Store:"
echo -e "   ${BLUE}aws ssm put-parameter --name '/chainlit/azure-openai-api-key' --value 'YOUR_API_KEY' --type 'SecureString' --region ${AWS_REGION}${PROFILE_FLAG}${NC}"
echo -e "2. Monitor deployment status:"
echo -e "   ${BLUE}aws apprunner describe-service --service-arn \$(aws apprunner list-services --query \"ServiceSummaryList[?ServiceName=='${APP_RUNNER_SERVICE_NAME}'].ServiceArn\" --output text --region ${AWS_REGION}${PROFILE_FLAG}) --region ${AWS_REGION}${PROFILE_FLAG}${NC}"
echo -e "3. Get your app URL when deployment is complete:"
echo -e "   ${BLUE}aws apprunner describe-service --service-arn \$(aws apprunner list-services --query \"ServiceSummaryList[?ServiceName=='${APP_RUNNER_SERVICE_NAME}'].ServiceArn\" --output text --region ${AWS_REGION}${PROFILE_FLAG}) --query 'Service.ServiceUrl' --output text --region ${AWS_REGION}${PROFILE_FLAG}${NC}"

# Clean up temporary file
rm -f apprunner-service.json

echo -e "${GREEN}🎉 Deployment script completed! Your Chainlit app will be available shortly.${NC}"#!/bin/bash

# AWS App Runner Deployment Script for Chainlit App
# Much simpler than ECS - App Runner handles most of the infrastructure!

set -e

# Configuration
AWS_REGION="us-east-1"
APP_RUNNER_SERVICE_NAME="chainlit-app"
ECR_REPO_NAME="chainlit-app"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting AWS App Runner deployment for Chainlit app...${NC}"

# Check if AWS CLI is configured
if ! aws sts get-caller-identity &>/dev/null; then
    echo -e "${RED}❌ Error: AWS CLI not configured. Please run 'aws configure' first.${NC}"
    exit 1
fi

# Get AWS account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_URI="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}"

echo -e "${YELLOW}📦 Building and pushing Docker image to ECR...${NC}"

# Create ECR repository if it doesn't exist
if ! aws ecr describe-repositories --repository-names ${ECR_REPO_NAME} --region ${AWS_REGION} &>/dev/null; then
    echo -e "${BLUE}Creating ECR repository...${NC}"
    aws ecr create-repository --repository-name ${ECR_REPO_NAME} --region ${AWS_REGION}
fi

# Get ECR login token
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_URI}

# Build and tag Docker image
docker build -t ${ECR_REPO_NAME} .
docker tag ${ECR_REPO_NAME}:latest ${ECR_URI}:latest

# Push image to ECR
docker push ${ECR_URI}:latest

echo -e "${GREEN}✅ Docker image pushed successfully!${NC}"

# Create App Runner service configuration
cat > apprunner-service.json << EOF
{
  "ServiceName": "${APP_RUNNER_SERVICE_NAME}",
  "SourceConfiguration": {
    "ImageRepository": {
      "ImageIdentifier": "${ECR_URI}:latest",
      "ImageConfiguration": {
        "Port": "8000",
        "RuntimeEnvironmentVariables": {
          "CHAINLIT_HOST": "0.0.0.0",
          "CHAINLIT_PORT": "8000",
          "AZURE_OPENAI_ENDPOINT": "https://platform-core-hackathon-ndtibpy.openai.azure.com",
          "AZURE_OPENAI_DEPLOYMENT": "openai-gpt4o-mini",
          "AZURE_OPENAI_API_VERSION": "2025-01-01-preview"
        }
      },
      "ImageRepositoryType": "ECR"
    },
    "AutoDeploymentsEnabled": true
  },
  "InstanceConfiguration": {
    "Cpu": "0.25 vCPU",
    "Memory": "0.5 GB"
  }
}
EOF

echo -e "${YELLOW}🔄 Checking if App Runner service exists...${NC}"

# Check if service already exists
if aws apprunner describe-service --service-arn $(aws apprunner list-services --query "ServiceSummaryList[?ServiceName=='${APP_RUNNER_SERVICE_NAME}'].ServiceArn" --output text) --region ${AWS_REGION} &>/dev/null; then
    echo -e "${BLUE}Service exists, updating...${NC}"
    # Update existing service
    aws apprunner start-deployment \
        --service-arn $(aws apprunner list-services --query "ServiceSummaryList[?ServiceName=='${APP_RUNNER_SERVICE_NAME}'].ServiceArn" --output text) \
        --region ${AWS_REGION}
else
    echo -e "${BLUE}Creating new App Runner service...${NC}"
    # Create new service
    aws apprunner create-service \
        --cli-input-json file://apprunner-service.json \
        --region ${AWS_REGION}
fi

echo -e "${GREEN}✅ App Runner deployment initiated!${NC}"
echo -e "${YELLOW}📝 Next steps:${NC}"
echo -e "1. Set your Azure OpenAI API key in AWS Systems Manager Parameter Store:"
echo -e "   ${BLUE}aws ssm put-parameter --name '/chainlit/azure-openai-api-key' --value 'YOUR_API_KEY' --type 'SecureString'${NC}"
echo -e "2. Monitor deployment status:"
echo -e "   ${BLUE}aws apprunner describe-service --service-arn \$(aws apprunner list-services --query \"ServiceSummaryList[?ServiceName=='${APP_RUNNER_SERVICE_NAME}'].ServiceArn\" --output text)${NC}"
echo -e "3. Get your app URL when deployment is complete:"
echo -e "   ${BLUE}aws apprunner describe-service --service-arn \$(aws apprunner list-services --query \"ServiceSummaryList[?ServiceName=='${APP_RUNNER_SERVICE_NAME}'].ServiceArn\" --output text) --query 'Service.ServiceUrl' --output text${NC}"

# Clean up temporary file
rm -f apprunner-service.json

echo -e "${GREEN}🎉 Deployment script completed! Your Chainlit app will be available shortly.${NC}"
