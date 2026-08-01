from nltk.stem import PorterStemmer
from nltk import wordpunct_tokenize
from collections import Counter
import os
import logging

HI_DICT_FILE = os.path.dirname(os.path.abspath(__file__)) + '/dictionaries/inquirerbasicttabsclean.txt'
LIWC_DICT_FILE = os.path.dirname(os.path.abspath(__file__)) + '/dictionaries/LIWC2007dictionarypostermarcelo.csv'

CUSTOM_SUMMARIES = {

    # 1. Cognitive / reasoning contribution
    "analytical_thinking": {
        "CogMech": 0.30,
        "Insight": 0.25,
        "Cause": 0.20,
        "Certain": 0.10,
        "Tentat": 0.05,
        "Prep": 0.05,
        "Conj": 0.05,
    },

    # 2. Reflection on prior ideas/events
    "reflection": {
        "Insight": 0.45,
        "Past": 0.35,
        "CogMech": 0.20,
    },

    # 3. task_focus
    "task_focus": {
        "Work": 0.40,
        "Achiev": 0.30,
        "CogMech": 0.20,
        "Numbers": 0.10
    },

    # 4. Confidence / clout / leadership
    "clout": {
        "Certain": 0.35,
        "Achiev": 0.20,
        "Assent": 0.15,
        "We": 0.15,
        "Work": 0.15
    },

    # 5. Uncertainty / confusion
    "uncertainty_confusion": {
        "Tentat": 0.35,
        "Discrep": 0.30,
        "Anx": 0.20,
        "Negate": 0.15,
    },

	"certainty": {
		"Certain": 0.50,
		"Assent": 0.20,
		"Achiev": 0.15,
		"Tentat": -0.10,
		"Discrep": -0.05
	},

    # 6. Collaboration / coordination / social engagement
    "collaborative_coordination": {
        "Social": 0.30,
        "We": 0.30,
        "Assent": 0.15,
        "Friends": 0.10,
        "Family": 0.05,
        "Conj": 0.10,
    },

    # 7. Other-oriented attention
    "social_attention": {
        "You": 0.40,
        "They": 0.30,
        "SheHe": 0.30,
    },

    # 8. Self-disclosure / authenticity
    "authenticity": {
        "I": 0.35,
        "Ppron": 0.25,
        "Pronoun": 0.10,
        "Affect": 0.15,
        "Anx": 0.07,
        "Sad": 0.05,
        "Posemo": 0.03,
    },

    # 9. Positive emotional climate
    "positive_climate": {
        "Posemo": 0.65,
        "Assent": 0.25,
        "Affect": 0.10,
    },

    # 10. Negative climate / conflict
    "negative_conflict_climate": {
        "Negemo": 0.30,
        "Anger": 0.25,
        "Sad": 0.15,
        "Anx": 0.10,
        "Discrep": 0.10,
        "Negate": 0.10,
    },

    # 11. Emotional expressiveness
    "emotional_expressiveness": {
        "Affect": 0.50,
        "Posemo": 0.25,
        "Negemo": 0.25,
    },

    # 12. Disfluency / hesitation signal
    "disfluency_signal": {
        "Nonflu": 0.60,
        "Filler": 0.40,
    },
}

COMPOSITE_LIWC_INDICES = {
    "analytical_thinking": [
        "Article", "Prep", "CogMech", "Insight", "Cause", "Certain"
    ],
	"Narrative_thinking": [
    "I",
    "Ppron",
    "AuxVb",
    "Adverbs",
    "Conj",
    "Negate"
    ],

    "clout": [
        "Certain", "Assent", "Achiev", "We"
    ],
	"no_clout":[
		"Tentat",
        "Anx"
    ],

    "authenticity": [
        "I", "Ppron", "Affect", "Negemo", "Anx", "Sad"
    ],

    "positive_climate": [
        "Posemo", "Assent", "Affect"
    ],

    "negative_conflict_climate": [
        "Negemo", "Anger", "Sad", "Anx", "Negate"
    ],

    "collaborative_coordination": [
        "Social", "We", "Assent"
    ],

    "social_attention": [
        "You", "They", "SheHe"
    ],

    "disfluency_signal": [
        "Nonflu", "Filler"
    ],
	"task_focus" : [
        "Work",
        "Achiev",
        "CogMech",
        "Cause",
        "Insight",
    ],
	"certainty": [
		"Certain",
		"Assent"
    ],
	"uncertainty":[
		"Tentat",
        "Discrep",
        "Negate"
    ]
	
} 

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

def get_value(features, key):
    """
    Safely get LIWC category value.
    """
    return float(features.get(key, 0.0))


