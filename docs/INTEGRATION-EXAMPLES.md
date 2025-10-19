# Williams Librarian - Integration Examples

**Version:** 2.0  
**Last Updated:** October 12, 2025  
**Purpose:** Real-world usage examples and integration patterns

---

## 🎯 Overview

This document provides **realistic, production-ready examples** of integrating Williams Librarian into various workflows.

---

## 📚 Example 1: Academic Research Workflow

### Scenario
PhD student researching quantum computing needs to:
1. Import 20 papers from arXiv
2. Generate a podcast series for learning during commute
3. Generate flashcards for memorization
4. Generate a literature review document

### Implementation

```python
import asyncio
from williams_librarian import LibrarianClient

async def academic_research_workflow():
    """Complete academic research workflow."""
    client = LibrarianClient(api_url="http://localhost:8000")
    
    # Step 1: Import papers from arXiv
    print("📚 Importing 20 papers from arXiv...")
    
    paper_urls = [
        "https://arxiv.org/abs/2401.00001",
        "https://arxiv.org/abs/2401.00002",
        # ... 18 more papers
    ]
    
    import_jobs = []
    for url in paper_urls:
        response = await client.import_content(
            url=url,
            content_type="document",
            priority=8  # High priority
        )
        import_jobs.append(response["job_id"])
        print(f"  ✓ Queued: {url}")
    
    # Wait for all imports to complete
    print("⏳ Waiting for imports to complete...")
    content_ids = []
    for job_id in import_jobs:
        content_id = await client.wait_for_job(
            job_id,
            timeout=300,  # 5 minutes per paper
            progress_callback=lambda p: print(f"  Progress: {p['progress']}% - {p['stage']}")
        )
        content_ids.append(content_id)
        print(f"  ✓ Imported: {content_id}")
    
    print(f"\n✅ Imported {len(content_ids)} papers\n")
    
    # Step 2: Generate podcast series (5 episodes, 90 minutes total)
    print("🎙️ Generating podcast series...")
    
    podcast_response = await client.export_content(
        source_ids=content_ids,
        format="podcast",
        parameters={
            "style": "educational",
            "voice": "professional_female",
            "episodes": 5,
            "duration_per_episode": 18,  # 18 minutes each
            "add_intro": True,
            "add_outro": True,
            "background_music": "ambient_learning",
            "pace": "moderate"
        }
    )
    
    podcast_job_id = podcast_response["job_id"]
    print(f"  Job ID: {podcast_job_id}")
    
    # Monitor progress via WebSocket
    async for update in client.stream_job_progress(podcast_job_id):
        print(f"  {update['stage']}: {update['progress']}%")
    
    podcast_id = await client.wait_for_job(podcast_job_id, timeout=600)
    print(f"  ✅ Generated podcast series: {podcast_id}\n")
    
    # Download podcast episodes
    podcast_info = await client.get_artifact(podcast_id)
    for i, episode in enumerate(podcast_info["episodes"], 1):
        download_url = episode["download_url"]
        await client.download_file(download_url, f"quantum_computing_ep{i}.mp3")
        print(f"  💾 Downloaded: quantum_computing_ep{i}.mp3")
    
    # Step 3: Generate flashcards (Anki-compatible)
    print("\n🗂️ Generating flashcards...")
    
    flashcards_response = await client.export_content(
        source_ids=content_ids,
        format="flashcards",
        parameters={
            "count": 250,  # 250 flashcards total
            "difficulty": "mixed",  # Easy, medium, hard
            "format": "anki",  # Anki-compatible format
            "include_images": True,
            "include_equations": True,
            "spaced_repetition": True
        }
    )
    
    flashcards_id = await client.wait_for_job(
        flashcards_response["job_id"],
        timeout=300
    )
    
    # Download flashcards
    flashcards_info = await client.get_artifact(flashcards_id)
    await client.download_file(
        flashcards_info["download_url"],
        "quantum_computing_flashcards.apkg"
    )
    print(f"  ✅ Generated 250 flashcards: quantum_computing_flashcards.apkg\n")
    
    # Step 4: Generate literature review
    print("📝 Generating literature review...")
    
    review_response = await client.export_content(
        source_ids=content_ids,
        format="document",
        parameters={
            "document_type": "literature_review",
            "length": "comprehensive",  # ~50 pages
            "format": "pdf",
            "style": "academic",
            "include_citations": True,
            "include_figures": True,
            "include_tables": True,
            "section_structure": [
                "Introduction",
                "Background",
                "Current State of Research",
                "Key Findings",
                "Research Gaps",
                "Future Directions",
                "Conclusion"
            ]
        }
    )
    
    review_id = await client.wait_for_job(
        review_response["job_id"],
        timeout=900  # 15 minutes for comprehensive review
    )
    
    # Download review
    review_info = await client.get_artifact(review_id)
    await client.download_file(
        review_info["download_url"],
        "quantum_computing_literature_review.pdf"
    )
    print(f"  ✅ Generated literature review: quantum_computing_literature_review.pdf\n")
    
    # Step 5: Get provenance and attribution
    print("📊 Getting provenance information...")
    
    # Get complete genealogy for podcast
    genealogy = await client.get_provenance_genealogy(podcast_id)
    print(f"  Sources used: {len(genealogy['sources'])}")
    print(f"  AI models used: {[m['name'] for m in genealogy['models']]}")
    
    # Get attribution text
    attribution = await client.get_provenance_attribution(podcast_id)
    print("\n  Attribution:")
    print(attribution["attribution_text"])
    
    # Save attribution to file
    with open("quantum_computing_attribution.txt", "w") as f:
        f.write(attribution["attribution_text"])
    
    print("\n🎉 Workflow complete!")
    print("\nGenerated:")
    print("  • 5 podcast episodes (90 minutes total)")
    print("  • 250 Anki flashcards")
    print("  • 50-page literature review")
    print("  • Complete attribution file")
    print("\nTime saved: ~200 hours of manual work! 🚀")

# Run workflow
asyncio.run(academic_research_workflow())
```

