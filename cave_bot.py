import pickle
import numpy as np
import sys

from piazza_api import Piazza

from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from elasticsearch_dsl import Search

import refined_lda
import piazza_class2txt


class CaveBot():
	def __init__(self, username, password, network_id, network_name):
		self.p = Piazza()
		self.p.user_login(username, password)

		self.user_profile = self.p.get_user_profile()
		self.network = self.p.network(network_id)
		self.network_name = network_name

		self.es = Elasticsearch()
		self.s = Search(using=self.es, index=self.network_name)
		self.jobs = []
		self.es_index_name = network_name

		self.index2nr = None
		self.nr2index = None
		self.corpus, self.lda_model, self.id2word, self.cleaned_documents = None, None, None, None

		self.topic_vectors = None
	


		bulk(self.es, self.index_all_with_recommendations())


		#  For debugging purposes and room for future play, reread every post, put into a .txt file and let lda use that.
		piazza_class2txt.main(self.network, "cs3169.txt")

		with open("index2nr.pkl", "rb") as file:
			self.index2nr = pickle.load(file)

		with open("nr2index.pkl", "rb") as file:
			self.nr2index = pickle.load(file)


		self.num_topics = 3
		self.train_iter = 50
		self.corpus, self.lda_model, self.id2word, self.cleaned_documents = refined_lda.main("cs3169.txt", num_topics=self.num_topics, iterations=self.train_iter)

		self.recommend()


	def main():
		if len(sys.argv) != 5:
			print("Usage: python3 cave_bot.py username password network_id network_name")

		bot = CaveBot(*sys.argv[1:])



	# Recommends once per post, responds to parent answers only
	def index_all_with_recommendations(self):
		for post in self.network.iter_all_posts(limit=None):
			trigger = False
			latest_state = post["history"][0]
			if "!RecommendMe" in latest_state["subject"] or "!RecommendMe" in latest_state["content"]:
				trigger = True
		
			# Doesn't look for its children
			for child in post["children"]:
				# felt cleaner than child.get
				if "history" in child:
					if "!RecommendMe" in child["history"][0]["content"]:
						trigger = True
					if "!@#$" in child["history"][0]["content"][:7]:
						trigger = False
						break
				else:
					if "!RecommendMe" in child["subject"]:
						trigger = True
					if "!@#$" in child["subject"][:7]:
						trigger = False
						break

			if trigger:
				self.jobs.append(post)

			i_answer = ""
			s_answer = ""
			for child in post["children"]:
					if child["type"] == "i_answer":
						i_answer = child["history"][0]["content"]
					if child["type"] == "s_answer":
						s_answer = child["history"][0]["content"]	

			yield {
					"_op_type": "index",
					"_index": self.es_index_name,
					"_id": post["nr"],
					"_source": {
						"subject": latest_state["subject"],
						"content": latest_state["content"],
						"i_answer": i_answer,
						"s_answer": s_answer,
						"responded": trigger
					}
			}

	
	def recommend(self, debug=True): # default to true to not accidentally post
		for post in self.jobs:
			response = "!@#$\n"
			# response = str(recommend_with_mlt(search, post)) + "\n"
			# print(int(post["nr"])-1, len(corpus))
			# # response += "Topic of this post: " + str(lda_model[corpus[int(post["nr"])-2]])
			topic = self.topic_of(self.nr2index[post["nr"]])
			response += "Topic of this post: " + str(topic) + "\n"
			# response += "Topic contents " + str(self.lda_model.show_topic(topic)) + "\n"

			response += "Contributive contents: " + str(["(" + pair[0] + ", " + str(pair[1])[:4] + ")" for pair in self.lda_model.show_topic(topic)]) + "\n"


			# # #may be useful for debugging
			# # response += str([id2word[id_[0]] for id_ in corpus[int(post["nr"])-2]])
			# response += "Post number: " + str(post["nr"]) + "\n"
			# response += "Post content: " + post["history"][0]["content"] + "\n"
			# response += str([self.id2word[id_[0]] for id_ in self.corpus[self.nr2index[post["nr"]]]])
			# response += "\n\n"
			# # response += str(self.get_posts_with_same_best_topic(post["nr"], topic)) + "\n"

			response += "Posts with same topic: " + str(self.get_posts_with_same_topic(post["nr"], topic))


			if not debug:
				result = network.create_followup(post["children"][1], response) # both nr and entire post works
			else:
				print("#### Start Post ####")
				print(response)
				print("#### End Post ####")
				print("train_iter, num_topics: ", self.train_iter, self.num_topics)


	# deprecated and bad
	def get_posts_with_same_best_topic(self, post_number, target_topic, num_docs = 3):
		# do one up one down
		docs = []
		looked = 0
		while len(docs) < 3 or looked > 100:
			looked += 1
			nrs = [post_number + looked, post_number - looked]
			for nr in nrs:
				if nr in self.nr2index and nr != -1 and self.topic_of(self.nr2index[nr]) == target_topic:
					docs.append("@" + str(nr))

		return docs[:num_docs]


	# extra atrocious
	def get_posts_with_same_topic(self, number, target_topic, num_docs = 3):
		self.get_topic_vectors()
		vector = self.topic_vectors[self.nr2index[number]]

		min_dists = [float("inf") for i in range(num_docs+1)]
		min_indices = [0 for i in range(num_docs+1)]
		for i in range(len(self.topic_vectors)):
			distance = np.sqrt(np.sum((vector - self.topic_vectors[i])**2, 0))
			if distance < max(min_dists):
				i_md = min_dists.index(max(min_dists))
				print(i, distance)
				min_dists[i_md] = distance
				min_indices[i_md] = i
				

		posts = ["@" + str(self.index2nr[i]) for i in min_indices]
		posts.remove("@"+str(number)) # no need to recommend the same post
		return posts


	def topic_of(self, document):
		topics = [topic for index, topic in self.lda_model[self.corpus[document]]]
		return topics.index(max(topics))


	def get_topic_vectors(self):
		docs_topics = []

		for i in range(len(self.corpus)):
			doc_topics = self.lda_model.get_document_topics(self.corpus[i])
			if len(doc_topics) == self.num_topics:
				docs_topics.append(np.array([component[1] for component in doc_topics])) 
			else:
				topics = []
				d_pop = doc_topics.pop(-1)
				for i in range(self.num_topics-1, -1, -1):
					if i != d_pop[0] or len(doc_topics) == 0:
						topics.append(0)
					else:
						topics.append(d_pop[1])
						d_pop = doc_topics.pop(-1)
				topics.reverse()
				docs_topics.append(np.array(topics))

		self.topic_vectors = docs_topics


	def recommend_with_mlt(self, post, score_limit=0):
		latest_state = post["history"][0]
		# Can do post likelyhood later
		search_text = latest_state["subject"] + latest_state["content"]

		# maybe static this later
		mlt_query = {
			"more_like_this": {
				"fields": ["subject", "content", "i_answer", "s_answer"],
				"like": search_text,
				"min_term_freq": 1,
				"min_doc_freq": 1,
				"max_query_terms": 50,
				# "term_vector": "with_positions_offsets"
			}
		}

		recommendation = []
		docs = s.query(mlt_query).execute()
		
		for doc in docs:
			if int(doc.meta["id"]) != int(post["nr"]) and doc.meta["score"] > score_limit:
				recommendation.append((doc.meta["id"], doc.meta["score"]))

		return recommendation


	def change_network(self, network_id):
		self.network = self.p.network(network_id)
		self.s = Search(using=self.es, index=self.network_name)
		self.es_index_name = network_name


if __name__ == '__main__':
	CaveBot.main()

