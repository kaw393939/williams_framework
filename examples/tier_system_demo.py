"""
Simple example showing how to mix models for different complexity levels.
"""

from app.intelligence.providers.factory import ProviderFactory


def main():
    """Demonstrate tier-based model selection."""
    
    # Create factory
    factory = ProviderFactory()
    
    print("\n" + "=" * 70)
    print("MULTI-MODEL TIER SYSTEM DEMONSTRATION")
    print("=" * 70)
    
    # Show available providers
    print("\n📋 Available LLM Providers:")
    for provider in factory.list_llm_providers():
        print(f"   - {provider}")
    
    print("\n" + "=" * 70)
    print("TIER 1: NANO - Data Extraction (Simple/Fast/Cheap)")
    print("=" * 70)
    
    # NANO tier: Use for high-volume, simple tasks
    print("\n🔷 Using local-nano (llama3.2, FREE):")
    nano_local = factory.create_llm_provider("local-nano")
    print(f"   Model: {nano_local.model_name}")
    print(f"   Context: {nano_local.get_context_window()} tokens")
    print(f"   Cost: $0.00 (local compute)")
    print(f"   Use for: Data extraction, simple summaries, high-volume tasks")
    
    print("\n🔷 Using anthropic-nano (Haiku, $):")
    # Note: This will only work if you have ANTHROPIC_API_KEY set
    try:
        nano_anthropic = factory.create_llm_provider("anthropic-nano")
        print(f"   Model: {nano_anthropic.model_name}")
        print(f"   Context: {nano_anthropic.get_context_window()} tokens")
        print(f"   Cost: $0.0008 input / $0.004 output per 1M tokens")
        print(f"   Use for: When consistency > local quality")
    except Exception as e:
        print(f"   ⚠️  Skipped (no API key): {e}")
    
    print("\n" + "=" * 70)
    print("TIER 2: MINI - Code Generation (Balanced)")
    print("=" * 70)
    
    # MINI tier: Balanced performance
    print("\n🔶 Using local-mini (llama3.1:8b, FREE):")
    mini_local = factory.create_llm_provider("local-mini")
    print(f"   Model: {mini_local.model_name}")
    print(f"   Context: {mini_local.get_context_window()} tokens")
    print(f"   Cost: $0.00 (local compute)")
    print(f"   Use for: Code generation, Q&A, chatbots")
    
    print("\n🔶 Using openai-mini (gpt-4o, $$):")
    try:
        mini_openai = factory.create_llm_provider("openai-mini")
        print(f"   Model: {mini_openai.model_name}")
        print(f"   Context: {mini_openai.get_context_window()} tokens")
        print(f"   Cost: $0.0025 input / $0.010 output per 1M tokens")
        print(f"   Use for: When quality > cost")
    except Exception as e:
        print(f"   ⚠️  Skipped (no API key): {e}")
    
    print("\n" + "=" * 70)
    print("TIER 3: STANDARD - Complex Analysis (Advanced)")
    print("=" * 70)
    
    # STANDARD tier: Complex reasoning
    print("\n🔸 Using local-standard (mistral:7b, FREE):")
    standard_local = factory.create_llm_provider("local-standard")
    print(f"   Model: {standard_local.model_name}")
    print(f"   Context: {standard_local.get_context_window()} tokens")
    print(f"   Cost: $0.00 (local compute)")
    print(f"   Use for: Complex analysis, multi-step reasoning")
    
    print("\n🔸 Using anthropic-standard (Sonnet 3.5, $$$):")
    try:
        standard_anthropic = factory.create_llm_provider("anthropic-standard")
        print(f"   Model: {standard_anthropic.model_name}")
        print(f"   Context: {standard_anthropic.get_context_window()} tokens")
        print(f"   Cost: $0.003 input / $0.015 output per 1M tokens")
        print(f"   Use for: Autonomous agents, complex analysis")
    except Exception as e:
        print(f"   ⚠️  Skipped (no API key): {e}")
    
    print("\n" + "=" * 70)
    print("TIER 4: PRO - Maximum Capability (Premium)")
    print("=" * 70)
    
    # PRO tier: No local equivalent
    print("\n🔴 No local PRO equivalent - must use hosted:")
    
    print("\n🔴 Using openai-pro (o1-preview, $$$$):")
    try:
        pro_openai = factory.create_llm_provider("openai-pro")
        print(f"   Model: {pro_openai.model_name}")
        print(f"   Context: {pro_openai.get_context_window()} tokens")
        print(f"   Cost: $0.015 input / $0.060 output per 1M tokens")
        print(f"   Use for: Complex coding, multi-hour research, autonomous agents")
    except Exception as e:
        print(f"   ⚠️  Skipped (no API key): {e}")
    
    # REAL WORLD USAGE EXAMPLE
    print("\n" + "=" * 70)
    print("PRACTICAL EXAMPLE: Dynamic Tier Selection")
    print("=" * 70)
    
    def get_llm_for_task(task_complexity: str):
        """Select LLM based on task complexity."""
        
        # Map complexity to tier (prefer local when possible for cost)
        tier_map = {
            "simple": "local-nano",
            "moderate": "local-mini",
            "complex": "local-standard",
            "maximum": "openai-pro",  # No local equivalent
        }
        
        provider_name = tier_map.get(task_complexity, "local-mini")
        llm = factory.create_llm_provider(provider_name)
        
        return llm, provider_name
    
    
    # Examples
    tasks = [
        ("Extract email from text", "simple"),
        ("Generate Python function", "moderate"),
        ("Architectural analysis", "complex"),
        ("Multi-step refactoring plan", "maximum"),
    ]
    
    print("\n")
    for task, complexity in tasks:
        try:
            llm, provider = get_llm_for_task(complexity)
            print(f"📊 Task: {task:<30} → {complexity:<10} → {provider}")
        except Exception as e:
            print(f"📊 Task: {task:<30} → {complexity:<10} → ERROR: {e}")
    
    # COST OPTIMIZATION SUMMARY
    print("\n" + "=" * 70)
    print("COST OPTIMIZATION STRATEGY")
    print("=" * 70)
    print("""
Strategy: Start cheap, upgrade only when quality demands it

1. DEVELOPMENT (FREE):
   - Use local-nano/mini/standard for all tasks
   - Cost: $0/month (GPU compute only)
   - Quality: Good enough for most tasks

2. PRODUCTION (OPTIMIZED):
   - NANO tasks → local-nano (FREE)
   - MINI tasks → Try local-mini first, fallback to anthropic-mini if quality poor
   - STANDARD tasks → anthropic-standard (best quality/cost)
   - PRO tasks → openai-pro only when absolutely necessary
   
3. PRODUCTION (PREMIUM):
   - NANO → anthropic-nano (speed + consistency)
   - MINI → openai-mini (balanced)
   - STANDARD → anthropic-standard (advanced reasoning)
   - PRO → openai-pro (maximum capability)

Example monthly costs:
- Dev: $0 (all local)
- Production optimized: $5-50 (mostly local, hosted for quality-critical)
- Production premium: $100-1000 (hosted for everything)
    """)


if __name__ == "__main__":
    main()
