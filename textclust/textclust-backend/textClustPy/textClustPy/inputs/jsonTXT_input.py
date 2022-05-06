from abc import ABC, abstractmethod

import sys
import json

import string
import time

from datetime import datetime

from .inputs import Input
from .inputs import Observation

## implementation of abstract class
class JsonTXTInput(Input):
    """
    This class implements the a json input

    :param  jsonfile: Relative path and filename of the json document
    :type csvfile:  string
    :param col_id: Field name that contains the text id 
    :type col_id: int
    :param col_time:Field name that contains the time
    :type col_time: int
    :param col_text: Field name that contains the text
    :type col_text: int
    :param col_label: Field name that contains the true cluster belonging
    :type col_label: int 
    """


    def __init__(self, jsonfiles, lang, **kwargs):
        
        super().__init__(**kwargs)

        self.lang = lang

        ## preload file
        print("preload file")
        
        for file in jsonfiles:
            self.reader = open(file, 'r')

            self.run()

    def run(self):
        '''
        Update the textclust algorithm with the complete data in the data frame
        '''
        for obj in self.reader:

            obj = json.loads(obj)
            if self.lang is not None:
                if self.lang != obj.get("lang", None):
                    continue

            try:
                text = obj["extended_tweet"]["full_text"]
            except KeyError:
                text = obj["text"]

            _id  = obj["id_str"]
            time = obj["@timestamp"]
            time = datetime.strptime(time, "%Y-%m-%dT%H:%M:%S.%fZ")
            time = time.strftime("%Y-%m-%d %H:%M:%S")

            data    = Observation(text, _id, time, None, json.dumps(obj))
            self.processdata(data)
                
               
    
    def update(self, n):
        '''
        Update the textclust algorithm on new observations 
        
        :param n: Number of observations that should be used by textclust
        :type n: int 
        '''
        for i in range(0,n):
            obj     = json.loads((next(self.reader)))
            text    = obj[self.col_text]
            _id     = obj[self.col_id]
            time    = obj[self.col_time]
            label   = obj[self.col_label] or None

            data = Observation(text, _id, time, label, obj)

            self.processdata(data)


    def fetch_from_stream(self, n):
        data = []
        for i in range(0, n):
            obj    = json.loads((next(self.reader)))
            text    = obj[self.col_text]
            _id     = obj[self.col_id]
            time    = obj[self.col_time]
            label   = obj[self.col_label] or None

            data.append(Observation(text, _id, time, label, obj))
        return data