def weighted_score(features, weights):
    """
    Compute weighted custom construct score.
    """
    score = 0.0

    for category, weight in weights.items():
        score += get_value(features, category) * weight

    return score


def weighted_score_normalized(features, weights):
    raw_score = sum(
        get_value(features, category) * weight
        for category, weight in weights.items()
    )

    max_score = 100 * sum(weights.values())

    return raw_score / max_score if max_score > 0 else 0.0

def weighted_average(features, weights):
    numerator = 0.0
    denominator = 0.0

    for category, weight in weights.items():
        value = features.get(category, 0.0)

        if value > 0:
            numerator += value * weight
            denominator += weight

    if denominator == 0:
        return 0.0

    return round(numerator / denominator, 2)

def mean_liwc_index(features, categories, decimals=2):
    values = [float(features.get(cat, 0.0)) for cat in categories]

    if not values:
        return 0.0

    return round(sum(values) / len(values), decimals)

def balance_index(positive, negative):
    total = positive + negative
    if total == 0:
        return 0.5  # no evidence either way
    return positive / total

def confidence_score(features, weights):
    """
    Confidence score based on:
    1. How many expected LIWC categories are present
    2. Word count adequacy
    3. Dictionary coverage

    This is not statistical confidence.
    It is a reliability/coverage indicator.
    """
    expected_categories = list(weights.keys())

    present = sum(
        1 for category in expected_categories
        if get_value(features, category) > 0
    )

    category_coverage = present / len(expected_categories)

    word_count = get_value(features, "word_count")

    if word_count >= 100:
        word_count_score = 1.0
    elif word_count >= 50:
        word_count_score = 0.75
    elif word_count >= 25:
        word_count_score = 0.50
    elif word_count >= 10:
        word_count_score = 0.25
    else:
        word_count_score = 0.10

    dictionary_coverage = min(get_value(features, "dictionary_coverage"), 1.0)

    confidence = (
        0.50 * category_coverage +
        0.30 * word_count_score +
        0.20 * dictionary_coverage
    )

    return round(confidence, 3)

def window_confidence_score(liwc_features):
    """
    One confidence score per transcript/window.

    Based on:
    1. word count adequacy
    2. LIWC dictionary coverage
    3. average coverage of categories used across all summaries

    This is a reliability score, not statistical confidence.
    """

    word_count = float(liwc_features.get("word_count", 0))
    dictionary_coverage = float(liwc_features.get("dictionary_coverage", 0))

    if word_count >= 100:
        word_count_score = 1.0
    elif word_count >= 50:
        word_count_score = 0.75
    elif word_count >= 25:
        word_count_score = 0.50
    elif word_count >= 10:
        word_count_score = 0.25
    else:
        word_count_score = 0.10

    all_categories = set()

    for weights in CUSTOM_SUMMARIES.values():
        all_categories.update(weights.keys())

    present_categories = sum(
        1 for category in all_categories
        if float(liwc_features.get(category, 0)) > 0
    )

    category_coverage = (
        present_categories / len(all_categories)
        if len(all_categories) > 0
        else 0
    )

    confidence = (
        0.45 * word_count_score +
        0.35 * min(dictionary_coverage, 1.0) +
        0.20 * category_coverage
    )

    return round(confidence, 3)



def extract_liwc_categories(text,liwc_dictionary, liwc_emots):
    """
    Extract LIWC category percentages from text.
    """
    detected_category_counts = Counter()
    liwc_emot_feature = {}
    total_words_count, liwc_emot = process_text(text,liwc_dictionary, liwc_emots)
    for category, cat_count in liwc_emot.items():
        if cat_count > 0:
            detected_category_counts[category] = cat_count
            liwc_emot_feature[category] = (cat_count / total_words_count) * 100
        else:
            liwc_emot_feature[category] = 0.0    

    liwc_emot_feature["word_count"] = total_words_count
    liwc_emot_feature["dictionary_coverage"] = (
        sum(detected_category_counts.values()) / total_words_count if total_words_count > 0 else 0.0
    )
    # logging.info("liwc_emot_feature : {0}".format(liwc_emot_feature))
    return liwc_emot_feature


if __name__ == '__main__':
	hgi_emots, hgi_dictionary = populate_dictionary_index_hi()
	liwc_emots, liwc_dictionary = populate_dictionary_index_liwc()
	for a in range(10):
		r = raw_input("Input text\n")
		hgi_count, hgi_emot_dict = process_text(r, hgi_dictionary, hgi_emots)
		liwc_count, liwc_emot_dict = process_text(r,liwc_dictionary, liwc_emots)
		print (hgi_count,liwc_count, hgi_emot_dict, liwc_emot_dict)
	#output all of the counts to a file based on listofEmots
