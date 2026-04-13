#!/usr/bin/env python3
"""
Quick Start Example for Text-to-Video Nature Generator

This script demonstrates how to use the API to generate a short video.
For testing purposes, it generates a 1-minute video (takes ~5-10 minutes on GPU).
"""

import requests
import time
import json
from pathlib import Path

# API endpoint
API_BASE = "http://localhost:8000"

def main():
    print("🌊 Text-to-Video Nature Generator - Quick Start Example")
    print("=" * 60)
    
    # Check if server is running
    try:
        response = requests.get(f"{API_BASE}/health", timeout=5)
        print(f"✓ Server status: {response.json()['status']}")
    except requests.exceptions.ConnectionError:
        print("❌ Error: Server not running!")
        print("   Start the server with: python backend/main.py")
        return
    
    # Get available presets
    print("\n📋 Available presets:")
    response = requests.get(f"{API_BASE}/presets")
    presets = response.json()
    for preset in presets['presets'][:5]:
        print(f"   • {preset['name']}: {preset['description']}")
    
    # Generate a short test video (1 minute for quick testing)
    print("\n🎬 Generating test video...")
    
    request_data = {
        "prompt": "Peaceful coral reef with colorful tropical fish swimming gently",
        "style": "coral_reef",
        "duration_minutes": 1,  # Short duration for testing
        "resolution": "1024x576",  # Lower resolution for speed
        "fps": 24,
        "target_fps": 30,
        "clip_duration": 6,
        "enable_audio": True,
        "audio_type": "ambient",
        "quality": "low",  # Faster generation
        "transition_type": "crossfade"
    }
    
    print(f"   Prompt: {request_data['prompt']}")
    print(f"   Duration: {request_data['duration_minutes']} minute(s)")
    print(f"   Resolution: {request_data['resolution']}")
    
    # Submit generation request
    response = requests.post(f"{API_BASE}/generate", json=request_data)
    
    if response.status_code != 200:
        print(f"❌ Error: {response.text}")
        return
    
    result = response.json()
    job_id = result['job_id']
    
    print(f"\n✅ Job submitted!")
    print(f"   Job ID: {job_id}")
    print(f"   Estimated time: {result['estimated_time_minutes']:.1f} minutes")
    
    # Poll for status
    print("\n⏳ Waiting for completion...")
    
    while True:
        response = requests.get(f"{API_BASE}/status/{job_id}")
        status = response.json()
        
        progress = status['progress']
        current_step = status['current_step']
        job_status = status['status']
        
        print(f"   [{progress:5.1f}%] {current_step} ({job_status})")
        
        if job_status in ['completed', 'failed', 'cancelled']:
            break
        
        time.sleep(5)
    
    # Show results
    if status['status'] == 'completed':
        print("\n🎉 Generation complete!")
        
        if status['result']:
            output_path = status['result'].get('output_path', 'N/A')
            print(f"   Output: {output_path}")
            
            # Show SEO metadata
            seo = status['result'].get('seo_metadata', {})
            if seo:
                print(f"\n📝 SEO Title: {seo.get('title', 'N/A')}")
                print(f"   Tags: {seo.get('tags', 'N/A')[:100]}...")
    else:
        print(f"\n❌ Generation failed: {status.get('error_message', 'Unknown error')}")
    
    print("\n" + "=" * 60)
    print("Example complete!")
    print("\nTo generate longer videos:")
    print("   1. Increase duration_minutes (up to 180)")
    print("   2. Use higher quality settings")
    print("   3. Run overnight for very long videos")

if __name__ == "__main__":
    main()
