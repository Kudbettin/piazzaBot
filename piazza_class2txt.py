import json

from piazza_api import Piazza

from html.parser import HTMLParser


def main(network, file_name):
	
	with open(file_name, "w") as file:
		# maybe do the stripping here to prevent many function calls?
		file.write("\n".join(questions_to_list(network)))
	



def questions_to_list(network):

	s = MLStripper()

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

