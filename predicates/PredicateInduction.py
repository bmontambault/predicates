import json
import os
import uuid
import dill
import subprocess
from .PredicatesRead import PredicatesRead

class PredicateInduction(object):
    
    def __init__(self, data, dtypes, target, score_func, attribute_predicates=None, frontier=None, accepted=None, path=None, background=False, predicate_generator_path=None):
        self.data = data
        self.dtypes = dtypes
        self.target = target
        self.score_func = score_func
        self.attribute_predicates = attribute_predicates
        
        self.predicate_data = {p.__repr__(): {'attribute_mask': p.attribute_mask, 'mask': p.mask} for p in [a for b in self.attribute_predicates.values() for a in b]} if self.attribute_predicates is not None else {}
        self.predicate_score = {}
        self.predicate_res = {}
        
        if frontier is None and self.attribute_predicates is not None:
            self.frontier = sorted([a for b in self.attribute_predicates.values() for a in b], key=lambda x: self.score(x), reverse=True)
        else:
            self.frontier = frontier
        if accepted is None and self.attribute_predicates is not None:
            self.accepted = {i+1: [] for i in range(len(self.attribute_predicates))}
        else:
            self.accepted = accepted
            
        self.background = background
        if self.background:
            self.path = str(uuid.uuid4())
        else:
            self.path = path
        
#         if predicate_generator_path is None:
#             self.predicate_generator_path = os.path.join(site.getsitepackages()[0], 'predicate-generator')
#         else:
#             self.predicate_generator_path = predicate_generator_path
        self.started_search = False
                    
    def score(self, predicate, **kwargs):
        if predicate.__repr__() not in self.predicate_score:
            score, res = self.score_func(self.target, predicate.mask, None, True, **kwargs)
            self.predicate_score[predicate.__repr__()] = score
            self.predicate_res[predicate.__repr__()] = res
        return self.predicate_score[predicate.__repr__()]

    def merge_predicate_attribute_adjacent(self, predicate, adjacent, attribute):
        children = [p for p,p_ in adjacent if self.score(p)>self.score(p_) and self.score(p)>self.score(predicate)]
        return children
    
    def expand_predicate_attribute(self, predicate, attribute):
        adjacent = predicate.get_adjacent_attribute_outer(attribute)
        children = self.merge_predicate_attribute_adjacent(predicate, adjacent, attribute)
        if len(children)>0:
            return self.expand_predicate_attribute(max(children, key=lambda x: self.score(x)), attribute)
        else:
            return predicate
        
    def fit_predicate_attribute(self, predicate, attribute):
        adjacent = predicate.get_adjacent_attribute_inner(attribute) + predicate.get_adjacent_attribute_outer(attribute)
        
        children = self.merge_predicate_attribute_adjacent(predicate, adjacent, attribute)
        if len(children)>0:
            return self.fit_predicate_attribute(max(children, key=lambda x: self.score(x)), attribute)
        else:
            return predicate
    
    def fit_other_attributes(self, predicate, attribute):
        for other_attribute in predicate.attribute_values.keys():
            if predicate.dtypes[other_attribute] != 'nominal':
                predicate = self.fit_predicate_attribute(predicate, other_attribute)
        return predicate
        
    def expand_predicate(self, predicate):
        new_predicates = []
        for k,v in self.attribute_predicates.items():
            if k not in predicate.attribute_values.keys():
                for p in v:
