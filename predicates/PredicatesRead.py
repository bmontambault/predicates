from collections.abc import Sequence
import json
from .Predicate import Predicate

class PredicatesRead(Sequence):
    
    def __init__(self, data, dtypes, path, predicate_data):
        self.data = data
        self.dtypes = dtypes
        self.path = path
        self.predicate_data = predicate_data
        self.predicates = []
        super().__init__()
        
    def update(self):
        with open(self.path+'.json', 'r') as f:
            predicates_dicts = list(json.load(f).values())
        self.predicates = [Predicate(attribute_values=predicate_dict) for predicate_dict in predicates_dicts]
        
        for predicate in self.predicates:
            predicate.set_data(
                self.data, self.dtypes,
                attribute_mask=self.predicate_data.get(predicate.__repr__(),{}).get('attribute_mask'),
                mask=self.predicate_data.get(predicate.__repr__(),{}).get('mask')
            )
        
    def __repr__(self):
        self.update()
        return self.predicates.__repr__()
    
    def __getitem__(self, i):
        self.update()
        return self.predicates[i]
    
    def __len__(self):
        return len(self.predicates)
