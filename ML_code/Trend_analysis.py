import json
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from pytrends.request import TrendReq

# Load the transcript JSON
def load_transcript(json_file_path):
    with open(json_file_path, 'r') as file:
        transcript_data = json.load(file)
    
    # Extract and join all text segments
    full_transcript = ' '.join([segment['text'] for segment in transcript_data])
    return full_transcript

# Get trending YouTube searches
def get_youtube_trends(timeframe='now 1-m'):
    # Initialize pytrends
    pytrend = TrendReq(hl='en-US', tz=360)
    
    # Get trending searches on YouTube
    trending_searches = pytrend.trending_searches(pn='united_states',)
    
    # Get trending YouTube searches
    trending_df = pd.DataFrame(trending_searches)
    trending_df.columns = ['keyword']
    
    return trending_df

# Convert text to vectors using TF-IDF
def vectorize_text(transcript_text, trending_keywords):
    # Combine transcript and keywords for vectorization
    all_texts = [transcript_text] + trending_keywords['keyword'].tolist()
    
    # Create TF-IDF vectors
    vectorizer = TfidfVectorizer(stop_words='english', max_features=1000)
    tfidf_matrix = vectorizer.fit_transform(all_texts)
    
    # Split into transcript vector and trending keywords vectors
    transcript_vector = tfidf_matrix[0]
    trend_vectors = tfidf_matrix[1:]
    
    return transcript_vector, trend_vectors, vectorizer.get_feature_names_out()

# Calculate vector similarities
def calculate_similarities(transcript_vector, trend_vectors, trending_keywords):
    # Calculate cosine similarity between transcript and each trending keyword
    similarities = cosine_similarity(transcript_vector, trend_vectors).flatten()
    
    # Create a DataFrame with similarities
    similarity_df = pd.DataFrame({
        'keyword': trending_keywords['keyword'],
        'similarity_score': similarities
    })
    
    # Sort by similarity in descending order
    sorted_similarity_df = similarity_df.sort_values(by='similarity_score', ascending=False)
    
    return sorted_similarity_df

# Main function to analyze transcript and trends
def analyze_transcript_trend_similarity(json_file_path='lalal.json'):
    # Load transcript
    print("Loading transcript...")
    transcript_text = load_transcript(json_file_path)
    
    # Get YouTube trends
    print("Fetching YouTube trends...")
    trending_keywords = get_youtube_trends()
    
    # Convert to vectors
    print("Vectorizing text...")
    transcript_vector, trend_vectors, feature_names = vectorize_text(transcript_text, trending_keywords)
    
    # Calculate similarities
    print("Calculating similarities...")
    similarity_results = calculate_similarities(transcript_vector, trend_vectors, trending_keywords)
    
    # Print top similar trends
    print("\nTop trending search terms most similar to your transcript:")
    print(similarity_results.head(10))
    
    # Return for further analysis
    return similarity_results, transcript_text, trending_keywords, feature_names

# Run the analysis
if __name__ == "__main__":
    results, transcript, trends, features = analyze_transcript_trend_similarity()
    
    # Additional analysis: Find which words from the transcript contribute most to the similarity
    top_trend = trends.iloc[results.index[0]]['keyword']
    print(f"\nTop matching trend: {top_trend}")
    
    # Extract key words that might be driving the similarity
    vectorizer = TfidfVectorizer(stop_words='english')
    combined_vector = vectorizer.fit_transform([transcript, top_trend])
    feature_names = vectorizer.get_feature_names_out()
    
    # Get important terms from transcript
    transcript_features = combined_vector[0].toarray()[0]
    top_indices = transcript_features.argsort()[-10:][::-1]
    
    print("\nKey terms in your transcript that may be driving similarity:")
    for idx in top_indices:
        if transcript_features[idx] > 0:
            print(f"- {feature_names[idx]}: {transcript_features[idx]:.4f}")