### Expected Output

```
📚 Importing 20 papers from arXiv...
  ✓ Queued: https://arxiv.org/abs/2401.00001
  ✓ Queued: https://arxiv.org/abs/2401.00002
  ...
⏳ Waiting for imports to complete...
  Progress: 50% - Extracting PDF
  Progress: 100% - Storage complete
  ✓ Imported: doc_abc123
  ...

✅ Imported 20 papers

🎙️ Generating podcast series...
  Job ID: job_podcast_xyz789
  Retrieving content: 5%
  Generating script: 15%
  Generating audio: 45%
  Composing episodes: 85%
  Storing podcast: 95%
  ✅ Generated podcast series: podcast_xyz789

  💾 Downloaded: quantum_computing_ep1.mp3
  💾 Downloaded: quantum_computing_ep2.mp3
  ...

🗂️ Generating flashcards...
  ✅ Generated 250 flashcards: quantum_computing_flashcards.apkg

📝 Generating literature review...
  ✅ Generated literature review: quantum_computing_literature_review.pdf

📊 Getting provenance information...
  Sources used: 20
  AI models used: ['GPT-4', 'ElevenLabs TTS']

  Attribution:
  This podcast series was generated from the following academic papers:
  1. Smith et al. (2024). Quantum Error Correction. arXiv:2401.00001
  2. Johnson (2024). Topological Quantum Computing. arXiv:2401.00002
  ...

🎉 Workflow complete!

Generated:
  • 5 podcast episodes (90 minutes total)
  • 250 Anki flashcards
  • 50-page literature review
  • Complete attribution file

Time saved: ~200 hours of manual work! 🚀
```

---

## 🎬 Example 2: Content Creator Workflow

### Scenario
YouTuber creating educational content needs to:
1. Research topic by importing 15 web articles and 5 YouTube videos
2. Generate video script with scene breakdowns
3. Generate video using Kling AI / Veo 3
4. Generate thumbnail concepts
5. Generate social media clips (TikTok/Reels)

### Implementation

