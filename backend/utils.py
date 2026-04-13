"""
Utility functions for the Text-to-Video Nature Generator.
Includes prompt enhancement, color grading, SEO generation, and helper functions.
"""

import os
import re
import json
import random
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from loguru import logger

from .config import settings


# Preset prompts for common nature scenes
PRESET_PROMPTS = {
    "shark_hunting": {
        "prompt": "Great white shark hunting in deep ocean waters, dramatic predator scene, powerful swimming motion, blue water, cinematic lighting, high contrast, documentary style",
        "style": "ocean",
        "description": "Dramatic underwater predator scene with great white sharks"
    },
    "peaceful_reef": {
        "prompt": "Peaceful coral reef ecosystem, colorful tropical fish swimming gently, vibrant corals, clear turquoise water, sunlight filtering from surface, serene atmosphere",
        "style": "coral_reef",
        "description": "Calm and colorful coral reef with tropical fish"
    },
    "bioluminescent_bay": {
        "prompt": "Bioluminescent creatures glowing in dark ocean depths, jellyfish with neon lights, mysterious deep sea environment, ethereal blue and green glow, otherworldly atmosphere",
        "style": "deep_sea",
        "description": "Mysterious deep sea with glowing bioluminescent life"
    },
    "arctic_wilderness": {
        "prompt": "Arctic ice landscape, polar bear walking on ice floe, aurora borealis in night sky, cold blue tones, dramatic wilderness, national geographic style",
        "style": "arctic",
        "description": "Polar wildlife in stunning arctic landscapes"
    },
    "tropical_storm": {
        "prompt": "Dramatic tropical storm over ocean, massive waves crashing, dark clouds, lightning, powerful nature forces, cinematic weather scene, high contrast",
        "style": "ocean",
        "description": "Powerful ocean storm with dramatic weather"
    },
    "whale_migration": {
        "prompt": "Majestic humpback whales migrating through open ocean, breaching surface, massive marine mammals, deep blue water, epic scale, documentary cinematography",
        "style": "ocean",
        "description": "Epic whale migration in open ocean"
    },
    "jungle_waterfall": {
        "prompt": "Magnificent waterfall cascading into emerald pool, dense rainforest vegetation, morning mist, shafts of sunlight through canopy, exotic birds flying",
        "style": "jungle",
        "description": "Serene jungle waterfall surrounded by lush vegetation"
    },
    "safari_sunset": {
        "prompt": "African savanna at golden hour, elephant herd silhouetted against orange sunset, acacia trees, warm atmospheric lighting, wildlife documentary style",
        "style": "wildlife",
        "description": "African wildlife at dramatic sunset"
    },
    "kelp_forest": {
        "prompt": "Underwater kelp forest, giant seaweed swaying in current, sun rays penetrating deep water, seals swimming gracefully, peaceful marine environment",
        "style": "ocean",
        "description": "Tranquil underwater kelp forest ecosystem"
    },
    "mountain_eagle": {
        "prompt": "Majestic golden eagle soaring over mountain peaks, dramatic clouds, golden hour lighting, aerial perspective, powerful bird of prey, wildlife cinematography",
        "style": "wildlife",
        "description": "Soaring eagle over dramatic mountain landscape"
    }
}


def enhance_prompt(prompt: str, style: str = "ocean") -> str:
    """
    Enhance a base prompt with style-specific keywords and quality modifiers.
    
    Args:
        prompt: Base text prompt from user
        style: Style preset to apply
        
    Returns:
        Enhanced prompt with additional descriptive keywords
    """
    # Get style configuration
    style_config = settings.STYLE_PRESETS.get(style, settings.STYLE_PRESETS["ocean"])
    
    # Quality enhancement keywords
    quality_keywords = [
        "ultra realistic",
        "cinematic lighting",
        "high contrast",
        "professional photography",
        "8k resolution",
        "highly detailed",
        "sharp focus",
        "dramatic atmosphere"
    ]
    
    # Randomly select 3-5 quality keywords to avoid overly long prompts
    selected_quality = random.sample(quality_keywords, random.randint(3, 5))
    
    # Combine base prompt, style suffix, and quality keywords
    enhanced = f"{prompt}, {style_config['prompt_suffix']}, {', '.join(selected_quality)}"
    
    logger.debug(f"Enhanced prompt: {enhanced}")
    return enhanced


