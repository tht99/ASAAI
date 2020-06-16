from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel
from model import reader
from nltk.stem.porter import PorterStemmer
import util, nltk, string
from database import dbfetch
import numpy as np

#The first part of the recommendation system
#Where the system calculates the similarities between each title using Tf-idf tokenized with nltk and cosine similarities
#Since the project is real time recommendation, it is wise not to redo
#The only time this file is called is when the bot upload a new title, the matrix needs to be recalculated again
#The executioni time is not too bad, around 30 seconds for 200 titles
class Engine():
    matrix = []
    def __init__(self):
        #initialize the weight of each similarity and max features for tokenizer
        self.WEIGHT_NAME = 0.1
        self.WEIGHT_PRODUCER = 0.2
        self.WEIGHT_DESCRIPTION = 0.1
        self.WEIGHT_TAGS = 0.6
        self.WEIGHT_TOTAL = self.WEIGHT_NAME + self.WEIGHT_PRODUCER + self.WEIGHT_DESCRIPTION + self.WEIGHT_TAGS
        self.max_features = 1000
        
    def preprocess(self, lst):
        #preprocess the data by turning to lowercase and removing punctuation
        return [x.lower().replace("[0-9]",'num ').translate(str.maketrans('', '', string.punctuation)) for x in lst]
    
    def tf_idf_transform(self, tf, lst):
        #return cosine similarities from tf idf
        arr = tf.fit_transform(lst)
        return linear_kernel(arr,arr)
        
    def train(self, path):
        #where the training is done
        #firstly, it needs to get the data from database
        #luckily, pandas support reading from sqlite to Dataframe so the steps aren't that hard
        #read from sqlite to dataframe
        if path is None:
            return "Path not defined"
        query = "SELECT id, name, transName, producer, description FROM AnimeModel"
        rd = reader.Reader(path)
        rd.readsqlite(path, query)
        
        #add column tags as string 
        idlist = rd.getColumn('id')
        tagList = [' '.join(util.jsonTags(dbfetch.getTag(i))) for i in idlist] #join with ''
        nameList = [' '.join([m,n]) for m, n in zip(rd.getColumn('name'),rd.getColumn('transName'))]
        nameReady = self.preprocess(nameList)
        descriptionReady = self.preprocess([x for x in rd.getColumn('description')])
        producerReady = self.preprocess([x for x in rd.getColumn('producer')])
        
        #
        tf = TfidfVectorizer(tokenizer = self.tokenizer, max_features = self.max_features)
        nametf = np.array(self.tf_idf_transform(tf, nameReady))
        destf = np.array(self.tf_idf_transform(tf, descriptionReady))
        prodtf = np.array(self.tf_idf_transform(tf, producerReady))
        tagtf = np.array(self.tf_idf_transform(tf, tagList))
        #final cosine similarity matrix
        total_similarity = np.round((destf*self.WEIGHT_DESCRIPTION + nametf*(self.WEIGHT_NAME) + prodtf*self.WEIGHT_PRODUCER + tagtf*self.WEIGHT_TAGS)*100/self.WEIGHT_TOTAL,5)
        for i in range(0,len(total_similarity)):
            #add 2 term into array, id and score
            #score join every value in np array with ',' 
            dbfetch.updateRecommendation(i + 1,(','.join(str(x) for x in total_similarity[i])))
        #print('COMPLETED')
    def tokenizer(self, text):
        words = nltk.word_tokenize(text)    
        ps = PorterStemmer()
        return [ps.stem(w) for w in words]
    
newTrainModel = Engine()
newTrainModel.train(dbfetch.DB)
