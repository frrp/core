#import nltk
#nltk.download('vader_lexicon')
import time
import pickle
import numpy as np
import praw
import pandas as pd
import logging
import requests
import tweepy
from abc import ABC, abstractmethod
from collections import namedtuple
from nltk.sentiment.vader import SentimentIntensityAnalyzer as SIA
from bs4 import BeautifulSoup
from tweepy import OAuthHandler
from apps.sentiment.models.nn_sentiment import load_model_and_tokenizer, predict_sentiment
from settings import SENTIMENT_TWITTER_CONSUMER_KEY, SENTIMENT_TWITTER_CONSUMER_SECRET, SENTIMENT_TWITTER_ACCESS_TOKEN, \
    SENTIMENT_TWITTER_ACCESS_TOKEN_SECRET, SENTIMENT_REDDIT_CLIENT_ID, SENTIMENT_REDDIT_CLIENT_SECRET, SENTIMENT_REDDIT_USER_AGENT
from apps.common.utilities.s3 import download_file_from_s3
from settings import LOCAL
from keras.models import load_model

logging.getLogger().setLevel(logging.INFO)

ForumTopic = namedtuple('ForumTopic', 'headline comments')
Score = namedtuple('Score', 'positive neutral negative compound')


class SentimentDataSource(ABC):

    def __init__(self):
        pass

    @property
    def topics(self):
        return self._topics

    @property
    def topic_headlines(self):
        return self._topic_headlines

    @abstractmethod
    def retrieve_data(self):
        pass


class Subreddit(SentimentDataSource):

    def __init__(self, subreddit, max_topics=None, get_top=False, time_filter='day'):
        self.reddit = praw.Reddit(client_id=SENTIMENT_REDDIT_CLIENT_ID,
                                  client_secret=SENTIMENT_REDDIT_CLIENT_SECRET,
                                  user_agent=SENTIMENT_REDDIT_USER_AGENT)
        self.subreddit = subreddit
        self.max_topics = max_topics
        self.get_top = get_top
        self.time_filter = time_filter

    def retrieve_data(self):
        self._topics = []
        self._topic_headlines = []

        if self.get_top:
            submissions = self.reddit.subreddit(self.subreddit).top(time_filter=self.time_filter, limit=self.max_topics)
        else:
            submissions = self.reddit.subreddit(self.subreddit).new(limit=self.max_topics)

        for submission in submissions:
            logging.info(f'Processing submission {submission.title}...')
            comments = []
            submission.comments.replace_more(limit=0)
            for top_level_comment in submission.comments:
               comments.append(top_level_comment.body)
            self._topics.append(ForumTopic(headline=submission.title, comments=comments))
            self._topic_headlines.append(submission.title)


class Bitcointalk(SentimentDataSource):

    def __init__(self, url):
        self.url = url

    def retrieve_data(self):
        self._topics = []
        self._topic_headlines = []

        soup = self._get_bs_parser(self.url)
        if soup is None:
            return

        # find all spans
        spans = soup.find_all('span')
        for span in spans:
            if str(span).startswith('<span id="msg_'):
                # print(f'{span} {span.next_element}')
                topic_link = span.next_element
                topic_link_url = topic_link['href']
                topic_title = topic_link.text
                logging.info(f'Processing topic {topic_title}...')
                time.sleep(5) # sleep 5 seconds so Bitcointalk doesn't drop us...
                small = topic_link.next_element.next_element.next_element  # parsing is an ugly thing
                if str(small).startswith('<small id="pages'):  # we have more than one topic page, find the last one
                    topic_links = small.find_all('a')
                    if len(topic_links) >= 2:
                        topic_link = topic_links[-2]
                        topic_link_url = topic_link['href']
                comments = self._fetch_posts(topic_link_url)
                topic = ForumTopic(topic_title, comments)
                self._topics.append(topic)
                self._topic_headlines.append(topic_title)

    def _get_bs_parser(self, url):
        r = requests.get(url)
        if r.status_code != 200:
            logging.warning(f'Unable to connect to {url}, status code {r.status_code}')
            return None
        return BeautifulSoup(r.text)


    def _fetch_posts(self, topic_link_url):
        posts = []
        soup = self._get_bs_parser(topic_link_url)
        data = soup.find_all('div', attrs={'class': 'post'})
        for div in data:
            for child in list(div.children):
                if isinstance(child, str) and not child.isdigit():
                    posts.append(child)
        return posts


