from nltk.stem import PorterStemmer
from nltk import wordpunct_tokenize
import os

HI_DICT_FILE = os.path.dirname(os.path.abspath(__file__)) + '/dictionaries/inquirerbasicttabsclean.txt'
LIWC_DICT_FILE = os.path.dirname(os.path.abspath(__file__)) + '/dictionaries/LIWC2007dictionarypostermarcelo.csv'

def listContainsVariant(l, word):
	for item in l:
		if item.endswith("*"):
			nItem = item.replace('*','').strip()
			try:
				if word.startswith(nItem):
					return 1
			except:
					pass
		else:
			if item == word:
				return 1
	return 0


def populate_dictionary_index_hi():
	#print "populating dictionary"
	iq = open(HI_DICT_FILE, 'r')
	s=0
	listofEmots=[]
	hgi_dictionary={}
	for line in iq:
		words = line.strip().split('\t')
		if s > 0:
			baseword = words[0].lower()
			baseword = baseword.split("#")[0]
			for item in range(0,len(listofEmots)):
				if len(words) > item:
					if words[item] != '':
						cList =[]
						if listofEmots[item] in hgi_dictionary:
							cList = hgi_dictionary[listofEmots[item]]
						if baseword not in cList:
							cList.append(baseword)
							hgi_dictionary[listofEmots[item]] = cList
		else:
			for word in words:
				listofEmots.append(word)
		s=s+1
	listofEmots = list(set(listofEmots))
	return listofEmots, hgi_dictionary


def populate_dictionary_index_liwc():
	#print "populating dictionary"
	iq = open(LIWC_DICT_FILE, 'r')
	s=0
	listofEmots=[]
	liwcDictionary={}
	for line in iq:
		words = line.strip().split(',')
		if s > 0:
			for item in range(0,len(words)):
				if len(words) > item:
					word = words[item].lower().strip()
					if word!= "":
						cList = []
						if listofEmots[item] in liwcDictionary:
							cList = liwcDictionary[listofEmots[item]]
						if word not in cList:
							cList.append(word)
							liwcDictionary[listofEmots[item]] = cList
		else:
			emotWord = ''
			for word in words:
				if (word!=''):
					emotWord = word
				listofEmots.append(emotWord)
		s=s+1
	listofEmots = list(set(listofEmots))
	return listofEmots, liwcDictionary


def write_to_file(output, listofEmots, wordCount, wordDictionary):
	#print "writing to file"
	for word in listofEmots:
		output.write(word + "\t")
	output.write("\n")
	for emot in listofEmots:
		if emot in wordDictionary:
			output.write(str(float(wordDictionary[emot])) + '\t')
		else:
			output.write("0.0\t")
	output.write(str(wordCount)+'\n')


def process_text(txt, hgi_dictionary, listofEmots, stemmer=PorterStemmer()):
	#print "processing text"
	wordDictionary = {}
	#strstopwords = [str(w).lower() for w in stopwords.words('english')]
	for emot in listofEmots: wordDictionary[emot]=0
	c_text = wordpunct_tokenize(txt)
	base_words = [word.lower() for word in c_text]
	stemmed_words = [stemmer.stem(word.lower()) for word in base_words]
	#non_stop = [word.lower() for word in base_words if word.lower() not in strstopwords]
	no_punct = [word.lower() for word in base_words if word.lower().isalpha()]
	wordCount = 0
	for cWord in no_punct:
		cWord = cWord.lower().strip()
		for emot in listofEmots:
			if emot!='Entry':
				if cWord in hgi_dictionary[emot]:
					emotCount = 0
					if emot in wordDictionary:
						emotCount = wordDictionary[emot]
					emotCount = emotCount +1
					wordDictionary[emot]=emotCount
		wordCount = wordCount + 1
	return wordCount, wordDictionary


if __name__ == '__main__':
	hgi_emots, hgi_dictionary = populate_dictionary_index_hi()
	liwc_emots, liwc_dictionary = populate_dictionary_index_liwc()
	for a in range(10):
		r = raw_input("Input text\n")
		hgi_count, hgi_emot_dict = process_text(r, hgi_dictionary, hgi_emots)
		liwc_count, liwc_emot_dict = process_text(r,liwc_dictionary, liwc_emots)
		print (hgi_count,liwc_count, hgi_emot_dict, liwc_emot_dict)
	#output all of the counts to a file based on listofEmots
