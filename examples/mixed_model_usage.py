"""
Example: Using different model tiers for different complexity levels.

This demonstrates the multi-provider tier system where you can:
1. Use cheap/fast models (NANO) for simple tasks
2. Use balanced models (MINI) for moderate complexity
3. Use powerful models (STANDARD) for complex reasoning
4. Use maximum capability models (PRO) for autonomous agents

Cost optimization: Start with local ($0), upgrade to hosted only when needed.
"""

from app.intelligence.providers.factory import ProviderFactory


def example_mixed_model_usage():
    """Demonstrate using different models for different complexity levels."""
    
    # Create factory instance
    factory = ProviderFactory()
    
    # ============= SCENARIO 1: Data Extraction (Simple) =============
    # Use NANO tier - fast, cheap, high volume
    # Could be local (llama3.2) or anthropic (Haiku) depending on load
    
    print("=" * 60)
    print("SCENARIO 1: Data Extraction - NANO tier")
    print("=" * 60)
    
    # Option A: Use local model (FREE)
    nano_local = factory.create_llm_provider("local-nano")
    response = nano_local.generate(
        prompt="Extract the phone number: Contact us at 555-1234",
        max_tokens=50
    )
    print(f"Local NANO (llama3.2): {response}")
    print(f"Cost: $0.00 (local compute)\n")
    
    # Option B: Use Anthropic Haiku (when you need consistency/speed)
    nano_anthropic = factory.create_llm_provider("anthropic-nano")
    response = nano_anthropic.generate(
        prompt="Extract the phone number: Contact us at 555-1234",
        max_tokens=50
    )
    print(f"Anthropic NANO (Haiku): {response}")
    print(f"Cost: ~$0.0001 per request\n")
    
    
    # ============= SCENARIO 2: Code Generation (Moderate) =============
    # Use MINI tier - balanced performance
    # Could be local (llama3.1:8b) or openai (gpt-4o) or anthropic (Sonnet 4)
    
    print("=" * 60)
    print("SCENARIO 2: Code Generation - MINI tier")
    print("=" * 60)
    
    code_prompt = """
    Write a Python function to calculate Fibonacci numbers recursively.
    Include docstring and type hints.
    """
    
    # Option A: Try local first (FREE)
    mini_local = factory.create_llm_provider("local-mini")
    response = mini_local.generate(prompt=code_prompt, max_tokens=300)
    print(f"Local MINI (llama3.1:8b): {response[:200]}...")
    print(f"Cost: $0.00\n")
    
    # Option B: Upgrade to OpenAI if local quality isn't sufficient
    mini_openai = factory.create_llm_provider("openai-mini")
    response = mini_openai.generate(prompt=code_prompt, max_tokens=300)
    print(f"OpenAI MINI (gpt-4o): {response[:200]}...")
    print(f"Cost: ~$0.0015 per request\n")
    
    
    # ============= SCENARIO 3: Complex Analysis (Advanced) =============
    # Use STANDARD tier - deep reasoning
    # Could be local (mistral:7b) or anthropic (Sonnet 4.5) or openai (gpt-4o)
    
    print("=" * 60)
    print("SCENARIO 3: Complex Analysis - STANDARD tier")
    print("=" * 60)
    
    analysis_prompt = """
    Analyze the architectural tradeoffs between microservices and monoliths
    for a growing SaaS startup. Consider:
    - Team size and expertise
    - Deployment complexity
    - Scalability needs
    - Development velocity
    
    Provide specific recommendations with reasoning.
    """
    
    # For complex reasoning, often better to use hosted models
    standard_anthropic = factory.create_llm_provider("anthropic-standard")
    response = standard_anthropic.generate(
        prompt=analysis_prompt,
        max_tokens=1000,
        system_prompt="You are an expert software architect."
    )
    print(f"Anthropic STANDARD (Sonnet 3.5): {response[:300]}...")
    print(f"Cost: ~$0.01 per request\n")
    
    
    # ============= SCENARIO 4: Autonomous Agent (Maximum) =============
    # Use PRO tier - maximum capability
    # No local equivalent - must use openai (o1-preview) or anthropic (Opus)
    
    print("=" * 60)
    print("SCENARIO 4: Autonomous Coding Agent - PRO tier")
    print("=" * 60)
    
    agent_prompt = """
    You are an autonomous coding agent. Analyze this codebase issue and propose
    a complete solution with implementation steps:
    
    Issue: The authentication system needs to support OAuth2 with multiple
    providers (Google, GitHub, Microsoft). Currently only supports username/password.
    
    Provide:
    1. Architecture changes needed
    2. Database schema modifications
    3. New endpoint designs
    4. Security considerations
    5. Testing strategy
    """
    
    # PRO tier for multi-step reasoning and planning
    pro_openai = factory.create_llm_provider("openai-pro")
    response = pro_openai.generate(
        prompt=agent_prompt,
        max_tokens=4000,
        system_prompt="You are an expert software architect and senior engineer."
    )
    print(f"OpenAI PRO (o1-preview): {response[:300]}...")
    print(f"Cost: ~$0.15 per request (but worth it for complex tasks)\n")