class Twitter(SentimentDataSource):

    def __init__(self, search_query, num_tweets_to_retrieve):
        consumer_key = SENTIMENT_TWITTER_CONSUMER_KEY
        consumer_secret = SENTIMENT_TWITTER_CONSUMER_SECRET
        access_token = SENTIMENT_TWITTER_ACCESS_TOKEN
        access_token_secret = SENTIMENT_TWITTER_ACCESS_TOKEN_SECRET

        self.search_query = search_query
        self.num_tweets_to_retrieve = num_tweets_to_retrieve

        try:
            self.auth = OAuthHandler(consumer_key, consumer_secret)
            self.auth.set_access_token(access_token, access_token_secret)
            self.api = tweepy.API(self.auth)
        except Exception as e:
            logging.error(f'Authentication failed: {str(e)}')

    def retrieve_data(self):
        self._topics = []
        self._topic_headlines = []

        try:
            tweets = self.api.search(q=self.search_query, count=self.num_tweets_to_retrieve, lang='en', result_type='popular')
            retained_tweets = set([tweet.text for tweet in tweets])
            self._topic_headlines = list(retained_tweets)
            self._topics = [ForumTopic(headline, []) for headline in self._topic_headlines]
        except tweepy.TweepError as e:
            logging.error(f'Could not retrieve tweets: {str(e)}')



class SentimentAnalyzer(ABC):

    def __init__(self, sentiment_data_source):
        self.sentiment_data_source = sentiment_data_source
        if sentiment_data_source is not None:
            self.update()

    @abstractmethod
    def _calculate_score(self, text):
        pass

    def calculate_score_stats(self, texts, score_function):
        scores = []
        for text in texts:
            scores.append(score_function(text))
        return Score(*np.nanmean(scores, axis=0))

    def calculate_headline_score(self, topic):
        return self._calculate_score(topic.headline)

    def calculate_aggregated_comment_score(self, topic):
        if len(topic.comments) == 0:
            return Score(np.nan, np.nan, np.nan, np.nan)
        return self.calculate_score_stats(topic.comments, self._calculate_score)

    def calculate_current_mean_headline_sentiment(self):
        return self.calculate_score_stats(self.sentiment_data_source.topic_headlines, self._calculate_score)

    def calculate_current_mean_topic_sentiment(self):
        return self.calculate_score_stats(self.sentiment_data_source.topics, self.calculate_aggregated_comment_score)

    def update(self):
        self.sentiment_data_source.retrieve_data()

    def to_dataframe(self):
        rows = []
        for topic in self.sentiment_data_source.topics:
            headline_score = self.calculate_headline_score(topic)
            comment_score = self.calculate_aggregated_comment_score(topic)
            rows.append({
                'headline': topic.headline,
                'headline_positive': headline_score.positive,
                'headline_neutral': headline_score.neutral,
                'headline_negative': headline_score.negative,
                'headline_compound': headline_score.compound,
                'comment_positive': comment_score.positive,
                'comment_neutral': comment_score.neutral,
                'comment_negative': comment_score.negative,
                'comment_compound': comment_score.compound
            })

        return pd.DataFrame.from_records(rows)


class VaderSentimentAnalyzer(SentimentAnalyzer):

    def __init__(self, sentiment_data_source):
        super(VaderSentimentAnalyzer, self).__init__(sentiment_data_source)
        self.vader = SIA()

    def _calculate_score(self, text):
        score = self.vader.polarity_scores(text)
        return Score(positive=score['pos'], neutral=score['neu'],
                     negative=score['neg'], compound=score['compound'])


class LSTMSentimentAnalyzer(SentimentAnalyzer):
    model = None
    tokenizer = None

    def __init__(self, sentiment_data_source):
        super(LSTMSentimentAnalyzer, self).__init__(sentiment_data_source)
        if self.model is None or self.tokenizer is None:
            if not LOCAL:
                self.model, self.tokenizer = load_model_and_tokenizer_from_s3()
            else:
                self.model, self.tokenizer = load_model_and_tokenizer()

    def _calculate_score(self, text):
        weights = predict_sentiment(text, self.model, self.tokenizer)
        return Score(positive=weights[1], neutral=np.nan,
                     negative=weights[0], compound=np.nan)


def load_model_and_tokenizer_from_s3():
    model_filename = 'sentiment_lstm_model.h5'
    tokenizer_filename = 'sentiment_tokenizer.pkl'
    try:
        download_file_from_s3(model_filename)
        model = load_model('sentiment_lstm_model.h5')
    except Exception as e:
        logging.error(f'Unable to load sentiment model: {str(e)}')

    try:
        download_file_from_s3(tokenizer_filename)
        with open(tokenizer_filename, 'rb') as handle:
            tokenizer = pickle.load(handle)
    except Exception as e:
        logging.error(f'Unable to load sentiment tokenizer: {str(e)}')

    return model, tokenizer


def vader_vs_lstm(text):
    vader = VaderSentimentAnalyzer(None)
    lstm = LSTMSentimentAnalyzer(None)
    vader_score = vader._calculate_score(text)
    lstm_score = lstm._calculate_score(text)

    print(f'Vader:\n    {vader_score.positive*100:.2f}% positive, {vader_score.negative*100:.2f}% negative, '
          f'{vader_score.neutral*100:.2f}% neutral, {vader_score.compound*100:.2f}% compound')

    print(f'LSTM:\n    {lstm_score.positive*100:.2f}% positive, {lstm_score.negative*100:.2f}% negative')




