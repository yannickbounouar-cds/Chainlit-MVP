# Chainlit App with Azure OpenAI

A modern conversational AI application built with Chainlit and powered by Azure OpenAI's GPT-4o-mini model. This application is designed for easy local development and seamless deployment to AWS.

## 🚀 Features

- **Azure OpenAI Integration**: Powered by GPT-4o-mini model
- **Chainlit Framework**: Modern conversational UI
- **Docker Support**: Containerized for consistent environments
- **AWS App Runner**: Simple production deployment with automatic scaling
- **Environment Management**: Secure configuration handling

## 📋 Prerequisites

- Python 3.11+
- Docker (for containerized deployment)
- AWS CLI (for AWS deployment)
- Azure OpenAI API access

## 🛠️ Local Development Setup

### Quick Start

1. **Clone and navigate to the project**:
   ```bash
   cd /Users/yannick.bounouar/Chainlit-MVP
   ```

2. **Run the setup script**:
   ```bash
   ./run-local.sh
   ```

3. **Update your environment variables**:
   - Copy `.env.example` to `.env`
   - Add your actual Azure OpenAI API key to `.env`

4. **Start the application**:
   ```bash
   source venv/bin/activate
   chainlit run app.py
   ```

5. **Open your browser** to `http://localhost:8000`

### Manual Setup

1. **Create virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your actual API key
   ```

4. **Run the application**:
   ```bash
   chainlit run app.py
   ```

## 🔧 Configuration

### Environment Variables

Required environment variables in your `.env` file:

```env
# Azure OpenAI Configuration
AZURE_OPENAI_API_KEY=your_actual_azure_openai_api_key_here
AZURE_OPENAI_ENDPOINT=https://platform-core-hackathon-ndtibpy.openai.azure.com
AZURE_OPENAI_DEPLOYMENT=openai-gpt4o-mini
AZURE_OPENAI_API_VERSION=2025-01-01-preview

# Chainlit Configuration
CHAINLIT_HOST=0.0.0.0
CHAINLIT_PORT=8000
```

### Chainlit Configuration

The app is configured via `.chainlit` file with:
- Custom branding and description
- Security settings
- UI preferences
- Telemetry disabled by default

## 🐳 Docker Development

### Using Docker Compose (Recommended)

```bash
# Start the application
docker-compose up --build

# Run in background
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop the application
docker-compose down
```

### Using Docker directly

```bash
# Build the image
docker build -t chainlit-app .

# Run the container
docker run -p 8000:8000 --env-file .env chainlit-app
```

## ☁️ AWS Deployment

### Prerequisites

1. **Configure AWS CLI**:
   ```bash
   aws configure
   ```

2. **Create required AWS resources**:
   - ECS Cluster named `chainlit-cluster`
   - ECS Service named `chainlit-service`
   - IAM roles for ECS tasks
   - AWS Secrets Manager secret for API key

### Deploy to AWS

1. **Update AWS configuration**:
   - Edit `aws/ecs-task-definition.json`
   - Replace placeholders with your AWS account details

2. **Run deployment script**:
   ```bash
   ./deploy-aws.sh
   ```

## ☁️ AWS App Runner Deployment

Deploy your Chainlit app to AWS App Runner with automatic scaling and SSL:

1. **Configure AWS CLI**:
   ```bash
   aws configure
   ```

2. **Run deployment script**:
   ```bash
   ./deploy-aws.sh
   ```

3. **Set your API key in AWS Systems Manager**:
   ```bash
   aws ssm put-parameter \
     --name '/chainlit/azure-openai-api-key' \
     --value 'your_actual_api_key' \
     --type 'SecureString'
   ```

4. **Get your app URL**:
   ```bash
   aws apprunner describe-service \
     --service-arn $(aws apprunner list-services \
       --query "ServiceSummaryList[?ServiceName=='chainlit-app'].ServiceArn" \
       --output text) \
     --query 'Service.ServiceUrl' --output text
   ```

### App Runner Benefits
- ✅ Automatic scaling from zero
- ✅ Built-in load balancing
- ✅ SSL certificates included
- ✅ No infrastructure management
- ✅ Pay only for usage


## 📁 Project Structure

```
├── app.py                          # Main Chainlit application
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment template
├── .env                           # Local environment (create from example)
├── .chainlit                      # Chainlit configuration
├── Dockerfile                     # Docker container definition
├── docker-compose.yml             # Local Docker development
├── apprunner.yaml                 # AWS App Runner configuration
├── run-local.sh                   # Local development script
├── deploy-aws.sh                  # AWS App Runner deployment script
└── .github/
    └── copilot-instructions.md    # GitHub Copilot instructions
```

## 🔒 Security

- ✅ Environment variables for sensitive data
- ✅ No API keys in source code
- ✅ AWS Secrets Manager integration
- ✅ Non-root Docker user
- ✅ Health checks configured

## 🚨 Important Notes

1. **Never commit your `.env` file** - it contains sensitive API keys
2. **Update AWS account details** in the ECS task definition
3. **Configure AWS Secrets Manager** for production deployment
4. **Test locally first** before deploying to AWS

## 🆘 Troubleshooting

### Common Issues

1. **"Module not found" errors**:
   - Ensure virtual environment is activated
   - Run `pip install -r requirements.txt`

2. **Azure OpenAI connection errors**:
   - Verify your API key in `.env`
   - Check network connectivity
   - Ensure correct endpoint URL

3. **Docker build failures**:
   - Check Docker is running
   - Ensure sufficient disk space
   - Try `docker system prune` to clean up

4. **AWS deployment issues**:
   - Verify AWS CLI configuration
   - Check IAM permissions
   - Ensure ECS cluster exists

## 📚 Resources

- [Chainlit Documentation](https://docs.chainlit.io/)
- [Azure OpenAI Documentation](https://docs.microsoft.com/en-us/azure/cognitive-services/openai/)
- [AWS ECS Documentation](https://docs.aws.amazon.com/ecs/)
- [Model Context Protocol](https://modelcontextprotocol.io/)

## 🤝 Contributing

1. Create a feature branch
2. Make your changes
3. Test locally and with Docker
4. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