def example_dynamic_tier_selection():
    """
    Example: Dynamically select tier based on task complexity.
    
    This is the REAL power - your application can automatically choose
    the right model based on the task requirements.
    """
    
    print("\n" + "=" * 60)
    print("DYNAMIC TIER SELECTION")
    print("=" * 60 + "\n")
    
    def get_llm_for_task(task_type: str, use_local: bool = True):
        """
        Select appropriate LLM tier based on task complexity.
        
        Args:
            task_type: Type of task (extraction, coding, analysis, planning)
            use_local: Prefer local models when possible ($0 cost)
        
        Returns:
            LLM provider instance
        """
        
        tier_mapping = {
            "extraction": "nano",      # Simple data extraction
            "summary": "nano",         # Document summarization
            "qa": "mini",              # Question answering
            "coding": "mini",          # Code generation
            "analysis": "standard",    # Complex analysis
            "reasoning": "standard",   # Multi-step reasoning
            "planning": "pro",         # Strategic planning
            "agent": "pro",            # Autonomous agents
        }
        
        tier = tier_mapping.get(task_type, "mini")
        
        if use_local:
            # Try local first (FREE)
            provider_name = f"local-{tier}"
            if tier == "pro":
                # No local PRO equivalent, fallback to STANDARD
                print(f"⚠️  No local PRO model, using local-standard instead")
                provider_name = "local-standard"
        else:
            # Use hosted (better quality, costs money)
            # Prefer Anthropic for most tasks, OpenAI for PRO
            if tier == "pro":
                provider_name = "openai-pro"
            else:
                provider_name = f"anthropic-{tier}"
        
        print(f"📊 Task: {task_type:<12} → Tier: {tier:<10} → Provider: {provider_name}")
        return factory.create_llm_provider(provider_name)
    
    
    # Example usage
    tasks = [
        ("extraction", True),   # Use local NANO
        ("summary", True),      # Use local NANO
        ("coding", True),       # Use local MINI
        ("analysis", False),    # Use Anthropic STANDARD (better quality)
        ("planning", False),    # Use OpenAI PRO (maximum capability)
    ]
    
    for task_type, use_local in tasks:
        llm = get_llm_for_task(task_type, use_local)
        # Now use llm for the actual task


def example_cost_optimized_strategy():
    """
    Example: Cost-optimized strategy with automatic fallbacks.
    
    Start with cheapest option, upgrade only if needed.
    """
    
    print("\n" + "=" * 60)
    print("COST-OPTIMIZED STRATEGY WITH FALLBACKS")
    print("=" * 60 + "\n")
    
    def generate_with_fallback(prompt: str, max_tokens: int = 500):
        """
        Try models in order of cost (cheapest first).
        Upgrade only if quality isn't sufficient.
        """
        
        # Try local NANO first (FREE)
        try:
            print("🔄 Trying local-nano (FREE)...")
            llm = factory.create_llm_provider("local-nano")
            response = llm.generate(prompt, max_tokens=max_tokens)
            
            # Simple quality check (you could make this more sophisticated)
            if len(response) > 20 and "error" not in response.lower():
                print("✅ Success with local-nano (cost: $0.00)")
                return response
            else:
                print("⚠️  Local-nano response insufficient, trying next tier...")
        except Exception as e:
            print(f"❌ Local-nano failed: {e}")
        
        # Fallback to Anthropic NANO (cheap but better)
        try:
            print("🔄 Trying anthropic-nano ($)...")
            llm = factory.create_llm_provider("anthropic-nano")
            response = llm.generate(prompt, max_tokens=max_tokens)
            
            if len(response) > 20:
                print("✅ Success with anthropic-nano (cost: ~$0.0002)")
                return response
        except Exception as e:
            print(f"❌ Anthropic-nano failed: {e}")
        
        # Final fallback to Anthropic STANDARD (expensive but reliable)
        print("🔄 Trying anthropic-standard ($$)...")
        llm = factory.create_llm_provider("anthropic-standard")
        response = llm.generate(prompt, max_tokens=max_tokens)
        print("✅ Success with anthropic-standard (cost: ~$0.002)")
        return response
    
    
    # Example: Start cheap, upgrade if needed
    prompt = "Explain quantum entanglement in simple terms."
    response = generate_with_fallback(prompt)
    print(f"\nFinal response: {response[:200]}...")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("MULTI-PROVIDER TIER SYSTEM EXAMPLES")
    print("=" * 60 + "\n")
    
    # Run examples
    example_mixed_model_usage()
    example_dynamic_tier_selection()
    example_cost_optimized_strategy()
    
    print("\n" + "=" * 60)
    print("COST SUMMARY")
    print("=" * 60)
    print("""
    Tier Strategy:
    
    NANO (Fast/Cheap):
    - Local: $0.00 (llama3.2 3B)
    - Anthropic: $0.0008/1M input, $0.004/1M output (Haiku)
    - OpenAI: $0.00015/1M input, $0.0006/1M output (gpt-4o-mini)
    - Use for: Data extraction, summaries, high-volume simple tasks
    
    MINI (Balanced):
    - Local: $0.00 (llama3.1:8b)
    - Anthropic: $0.003/1M input, $0.015/1M output (Sonnet 4)
    - OpenAI: $0.0025/1M input, $0.010/1M output (gpt-4o)
    - Use for: Code generation, Q&A, chatbots, agentic tasks
    
    STANDARD (Advanced):
    - Local: $0.00 (mistral:7b)
    - Anthropic: $0.003/1M input, $0.015/1M output (Sonnet 3.5)
    - OpenAI: $0.0025/1M input, $0.010/1M output (gpt-4o)
    - Use for: Complex analysis, autonomous agents, cybersecurity
    
    PRO (Maximum):
    - Local: N/A (no local equivalent)
    - Anthropic: $0.015/1M input, $0.075/1M output (Opus)
    - OpenAI: $0.015/1M input, $0.060/1M output (o1-preview)
    - Use for: Multi-hour research, complex refactoring, specialized science
    
    Strategy: Start with local (FREE), upgrade to hosted only when quality demands it.
    """)
