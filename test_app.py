"""
Quick Test Script for Nature Frontiers
Tests basic functionality without requiring heavy AI models.
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

def test_imports():
    """Test that all modules can be imported."""
    print("🔍 Testing imports...")
    
    try:
        from config import settings
        print(f"✅ Config loaded: {settings.APP_NAME} v{settings.APP_VERSION}")
    except Exception as e:
        print(f"❌ Config failed: {e}")
        return False
    
    try:
        from utils import list_presets, enhance_prompt
        presets = list_presets()
        print(f"✅ Utils loaded: {len(presets)} presets available")
        
        # Test prompt enhancement
        enhanced = enhance_prompt("ocean scene", "ocean")
        print(f"   Sample enhanced prompt: {enhanced[:80]}...")
    except Exception as e:
        print(f"❌ Utils failed: {e}")
        return False
    
    try:
        from pipeline import pipeline
        print(f"✅ Pipeline initialized on device: {pipeline.device}")
    except Exception as e:
        print(f"⚠️  Pipeline warning: {e}")
    
    try:
        from audio import audio_generator
        print(f"✅ Audio generator initialized on device: {audio_generator.device}")
    except Exception as e:
        print(f"⚠️  Audio warning: {e}")
    
    try:
        from video_builder import builder
        print(f"✅ Video builder ready")
    except Exception as e:
        print(f"❌ Video builder failed: {e}")
        return False
    
    return True


def test_preset_generation():
    """Test generating prompts from presets."""
    print("\n🎬 Testing preset generation...")
    
    from utils import list_presets, generate_prompt_variations
    
    presets = list_presets()
    for i, preset in enumerate(presets[:3]):  # Test first 3 presets
        print(f"\n{i+1}. {preset['name']}")
        print(f"   Style: {preset['style']}")
        print(f"   Prompt: {preset['prompt'][:60]}...")
        
        # Generate variations
        variations = generate_prompt_variations(preset['prompt'], 2)
        print(f"   Variations: {len(variations)} generated")
    
    print(f"\n✅ Tested {min(3, len(presets))} presets successfully")


def test_seo_generation():
    """Test SEO metadata generation."""
    print("\n📝 Testing SEO generation...")
    
    from utils import generate_seo_metadata
    
    seo = generate_seo_metadata(
        prompt="Deep ocean with bioluminescent creatures",
        duration_minutes=10,
        style="deep_sea",
        video_filename="test_video.mp4"
    )
    
    print(f"✅ Title: {seo['title'][:60]}...")
    print(f"✅ Tags: {len(seo['tags'])} tags generated")
    print(f"✅ Description length: {len(seo['description'])} chars")


if __name__ == "__main__":
    print("=" * 60)
    print("🌊 Nature Frontiers - Quick Test")
    print("=" * 60)
    
    success = test_imports()
    
    if success:
        test_preset_generation()
        test_seo_generation()
        
        print("\n" + "=" * 60)
        print("✅ All tests passed! Application is ready.")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Install FFmpeg: https://ffmpeg.org/download.html")
        print("2. Run: python frontend/app.py")
        print("3. Open browser to: http://localhost:7860")
        print("\nNote: First video generation will download AI models (~5-10GB)")
    else:
        print("\n❌ Some tests failed. Check error messages above.")
        sys.exit(1)
