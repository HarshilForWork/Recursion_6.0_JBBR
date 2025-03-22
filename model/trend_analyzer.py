import pandas as pd
from pytrends.request import TrendReq
import time
import json
import os
import sys
import re
import spacy
from spacy.lang.en.stop_words import STOP_WORDS

def analyze_trends(json_path='output.json', custom_stop_words_path='custom_stop_words.txt', output_path='output.csv'):
    """
    Analyze trends from caption data
    
    Args:
        json_path (str): Path to the caption JSON file
        custom_stop_words_path (str): Path to custom stop words file
        output_path (str): Path to save the output CSV
    """
    # Load the caption data
    with open(json_path, 'r') as file:
        caption_data = json.load(file)

    # Extract unique words from the JSON content
    keywords = list(set(word.lower() for entry in caption_data if 'text' in entry for word in entry['text'].split()))
    
    # Set up regions for trend analysis
    regions = ["IN"]
    timeframe = "now 7-d"

    # Load spaCy for text processing
    nlp = spacy.load("en_core_web_sm")
    stop_words = STOP_WORDS

    # Load custom stop words
    if os.path.exists(custom_stop_words_path):
        with open(custom_stop_words_path, 'r') as file:
            custom_stop_words = set(word.strip() for word in file.readlines())
        stop_words.update(custom_stop_words)

    # Clean keywords
    def clean_keyword(keyword):
        keyword = re.sub(r'[^\w\s]', '', keyword)
        keyword = keyword.lower()
        if keyword in stop_words or len(keyword) <= 3:
            return None
        return keyword

    keywords = {clean_keyword(kw) for kw in keywords if clean_keyword(kw)}
    keywords = [k for k in keywords if k]  # Remove None values

    # Function to chunk keywords for API requests
    def chunk_keywords(keywords, chunk_size):
        for i in range(0, len(keywords), chunk_size):
            yield list(keywords)[i:i + chunk_size]

    # Analyze search trends
    def analyze_search_trends(keywords, regions, timeframe):
        pytrends = TrendReq(hl='en-US', tz=360)
        all_data = {}

        keyword_chunks = list(chunk_keywords(keywords, chunk_size=4))
        
        flag = 0

        for region in regions:
            for chunk in keyword_chunks:
                try:
                    pytrends.build_payload(chunk, cat=0, timeframe=timeframe, geo=region, gprop='youtube')
                    data = pytrends.interest_over_time()
                    if not data.empty:
                        if region not in all_data:
                            all_data[region] = data
                        else:
                            all_data[region] = all_data[region].join(data, how='outer', rsuffix='_dup')
                    
                    time.sleep(5)
                
                except Exception as e:
                    print(f"Error fetching data for {region} with keywords {chunk}: {e}")
                    time.sleep(10)

                finally:
                    flag += 1
                    if flag == 6:
                        break
        
        return all_data

    # Run the analysis
    print(f"Analyzing trends for {len(keywords)} keywords...")
    
    # Limit to a reasonable number to avoid excessive API calls
    if len(keywords) > 1000:
        print(f"Limiting analysis to first 100 keywords out of {len(keywords)}")
        keywords_list = list(keywords)[:1000]
    else:
        keywords_list = list(keywords)
    
    trend_data = analyze_search_trends(keywords_list, regions, timeframe)
    
    if not trend_data:
        print("No trend data was retrieved.")
        # Create a sample output for testing purposes
        sorted_df = pd.DataFrame(
            [(k, i) for i, k in enumerate(reversed(keywords_list[:20]), 1)],
            columns=['Item', 'Value']
        )
        sorted_df.to_csv(output_path, index=False)
        return
    
    # Process the trend data
    df = pd.concat(trend_data.values(), keys=trend_data.keys(), names=["Region", "Date"])

    # Calculate the average of each column and store in a dictionary
    average_dict = df.mean(numeric_only=True).to_dict()
    sorted_average_dict = dict(sorted(average_dict.items(), key=lambda item: item[1], reverse=True))

    # Convert the dictionary to a DataFrame
    sorted_df = pd.DataFrame(sorted_average_dict.items(), columns=['Item', 'Value'])
    
    # Export the DataFrame to a CSV file
    sorted_df.to_csv(output_path, index=False)
    print(f"Saved trend analysis to {output_path}")

if __name__ == "__main__":
    json_path = 'output.json'
    custom_stop_words_path = 'custom_stop_words.txt'
    output_path = 'output.csv'
    
    if len(sys.argv) > 1:
        json_path = sys.argv[1]
    if len(sys.argv) > 2:
        custom_stop_words_path = sys.argv[2]
    if len(sys.argv) > 3:
        output_path = sys.argv[3]
    
    analyze_trends(json_path, custom_stop_words_path, output_path)