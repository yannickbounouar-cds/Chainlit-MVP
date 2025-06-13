<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

# Chainlit App with Azure OpenAI - Copilot Instructions

## Project Overview
This is a Chainlit application integrated with Azure OpenAI GPT-4o-mini, designed for easy deployment on AWS and local development.

## Key Technologies
- **Chainlit**: Python framework for building conversational AI applications
- **Azure OpenAI**: GPT-4o-mini model for chat completions
- **Docker**: Containerization for deployment
- **AWS ECS**: Production deployment platform

## Architecture
- `app.py`: Main Chainlit application with Azure OpenAI integration
- `requirements.txt`: Python dependencies
- `Dockerfile` & `docker-compose.yml`: Containerization
- `aws/`: AWS deployment configurations
- `deploy-aws.sh`: AWS deployment script
- `run-local.sh`: Local development script

## Development Guidelines
1. **Environment Variables**: Always use environment variables for API keys and configuration
2. **Error Handling**: Implement proper try-catch blocks for external API calls
3. **Async/Await**: Use async patterns for better performance with Chainlit
4. **Docker**: Ensure all changes work in containerized environment
5. **AWS Compatibility**: Consider ECS deployment requirements

## Azure OpenAI Configuration
- Endpoint: `https://platform-core-hackathon-ndtibpy.openai.azure.com`
- Model: `openai-gpt4o-mini`
- API Version: `2025-01-01-preview`

## Security Notes
- Never commit actual API keys to version control
- Use AWS Secrets Manager for production secrets
- Environment variables for local development

When suggesting code changes:
- Follow the existing async/await patterns
- Maintain compatibility with both local and AWS deployment
- Ensure proper error handling and logging
