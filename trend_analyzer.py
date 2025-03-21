import pandas as pd
from pytrends.request import TrendReq
import time
import json
with open('output.json', 'r') as file:
    uptownfunk_data = json.load(file)

# Extract unique words from the JSON content
keywords = list(set(word.lower() for entry in uptownfunk_data if 'text' in entry for word in entry['text'].split()))
regions = [
    "IN" 
]
timeframe = "now 7-d"  

import re
from nltk.corpus import stopwords
stop_words = set(stopwords.words('english'))
with open('custom_stop_words.txt', 'r') as file:
    custom_stop_words = set(word.strip() for word in file.readlines())
stop_words.update(custom_stop_words)

def clean_keyword(keyword):
    keyword = re.sub(r'[^\w\s]', '', keyword)
    keyword = keyword.lower()
    if keyword in stop_words or len(keyword) < 2:
        return None
    return keyword

keywords = {clean_keyword(kw) for kw in keywords if clean_keyword(kw)}

def chunk_keywords(keywords, chunk_size):
    """
    Splits a list of keywords into chunks of a specified size.
    
    Args:
        keywords (list): List of keywords to split.
        chunk_size (int): Size of each chunk.
    
    Returns:
        list: List of keyword chunks.
    """
    for i in range(0, len(keywords), chunk_size):
        yield keywords[i:i + chunk_size]

def analyze_search_trends(keywords, regions, timeframe):
    """
    Analyzes search trends for given keywords and regions with delays to avoid rate limits.
    
    Args:
        keywords (list): List of keywords to analyze (up to 5 per request).
        regions (list): List of region codes (e.g., 'US', 'UK').
        timeframe (str): Timeframe for trends (e.g., 'today 5-y').
    
    Returns:
        dict: Trend data for each region.
    """
    pytrends = TrendReq(hl='en-US', tz=360)
    all_data = {}

    keyword_chunks = chunk_keywords(keywords, chunk_size=4)

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


keywords_list = list(keywords)
trend_data = analyze_search_trends(keywords_list, regions, timeframe)

df = pd.concat(trend_data.values(), keys=trend_data.keys(), names=["Region", "Date"])

# Calculate the average of each column and store in a dictionary
average_dict = df.mean(numeric_only=True).to_dict()
sorted_average_dict = dict(sorted(average_dict.items(), key=lambda item: item[1]))

# Convert the dictionary to a DataFrame
sorted_df = pd.DataFrame(sorted_average_dict.items(), columns=['Item', 'Value'])
sorted_df = sorted_df.sort_values(by='Value', ascending=False)

# Export the DataFrame to a CSV file
sorted_df.to_csv('output.csv', index=False)

