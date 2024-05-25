#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
from math import log
import re


# In[ ]:


def initDictionary():
    # Build a cost dictionary, assuming Zipf's law and cost = -math.log(probability).
    words = open("wiki125k-words.txt").read().split()
    wordcost = dict((k, log((i+1)*log(len(words)))) for i,k in enumerate(words))
    maxword = max(len(x) for x in words)
    return wordcost,maxword
wordcost,maxword=initDictionary()


# In[ ]:


'''
Code to split unspaced words into a space separated string
Can be useful for labels defined with no space or irregular spaces
Code source: https://stackoverflow.com/questions/8870261/how-to-split-text-without-spaces-into-list-of-words
Wordlist: http://controlc.com/c1666a6b
'''

def infer_spaces(s,wordcost=wordcost,maxword=maxword):
    """Uses dynamic programming to infer the location of spaces in a string
    without spaces."""
    s=s.lower()
    # Regular expression to remove all but alphanumeric characters
    # Reference: https://www.techiedelight.com/remove-non-alphanumeric-characters-string-python/
    s = re.sub(r'[^a-zA-Z0-9]', '', s)
    
    
    # Find the best match for the i first characters, assuming cost has
    # been built for the i-1 first characters.
    # Returns a pair (match_cost, match_length).
    def best_match(i):
        candidates = enumerate(reversed(cost[max(0, i-maxword):i]))
        return min((c + wordcost.get(s[i-k-1:i], 9e999), k+1) for k,c in candidates)

    # Build the cost array.
    cost = [0]
    for i in range(1,len(s)+1):
        c,k = best_match(i)
        cost.append(c)

    # Backtrack to recover the minimal-cost string.
    out = []
    i = len(s)
    while i>0:
        c,k = best_match(i)
        assert c == cost[i]
        out.append(s[i-k:i])
        i -= k
    
    spacedString=" ".join(reversed(out))
    
    return spacedString

