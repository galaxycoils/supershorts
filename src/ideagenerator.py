# src/ideagenerator.py
# YouTube Studio Idea Generator – Fully local with Ollama
import json
from pathlib import Path
import ollama
import random
import datetime
from src.generator import generate_visuals  # reuse existing thumbnail generator

LOG_FILE = Path("performance_log.json")
IDEAS_FILE = Path("youtube_studio_ideas.json")

def load_performance_data():
    if not LOG_FILE.exists():
        return []
    try:
        return json.loads(LOG_FILE.read_text())
    except:
        return []

def get_trending_context():
    """Simulates a trending AI search context."""
    return "Trending: DeepSeek-V3, Qwen-2.5-Max, Agentic Workflows, local RAG, AI video generation, coding agents."

def generate_ideas(num_ideas: int = 5):
    """Ollama-powered YouTube Studio idea generator"""
    data = load_performance_data()
    trending = get_trending_context()

    if not data:
        past_data = "No past data yet. Generate fresh ideas based on trending topics only."
    else:
        recent = data[-10:]
        lines = [f"- {e.get('title', 'Untitled')} (mode: {e.get('mode', '?')})" for e in recent]
        past_data = "\n".join(lines)

    prompt = f"""
    You are YouTube Studio's AI Idea Generator.
    Analyze my past high-performing videos and trending tech topics.

    TRENDING TOPICS:
    {trending}

    PAST PERFORMANCE:
    {past_data}

    Generate {num_ideas} fresh video ideas for SuperShorts.
    For each idea include:
    - Title (clickbait + searchable)
    - Short description / hook
    - Full dialogue/script (60-90 seconds for Shorts or 8-10 minutes for long form)
    - Suggested thumbnail prompt (describe the image visual style)

    Focus on high-engagement hooks and trending AI topics like DeepSeek, Qwen, local LLMs, and agentic workflows.
    Return ONLY a valid JSON array of objects.
    """

    print("🧠 Asking Ollama to generate YouTube Studio-style ideas...")
    try:
        response = ollama.chat(
            model="qwen2.5-coder:3b",
            messages=[{"role": "user", "content": prompt}],
            options={'temperature': 0.8, 'num_ctx': 4096}
        )
        text = response['message']['content']

        # Robust JSON extraction
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1]
        
        try:
            ideas = json.loads(text)
        except Exception:
            import re
            match = re.search(r'\[.*\]', text, re.DOTALL)
            ideas = json.loads(match.group(0)) if match else []
            
        if not isinstance(ideas, list):
            if isinstance(ideas, dict):
                # Maybe it returned a single object or an object containing the list
                if "ideas" in ideas: ideas = ideas["ideas"]
                else: ideas = [ideas]
            else:
                raise ValueError("Not a list")
    except Exception as e:
        print(f"⚠️ Idea generation failed: {e}. using fallback.")
        ideas = [{"title": f"Trending AI Trend {i}", "description": "Shocking reveal about local LLMs", "dialogue": "Did you know you can run GPT-4 class models on your laptop? Here is how...", "thumbnail_prompt": "cinematic tech background with neon circuits"} for i in range(num_ideas)]

    # Save for later reuse
    IDEAS_FILE.write_text(json.dumps(ideas, indent=2))
    return ideas

def create_thumbnail_from_idea(idea):
    """Uses existing generate_visuals to create thumbnail from the idea"""
    thumbnail_title = idea.get("title", "New Idea")
    print(f"🖼️ Generating thumbnail for: {thumbnail_title}")
    
    output_path = Path("output/thumbnails")
    output_path.mkdir(exist_ok=True, parents=True)
    
    # generate_visuals(output_dir, video_type, slide_content=None, thumbnail_title=None, slide_number=0, total_slides=0)
    return generate_visuals(
        output_dir=output_path,
        video_type='long',
        thumbnail_title=thumbnail_title
    )

def start_idea_generator():
    print("\n🔥 YouTube Studio Idea Generator")
    print("1. Generate new ideas based on my best videos")
    print("2. Reuse previous dialogues/scripts")
    print("3. Back to menu")
    choice = input("Choose (1-3): ").strip()

    if choice == "1":
        ideas = generate_ideas(num_ideas=5)
        if not ideas:
            print("❌ No ideas generated.")
            return
            
        for i, idea in enumerate(ideas):
            print(f"\n{i+1}. {idea.get('title', 'No title')}")
            desc = idea.get('description') or idea.get('hook', 'No description')
            print(f"   Hook: {desc[:80]}...")
            print(f"   Thumbnail prompt: {idea.get('thumbnail_prompt', 'N/A')}")
        
        use = input("\nUse one of these ideas? Enter number (or 0 to skip): ")
        if use.isdigit() and 1 <= int(use) <= len(ideas):
            selected = ideas[int(use)-1]
            thumb_path = create_thumbnail_from_idea(selected)
            print(f"✅ Thumbnail saved: {thumb_path}")
            dialogue = selected.get('dialogue') or selected.get('script', 'No dialogue')
            print(f"✅ Full dialogue ready to use:\n{dialogue[:500]}...")
            print("\n(Note: You can copy this script and use it in Options 1-4)")

    elif choice == "2":
        if IDEAS_FILE.exists():
            try:
                ideas = json.loads(IDEAS_FILE.read_text())
                print("\n📜 Previous ideas/dialogues:")
                for i, idea in enumerate(ideas):
                    print(f"{i+1}. {idea.get('title')}")
                
                sel = input("\nView details for which one? (Number or 0 to back): ")
                if sel.isdigit() and 1 <= int(sel) <= len(ideas):
                    s = ideas[int(sel)-1]
                    print(f"\nTITLE: {s.get('title')}")
                    print(f"DESC: {s.get('description') or s.get('hook')}")
                    print(f"SCRIPT:\n{s.get('dialogue') or s.get('script')}")
            except Exception:
                print("Error reading ideas file.")
        else:
            print("No saved ideas yet.")

    input("\nPress Enter to return to main menu...")