```python
async def content_creator_workflow():
    """Complete content creation workflow."""
    client = LibrarianClient(api_url="http://localhost:8000")
    
    # Step 1: Research - Import source materials
    print("🔍 Importing research materials...")
    
    sources = {
        "articles": [
            "https://example.com/article1",
            "https://example.com/article2",
            # ... 13 more articles
        ],
        "videos": [
            "https://youtube.com/watch?v=video1",
            "https://youtube.com/watch?v=video2",
            # ... 3 more videos
        ]
    }
    
    content_ids = []
    
    # Import articles
    for url in sources["articles"]:
        response = await client.import_content(url, "webpage", priority=7)
        content_id = await client.wait_for_job(response["job_id"])
        content_ids.append(content_id)
        print(f"  ✓ Imported article: {url}")
    
    # Import videos
    for url in sources["videos"]:
        response = await client.import_content(url, "video", priority=7)
        content_id = await client.wait_for_job(response["job_id"])
        content_ids.append(content_id)
        print(f"  ✓ Imported video: {url}")
    
    print(f"\n✅ Imported {len(content_ids)} sources\n")
    
    # Step 2: Generate video script with scene breakdown
    print("📝 Generating video script...")
    
    script_response = await client.export_content(
        source_ids=content_ids,
        format="video_script",
        parameters={
            "video_length": 600,  # 10 minutes
            "style": "educational_entertaining",
            "target_audience": "general",
            "hook_style": "question",  # Start with a question
            "scenes": "auto",  # Auto-generate scenes
            "include_transitions": True,
            "include_visual_descriptions": True,
            "include_on_screen_text": True,
            "pacing": "dynamic"
        }
    )
    
    script_id = await client.wait_for_job(script_response["job_id"])
    script = await client.get_artifact(script_id)
    
    print("  ✅ Generated script with scenes:")
    for scene in script["scenes"]:
        print(f"    Scene {scene['num']}: {scene['description'][:50]}...")
    print()
    
    # Step 3: Generate video using smart backend routing
    print("🎬 Generating video (using Kling AI / Veo 3)...")
    
    video_response = await client.export_content(
        source_ids=content_ids,
        format="video",
        parameters={
            "duration": 600,  # 10 minutes
            "resolution": "1080p",
            "style": "educational",
            "backend": "smart",  # Auto-select Kling or Veo3
            "script": script["script"],
            "scenes": script["scenes"],
            "add_voiceover": True,
            "voice": "professional_male",
            "add_music": True,
            "music_style": "upbeat_corporate",
            "add_captions": True,
            "caption_style": "modern"
        }
    )
    
    # Stream progress
    print("  Generating video...")
    async for update in client.stream_job_progress(video_response["job_id"]):
        backend = update.get("backend", "Unknown")
        print(f"    [{backend}] {update['stage']}: {update['progress']}%")
    
    video_id = await client.wait_for_job(video_response["job_id"], timeout=1800)
    
    # Download video
    video_info = await client.get_artifact(video_id)
    await client.download_file(
        video_info["download_url"],
        "educational_video_10min.mp4"
    )
    print("  ✅ Generated 10-minute video: educational_video_10min.mp4\n")
    
    # Step 4: Generate thumbnail concepts
    print("🖼️ Generating thumbnail concepts...")
    
    thumbnail_response = await client.export_content(
        source_ids=content_ids,
        format="image",
        parameters={
            "image_type": "youtube_thumbnail",
            "count": 5,  # 5 different concepts
            "style": "eye_catching",
            "include_text": True,
            "text": script["title"],
            "resolution": "1280x720"
        }
    )
    
    thumbnail_id = await client.wait_for_job(thumbnail_response["job_id"])
    
    # Download thumbnails
    thumbnail_info = await client.get_artifact(thumbnail_id)
    for i, thumb in enumerate(thumbnail_info["thumbnails"], 1):
        await client.download_file(
            thumb["download_url"],
            f"thumbnail_concept_{i}.jpg"
        )
        print(f"  💾 Downloaded: thumbnail_concept_{i}.jpg")
    
    print(f"  ✅ Generated 5 thumbnail concepts\n")
    
    # Step 5: Generate social media clips (vertical)
    print("📱 Generating social media clips...")
    
    clips_response = await client.export_content(
        source_ids=[video_id],  # Use generated video as source
        format="video",
        parameters={
            "duration": 30,  # 30 seconds
            "aspect_ratio": "9:16",  # Vertical
            "count": 3,  # 3 different clips
            "style": "attention_grabbing",
            "auto_select_highlights": True,
            "add_captions": True,
            "caption_style": "tiktok",
            "add_trending_music": True
        }
    )
    
    clips_id = await client.wait_for_job(clips_response["job_id"])
    
    # Download clips
    clips_info = await client.get_artifact(clips_id)
    for i, clip in enumerate(clips_info["clips"], 1):
        await client.download_file(
            clip["download_url"],
            f"social_clip_{i}.mp4"
        )
        print(f"  💾 Downloaded: social_clip_{i}.mp4")
    
    print(f"  ✅ Generated 3 social media clips\n")
    
    # Step 6: Get attribution for video description
    print("📋 Getting attribution for video description...")
    
    attribution = await client.get_provenance_attribution(video_id)
    
    print("\n  📝 Add this to your video description:")
    print("  " + "─" * 50)
    print("  " + attribution["attribution_text"].replace("\n", "\n  "))
    print("  " + "─" * 50)
    
    # Save as file
    with open("video_description_attribution.txt", "w") as f:
        f.write(attribution["attribution_text"])
    
    print("\n🎉 Content creation workflow complete!")
    print("\nGenerated:")
    print("  • 10-minute educational video")
    print("  • 5 thumbnail concepts")
    print("  • 3 social media clips (30s each)")
    print("  • Attribution text for description")
    print("\nTime saved: ~40 hours of video production! 🚀")

# Run workflow
asyncio.run(content_creator_workflow())
```

