import re
import numpy as np

# Gensim
import gensim
import gensim.corpora as corpora
from gensim.utils import simple_preprocess
from gensim.models import CoherenceModel

# spacy for lemmatization
import spacy

# Plotting tools
import pyLDAvis
import pyLDAvis.gensim  # don't skip this
import matplotlib.pyplot as plt

from nltk.corpus import stopwords
from pathlib import Path

import pickle

import piazza_class2txt
# Enable logging for gensim - optional
import logging
logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.ERROR)

import warnings
warnings.filterwarnings("ignore",category=DeprecationWarning)

def main(file_name, num_topics=26, write=True, ret=True, iterations=1000):
	with open(file_name, "r") as file:
		raw_data = [d for d in file.readlines()]

	cleaned_documents = clean(raw_data)

		# Create Dictionary
	id2word = corpora.Dictionary(cleaned_documents)

	# Term Document Frequency
	corpus = [id2word.doc2bow(doc) for doc in cleaned_documents]


	# path depends on mallet installation
	p = Path("./mallet-2.0.8/bin/mallet")

	# mallet_path = '/Mallet/bin/mallet' # update this path
	ldamallet = gensim.models.wrappers.LdaMallet(str(p), corpus=corpus, num_topics=num_topics, id2word=id2word, iterations=iterations)
	lda_model = gensim.models.wrappers.ldamallet.malletmodel2ldamodel(ldamallet)

	vis = pyLDAvis.gensim.prepare(lda_model, corpus, id2word)
	pyLDAvis.save_html(vis, 'lda.html')

	if write:
		lda_model.save("lda_mallet.model")

		with open("corpus.txt", "wb") as file:
			pickle.dump(corpus, file)
		with open("id2word.txt", "wb") as file:
			pickle.dump(id2word, file)
		with open("cleaned_documents.txt", "wb") as file:
			pickle.dump(cleaned_documents, file)

	if ret:
		return corpus, lda_model, id2word, cleaned_documents


def clean(raw_data):
	#TODO add mark down stopwords
	stop_words = stopwords.words("english")
	# stop_words.extend(["[" + str(i) + "]" for i in range(12)])
	# stop_words.extend(["one", "two", "three", "four", "five", "six", "seven", "eight", "nine"])

	# Remove new line characters
	data = [re.sub('\s+', ' ', sent) for sent in raw_data]

	data_words = [gensim.utils.simple_preprocess(str(sentence), deacc=True) for sentence in data]

	# Remove Stop Words
	data_words_nostops = [[word for word in doc if word not in stop_words] for doc in data_words]
	# data_words_nostops = [[word for word in simple_preprocess(str(doc)) if word not in stop_words] for doc in data_words]


	# Build the bigram model
	bigram = gensim.models.Phrases(data_words, min_count=5, threshold=100) # higher threshold fewer phrases.

	# Faster way to get a sentence clubbed as a bigram
	bigram_mod = gensim.models.phrases.Phraser(bigram)

	# Form Bigrams
	data_words_bigrams = [bigram_mod[doc] for doc in data_words_nostops]

	# Initialize spacy 'en' model, keeping only tagger component (for efficiency)
	# python3 -m spacy download en
	nlp = spacy.load('en', disable=['parser', 'ner'])

	# Do lemmatization keeping only noun, adj, vb, adv
	allowed_postags = ['NOUN', 'ADJ', 'VERB', 'ADV']
	data_lemmatized = []
	for sent in data_words_bigrams:
		doc = nlp(" ".join(sent)) 
		data_lemmatized.append([token.lemma_ for token in doc if token.pos_ in allowed_postags])

	return data_lemmatized





if __name__ == '__main__':
	main()