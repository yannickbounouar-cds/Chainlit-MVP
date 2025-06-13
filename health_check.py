#!/usr/bin/env python3

"""
Simple health check script for the Chainlit app
Tests basic imports and configuration
"""

import sys
import os

def test_imports():
    """Test that all required packages can be imported"""
    try:
        import chainlit as cl
        print("✅ Chainlit import successful")
        
        import openai
        print("✅ OpenAI import successful")
        
        from openai import AsyncAzureOpenAI
        print("✅ Azure OpenAI client import successful")
        
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_env_config():
    """Test environment configuration"""
    required_vars = [
        'AZURE_OPENAI_API_KEY',
        'AZURE_OPENAI_ENDPOINT', 
        'AZURE_OPENAI_DEPLOYMENT',
        'AZURE_OPENAI_API_VERSION'
    ]
    
    # Load environment variables
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("✅ Environment variables loaded")
    except Exception as e:
        print(f"⚠️  Could not load .env file: {e}")
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var) or os.getenv(var) == f"your_actual_{var.lower()}_here":
            missing_vars.append(var)
    
    if missing_vars:
        print(f"⚠️  Missing or placeholder environment variables: {', '.join(missing_vars)}")
        print("   Please update your .env file with actual values")
        return False
    else:
        print("✅ All required environment variables are set")
        return True

def main():
    """Run all health checks"""
    print("🏥 Running Chainlit App Health Check...\n")
    
    # Test imports
    imports_ok = test_imports()
    print()
    
    # Test environment
    env_ok = test_env_config()
    print()
    
    if imports_ok and env_ok:
        print("🎉 Health check passed! Your Chainlit app is ready to run.")
        print("\nTo start the app:")
        print("1. Make sure your .env file has your actual Azure OpenAI API key")
        print("2. Run: source venv/bin/activate")
        print("3. Run: chainlit run app.py")
        print("4. Open: http://localhost:8000")
        return 0
    else:
        print("❌ Health check failed. Please fix the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