---

## 💼 Example 3: Corporate Training Workflow

### Scenario
Enterprise needs to convert company documentation into training materials:
1. Import internal documentation (4 PDFs)
2. Generate training video series (8 videos, 2 hours total)
3. Generate training manual (100-page PDF)
4. Generate assessment quiz (50 questions)
5. Generate certificates of completion

### Implementation

```python
async def corporate_training_workflow():
    """Corporate training material generation."""
    client = LibrarianClient(api_url="http://localhost:8000")
    
    # Step 1: Import company documentation
    print("📄 Importing company documentation...")
    
    docs = [
        "/path/to/product_specifications.pdf",
        "/path/to/user_manual.pdf",
        "/path/to/troubleshooting_guide.pdf",
        "/path/to/best_practices.pdf"
    ]
    
    content_ids = []
    for doc_path in docs:
        # Upload local file
        response = await client.upload_document(
            file_path=doc_path,
            content_type="document",
            metadata={"category": "training_material"}
        )
        content_ids.append(response["content_id"])
        print(f"  ✓ Uploaded: {doc_path}")
    
    print(f"\n✅ Uploaded {len(content_ids)} documents\n")
    
    # Step 2: Generate training video series
    print("🎥 Generating training video series...")
    
    video_series_response = await client.export_content(
        source_ids=content_ids,
        format="video_series",
        parameters={
            "episodes": 8,
            "duration_per_episode": 15,  # 15 minutes each
            "style": "professional_training",
            "backend": "synthesia",  # Use avatar presenter
            "avatar": "professional_male",
            "include_chapters": True,
            "add_quiz_markers": True,  # Pause points for quizzes
            "company_branding": True,
            "logo_path": "/path/to/company_logo.png",
            "color_scheme": "#003366"  # Company colors
        }
    )
    
    series_id = await client.wait_for_job(
        video_series_response["job_id"],
        timeout=3600  # 1 hour
    )
    
    # Download all episodes
    series_info = await client.get_artifact(series_id)
    for i, episode in enumerate(series_info["episodes"], 1):
        await client.download_file(
            episode["download_url"],
            f"training_module_{i}.mp4"
        )
        print(f"  💾 Downloaded: training_module_{i}.mp4")
    
    print(f"  ✅ Generated 8 training videos (2 hours total)\n")
    
    # Step 3: Generate training manual
    print("📖 Generating training manual...")
    
    manual_response = await client.export_content(
        source_ids=content_ids,
        format="document",
        parameters={
            "document_type": "training_manual",
            "length": "comprehensive",  # ~100 pages
            "format": "pdf",
            "style": "corporate",
            "include_toc": True,
            "include_index": True,
            "include_diagrams": True,
            "include_exercises": True,
            "company_branding": True,
            "logo_path": "/path/to/company_logo.png"
        }
    )
    
    manual_id = await client.wait_for_job(manual_response["job_id"])
    
    # Download manual
    manual_info = await client.get_artifact(manual_id)
    await client.download_file(
        manual_info["download_url"],
        "training_manual.pdf"
    )
    print(f"  ✅ Generated training manual: training_manual.pdf\n")
    
    # Step 4: Generate assessment quiz
    print("✅ Generating assessment quiz...")
    
    quiz_response = await client.export_content(
        source_ids=content_ids,
        format="quiz",
        parameters={
            "question_count": 50,
            "difficulty": "mixed",
            "question_types": ["multiple_choice", "true_false", "short_answer"],
            "format": "scorm",  # SCORM-compliant for LMS
            "passing_score": 80,
            "include_explanations": True,
            "randomize_questions": True
        }
    )
    
    quiz_id = await client.wait_for_job(quiz_response["job_id"])
    
    # Download quiz
    quiz_info = await client.get_artifact(quiz_id)
    await client.download_file(
        quiz_info["download_url"],
        "training_assessment.zip"  # SCORM package
    )
    print(f"  ✅ Generated assessment quiz: training_assessment.zip\n")
    
    # Step 5: Generate certificate template
    print("🎓 Generating certificate template...")
    
    cert_response = await client.export_content(
        source_ids=content_ids,
        format="certificate",
        parameters={
            "template_style": "formal",
            "certificate_title": "Product Training Certification",
            "issued_by": "Acme Corporation",
            "include_signature_line": True,
            "include_date": True,
            "company_logo": "/path/to/company_logo.png",
            "format": "pdf"
        }
    )
    
    cert_id = await client.wait_for_job(cert_response["job_id"])
    
    # Download certificate template
    cert_info = await client.get_artifact(cert_id)
    await client.download_file(
        cert_info["download_url"],
        "certificate_template.pdf"
    )
    print(f"  ✅ Generated certificate template: certificate_template.pdf\n")
    
    # Step 6: Get complete provenance for compliance
    print("📊 Generating compliance report...")
    
    genealogy = await client.get_provenance_genealogy(series_id)
    
    compliance_report = {
        "training_series_id": series_id,
        "source_documents": [s["title"] for s in genealogy["sources"]],
        "generation_date": genealogy["created_at"],
        "ai_models_used": [m["name"] for m in genealogy["models"]],
        "total_duration": "2 hours",
        "episodes": 8,
        "assessment_questions": 50
    }
    
    # Save compliance report
    with open("training_compliance_report.json", "w") as f:
        json.dump(compliance_report, f, indent=2)
    
    print("  ✅ Generated compliance report: training_compliance_report.json\n")
    
    print("🎉 Corporate training workflow complete!")
    print("\nGenerated:")
    print("  • 8 training videos (2 hours)")
    print("  • 100-page training manual")
    print("  • 50-question assessment (SCORM)")
    print("  • Certificate template")
    print("  • Compliance report")
    print("\nCost saved: $50,000+ in production costs! 💰")

# Run workflow
asyncio.run(corporate_training_workflow())
```

