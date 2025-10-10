# Cost Optimization Strategy

## Monthly Budget Management

**Default Budget**: $100/month  
**Budget Allocation**:
- Content processing: 60% ($60)
- Daily digest: 20% ($20)
- Search queries: 15% ($15)
- Maintenance tasks: 5% ($5)

## Model Pricing (GPT-5 Family)

| Model | Input ($/1M tokens) | Output ($/1M tokens) | Use Case |
|-------|---------------------|----------------------|----------|
| gpt-5-nano | $0.05 | $0.40 | URL screening, classification, simple extraction |
| gpt-5-mini | $0.25 | $2.00 | Summarization, analysis, moderate reasoning |
| gpt-5 | $1.25 | $10.00 | Complex reasoning, validation, critique |

## Task Complexity Mapping

### LOW Complexity → gpt-5-nano ($0.05/1M)

**Tasks**:
- URL screening (relevance check)
- Content type classification
- Simple keyword extraction
- Duplicate detection
- Topic categorization

**Typical Usage**:
- Input: 500-1000 tokens (URL + context)
- Output: 100-200 tokens (JSON response)
- Cost per call: ~$0.0001

**Example Cost**:
- 10,000 URLs screened/month
- ~$1.00/month

### MEDIUM Complexity → gpt-5-mini ($0.25/1M)

**Tasks**:
- Content summarization
- Named entity recognition
- Sentiment analysis
- Key concept extraction
- Relationship identification

**Typical Usage**:
- Input: 3000-5000 tokens (full article)
- Output: 500-1000 tokens (summary + metadata)
- Cost per call: ~$0.002

**Example Cost**:
- 100 articles processed/month
- ~$0.20/month

### HIGH Complexity → gpt-5 ($1.25/1M)

**Tasks**:
- Deep content analysis
- Knowledge graph reasoning
- Content quality validation
- Complex query answering
- Multi-document synthesis

**Typical Usage**:
- Input: 8000-10000 tokens (multiple docs)
- Output: 1000-2000 tokens (detailed analysis)
- Cost per call: ~$0.03

**Example Cost**:
- 20 complex queries/month
- ~$0.60/month

## OpenAI Tools Pricing

### web_search
- **Cost**: $10 per 1,000 calls + content token costs
- **When to use**: Real-time information needed, fact-checking
- **Default**: DISABLED (too expensive for bulk operations)
- **Enable for**: High-value queries, current events

### file_search
- **Cost**: $2.50 per 1,000 calls
- **When to use**: Searching within uploaded documents
- **Default**: ENABLED (cost-effective for local library search)
- **Optimizations**: 
  - Index only high-quality content (tier A/B)
  - Batch queries when possible

### code_interpreter
- **Cost**: $0.03 per session
- **When to use**: Data analysis, visualization generation
- **Default**: DISABLED
- **Enable for**: Special maintenance tasks, analysis requests

### image_generation
- **Cost**: Varies by model ($0.040-$0.120 per image)
- **When to use**: Visual content creation
- **Default**: DISABLED
- **Not currently used** in Williams Framework

## Caching Strategy

### Prompt Caching (7-Day TTL)

**Cached Elements**:
1. System prompts (screening, summarization)
2. Few-shot examples
3. Taxonomy definitions
4. User preferences

**Savings**:
- Cached tokens: 50% discount
- Average cache hit rate: 70%
- **Estimated savings**: 35% on repeated operations

**Example**:
```python
# Screening prompt (same for all URLs)
SCREENING_SYSTEM_PROMPT = """
You are an AI research librarian...
[1000 tokens]
"""
# First call: 1000 tokens @ $0.05/1M = $0.00005
# Cached calls (7 days): 1000 tokens @ $0.025/1M = $0.000025
# Savings per call: 50%
```

### Result Caching (Redis)

**Cached Results**:
- URL screening results (30 days)
- Summarization outputs (90 days)
- Search query results (7 days)

**Benefits**:
- Instant response for repeated queries
- Zero API cost for cache hits
- **Cache hit rate target**: 40% for searches

## Batch Processing

### Batch Size Optimization

**Small batches (5-10 items)**:
- URL screening
- Topic classification
- Quality checks

**Large batches (20-50 items)**:
- Daily digest generation
- Knowledge graph updates
- Similarity calculations

**Cost Savings**:
- Single API call instead of N calls
- Amortized overhead costs
- **Estimated savings**: 20-30% vs individual calls

**Example**:
```python
# Individual calls (10 URLs)
# 10 calls × $0.0001 = $0.001

# Batch call (10 URLs in one request)
# 1 call × $0.0007 = $0.0007
# Savings: 30%
```

## Token Optimization

### Input Token Reduction

**Techniques**:
1. **Truncation**: Limit article length to 5000 tokens max
2. **Smart chunking**: Process in segments with overlap
3. **Metadata stripping**: Remove non-essential HTML/formatting
4. **Context pruning**: Only send relevant sections

**Example**:
```python
# Before: 15,000 token article
# After: 5,000 token article (first + middle + last sections)
# Savings: 67% token reduction
```

### Output Token Management

**Techniques**:
1. **Structured output**: JSON schema enforcement (shorter than prose)
2. **Length limits**: `max_tokens` parameter
3. **Temperature control**: Lower temp = more concise

**Example**:
```python
{
    "max_tokens": 500,  # Limit summary length
    "temperature": 0.3,  # Concise output
    "response_format": {"type": "json_object"}  # Structured
}
```

## Cost Tracking

### Real-Time Monitoring

**Tracked Metrics**:
- Cost per request
- Cost per content item
- Daily/monthly spending
- Per-model usage
- Per-feature breakdown

