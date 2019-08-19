import json

from piazza_api import Piazza

from html.parser import HTMLParser

import pickle


def main(network=None, file_name="cs3169.txt"):

	index2nr = []
	with open(file_name, "w") as file:
		# maybe do the stripping here to prevent many function calls?
		file.write("\n".join(questions_to_list(network, index2nr)))


	with open("index2nr.pkl", "wb") as file:
		pickle.dump(index2nr, file)

	nr2index = [-1 for i in range(max(index2nr) + 1)]

	for index in range(len(index2nr)):
		nr2index[index2nr[index]] = index

	with open("nr2index.pkl", "wb") as file:
		pickle.dump(nr2index, file)



def questions_to_list(network, index2nr):

	s = MLStripper()

	# index2nr = []
	returnable = []
	for post in network.iter_all_posts(limit=None):
		latest_state = post["history"][0]
		# post["subject"] = latest_state["subject"]
		# post["content"] = latest_state["content"]
		children = post["children"]
		i_answer = ""
		s_answer = ""
		for child in children:
				if child["type"] == "i_answer":
					i_answer = child["history"][0]["content"]
				if child["type"] == "s_answer":
					s_answer = child["history"][0]["content"]			
		
		string = s.strip_tags(latest_state["subject"] + " " + latest_state["content"] + " " + i_answer + " " + s_answer + " ").replace("\n", " ")
		# print(string)
		returnable.append(string)
		index2nr.append(int(post["nr"]))
	# print(returnable)
	return returnable


class MLStripper(HTMLParser):
	def __init__(self):
		self.reset()
		self.strict = False
		self.convert_charrefs= True
		self.fed = []
	def handle_data(self, d):
		self.fed.append(d)
	def get_data(self):
		return ''.join(self.fed)

	def strip_tags(self, html):
		self.fed = []
		self.feed(html)
		return self.get_data()


if __name__ == '__main__':
    main()
