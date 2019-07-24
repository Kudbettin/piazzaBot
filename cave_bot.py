import json

from piazza_api import Piazza

from elasticsearch import Elasticsearch

from elasticsearch.helpers import bulk
from elasticsearch_dsl import Search

from gensim.models import LdaMulticore
import pickle
import refined_lda
import piazza_class2txt

INDEX_NAME = "your_class_index_name"
jobs = []

def main():
	p = Piazza()
	p.user_login("your_id", "your_password")

	es = Elasticsearch()
	

	user_profile = p.get_user_profile()

	csxx = p.network('your_network_id')
	

	bulk(es, index_all_with_recommendations(csxx))

	#  For debugging purposes and room for future play, reread every post, put into a .txt file and let lda use that.
	piazza_class2txt.main(csxx, "csxx.txt")

	corpus, lda_model, id2word = refined_lda.main("csxx.txt", num_topics = 6, iterations=50)

	s = Search(using=es, index=INDEX_NAME)
	recommend(csxx, jobs, s, lda_model, corpus)





# Recommends once per post, responds to parent answers only
def index_all_with_recommendations(network):
	for post in network.iter_all_posts(limit=None):
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
			jobs.append(post)

		i_answer = ""
		s_answer = ""
		for child in post["children"]:
				if child["type"] == "i_answer":
					i_answer = child["history"][0]["content"]
				if child["type"] == "s_answer":
					s_answer = child["history"][0]["content"]	

		yield {
				"_op_type": "index",
				"_index": INDEX_NAME,
				"_id": post["nr"],
				"_source": {
					"subject": latest_state["subject"],
					"content": latest_state["content"],
					"i_answer": i_answer,
					"s_answer": s_answer,
					"responded": trigger
				}
		}




def topic_of(lda_model, corpus, document):
    topics = [topic for index, topic in lda_model[corpus[document]]]
    return topics.index(max(topics))

def recommend(network, posts, search, lda_model, corpus):
	
	for post in posts:
		response = str(recommend_with_mlt(search, post))
		print(int(post["nr"])-1, len(corpus))
		response += "Topic of this post: " + str(topic_of(lda_model, corpus, int(post["nr"])-2))
		
		network.create_followup(post["children"][1], response) # both nr and entire post works


def recommend_with_mlt(s, post, score_limit=0):
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


def index_question(es, post):
	latest_state = post["history"][0]
	children = post["children"]
	i_answer = ""
	s_answer = ""
	for child in children:
			if child["type"] == "i_answer":
				i_answer = child["history"][0]["content"]
			if child["type"] == "s_answer":
				s_answer = child["history"][0]["content"]			
	es.create(
			index=INDEX_NAME,
			id=post["nr"],
			body={
				"subject": latest_state["subject"],
				"content": latest_state["content"],
				"i_answer": i_answer,
				"s_answer": s_answer
			}
		)
	print("Indexed post number: {}".format(post["nr"]))



def index_questions(network):

	for post in network.iter_all_posts(limit=None):
		latest_state = post["history"][0]
		children = post["children"]
		i_answer = ""
		s_answer = ""
		for child in children:
				if child["type"] == "i_answer":
					i_answer = child["history"][0]["content"]
				if child["type"] == "s_answer":
					s_answer = child["history"][0]["content"]			
		yield {
				"_op_type": "index",
				"_index": INDEX_NAME,
				"_id": post["nr"],
				"_source": {
					"subject": latest_state["subject"],
					"content": latest_state["content"],
					"i_answer": i_answer,
					"s_answer": s_answer
				}
		}



if __name__ == '__main__':
	main()