**Budget Alerts**:
- 70% budget reached → Warning
- 90% budget reached → Throttle non-essential tasks
- 100% budget reached → Pause all operations

### Cost Dashboard

```python
@dataclass
class CostMetrics:
    total_spent: float
    budget_remaining: float
    cost_by_model: Dict[str, float]
    cost_by_feature: Dict[str, float]
    avg_cost_per_item: float
    most_expensive_items: List[Tuple[str, float]]
```

**Visualization**:
- Daily spending trend
- Model usage breakdown
- Cost per content type
- Projected monthly cost

## Optimization Recommendations

### Daily Operations

**Screening (10 URLs/day)**:
- Model: gpt-5-nano
- Input: 500 tokens × 10 = 5k tokens
- Output: 100 tokens × 10 = 1k tokens
- Cost: (5k × $0.05 + 1k × $0.40) / 1M = **$0.0007/day**
- Monthly: **$0.02**

**Processing (3 articles/day)**:
- Model: gpt-5-mini
- Input: 4000 tokens × 3 = 12k tokens
- Output: 500 tokens × 3 = 1.5k tokens
- Cost: (12k × $0.25 + 1.5k × $2.00) / 1M = **$0.006/day**
- Monthly: **$0.18**

**Daily Digest (1/day)**:
- Model: gpt-5-mini
- Input: 8000 tokens (all day's content)
- Output: 1000 tokens (digest)
- Cost: (8k × $0.25 + 1k × $2.00) / 1M = **$0.004/day**
- Monthly: **$0.12**

**Search Queries (5/day)**:
- Model: gpt-5-mini
- Input: 3000 tokens × 5 = 15k tokens
- Output: 500 tokens × 5 = 2.5k tokens
- Cost: (15k × $0.25 + 2.5k × $2.00) / 1M = **$0.009/day**
- Monthly: **$0.27**

### Monthly Projections

**Base Usage** (daily operations above):
- Screening: $0.02
- Processing: $0.18
- Digest: $0.12
- Search: $0.27
- **Total**: **$0.59/month**

**With Caching (35% savings)**:
- **Total**: **$0.38/month**

**Safety Margin** (for experimentation, maintenance):
- Budget: $100/month
- Baseline: $0.38/month
- **Available for experiments**: **$99.62/month**

## Cost vs. Quality Tradeoffs

### When to Use Higher-Tier Models

**Upgrade from nano → mini**:
- Content quality score > 9.0
- User-flagged as important
- Complex content type (academic papers)

**Upgrade from mini → standard**:
- High-value research tasks
- Multi-document synthesis
- Critical knowledge validation

**ROI Calculation**:
```python
def should_upgrade_model(content: ProcessedContent) -> bool:
    """Decide if higher-tier model is worth the cost"""
    
    # Quality-based
    if content.quality_score > 9.0:
        return True
    
    # Value-based (user preferences)
    if content.topic in user.high_priority_topics:
        return True
    
    # Complexity-based
    if content.word_count > 10000:
        return True
    
    return False
```

## Emergency Cost Controls

### Budget Overrun Response

**70% Budget Used**:
- Log warning
- Notify user
- Continue normal operations

**90% Budget Used**:
- Pause low-priority tasks:
  - Background maintenance
  - Knowledge graph building
  - Automated curation
- Continue essential tasks:
  - User-initiated searches
  - Explicit content additions

**100% Budget Used**:
- Pause all API calls
- Use cached results only
- Notify user
- Provide cost report

### Cost Optimization Modes

**Economy Mode** (50% cost reduction):
- Use only gpt-5-nano
- Aggressive caching
- Batch size = 50
- Skip knowledge graph updates

**Standard Mode** (default):
- Tiered model selection
- Normal caching
- Batch size = 10
- Regular knowledge graph updates

**Performance Mode** (higher quality):
- Prefer higher-tier models
- Minimal caching
- Batch size = 5
- Real-time knowledge graph updates

## Future Optimizations

### Model Distillation
- Train local models on curated data
- Use for screening/classification
- Reserve API calls for complex tasks
- **Potential savings**: 80% on routine tasks

### Hybrid Search
- Local embeddings (sentence-transformers)
- API only for reranking
- **Potential savings**: 90% on search costs

### Smart Scheduling
- Process during off-peak hours (if pricing available)
- Batch similar tasks
- Prioritize by ROI

## Cost Monitoring Tools

### CLI Commands

```bash
# View current spending
poetry run librarian costs show

# View breakdown by feature
poetry run librarian costs breakdown

# Set budget alert threshold
poetry run librarian costs set-alert 70

# Export cost report
poetry run librarian costs export --format csv
```

### API Endpoints

```python
GET /api/costs/current        # Current month spending
GET /api/costs/forecast        # Projected end-of-month cost
GET /api/costs/by-feature      # Feature breakdown
POST /api/costs/set-budget     # Update budget
```

### Prometheus Metrics

```python
# Cost metrics
librarian_api_cost_total
librarian_api_cost_by_model
librarian_api_tokens_used_total

# Budget metrics
librarian_budget_remaining
librarian_budget_utilization_percent

# Efficiency metrics
librarian_cache_hit_rate
librarian_cost_per_processed_item
```

## Best Practices

1. **Always set max_tokens**: Prevent runaway costs
2. **Use streaming for long responses**: Early termination if needed
3. **Implement circuit breakers**: Stop on repeated errors
4. **Cache aggressively**: Especially for repeated prompts
5. **Batch when possible**: Amortize API overhead
6. **Monitor continuously**: Set up alerts
7. **Test with small batches**: Verify cost before scaling
8. **Use lowest-tier model**: Upgrade only when necessary
9. **Leverage prompt caching**: Keep prompts stable
10. **Set monthly budget**: Hard limit to prevent surprises
