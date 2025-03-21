from youtube_transcript_api import YouTubeTranscriptApi
import json
import sys
import re
import requests
from pytrends.request import TrendReq
import pandas as pd
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import nltk
from collections import Counter
import time

# Download necessary NLTK resources
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('corpora/stopwords')
    nltk.data.find('corpora/wordnet')
except LookupError:
    nltk.download('punkt')
    nltk.download('stopwords')
    nltk.download('wordnet')

def extract_video_id(url):
    """Extract the video ID from a YouTube URL."""
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'(?:embed\/)([0-9A-Za-z_-]{11})',
        r'(?:youtu\.be\/)([0-9A-Za-z_-]{11})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None

def get_trending_topics(country='US', num_trends=20):
    """Get current trending topics from Google Trends."""
    print("Fetching trending topics from Google Trends...")
    
    try:
        # Initialize pytrends
        pytrends = TrendReq(hl='en-US', tz=360)
        
        # Get trending searches for the day
        trending_searches = pytrends.trending_searches(pn=country)
        
        # Convert to list and take top n trends
        trends = trending_searches[0].tolist()[:num_trends]
        
        # Get related queries for each trending topic
        expanded_trends = []
        for trend in trends[:5]:  # Limit to top 5 trends to avoid API limits
            try:
                pytrends.build_payload(kw_list=[trend], timeframe='now 1-d')
                related = pytrends.related_queries()
                if related and trend in related and 'top' in related[trend]:
                    related_df = related[trend]['top']
                    if not related_df.empty:
                        for query in related_df['query'].tolist()[:3]:
                            expanded_trends.append(query)
                # Add small delay to avoid rate limiting
                time.sleep(0.5)
            except Exception as e:
                print(f"Error getting related queries for {trend}: {e}")
        
        # Combine original trends with expanded trends
        all_trends = trends + expanded_trends
        
        # Remove duplicates while preserving order
        unique_trends = []
        for trend in all_trends:
            if trend not in unique_trends:
                unique_trends.append(trend)
        
        print(f"Found {len(unique_trends)} trending topics")
        return unique_trends
        
    except Exception as e:
        print(f"Error fetching trends: {e}")
        # Fallback to some generic popular topics
        return ["climate change", "artificial intelligence", "covid", 
                "election", "cryptocurrency", "inflation", "ukraine",
                "stocks", "economy", "sports", "entertainment", "technology"]

def preprocess_text(text):
    """Preprocess text for better matching."""
    # Tokenize
    tokens = word_tokenize(text.lower())
    
    # Remove stopwords and non-alphabetic tokens
    stop_words = set(stopwords.words('english'))
    tokens = [token for token in tokens if token.isalpha() and token not in stop_words]
    
    # Lemmatize
    lemmatizer = WordNetLemmatizer()
    tokens = [lemmatizer.lemmatize(token) for token in tokens]
    
    return tokens

def calculate_trend_relevance(caption, trends):
    """Calculate relevance of caption to current trends."""
    caption_tokens = preprocess_text(caption)
    
    # Calculate relevance for each trend
    relevance_scores = {}
    for trend in trends:
        trend_tokens = preprocess_text(trend)
        
        # Count matches
        matches = sum(token in caption_tokens for token in trend_tokens)
        
        # Calculate relevance score (higher is more relevant)
        if matches > 0:
            # Prioritize trends that have more matching words
            relevance_scores[trend] = matches / len(trend_tokens)
    
    return relevance_scores

def download_and_analyze_captions(video_url, output_file=None, max_results=20):
    """Download captions and analyze them against trending topics."""
    # Extract video ID
    video_id = extract_video_id(video_url)
    if not video_id:
        video_id = video_url
    
    try:
        # Get trending topics
        trending_topics = get_trending_topics()
        
        # Get video captions
        print(f"Downloading captions for video ID: {video_id}")
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
        
        # Process captions
        caption_entries = []
        current_dialogue = ""
        
        # Group captions into meaningful dialogues (sentences or paragraphs)
        for i, entry in enumerate(transcript):
            text = entry['text']
            start_time = entry['start']
            
            # Format timestamp
            minutes = int(start_time // 60)
            seconds = int(start_time % 60)
            timestamp = f"[{minutes:02d}:{seconds:02d}]"
            
            # If text ends with punctuation or is the last entry, treat it as end of dialogue
            if text.rstrip().endswith(('.', '!', '?')) or i == len(transcript) - 1:
                current_dialogue += " " + text
                
                # Add completed dialogue to entries
                if current_dialogue.strip():
                    caption_entries.append({
                        'timestamp': timestamp,
                        'text': current_dialogue.strip(),
                        'start_time': start_time
                    })
                    current_dialogue = ""
            else:
                current_dialogue += " " + text
        
        # Analyze each dialogue for trend relevance
        print("Analyzing captions for trending topics...")
        for entry in caption_entries:
            relevance = calculate_trend_relevance(entry['text'], trending_topics)
            entry['trends'] = relevance
            # Calculate an overall relevance score (sum of all trend scores)
            entry['relevance_score'] = sum(relevance.values())
        
        # Sort dialogues by relevance score (highest first)
        trending_dialogues = sorted(
            [entry for entry in caption_entries if entry['relevance_score'] > 0],
            key=lambda x: x['relevance_score'], 
            reverse=True
        )
        
        # Limit results
        trending_dialogues = trending_dialogues[:max_results]
        
        # Format output
        output = "YOUTUBE CAPTION TREND ANALYSIS\n"
        output += "=" * 40 + "\n\n"
        output += f"Video ID: {video_id}\n"
        output += f"Trending Topics: {', '.join(trending_topics[:10])}...\n\n"
        
        if trending_dialogues:
            output += "TRENDING DIALOGUES (in order of relevance):\n"
            output += "=" * 40 + "\n\n"
            
            for i, entry in enumerate(trending_dialogues, 1):
                output += f"{i}. {entry['timestamp']} - Score: {entry['relevance_score']:.2f}\n"
                output += f"   \"{entry['text']}\"\n"
                output += f"   Matching trends: {', '.join(entry['trends'].keys())}\n\n"
        else:
            output += "No dialogues matching current trends were found.\n"
        
        # Output results
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(output)
            print(f"Analysis saved to {output_file}")
            
            # Also save raw data for further processing
            with open(f"{output_file}.json", 'w', encoding='utf-8') as f:
                json.dump({
                    'video_id': video_id,
                    'trending_topics': trending_topics,
                    'trending_dialogues': trending_dialogues
                }, f, ensure_ascii=False, indent=2)
            print(f"Raw data saved to {output_file}.json")
        else:
            print(output)
        
        return trending_dialogues
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return None

if __name__ == "__main__":
    # If run from command line
    if len(sys.argv) > 1:
        video_url = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else None
        download_and_analyze_captions(video_url, output_file)
    else:
        # Interactive mode
        print("YouTube Caption Trend Analyzer")
        print("=============================")
        video_url = input("Enter YouTube video URL: ")
        output_file = input("Enter output file name (leave blank to print to console): ").strip()
        
        if not output_file:
            output_file = None
            
        download_and_analyze_captions(video_url, output_file)