def generate_prompt_variations(base_prompt: str, num_variations: int = 5) -> List[str]:
    """
    Generate variations of a base prompt for diverse clip generation.
    
    Args:
        base_prompt: Original prompt
        num_variations: Number of variations to generate
        
    Returns:
        List of varied prompts
    """
    variation_templates = [
        "wide angle view of {prompt}",
        "close-up shot of {prompt}",
        "aerial perspective of {prompt}",
        "underwater view of {prompt}",
        "slow motion capture of {prompt}",
        "dramatic lighting on {prompt}",
        "golden hour {prompt}",
        "misty atmosphere {prompt}",
        "crystal clear {prompt}",
        "dynamic motion {prompt}"
    ]
    
    variations = []
    selected_templates = random.sample(variation_templates, min(num_variations, len(variation_templates)))
    
    for template in selected_templates:
        variations.append(template.format(prompt=base_prompt))
    
    # If we need more variations, add time-based modifiers
    while len(variations) < num_variations:
        time_modifiers = [
            "morning light",
            "midday sun",
            "sunset glow",
            "twilight ambiance",
            "moonlit scene"
        ]
        modifier = random.choice(time_modifiers)
        variations.append(f"{modifier}, {base_prompt}")
    
    logger.debug(f"Generated {len(variations)} prompt variations")
    return variations


def apply_color_grading(image_array, color_grade: str = "deep_ocean"):
    """
    Apply color grading to an image using OpenCV.
    
    Args:
        image_array: numpy array of image (RGB format)
        color_grade: Color grading preset name
        
    Returns:
        Color-graded image array
    """
    try:
        import cv2
        import numpy as np
        
        # Convert RGB to BGR for OpenCV
        if len(image_array.shape) == 3 and image_array.shape[2] == 3:
            image_bgr = cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR)
        else:
            image_bgr = image_array.copy()
        
        # Apply contrast boost
        contrast = settings.CONTRAST_BOOST
        image_bgr = cv2.convertScaleAbs(image_bgr, alpha=contrast, beta=0)
        
        # Apply color grading based on preset
        if color_grade == "deep_ocean":
            # Enhance blues and cyans
            hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
            h, s, v = cv2.split(hsv)
            
            # Boost saturation for blues
            s = cv2.multiply(s, settings.SATURATION_BOOST)
            s = np.clip(s, 0, 255).astype(np.uint8)
            
            # Adjust value for depth
            v = cv2.multiply(v, 0.9)  # Slightly darken for deep water feel
            v = np.clip(v, 0, 255).astype(np.uint8)
            
            hsv = cv2.merge([h, s, v])
            image_bgr = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
            
        elif color_grade == "tropical":
            # Enhance greens and cyans for tropical feel
            hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
            h, s, v = cv2.split(hsv)
            
            s = cv2.multiply(s, 1.2)
            s = np.clip(s, 0, 255).astype(np.uint8)
            
            hsv = cv2.merge([h, s, v])
            image_bgr = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
            
        elif color_grade == "arctic":
            # Cool tones, reduce saturation
            hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
            h, s, v = cv2.split(hsv)
            
            s = cv2.multiply(s, 0.8)  # Reduce saturation
            s = np.clip(s, 0, 255).astype(np.uint8)
            
            # Shift towards blue
            h = cv2.add(h, 10)
            h = np.clip(h, 0, 179).astype(np.uint8)
            
            hsv = cv2.merge([h, s, v])
            image_bgr = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
        
        # Convert back to RGB
        image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        
        logger.debug(f"Applied color grading: {color_grade}")
        return image_rgb
        
    except Exception as e:
        logger.error(f"Error applying color grading: {e}")
        return image_array