---

## 🔧 Example 4: CLI Integration

### Scenario
Automate content processing via command-line scripts

```bash
#!/bin/bash
# Import and generate workflow using CLI

# Import YouTube videos
for url in $(cat youtube_urls.txt); do
    echo "Importing: $url"
    librarian import "$url" --type video --priority 8
done

# Wait for imports to complete
librarian jobs wait --timeout 3600

# Generate podcast from all videos
librarian export podcast \
    --sources "type:video" \
    --voice professional_female \
    --episodes 5 \
    --duration 20 \
    --output podcast_series.zip

# Generate attribution
librarian provenance attribution podcast_series \
    --format markdown \
    --output attribution.md

echo "✅ Workflow complete!"
```

---

## 🌐 Example 5: REST API Integration

### Scenario
Integrate Williams Librarian into existing web application

```javascript
// JavaScript/Node.js integration

const axios = require('axios');
const WebSocket = require('ws');

class LibrarianClient {
    constructor(baseUrl) {
        this.baseUrl = baseUrl;
    }
    
    async importContent(url, type, priority = 5) {
        const response = await axios.post(`${this.baseUrl}/api/content/import`, {
            url,
            type,
            priority
        });
        return response.data.job_id;
    }
    
    async exportContent(sourceIds, format, parameters = {}) {
        const response = await axios.post(`${this.baseUrl}/api/content/export`, {
            source_ids: sourceIds,
            format,
            parameters
        });
        return response.data.job_id;
    }
    
    streamJobProgress(jobId, callback) {
        const ws = new WebSocket(`${this.baseUrl}/ws/jobs/${jobId}`);
        
        ws.on('message', (data) => {
            const update = JSON.parse(data);
            callback(update);
        });
        
        ws.on('close', () => {
            console.log('Progress stream closed');
        });
        
        return ws;
    }
    
    async waitForJob(jobId, timeout = 300000) {
        return new Promise((resolve, reject) => {
            const startTime = Date.now();
            
            const ws = this.streamJobProgress(jobId, (update) => {
                console.log(`${update.stage}: ${update.progress}%`);
                
                if (update.status === 'completed') {
                    ws.close();
                    resolve(update.artifact_id || update.content_id);
                }
                
                if (update.status === 'failed') {
                    ws.close();
                    reject(new Error(update.error_message));
                }
                
                if (Date.now() - startTime > timeout) {
                    ws.close();
                    reject(new Error('Timeout'));
                }
            });
        });
    }
}

// Usage
async function main() {
    const client = new LibrarianClient('http://localhost:8000');
    
    // Import content
    const jobId = await client.importContent(
        'https://youtube.com/watch?v=abc123',
        'video',
        8
    );
    
    // Wait for completion with live progress
    const videoId = await client.waitForJob(jobId);
    console.log(`✅ Imported: ${videoId}`);
    
    // Generate podcast
    const exportJobId = await client.exportContent(
        [videoId],
        'podcast',
        { voice: 'professional_male' }
    );
    
    const podcastId = await client.waitForJob(exportJobId);
    console.log(`✅ Generated podcast: ${podcastId}`);
}

main().catch(console.error);
```