#                     vals = self.data.loc[predicate.mask, k]
#                     values = list(vals.unique()) if self.dtypes[k] == 'nominal' else [vals.min(), vals.max()]
#                     if not p.is_contained_values(values, k):
                    new_predicate = predicate.add_attribute(p, k)
                    if not new_predicate.is_contained_any(new_predicates):
                        if predicate.dtypes[k] != 'nominal':
                            new_predicate = self.expand_predicate_attribute(new_predicate, k)
                        new_predicate = self.fit_other_attributes(new_predicate, k)
                        if self.score(new_predicate) > self.score(predicate):
                            new_predicates.append(new_predicate)
        return new_predicates
    
    def insert_sorted(self, lst, predicate, breadth_first=False):
        if predicate.__repr__() not in self.predicate_data:
            self.predicate_data[predicate.__repr__()] = {
                'attribute_mask': predicate.attribute_mask,
                'mask': predicate.mask
            }

        if len(lst) == 0:
            lst.append(predicate)
            return 1
        score = self.score(predicate)
        for i in range(len(lst)):
            i_score = self.score(lst[i])
            if (score > i_score and not breadth_first) or (score > i_score and len(predicate.attribute_values)<=len(lst[i].attribute_values)):
                lst.insert(i, predicate)
                return i
        lst.append(predicate)
        return len(lst)
    
    def insert_sorted_all(self, lst, predicates, breadth_first=False):
        for predicate in predicates:
            self.insert_sorted(lst, predicate, breadth_first)
    
    def stop(self):
        if hasattr(self, 'worker'):
            self.worker.kill()
    
    def save_predicates(self, predicates, name):
        if not os.path.isdir(self.path):
            os.makedirs(self.path)
        with open(os.path.join(self.path, name+'.json'), 'w') as f:
            predicate_dicts = {i: predicates[i].attribute_values for i in range(len(predicates))}
            json.dump(predicate_dicts, f)        
    
    def save_state(self):
        self.save_predicates(self.frontier, 'frontier')
        for k,v in self.accepted.items():
            self.save_predicates(v, f'accepted_{k}')
    
    def search(self, predicates=None, max_accepted=None, max_steps=None, max_clauses=None, breadth_first=False):        
        self.started_search = True
        if self.background:
            has_predicates = predicates is not None
            has_frontier = self.frontier is not None
            has_accepted = self.accepted is not None
            if has_predicates:
                self.save_predicates(predicates, 'predicates')
            if has_frontier:
                if not self.started_search:
                    self.save_predicates(self.frontier, 'frontier')
                self.frontier = []
            if has_accepted:
                if not self.started_search:
                    for k,v in self.accepted.items():
                        self.save_predicates(v, f'accepted_{k}')
                self.accepted = {i+1: [] for i in range(len(self.attribute_predicates))}
            
            self.started_search = True
            with open(os.path.join(self.path, 'predicate_induction.pkl'), 'wb') as f:
                dill.dump(self, f)
            
            self.worker = subprocess.Popen([
                "python", os.path.join(self.predicate_generator_path, "run.py"),
                str(has_predicates), str(has_frontier), str(has_accepted),
                self.path, str(max_accepted), str(max_steps), str(max_clauses), str(breadth_first)
            ])
            
            self.frontier = PredicatesRead(self.data, self.dtypes, os.path.join(self.path, 'frontier'), self.predicate_data)
            self.accepted = {
                i+1: PredicatesRead(self.data, self.dtypes, os.path.join(self.path, f'accepted_{i+1}'), self.predicate_data) for i in range(len(self.attribute_predicates))
            }
                        
        else:
            num_accepted = 0
            num_steps = 0
            if predicates is not None:
                self.frontier = sorted(predicates, key=lambda x: self.score(x), reverse=True)
            
            while len(self.frontier)>0 and (max_accepted is None or num_accepted<max_accepted) and (max_steps is None or num_steps<max_steps):
                num_steps+=1
                predicate = self.frontier.pop(0)
                for attribute in predicate.predicate_attributes:
                    predicate = self.fit_predicate_attribute(predicate, attribute)
                    
                print('evaluate', predicate, self.score(predicate))
                size = len(predicate.predicate_attributes)
                accepted_could_contain = [a for b in [v for k,v in self.accepted.items() if k>=size] for a in b]
                new_predicates = self.expand_predicate(predicate)
                if not predicate.is_contained_any(accepted_could_contain+self.frontier):                
                    if max_clauses is None or size<max_clauses:
                        if len(new_predicates)>0:
                            self.insert_sorted_all(self.frontier, new_predicates, breadth_first)
                        else:
                            if self.score(predicate)>0:
                                self.insert_sorted(self.accepted[size], predicate)
                                print('accept', predicate, self.score(predicate))
                                                                
                                num_accepted+=1                                
                                if self.path is not None:
                                    self.save_state()
                    else:
                        if self.score(predicate)>0:
                            self.insert_sorted(self.accepted[size], predicate)
                            print('accept', predicate, self.score(predicate))
                            
                            num_accepted+=1  
                            if self.path is not None:
                                self.save_state()
