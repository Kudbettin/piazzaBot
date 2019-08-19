#Piazza Bot

When run, responds to not yet responed !RecommendMe calls in a Piazza class.

## Issues and TODO

load option for everyhting
	- Currently pickles many things

Everything is stored twice. It's less elegant, but since it doesn't affect the performance due to size of the classes, I can't find the incentive to combine .txt and elasticsearch data


## Resources

become familiar with gensim:
https://www.machinelearningplus.com/nlp/gensim-tutorial/


## Installation

Install LDA Mallet and elasticsearch

pip3 install -r requirements.txt


### Notes and Future work

- Since I only had one account and a number of piazza threads that I could play with, you may get different/unintended results with your credentials

- I excluded how to get network id's. For more information, check piazza api

- Can integrate more rigorous modeling to get more interesting results.

- Can do more visualization (easy pca of the topic vectors for example). However, it's hard to automate sending non-text content. 
	- For this reason pyLDAvis results are not sent. (see lda.html)