---

## 📊 Performance Benchmarks

### Typical Processing Times

```
Import:
├─ YouTube video (10 min): ~2-3 minutes
├─ PDF document (50 pages): ~30 seconds
├─ Web page: ~10 seconds
└─ Academic paper: ~45 seconds

Export:
├─ Podcast (20 min): ~3 minutes
├─ Video (Kling, 30s): ~2 minutes
├─ Video (Veo3, 3 min): ~15 minutes
├─ Flashcards (250): ~1 minute
└─ Document (50 pages): ~5 minutes
```

### Cost Estimates

```
Import: Free (no AI generation)

Export:
├─ Podcast (20 min): ~$0.05
├─ Video (Kling, 30s): ~$0.50
├─ Video (Veo3, 3 min): ~$7.50
├─ Flashcards: ~$0.10
└─ Document: ~$0.20
```

---

## 🎯 Best Practices

### 1. Use Priority Queues
```python
# High priority for urgent content
await client.import_content(url, "video", priority=10)

# Normal priority for batch processing
await client.import_content(url, "document", priority=5)
```

### 2. Monitor Progress
```python
# Stream real-time updates
async for update in client.stream_job_progress(job_id):
    print(f"{update['progress']}%: {update['stage']}")
```

### 3. Handle Errors Gracefully
```python
try:
    content_id = await client.wait_for_job(job_id, timeout=300)
except TimeoutError:
    # Retry with higher priority
    await client.retry_job(job_id, manual=True)
except Exception as e:
    # Log error and notify user
    logger.error(f"Import failed: {e}")
```

### 4. Track Provenance
```python
# Always get attribution for generated content
attribution = await client.get_provenance_attribution(artifact_id)

# Include in output
with open("README.txt", "w") as f:
    f.write(attribution["attribution_text"])
```

### 5. Batch Operations
```python
# Import multiple sources in parallel
jobs = []
for url in urls:
    job_id = await client.import_content(url, "video")
    jobs.append(job_id)

# Wait for all to complete
content_ids = await asyncio.gather(*[
    client.wait_for_job(job_id) for job_id in jobs
])
```

---

## 📚 Additional Resources

- **API Documentation**: `/docs` (Swagger UI)
- **WebSocket Protocol**: See `ARCHITECTURE.md`
- **Plugin Development**: See `plugin-development.md`
- **Deployment Guide**: See `deployment.md`

---

**Last Updated:** October 12, 2025  
**Version:** 2.0 (Definitive)