def generate_seo_metadata(
    prompt: str,
    duration_minutes: int,
    style: str,
    video_filename: str
) -> Dict[str, str]:
    """
    Generate SEO-optimized title, description, and tags for YouTube upload.
    
    Args:
        prompt: Original video prompt
        duration_minutes: Video duration in minutes
        style: Style preset used
        video_filename: Output video filename
        
    Returns:
        Dictionary with SEO metadata
    """
    # Extract key themes from prompt
    keywords = extract_keywords(prompt)
    
    # Generate title
    title_templates = [
        f"Relaxing {style.title()} Nature Scene - {keywords[0].title()} in 4K",
        f"Stunning {keywords[0].title()} Footage - {duration_minutes} Minute Nature Documentary",
        f"Beautiful {style.title()} Wildlife - Ultra Realistic Nature Video",
        f"{keywords[0].title()} in Natural Habitat - Cinematic Nature Film",
        f"Immersive {style.title()} Experience - {duration_minutes} Minutes of Nature"
    ]
    
    title = random.choice(title_templates)
    
    # Generate description
    description = f"""
Experience the beauty of nature with this stunning {duration_minutes}-minute {style} video.

🎬 Generated with AI using advanced text-to-video technology
📍 Scene: {prompt}
⏱️ Duration: {duration_minutes} minutes
🎨 Style: {style.title()}

This ultra-realistic nature footage features high-contrast cinematography and smooth 
60 FPS motion for an immersive viewing experience. Perfect for relaxation, meditation, 
background display, or nature appreciation.

#NatureVideo #{style.replace('_', '').title()} #Wildlife #Relaxation #4KNature #AIGenerated
""".strip()
    
    # Generate tags
    base_tags = [
        "nature video",
        f"{style} scene",
        "wildlife documentary",
        "relaxing nature",
        "4k nature",
        "ultra realistic",
        "AI generated video",
        "text to video",
        "nature footage",
        "cinematic nature"
    ]
    
    # Add keyword-specific tags
    keyword_tags = [f"{kw} video" for kw in keywords[:5]]
    tags = base_tags + keyword_tags
    
    seo_data = {
        "title": title,
        "description": description,
        "tags": ", ".join(tags),
        "category": "Pets & Animals",
        "thumbnail_suggestion": f"Best moment from {keywords[0]} scene",
        "filename": video_filename,
        "generated_at": datetime.now().isoformat()
    }
    
    logger.info(f"Generated SEO metadata for {video_filename}")
    return seo_data


def extract_keywords(text: str, max_keywords: int = 10) -> List[str]:
    """
    Extract important keywords from text for tagging and SEO.
    
    Args:
        text: Input text
        max_keywords: Maximum number of keywords to extract
        
    Returns:
        List of extracted keywords
    """
    # Common stop words to filter out
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
        'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
        'could', 'should', 'may', 'might', 'must', 'shall', 'can', 'need',
        'it', 'its', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she',
        'we', 'they', 'what', 'which', 'who', 'whom', 'whose', 'where', 'when',
        'why', 'how', 'all', 'each', 'every', 'both', 'few', 'more', 'most',
        'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so'
    }
    
    # Clean and tokenize
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    
    # Filter stop words and get unique words
    keywords = []
    seen = set()
    for word in words:
        if word not in stop_words and word not in seen:
            keywords.append(word)
            seen.add(word)
    
    return keywords[:max_keywords]


def format_timestamp(seconds: float) -> str:
    """
    Format seconds into HH:MM:SS.mmm format.
    
    Args:
        seconds: Time in seconds
        
    Returns:
        Formatted timestamp string
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"
    else:
        return f"{minutes:02d}:{secs:06.3f}"


def calculate_clip_count(duration_minutes: int, clip_duration_seconds: int) -> int:
    """
    Calculate the number of clips needed for a given duration.
    
    Args:
        duration_minutes: Total video duration in minutes
        clip_duration_seconds: Duration of each individual clip
        
    Returns:
        Number of clips required
    """
    total_seconds = duration_minutes * 60
    clip_count = total_seconds / clip_duration_seconds
    
    # Round up to ensure we have enough content
    import math
    return math.ceil(clip_count)


def get_preset_info(preset_name: str) -> Optional[Dict[str, Any]]:
    """
    Get information about a preset prompt.
    
    Args:
        preset_name: Name of the preset
        
    Returns:
        Preset information dictionary or None if not found
    """
    return PRESET_PROMPTS.get(preset_name)


def list_presets() -> List[Dict[str, Any]]:
    """
    List all available presets with their information.
    
    Returns:
        List of preset information dictionaries
    """
    presets_list = []
    for name, info in PRESET_PROMPTS.items():
        presets_list.append({
            "name": name,
            "prompt": info["prompt"],
            "style": info["style"],
            "description": info["description"]
        })
    return presets_list


def generate_batch_id() -> str:
    """
    Generate a unique batch ID for tracking video generation jobs.
    
    Returns:
        Unique batch ID string
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    random_suffix = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=6))
    return f"batch_{timestamp}_{random_suffix}"


def save_seo_metadata(seo_data: Dict[str, Any], output_path: Path) -> Path:
    """
    Save SEO metadata to a JSON file.
    
    Args:
        seo_data: SEO metadata dictionary
        output_path: Directory to save the file
        
    Returns:
        Path to saved JSON file
    """
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"seo_{timestamp}.json"
    filepath = output_path / filename
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(seo_data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Saved SEO metadata to {filepath}")
    return filepath
